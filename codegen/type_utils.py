from llvmlite import ir

from ast2 import Type


def get_type_from_value(self, value):
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
    source_type = get_type_from_value(self, value)
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
        source_ir_type = value.type

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
    value_type = get_type_from_value(self, value)

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
