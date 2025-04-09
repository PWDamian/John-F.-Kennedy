from llvmlite import ir


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
    CLASS = "class"  # Add class type constant

    # Type hierarchy for numeric types (from lowest to highest precision)
    numeric_hierarchy = [
        BOOL, INT8, INT16, INT32, INT64,
        FLOAT16, FLOAT32, FLOAT64
    ]

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
        elif cls.is_class_type(type):
            # Handle class types as pointers to structures
            # In a proper implementation, we would look up the actual structure type
            # based on the class name
            return ir.PointerType(ir.IntType(8))
        else:
            raise ValueError(f"Unsupported type in type get ir: {type}")

    @classmethod
    def is_class_type(cls, type_name):
        # A class type is any type that's not one of our predefined types
        # This is a simple heuristic that will work for now
        predefined_types = [
            cls.INT8, cls.INT16, cls.INT32, cls.INT64, cls.INT,
            cls.FLOAT16, cls.FLOAT32, cls.FLOAT64, cls.FLOAT,
            cls.STRING, cls.ARRAY, cls.BOOL, cls.VOID
        ]
        return type_name not in predefined_types
