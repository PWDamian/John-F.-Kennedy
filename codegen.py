import random
import uuid
from enum import nonmember

from llvmlite import ir

from ast_1 import Type, AssignNode, DeclareAssignNode, PrintNode, ReadNode, NumberNode, VariableNode, BinaryOpNode, StringValueNode


class CodeGenerator:
    def __init__(self):
        self.module = ir.Module(name="JohnFKennedy")
        self.module.triple = "x86_64-pc-linux-gnu"
        self.builder = None
        self.func = None
        self.variables = {}
        self.variable_types = {}
        self.printf = None
        self.scanf = None
        self.format_str_int = None
        self.format_str_float = None
        self.format_str_string = None
        self.scan_format_int = None
        self.scan_format_float = None
        self.scan_format_string = None

    def generate_code(self, ast):
        self._create_main_function()
        for node in ast:
            try:
                self._generate_node(node)
            except Exception as e:
                if None not in [node.line, node.column]:
                    print(f"Error at {node.line}:{node.column}:")
                else:
                    print(node)
                print(f"\tMessage: {str(e)}")
                exit(1)
        self.builder.ret(ir.Constant(ir.IntType(32), 0))

    def _create_main_function(self):
        func_type = ir.FunctionType(ir.IntType(32), [])
        self.func = ir.Function(self.module, func_type, name="main")
        block = self.func.append_basic_block(name="entry")
        self.builder = ir.IRBuilder(block)

    def _generate_node(self, node):
        if isinstance(node, AssignNode):
            self._generate_assign(node)
        elif isinstance(node, DeclareAssignNode):
            self._generate_declare_assign(node)
        elif isinstance(node, PrintNode):
            self._generate_print(node)
        elif isinstance(node, ReadNode):
            self._generate_read(node)

    def _generate_declare_assign(self, node):
        llvm_type = Type.get_ir_type(node.type)
        ptr = self.builder.alloca(llvm_type, name=node.name)
        self.variables[node.name] = ptr
        self.variable_types[node.name] = node.type
        if node.value:
            value = self._generate_expression(node.value)
            value = self._convert_if_needed(value, node.type)
            self.builder.store(value, ptr)

    def _generate_assign(self, node):
        ptr = self.variables.get(node.name)
        if not ptr:
            raise ValueError(f"Variable {node.name} not declared")
        value = self._generate_expression(node.value)
        type_name = self.variable_types.get(node.name)
        value = self._convert_if_needed(value, type_name)
        self.builder.store(value, ptr)

    def _generate_print(self, node):
        value = self._generate_expression(node.expression)
        type_name = self._get_type_from_value(value)

        if not self.printf:
            printf_ty = ir.FunctionType(ir.IntType(32), [ir.PointerType(ir.IntType(8))], var_arg=True)
            self.printf = ir.Function(self.module, printf_ty, name="printf")

        if "int" in type_name:
            if not self.format_str_int:
                format_data = bytearray("%d\n\0", "utf8")
                format_arr_ty = ir.ArrayType(ir.IntType(8), len(format_data))
                self.format_str_int = ir.GlobalVariable(self.module, format_arr_ty, name="format_str_int")
                self.format_str_int.initializer = ir.Constant(format_arr_ty, format_data)
                self.format_str_int.global_constant = True
            fmt_ptr = self.builder.bitcast(self.format_str_int, ir.PointerType(ir.IntType(8)))
        elif "float" in type_name:
            if not self.format_str_float:
                format_data = bytearray("%f\n\0", "utf8")
                format_arr_ty = ir.ArrayType(ir.IntType(8), len(format_data))
                self.format_str_float = ir.GlobalVariable(self.module, format_arr_ty, name="format_str_float")
                self.format_str_float.initializer = ir.Constant(format_arr_ty, format_data)
                self.format_str_float.global_constant = True
            fmt_ptr = self.builder.bitcast(self.format_str_float, ir.PointerType(ir.IntType(8)))
        else:
            if not self.format_str_string:
                format_data = bytearray("%s\n\0", "utf8")
                format_arr_ty = ir.ArrayType(ir.IntType(8), len(format_data))
                self.format_str_string = ir.GlobalVariable(self.module, format_arr_ty, name="format_str_string")
                self.format_str_string.initializer = ir.Constant(format_arr_ty, format_data)
                self.format_str_string.global_constant = True
            fmt_ptr = self.builder.bitcast(self.format_str_string, ir.PointerType(ir.IntType(8)))

        self.builder.call(self.printf, [fmt_ptr, value])

    def _generate_read(self, node):
        if not self.scanf:
            scanf_ty = ir.FunctionType(ir.IntType(32), [ir.PointerType(ir.IntType(8))], var_arg=True)
            self.scanf = ir.Function(self.module, scanf_ty, name="scanf")

        ptr = self.variables.get(node.name)
        if not ptr:
            raise ValueError(f"Variable {node.name} not declared")

        type_name = self.variable_types.get(node.name)
        if "int" in type_name:
            if not self.scan_format_int:
                scan_data = bytearray("%d\0", "utf8")
                scan_arr_ty = ir.ArrayType(ir.IntType(8), len(scan_data))
                self.scan_format_int = ir.GlobalVariable(self.module, scan_arr_ty, name="scan_format_int")
                self.scan_format_int.initializer = ir.Constant(scan_arr_ty, scan_data)
                self.scan_format_int.global_constant = True
            fmt_ptr = self.builder.bitcast(self.scan_format_int, ir.PointerType(ir.IntType(8)))
        elif "float" in type_name:
            if not self.scan_format_float:
                scan_data = bytearray("%lf\0", "utf8")
                scan_arr_ty = ir.ArrayType(ir.IntType(8), len(scan_data))
                self.scan_format_float = ir.GlobalVariable(self.module, scan_arr_ty, name="scan_format_float")
                self.scan_format_float.initializer = ir.Constant(scan_arr_ty, scan_data)
                self.scan_format_float.global_constant = True
            fmt_ptr = self.builder.bitcast(self.scan_format_float, ir.PointerType(ir.IntType(8)))
        else:
            if not self.scan_format_string:
                scan_data = bytearray("%s\0", "utf8")
                scan_arr_ty = ir.ArrayType(ir.IntType(8), len(scan_data))
                self.scan_format_string = ir.GlobalVariable(self.module, scan_arr_ty, name="scan_format_string")
                self.scan_format_string.initializer = ir.Constant(scan_arr_ty, scan_data)
                self.scan_format_string.global_constant = True
            fmt_ptr = self.builder.bitcast(self.scan_format_string, ir.PointerType(ir.IntType(8)))

        self.builder.call(self.scanf, [fmt_ptr, ptr])

    def _generate_expression(self, node):
        if isinstance(node, NumberNode):

            if node.type == Type.INT8:
                return ir.Constant(ir.IntType(8), node.value)
            elif node.type == Type.INT16:
                return ir.Constant(ir.IntType(16), node.value)
            elif node.type == Type.INT32:
                return ir.Constant(ir.IntType(32), node.value)
            elif node.type == Type.INT:
                return ir.Constant(ir.IntType(64), node.value)
            elif node.type == Type.FLOAT16:
                return ir.Constant(ir.HalfType(), node.value)
            elif node.type == Type.FLOAT32:
                return ir.Constant(ir.FloatType(), node.value)
            elif node.type == Type.FLOAT:
                return ir.Constant(ir.DoubleType(), node.value)
            else:
                raise ValueError(f"Unsupported type in expr gen: {node.type}")
        elif isinstance(node, VariableNode):
            ptr = self.variables.get(node.name)
            if not ptr:
                raise ValueError(f"Variable {node.name} not declared")
            return self.builder.load(ptr, name=node.name)
        elif isinstance(node, BinaryOpNode):
            left = self._generate_expression(node.left)
            right = self._generate_expression(node.right)
            left_type = self._get_type_from_value(left)
            right_type = self._get_type_from_value(right)
            result_type = Type.get_common_type(left_type, right_type)
            left = self._convert_if_needed(left, result_type)
            right = self._convert_if_needed(right, result_type)

            if result_type == Type.INT:
                return {
                    '+': self.builder.add,
                    '-': self.builder.sub,
                    '*': self.builder.mul,
                    '/': self.builder.sdiv
                }[node.op](left, right, name="int_op")
            else:
                return {
                    '+': self.builder.fadd,
                    '-': self.builder.fsub,
                    '*': self.builder.fmul,
                    '/': self.builder.fdiv
                }[node.op](left, right, name="float_op")
        elif isinstance(node, StringValueNode):
            string_data = bytearray(node.value + "\0", "utf8")
            string_arr_ty = ir.ArrayType(ir.IntType(8), len(string_data))
            string_const = ir.GlobalVariable(self.module, string_arr_ty, name=str(uuid.uuid4()))
            string_const.initializer = ir.Constant(string_arr_ty, string_data)
            string_const.global_constant = True
            return self.builder.bitcast(string_const, ir.PointerType(ir.IntType(8)))

    def _get_type_from_value(self, value):
        if value.type is ir.IntType(8):
            return Type.INT8
        elif value.type is ir.IntType(16):
            return Type.INT16
        elif value.type is  ir.IntType(32):
            return Type.INT32
        elif value.type is  ir.IntType(64):
            return Type.INT
        elif value.type is  ir.HalfType():
            return Type.FLOAT16
        elif value.type is ir.FloatType():
            return Type.FLOAT32
        elif value.type is ir.DoubleType():
            return Type.FLOAT
        elif isinstance(value.type, ir.PointerType) and value.type.pointee == ir.IntType(8):
            return Type.STRING
        else:
            raise ValueError(f"Unknown LLVM type: {value.type}")

    def _convert_if_needed(self, value, target_type):
        source_type = self._get_type_from_value(value)
        if source_type == target_type:
            return value
        if "int" in source_type and "float" in target_type:
            return self.builder.sitofp(value, Type.get_ir_type(target_type), name="int_to_float")
        elif "int" in target_type and "float" in source_type:
            return self.builder.fptosi(value, Type.get_ir_type(target_type), name="float_to_int")
        elif "float" in target_type and "float" in source_type:
            ttype = Type.get_common_type(source_type, target_type)
            if ttype is target_type:
                # target type is higher, so we need to increate precision
                return self.builder.fpext(value, Type.get_ir_type(ttype))
            else:
                return self.builder.fptrunc(value, Type.get_ir_type(ttype))
        elif "int" in target_type and "int" in source_type:
          ttype = Type.get_common_type(source_type, target_type)
          if ttype is target_type:
            # target type is higher, so we need to increate precision
            return self.builder.sext(value, Type.get_ir_type(ttype))
          else:
            return self.builder.trunc(value, Type.get_ir_type(ttype))
            
        else:
            raise ValueError(f"Semantic error - Illegal assignment of {source_type} to {target_type}")

    def get_ir(self):
        return str(self.module)