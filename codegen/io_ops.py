from llvmlite import ir

from ast2 import Type
from codegen import expression, type_utils


def generate_print(self, node):
    value = expression.generate_expression(self, node.expression)

    if hasattr(node.expression, 'name'):
        type_name = self.get_variable_type(node.expression.name)
    elif hasattr(node.expression, 'array_element_types') and hasattr(node.expression, 'name'):
        element_type = self.array_element_types.get(node.expression.name)
        type_name = element_type if element_type else type_utils.get_type_from_value(value)
    else:
        type_name = type_utils.get_type_from_value(value)

    type_name = Type.map_to_internal_type(type_name)

    if not self.printf:
        printf_ty = ir.FunctionType(ir.IntType(32), [ir.PointerType(ir.IntType(8))], var_arg=True)
        self.printf = ir.Function(self.module, printf_ty, name="printf")

    if type_name == Type.STRING:
        fmt_ptr = get_print_format(self, "%s\n\0", "format_str_string")
        if hasattr(node.expression, 'name') and self.get_variable_type(node.expression.name + "_ptr") == Type.STRING:
            str_ptr = self.get_variable(node.expression.name + "_ptr")
            self.builder.call(self.printf, [fmt_ptr, str_ptr])
        else:
            self.builder.call(self.printf, [fmt_ptr, value])
    elif type_name == Type.BOOL:
        if not hasattr(self, 'true_str'):
            true_data = bytearray("true\0", "utf8")
            true_arr_ty = ir.ArrayType(ir.IntType(8), len(true_data))
            self.true_str = ir.GlobalVariable(self.module, true_arr_ty, name="true_str")
            self.true_str.initializer = ir.Constant(true_arr_ty, true_data)
            self.true_str.global_constant = True

            false_data = bytearray("false\0", "utf8")
            false_arr_ty = ir.ArrayType(ir.IntType(8), len(false_data))
            self.false_str = ir.GlobalVariable(self.module, false_arr_ty, name="false_str")
            self.false_str.initializer = ir.Constant(false_arr_ty, false_data)
            self.false_str.global_constant = True

        true_ptr = self.builder.bitcast(self.true_str, ir.PointerType(ir.IntType(8)))
        false_ptr = self.builder.bitcast(self.false_str, ir.PointerType(ir.IntType(8)))
        bool_str = self.builder.select(value, true_ptr, false_ptr)

        fmt_ptr = get_print_format(self, "%s\n\0", "format_str_bool")
        self.builder.call(self.printf, [fmt_ptr, bool_str])
    elif "int" in type_name:
        fmt_ptr = get_print_format(self, "%d\n\0", "format_str_int")
        self.builder.call(self.printf, [fmt_ptr, value])
    elif "float" in type_name:
        if type_name in [Type.FLOAT16, Type.FLOAT32]:
            value = self.builder.fpext(value, ir.DoubleType())
        fmt_ptr = get_print_format(self, "%.49f\n\0", "format_str_float")
        self.builder.call(self.printf, [fmt_ptr, value])


def get_print_format(self, fmt_str, name):
    fmt_arr = bytearray(fmt_str, "utf8")
    fmt_type = ir.ArrayType(ir.IntType(8), len(fmt_arr))
    fmt_var = self.builder.alloca(fmt_type, name=name)
    self.builder.store(ir.Constant(fmt_type, fmt_arr), fmt_var)
    return self.builder.bitcast(fmt_var, ir.PointerType(ir.IntType(8)))


def generate_read(self, node):
    if not self.scanf:
        scanf_ty = ir.FunctionType(ir.IntType(32), [ir.PointerType(ir.IntType(8))], var_arg=True)
        self.scanf = ir.Function(self.module, scanf_ty, name="scanf")

    ptr = self.get_variable(node.name)
    if not ptr:
        raise ValueError(f"Variable {node.name} not declared")

    type_name = self.get_variable_type(node.name)
    if type_name == Type.STRING:
        ptr = self.builder.bitcast(ptr, ir.PointerType(ir.IntType(8)))

    fmt_str = "%d\0" if "int" in type_name else "%lf\0" if "float" in type_name else "%s\0"
    fmt_arr = bytearray(fmt_str, "utf8")
    fmt_type = ir.ArrayType(ir.IntType(8), len(fmt_arr))

    fmt_var = self.builder.alloca(fmt_type, name="fmt")
    self.builder.store(ir.Constant(fmt_type, fmt_arr), fmt_var)

    fmt_ptr = self.builder.bitcast(fmt_var, ir.PointerType(ir.IntType(8)))

    self.builder.call(self.scanf, [fmt_ptr, ptr])
