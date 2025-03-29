from llvmlite import ir

from codegen import expression, type_utils


def generate_lazy_and(self, node, op_id):
    result_ptr = self.builder.alloca(ir.IntType(1), name=f"and_result_ptr_{op_id}")

    left = expression.generate_expression(self, node.left)

    if not isinstance(left.type, ir.IntType) or left.type.width != 1:
        left = type_utils.to_boolean(self, left)

    eval_right_block = self.func.append_basic_block(name=f"and_eval_right_{op_id}")
    merge_block = self.func.append_basic_block(name=f"and_merge_{op_id}")

    current_block = self.builder.block

    self.builder.cbranch(left, eval_right_block, merge_block)

    self.builder.position_at_end(eval_right_block)
    right = expression.generate_expression(self, node.right)
    if not isinstance(right.type, ir.IntType) or right.type.width != 1:
        right = type_utils.to_boolean(self, right)
    right_block = self.builder.block
    self.builder.branch(merge_block)

    self.builder.position_at_end(merge_block)

    phi = self.builder.phi(ir.IntType(1), name=f"and_phi_{op_id}")
    phi.add_incoming(ir.Constant(ir.IntType(1), 0), current_block)
    phi.add_incoming(right, right_block)

    self.builder.store(phi, result_ptr)

    return self.builder.load(result_ptr, name=f"and_result_{op_id}")


def generate_lazy_or(self, node, op_id):
    result_ptr = self.builder.alloca(ir.IntType(1), name=f"or_result_ptr_{op_id}")

    left = expression.generate_expression(self, node.left)

    if not isinstance(left.type, ir.IntType) or left.type.width != 1:
        left = type_utils.to_boolean(self, left)

    eval_right_block = self.func.append_basic_block(name=f"or_eval_right_{op_id}")
    merge_block = self.func.append_basic_block(name=f"or_merge_{op_id}")

    current_block = self.builder.block

    self.builder.cbranch(left, merge_block, eval_right_block)

    self.builder.position_at_end(eval_right_block)
    right = expression.generate_expression(self, node.right)
    if not isinstance(right.type, ir.IntType) or right.type.width != 1:
        right = type_utils.to_boolean(self, right)
    right_block = self.builder.block
    self.builder.branch(merge_block)

    self.builder.position_at_end(merge_block)

    phi = self.builder.phi(ir.IntType(1), name=f"or_phi_{op_id}")
    phi.add_incoming(ir.Constant(ir.IntType(1), 1), current_block)
    phi.add_incoming(right, right_block)

    self.builder.store(phi, result_ptr)

    return self.builder.load(result_ptr, name=f"or_result_{op_id}")


def generate_direct_logical_op(self, node, op_func):
    left = expression.generate_expression(self, node.left)
    right = expression.generate_expression(self, node.right)

    if not isinstance(left.type, ir.IntType) or left.type.width != 1:
        left = type_utils.to_boolean(self, left)

    if not isinstance(right.type, ir.IntType) or right.type.width != 1:
        right = type_utils.to_boolean(self, right)

    return op_func(left, right)
