from llvmlite import ir

from ast2 import Type
from codegen import expression, type_utils


def generate_assign(self, node):
    # Use get_variable instead of directly accessing self.variables
    ptr = self.get_variable(node.name)
    if not ptr:
        raise ValueError(f"Variable {node.name} not declared")

    var_type = self.variable_types.get(node.name)
    var_type = Type.map_to_internal_type(var_type)

    value = expression.generate_expression(self, node.value)

    if var_type == Type.STRING:
        if not hasattr(self, 'strcpy'):
            strcpy_ty = ir.FunctionType(ir.PointerType(ir.IntType(8)),
                                        [ir.PointerType(ir.IntType(8)), ir.PointerType(ir.IntType(8))])
            self.strcpy = ir.Function(self.module, strcpy_ty, name="strcpy")

        dest_ptr = self.builder.bitcast(ptr, ir.PointerType(ir.IntType(8)))
        self.builder.call(self.strcpy, [dest_ptr, value])
    else:
        value = type_utils.convert_if_needed(self, value, var_type)
        self.builder.store(value, ptr)


def generate_declare_assign(self, node):
    if node.type == Type.STRING:
        buffer = self.builder.alloca(ir.ArrayType(ir.IntType(8), 256), name=node.name)
        ptr = self.builder.bitcast(buffer, ir.PointerType(ir.IntType(8)))
        # Store in scope system
        self.declare_variable(node.name, buffer)
        # Also keep in global tracking for type information
        self.variables[node.name] = buffer
        self.variable_types[node.name] = node.type

        if node.value:
            value = expression.generate_expression(self, node.value)

            if not hasattr(self, 'strcpy'):
                strcpy_ty = ir.FunctionType(ir.PointerType(ir.IntType(8)),
                                            [ir.PointerType(ir.IntType(8)), ir.PointerType(ir.IntType(8))])
                self.strcpy = ir.Function(self.module, strcpy_ty, name="strcpy")

            self.builder.call(self.strcpy, [ptr, value])
    else:
        internal_type = Type.map_to_internal_type(node.type)
        llvm_type = Type.get_ir_type(internal_type)
        ptr = self.builder.alloca(llvm_type, name=node.name)
        # Store in scope system
        self.declare_variable(node.name, ptr)
        # Also keep in global tracking for type information
        self.variables[node.name] = ptr
        self.variable_types[node.name] = internal_type

        if node.value:
            value = expression.generate_expression(self, node.value)
            value = type_utils.convert_if_needed(self, value, internal_type)
            self.builder.store(value, ptr)
