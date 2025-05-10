from llvmlite import ir

from ast2 import VariableNode


class Type:
    INT8 = "int8"
    INT16 = "int16"
    INT32 = "int32"
    INT64 = "int64"
    INT = "int"  # Alias for INT64

    FLOAT16 = "float16"
    FLOAT32 = "float32"
    FLOAT64 = "float64"
    FLOAT = "float"  # Alias for FLOAT64

    STRING = "string"
    ARRAY = "array"
    BOOL = "bool"
    VOID = "void"  # Add void type constant
    STRUCT = "struct"  # Add struct type
    VAR = "var"  # Add var type for type inference

    # Type hierarchy for numeric types (from lowest to highest precision)
    numeric_hierarchy = [
        BOOL, INT8, INT16, INT32, INT64,
        FLOAT16, FLOAT32, FLOAT64
    ]

    # Store struct definitions
    struct_types = {}

    @classmethod
    def infer_type_from_value(cls, value):
        from .nodes import (
            NumberNode, BooleanNode, StringValueNode, ArrayAccessNode,
            MatrixAccessNode, BinaryOpNode, LogicalOpNode, ComparisonNode,
            LogicalNotNode, StructFieldAccessNode
        )
        """Infer the type from a value node"""
        if isinstance(value, NumberNode):
            if isinstance(value.value, int):
                return cls.INT64  # Default to int64 for integers
            elif isinstance(value.value, float):
                return cls.FLOAT64  # Default to float64 for floats
        elif isinstance(value, BooleanNode):
            return cls.BOOL
        elif isinstance(value, StringValueNode):
            return cls.STRING
        elif isinstance(value, ArrayAccessNode):
            return cls.ARRAY
        elif isinstance(value, MatrixAccessNode):
            return cls.ARRAY  # For now, treat matrices as arrays
        elif isinstance(value, StructFieldAccessNode):
            return cls.STRUCT
        elif isinstance(value, BinaryOpNode):
            # For binary operations, infer type from operands
            left_type = cls.infer_type_from_value(value.left)
            right_type = cls.infer_type_from_value(value.right)
            return cls.get_common_type(left_type, right_type)
        elif isinstance(value, LogicalOpNode):
            return cls.BOOL
        elif isinstance(value, ComparisonNode):
            return cls.BOOL
        elif isinstance(value, LogicalNotNode):
            return cls.BOOL
        else:
            raise ValueError(f"Cannot infer type from value: {value}")

    @classmethod
    def register_struct_type(cls, name, fields):
        """
        Register a struct type definition
        fields: dict mapping field names to their types
        """
        cls.struct_types[name] = fields

    @classmethod
    def is_struct_type(cls, type_name):
        """Check if a type name refers to a struct"""
        return type_name in cls.struct_types

    @classmethod
    def get_struct_field_type(cls, struct_type, field_name):
        """Get the type of a struct field"""
        if not cls.is_struct_type(struct_type):
            raise ValueError(f"Unknown struct type: {struct_type}")
        
        if field_name not in cls.struct_types[struct_type]:
            raise ValueError(f"Field {field_name} not found in struct {struct_type}")
            
        return cls.struct_types[struct_type][field_name]

    @classmethod
    def map_to_internal_type(cls, type_name):
        if type_name == cls.INT:
            return cls.INT64
        elif type_name == cls.FLOAT:
            return cls.FLOAT64
        return type_name

    @classmethod
    def get_common_type(cls, left_type, right_type):
        # Map backward compatibility types to internal types
        left_type = cls.map_to_internal_type(left_type)
        right_type = cls.map_to_internal_type(right_type)

        # If either is array or string, can't determine common type
        if left_type == Type.ARRAY or right_type == Type.ARRAY or \
                left_type == Type.STRING or right_type == Type.STRING:
            raise ValueError("Cannot determine common type involving arrays or strings")

        # Get indices in hierarchy
        try:
            left_idx = cls.numeric_hierarchy.index(left_type)
            right_idx = cls.numeric_hierarchy.index(right_type)
        except ValueError:
            raise ValueError(f"Unknown type in common type determination: {left_type} or {right_type}")

        # Return the type with higher precision
        return cls.numeric_hierarchy[max(left_idx, right_idx)]

    @classmethod
    def get_ir_type(cls, type):
        type = cls.map_to_internal_type(type)

        if type == cls.VOID:
            return ir.VoidType()
        elif type == cls.BOOL:
            return ir.IntType(1)
        elif type == cls.INT8:
            return ir.IntType(8)
        elif type == cls.INT16:
            return ir.IntType(16)
        elif type == cls.INT32:
            return ir.IntType(32)
        elif type == cls.INT64:
            return ir.IntType(64)
        elif type == cls.FLOAT16:
            return ir.HalfType()
        elif type == cls.FLOAT32:
            return ir.FloatType()
        elif type == cls.FLOAT64:
            return ir.DoubleType()
        elif type == cls.STRING:
            return ir.PointerType(ir.IntType(8))
        elif cls.is_struct_type(type):
            # For structs, we just use an opaque pointer type
            # The actual struct type will be defined separately in struct_ops.py
            return ir.IntType(64)  # Use a standard integer as placeholder
        else:
            raise ValueError(f"Unsupported type in type get ir: {type}")
