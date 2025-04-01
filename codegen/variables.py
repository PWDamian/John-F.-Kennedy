from llvmlite import ir

from ast2 import Type
from codegen import expression, type_utils


def generate_assign(self, node):
    ptr = self.get_variable(node.name)
    if not ptr:
        raise ValueError(f"Variable {node.name} not declared")

    var_type = self.get_variable_type(node.name)
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
    is_global = self.func is None or self.func.name == "main" and len(self.scopes) == 1

    if node.type == Type.STRING:
        if is_global:
            string_type = ir.ArrayType(ir.IntType(8), 256)
            global_var = ir.GlobalVariable(self.module, string_type, name=node.name)
            global_var.initializer = ir.Constant(string_type, bytearray(256))  # Initialize to zero
            global_var.linkage = 'common'

            self.declare_variable(node.name, global_var, Type.STRING)

            if node.value:
                value = expression.generate_expression(self, node.value)

                if not hasattr(self, 'strcpy'):
                    strcpy_ty = ir.FunctionType(ir.PointerType(ir.IntType(8)),
                                                [ir.PointerType(ir.IntType(8)), ir.PointerType(ir.IntType(8))])
                    self.strcpy = ir.Function(self.module, strcpy_ty, name="strcpy")

                ptr = self.builder.bitcast(global_var, ir.PointerType(ir.IntType(8)))
                self.builder.call(self.strcpy, [ptr, value])
        else:
            buffer = self.builder.alloca(ir.ArrayType(ir.IntType(8), 256), name=node.name)
            ptr = self.builder.bitcast(buffer, ir.PointerType(ir.IntType(8)))
            self.declare_variable(node.name, buffer, node.type)

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

        if is_global:
            global_var = ir.GlobalVariable(self.module, llvm_type, name=node.name)

            if node.value:
                value = expression.generate_expression(self, node.value)
                value = type_utils.convert_if_needed(self, value, internal_type)
                if isinstance(value, ir.Constant):
                    global_var.initializer = value
                else:
                    global_var.initializer = ir.Constant(llvm_type, 0)
                    self.builder.store(value, global_var)
            else:
                global_var.initializer = ir.Constant(llvm_type, 0)

            self.declare_variable(node.name, global_var, internal_type)
        else:
            ptr = self.builder.alloca(llvm_type, name=node.name)
            self.declare_variable(node.name, ptr, internal_type)

            if node.value:
                value = expression.generate_expression(self, node.value)
                value = type_utils.convert_if_needed(self, value, internal_type)
                self.builder.store(value, ptr)
