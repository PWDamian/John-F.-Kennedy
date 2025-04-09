import struct
import uuid

from llvmlite import ir

from ast2 import Type
from ast2.nodes import NumberNode, BooleanNode, VariableNode, StringValueNode, ArrayAccessNode, MatrixAccessNode, \
    BinaryOpNode, ComparisonNode, LogicalOpNode, LogicalNotNode, FunctionCallNode, MemberAccessNode, MethodCallNode
from codegen import logical_ops, type_utils, function_ops, array_ops, matrix_ops, class_ops
from codegen.function_ops import generate_function_call


def generate_expression(self, node):
    if isinstance(node, NumberNode):
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

    elif isinstance(node, BooleanNode):
        return ir.Constant(ir.IntType(1), 1 if node.value else 0)

    elif isinstance(node, VariableNode):
        ptr = self.get_variable(node.name)
        if not ptr:
            raise ValueError(f"Variable {node.name} not declared")

        if self.get_variable_type(node.name) == Type.STRING:
            return self.builder.bitcast(ptr, ir.PointerType(ir.IntType(8)))
        else:
            return self.builder.load(ptr, name=node.name)

    elif isinstance(node, BinaryOpNode):
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

    elif isinstance(node, LogicalOpNode):
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

    elif isinstance(node, LogicalNotNode):
        expr = generate_expression(self, node.expr)

        if not isinstance(expr.type, ir.IntType) or expr.type.width != 1:
            expr = type_utils.to_boolean(self, expr)

        return self.builder.not_(expr, name="not_result")

    elif isinstance(node, StringValueNode):
        string_data = bytearray(node.value + "\0", "utf8")
        string_arr_ty = ir.ArrayType(ir.IntType(8), len(string_data))
        string_const = ir.GlobalVariable(self.module, string_arr_ty, name=str(uuid.uuid4()))
        string_const.initializer = ir.Constant(string_arr_ty, string_data)
        string_const.global_constant = True
        return self.builder.bitcast(string_const, ir.PointerType(ir.IntType(8)))

    elif isinstance(node, ArrayAccessNode):
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

    elif isinstance(node, MatrixAccessNode):
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

    elif isinstance(node, ComparisonNode):
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

    elif isinstance(node, MemberAccessNode):
        return class_ops.generate_member_access(self, node)

    elif isinstance(node, MethodCallNode):
        # Get the object instance and class name
        instance = self.get_variable(node.object_name)
        class_name = self.get_variable_type(node.object_name)
        
        # Generate arguments
        args = [generate_expression(self, arg) for arg in node.arguments]
        
        # Call the method
        return class_ops.generate_method_call(self, instance, class_name, node.method_name, args)

    elif isinstance(node, FunctionCallNode):
        result = function_ops.generate_function_call(self, node)
        if result is None:
            raise ValueError(f"Cannot use void function '{node.name}' in an expression")
        return result
