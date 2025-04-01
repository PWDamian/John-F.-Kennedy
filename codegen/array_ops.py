from llvmlite import ir

from ast2 import Type
from codegen import expression, type_utils


def generate_array_assign(self, node):
    array_ptr = self.get_variable(node.name)
    if not array_ptr:
        raise ValueError(f"Array variable {node.name} not declared")

    element_type = self.array_element_types.get(node.name)
    if not element_type:
        raise ValueError(f"Unknown element type for array {node.name}")

    index_value = expression.generate_expression(self, node.index)
    index_value = type_utils.normalize_index(self, index_value)

    element_ptr = self.builder.gep(array_ptr, [ir.Constant(ir.IntType(32), 0), index_value])

    value = expression.generate_expression(self, node.value)
    value = type_utils.convert_if_needed(self, value, element_type)
    self.builder.store(value, element_ptr)


def generate_declare_array(self, node):
    if node.size <= 0:
        raise ValueError(f"Array size must be positive, got {node.size}")

    element_type = node.element_type
    llvm_element_type = Type.get_ir_type(element_type)

    array_type = ir.ArrayType(llvm_element_type, node.size)
    array_ptr = self.builder.alloca(array_type, name=node.name)
    self.declare_variable(node.name, array_ptr, Type.ARRAY)

    self.array_sizes[node.name] = node.size
    self.array_element_types[node.name] = element_type
