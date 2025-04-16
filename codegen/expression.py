from llvmlite import ir
import struct
import uuid

from ast2 import Type, BinaryOpNode, NumberNode, VariableNode, ComparisonNode, StringValueNode, ArrayAccessNode, \
    MatrixAccessNode, LogicalOpNode, LogicalNotNode, BooleanNode, FunctionCallNode, StructFieldAccessNode
from codegen import logical_ops, type_utils, function_ops, struct_ops


def generate_expression(self, node):
    if isinstance(node, BinaryOpNode):
        return generate_binary_op(self, node)
    elif isinstance(node, NumberNode):
        return generate_number(self, node)
    elif isinstance(node, VariableNode):
        return generate_variable(self, node)
    elif isinstance(node, ComparisonNode):
        return generate_comparison(self, node)
    elif isinstance(node, StringValueNode):
        return generate_string(self, node)
    elif isinstance(node, ArrayAccessNode):
        return generate_array_access(self, node)
    elif isinstance(node, MatrixAccessNode):
        return generate_matrix_access(self, node)
    elif isinstance(node, LogicalOpNode):
        return generate_logical_op(self, node)
    elif isinstance(node, LogicalNotNode):
        return generate_logical_not(self, node)
    elif isinstance(node, BooleanNode):
        return generate_boolean(self, node)
    elif isinstance(node, FunctionCallNode):
        return function_ops.generate_function_call(self, node)
    elif isinstance(node, StructFieldAccessNode):
        return struct_ops.generate_struct_field_access(self, node)
    else:
        raise ValueError(f"Unsupported expression node: {type(node)}")


def generate_binary_op(self, node):
    left = generate_expression(self, node.left)
    right = generate_expression(self, node.right)
    left_type = type_utils.get_type_from_value(left)
    right_type = type_utils.get_type_from_value(right)
    result_type = Type.get_common_type(left_type, right_type)
    left = type_utils.convert_if_needed(self, left, result_type)
    right = type_utils.convert_if_needed(self, right, result_type)

    if "int" in result_type:
        return {
            '+': self.builder.add,
            '-': self.builder.sub,
            '*': self.builder.mul,
            '/': self.builder.sdiv
        }[node.op](left, right, name="int_op")
    elif result_type == "bool":
        raise Exception("Operations (+,-,/,*) are not allowed for boolean values.")
    else:
        return {
            '+': self.builder.fadd,
            '-': self.builder.fsub,
            '*': self.builder.fmul,
            '/': self.builder.fdiv
        }[node.op](left, right, name="float_op")


def generate_number(self, node):
    if node.type == Type.INT8:
        return ir.Constant(ir.IntType(8), node.value)
    elif node.type == Type.INT16:
        return ir.Constant(ir.IntType(16), node.value)
    elif node.type == Type.INT32:
        return ir.Constant(ir.IntType(32), node.value)
    elif node.type == Type.INT or node.type == Type.INT64:
        return ir.Constant(ir.IntType(64), node.value)
    elif node.type == Type.FLOAT16:
        float_val = struct.unpack('e', struct.pack('e', node.value))[0]
        return ir.Constant(ir.HalfType(), float_val)
    elif node.type == Type.FLOAT32:
        float_val = struct.unpack('f', struct.pack('f', node.value))[0]
        return ir.Constant(ir.FloatType(), float_val)
    elif node.type == Type.FLOAT or node.type == Type.FLOAT64:
        float_val = struct.unpack('d', struct.pack('d', node.value))[0]
        return ir.Constant(ir.DoubleType(), float_val)
    else:
        raise ValueError(f"Unsupported type in expr gen: {node.type}")


def generate_variable(self, node):
    ptr = self.get_variable(node.name)
    if not ptr:
        raise ValueError(f"Variable {node.name} not declared")

    if self.get_variable_type(node.name) == Type.STRING:
        return self.builder.bitcast(ptr, ir.PointerType(ir.IntType(8)))
    else:
        return self.builder.load(ptr, name=node.name)


