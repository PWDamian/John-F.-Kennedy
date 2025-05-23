from llvmlite import ir

from ast2 import Type
from codegen import expression, type_utils


def generate_declare_matrix(self, node):
    if node.rows <= 0 or node.cols <= 0:
        raise ValueError(f"Matrix dimensions must be positive, got [{node.rows}][{node.cols}]")

    element_type = node.element_type
    llvm_element_type = Type.get_ir_type(element_type)

    row_type = ir.ArrayType(llvm_element_type, node.cols)
    matrix_type = ir.ArrayType(row_type, node.rows)
    matrix_ptr = self.builder.alloca(matrix_type, name=node.name)
    self.declare_variable(node.name, matrix_ptr, Type.ARRAY)
    self.matrix_rows[node.name] = node.rows
    self.matrix_cols[node.name] = node.cols
    self.matrix_element_types[node.name] = element_type


def generate_matrix_assign(self, node):
    matrix_ptr = self.get_variable(node.name)
    if not matrix_ptr:
        raise ValueError(f"Matrix variable {node.name} not declared")


    element_type = self.matrix_element_types.get(node.name)
    if not element_type:
        raise ValueError(f"Unknown element type for matrix {node.name}")


    row_index = expression.generate_expression(self, node.row_index)
    col_index = expression.generate_expression(self, node.col_index)

    # Ensure indices are within bounds
    if not isinstance(row_index.type, ir.IntType) or not isinstance(col_index.type, ir.IntType):
        raise ValueError("Matrix indices must be integers")

    # Calculate the element pointer
    element_ptr = self.builder.gep(matrix_ptr, [ir.Constant(ir.IntType(32), 0), row_index, col_index])

    # Generate the value to assign
    value = expression.generate_expression(self, node.value)
    value = type_utils.convert_if_needed(self, value, element_type)
    self.builder.store(value, element_ptr)


def generate_matrix_access(self, node):
    matrix_ptr = self.get_variable(node.name)
    if not matrix_ptr:
        raise ValueError(f"Matrix variable {node.name} not declared")

    row_index = expression.generate_expression(self, node.row_index)
    col_index = expression.generate_expression(self, node.col_index)

    # Ensure indices are within bounds
    if not isinstance(row_index.type, ir.IntType) or not isinstance(col_index.type, ir.IntType):
        raise ValueError("Matrix indices must be integers")

    # Calculate the element pointer
    element_ptr = self.builder.gep(matrix_ptr, [ir.Constant(ir.IntType(32), 0), row_index, col_index])

    # Load the element value
    return self.builder.load(element_ptr, name=f"{node.name}_element")
