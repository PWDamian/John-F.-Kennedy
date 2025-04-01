from llvmlite import ir

from ast2 import Type


def get_type_from_value(value):
    if isinstance(value.type, ir.IntType):
        if value.type.width == 1:
            return Type.BOOL
        elif value.type.width == 8:
            return Type.INT8
        elif value.type.width == 16:
            return Type.INT16
        elif value.type.width == 32:
            return Type.INT32
        elif value.type.width == 64:
            return Type.INT
        else:
            raise ValueError(f"Unknown integer width: {value.type.width}")
    elif value.type == ir.HalfType():
        return Type.FLOAT16
    elif value.type == ir.FloatType():
        return Type.FLOAT32
    elif value.type == ir.DoubleType():
        return Type.FLOAT
    elif isinstance(value.type, ir.PointerType) and value.type.pointee == ir.IntType(8):
        return Type.STRING
    else:
        raise ValueError(f"Unknown LLVM type: {value.type}")


def convert_if_needed(self, value, target_type):
    source_type = get_type_from_value(value)
    if source_type == target_type:
        return value

    source_type = Type.map_to_internal_type(source_type)
    target_type = Type.map_to_internal_type(target_type)

    if "int" in source_type and "float" in target_type:
        return self.builder.sitofp(value, Type.get_ir_type(target_type), name="int_to_float")
    elif "int" in target_type and "float" in source_type:
        return self.builder.fptosi(value, Type.get_ir_type(target_type), name="float_to_int")
    elif "float" in target_type and "float" in source_type:
        target_ir_type = Type.get_ir_type(target_type)

        source_precision = Type.numeric_hierarchy.index(source_type)
        target_precision = Type.numeric_hierarchy.index(target_type)

        if target_precision > source_precision:
            return self.builder.fpext(value, target_ir_type, name="float_extend")
        else:
            return self.builder.fptrunc(value, target_ir_type, name="float_trunc")
    elif "int" in target_type and "int" in source_type:
        target_ir_type = Type.get_ir_type(target_type)
        source_bits = int(value.type.width)
        target_bits = int(target_ir_type.width)

        if target_bits > source_bits:
            return self.builder.sext(value, target_ir_type, name="int_extend")
        elif target_bits < source_bits:
            return self.builder.trunc(value, target_ir_type, name="int_trunc")
        else:
            return value
    else:
        raise ValueError(f"Cannot convert between types {source_type} and {target_type}")


def normalize_index(self, index_value):
    if not isinstance(index_value.type, ir.IntType):
        raise ValueError(f"Index must be integer, got {index_value.type}")
    if index_value.type.width != 32:
        index_value = self.builder.trunc(index_value, ir.IntType(32)) if index_value.type.width > 32 \
            else self.builder.sext(index_value, ir.IntType(32))
    return index_value


def to_boolean(self, value):
    value_type = get_type_from_value(value)

    if value_type == Type.BOOL:
        return value
    elif "int" in value_type:
        zero = ir.Constant(value.type, 0)
        return self.builder.icmp_signed('!=', value, zero)
    elif "float" in value_type:
        zero = ir.Constant(value.type, 0)
        return self.builder.fcmp_ordered('!=', value, zero)
    else:
        return ir.Constant(ir.IntType(1), 1)


def convert_value_to_type(self, value, target_ir_type):
    """
    Convert a value to a specific LLVM IR type
    """
    # Get source type information
    source_type = get_type_from_value(value)
    source_ir_type = value.type

    # Handle pointer types like strings
    if isinstance(target_ir_type, ir.PointerType) and isinstance(source_ir_type, ir.PointerType):
        # For string handling, ensure we're using the right pointer type
        if target_ir_type.pointee == ir.IntType(8) and source_ir_type.pointee == ir.IntType(8):
            # Both are pointers to i8 (char*), so no need for bitcast
            return value
        return self.builder.bitcast(value, target_ir_type)

    # Convert between numeric types
    if isinstance(target_ir_type, ir.IntType) and isinstance(source_ir_type, ir.IntType):
        # Integer to integer conversion
        if target_ir_type.width > source_ir_type.width:
            return self.builder.sext(value, target_ir_type)
        elif target_ir_type.width < source_ir_type.width:
            return self.builder.trunc(value, target_ir_type)
        else:
            return value

    elif isinstance(target_ir_type, (ir.FloatType, ir.DoubleType, ir.HalfType)) and isinstance(source_ir_type,
                                                                                               ir.IntType):
        # Integer to floating point
        return self.builder.sitofp(value, target_ir_type)

    elif isinstance(target_ir_type, ir.IntType) and isinstance(source_ir_type,
                                                               (ir.FloatType, ir.DoubleType, ir.HalfType)):
        # Floating point to integer
        return self.builder.fptosi(value, target_ir_type)

    elif isinstance(target_ir_type, (ir.FloatType, ir.DoubleType, ir.HalfType)) and isinstance(source_ir_type, (
            ir.FloatType, ir.DoubleType, ir.HalfType)):
        # Floating point to floating point
        if (isinstance(target_ir_type, ir.DoubleType) and not isinstance(source_ir_type, ir.DoubleType)) or \
                (isinstance(target_ir_type, ir.FloatType) and isinstance(source_ir_type, ir.HalfType)):
            return self.builder.fpext(value, target_ir_type)
        elif (isinstance(source_ir_type, ir.DoubleType) and not isinstance(target_ir_type, ir.DoubleType)) or \
                (isinstance(source_ir_type, ir.FloatType) and isinstance(target_ir_type, ir.HalfType)):
            return self.builder.fptrunc(value, target_ir_type)
        else:
            return value

    # If types are already compatible, no conversion needed
    elif target_ir_type == source_ir_type:
        return value

    else:
        raise ValueError(f"Cannot convert from {source_ir_type} to {target_ir_type}")


def get_common_ir_type(self, left_value, right_value):
    """
    Determine the common IR type between two LLVM values
    """
    # Get the type enums from LLVM values
    left_type = get_type_from_value(left_value)
    right_type = get_type_from_value(right_value)

    # Use the Type's get_common_type to find higher precision type
    common_type = Type.get_common_type(left_type, right_type)

    # Return the IR type for this common type
    return Type.get_ir_type(common_type)
