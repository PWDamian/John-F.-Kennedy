from llvmlite import ir

from codegen import expression


def generate_if(self, node):
    cond_value = expression.generate_expression(self, node.condition)

    if not isinstance(cond_value.type, ir.IntType) or cond_value.type.width != 1:
        if isinstance(cond_value.type, ir.IntType):
            zero = ir.Constant(cond_value.type, 0)
            cond_value = self.builder.icmp_signed('!=', cond_value, zero)
        elif isinstance(cond_value.type, (ir.FloatType, ir.DoubleType, ir.HalfType)):
            zero = ir.Constant(cond_value.type, 0)
            cond_value = self.builder.fcmp_ordered('!=', cond_value, zero)
        else:
            cond_value = self.builder.trunc(cond_value, ir.IntType(1))

    then_block = self.func.append_basic_block(name="if_then")
    else_block = self.func.append_basic_block(name="if_else") if node.else_body else None
    end_block = self.func.append_basic_block(name="if_end")

    self.builder.cbranch(cond_value, then_block, else_block if else_block else end_block)

    self.builder.position_at_end(then_block)
    self.push_scope()
    for stmt in node.body:
        self.generate_node(stmt)
    self.pop_scope()

    if not self.builder.block.is_terminated:
        self.builder.branch(end_block)

    if else_block:
        self.builder.position_at_end(else_block)
        self.push_scope()
        for stmt in node.else_body:
            self.generate_node(stmt)
        self.pop_scope()
        self.builder.branch(end_block)

    self.builder.position_at_end(end_block)


def generate_for(self, node):
    self.generate_node(node.init)

    cond_block = self.func.append_basic_block(name="for_cond")
    body_block = self.func.append_basic_block(name="for_body")
    update_block = self.func.append_basic_block(name="for_update")
    end_block = self.func.append_basic_block(name="for_end")

    self.builder.branch(cond_block)

    self.builder.position_at_end(cond_block)
    cond_value = expression.generate_expression(self, node.condition)

    if isinstance(cond_value.type, ir.IntType):
        zero = ir.Constant(cond_value.type, 0)
        cond_value = self.builder.icmp_signed('!=', cond_value, zero)
    elif isinstance(cond_value.type, (ir.FloatType, ir.DoubleType, ir.HalfType)):
        zero = ir.Constant(cond_value.type, 0)
        cond_value = self.builder.fcmp_ordered('!=', cond_value, zero)

    self.builder.cbranch(cond_value, body_block, end_block)

    self.builder.position_at_end(body_block)
    self.push_scope()
    for stmt in node.body:
        self.generate_node(stmt)
    self.pop_scope()
    self.builder.branch(update_block)

    self.builder.position_at_end(update_block)
    self.generate_node(node.update)
    self.builder.branch(cond_block)

    self.builder.position_at_end(end_block)