def generate_comparison(self, node):
    left = generate_expression(self, node.left)
    right = generate_expression(self, node.right)
    left_type = type_utils.get_type_from_value(left)
    right_type = type_utils.get_type_from_value(right)

    result_type = Type.get_common_type(left_type, right_type)
    left = type_utils.convert_if_needed(self, left, result_type)
    right = type_utils.convert_if_needed(self, right, result_type)

    if "int" in result_type:
        return {
            '<': self.builder.icmp_signed('<', left, right),
            '>': self.builder.icmp_signed('>', left, right),
            '<=': self.builder.icmp_signed('<=', left, right),
            '>=': self.builder.icmp_signed('>=', left, right),
            '==': self.builder.icmp_signed('==', left, right),
            '!=': self.builder.icmp_signed('!=', left, right)
        }[node.op]
    else:
        return {
            '<': self.builder.fcmp_ordered('<', left, right),
            '>': self.builder.fcmp_ordered('>', left, right),
            '<=': self.builder.fcmp_ordered('<=', left, right),
            '>=': self.builder.fcmp_ordered('>=', left, right),
            '==': self.builder.fcmp_ordered('==', left, right),
            '!=': self.builder.fcmp_ordered('!=', left, right)
        }[node.op]


def generate_string(self, node):
    string_data = bytearray(node.value + "\0", "utf8")
    string_arr_ty = ir.ArrayType(ir.IntType(8), len(string_data))
    string_const = ir.GlobalVariable(self.module, string_arr_ty, name=str(uuid.uuid4()))
    string_const.initializer = ir.Constant(string_arr_ty, string_data)
    string_const.global_constant = True
    return self.builder.bitcast(string_const, ir.PointerType(ir.IntType(8)))


def generate_array_access(self, node):
    array_ptr = self.get_variable(node.name)
    if not array_ptr:
        raise ValueError(f"Array variable {node.name} not declared")

    element_type = self.array_element_types.get(node.name)
    if not element_type:
        raise ValueError(f"Unknown element type for array {node.name}")

    index_value = generate_expression(self, node.index)

    if not isinstance(index_value.type, ir.IntType):
        raise ValueError(f"Array index must be of integer type, got {index_value.type}")

    if index_value.type.width != 32:
        index_value = self.builder.trunc(index_value, ir.IntType(32)) if index_value.type.width > 32 \
            else self.builder.sext(index_value, ir.IntType(32))

    element_ptr = self.builder.gep(array_ptr, [ir.Constant(ir.IntType(32), 0), index_value])

    return self.builder.load(element_ptr, f"{node.name}_element")


def generate_matrix_access(self, node):
    matrix_ptr = self.get_variable(node.name)
    if not matrix_ptr:
        raise ValueError(f"Matrix variable {node.name} not declared")

    element_type = self.matrix_element_types.get(node.name)
    if not element_type:
        raise ValueError(f"Unknown element type for matrix {node.name}")

    row_index = generate_expression(self, node.row_index)
    col_index = generate_expression(self, node.col_index)

    if not isinstance(row_index.type, ir.IntType):
        raise ValueError(f"Matrix row index must be of integer type, got {row_index.type}")

    if not isinstance(col_index.type, ir.IntType):
        raise ValueError(f"Matrix column index must be of integer type, got {col_index.type}")

    if row_index.type.width != 32:
        row_index = self.builder.trunc(row_index, ir.IntType(32)) if row_index.type.width > 32 \
            else self.builder.sext(row_index, ir.IntType(32))

    if col_index.type.width != 32:
        col_index = self.builder.trunc(col_index, ir.IntType(32)) if col_index.type.width > 32 \
            else self.builder.sext(col_index, ir.IntType(32))

    indices = [
        ir.Constant(ir.IntType(32), 0),
        row_index,
        col_index
    ]
    element_ptr = self.builder.gep(matrix_ptr, indices)

    return self.builder.load(element_ptr, f"{node.name}_element")


def generate_logical_op(self, node):
    self.block_counter += 1
    op_id = self.block_counter

    if node.op == '&&':
        return logical_ops.generate_lazy_and(self, node, op_id)
    elif node.op == '||':
        return logical_ops.generate_lazy_or(self, node, op_id)
    elif node.op == '^':
        return logical_ops.generate_direct_logical_op(self, node,
                                                      lambda l, r: self.builder.xor(l, r, f"xor_result_{op_id}"))
    else:
        raise ValueError(f"Unknown logical operator: {node.op}")


def generate_logical_not(self, node):
    expr = generate_expression(self, node.expr)

    if not isinstance(expr.type, ir.IntType) or expr.type.width != 1:
        expr = type_utils.to_boolean(self, expr)

    return self.builder.not_(expr, name="not_result")


def generate_boolean(self, node):
    return ir.Constant(ir.IntType(1), 1 if node.value else 0)
