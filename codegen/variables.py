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
    # If this is a var declaration, infer the type from the value
    if node.type_name == Type.VAR and node.value is not None:
        node.type_name = Type.infer_type_from_value(node.value)

    if node.type_name == Type.STRING:
        # For strings, we need to allocate memory for the string
        string_ptr = self.builder.alloca(ir.PointerType(ir.IntType(8)))
        if node.value is not None:
            # If there's an initial value, create a global string constant
            string_data = bytearray(str(node.value.value) + "\0", "utf8")
            string_arr_ty = ir.ArrayType(ir.IntType(8), len(string_data))
            string_global = ir.GlobalVariable(self.module, string_arr_ty, name=f"str_{node.name}")
            string_global.initializer = ir.Constant(string_arr_ty, string_data)
            string_global.global_constant = True
            string_ptr_val = self.builder.bitcast(string_global, ir.PointerType(ir.IntType(8)))
            self.builder.store(string_ptr_val, string_ptr)
        else:
            # If no initial value, store null
            self.builder.store(ir.Constant(ir.PointerType(ir.IntType(8)), None), string_ptr)
        self.declare_variable(node.name, string_ptr, node.type_name)
    else:
        # For other types, allocate memory based on the type
        var_type = Type.get_ir_type(node.type_name)
        var_ptr = self.builder.alloca(var_type)
        if node.value is not None:
            value = expression.generate_expression(self, node.value)
            # Convert value to the correct type if needed
            value = type_utils.convert_if_needed(self, value, node.type_name)
            self.builder.store(value, var_ptr)
        self.declare_variable(node.name, var_ptr, node.type_name)
