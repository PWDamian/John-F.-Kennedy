import uuid

from llvmlite import ir

from ast import Type, AssignNode, DeclareAssignNode, PrintNode, ReadNode, NumberNode, VariableNode, BinaryOpNode, \
    StringValueNode, ArrayAccessNode, DeclareArrayNode, ArrayAssignNode


class CodeGenerator:
    def __init__(self):
        self.module = ir.Module(name="JohnFKennedy")
        self.module.triple = "x86_64-pc-linux-gnu"
        self.builder = None
        self.func = None
        self.variables = {}
        self.variable_types = {}
        self.array_sizes = {}  # Store array sizes
        self.array_element_types = {}  # Store element types for arrays
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
        elif isinstance(node, DeclareArrayNode):
            self._generate_declare_array(node)
        elif isinstance(node, ArrayAssignNode):
            self._generate_array_assign(node)

    def _generate_array_assign(self, node):
        # Get array variable
        array_ptr = self.variables.get(node.name)
        if not array_ptr:
            raise ValueError(f"Array variable {node.name} not declared")

        element_type = self.array_element_types.get(node.name)
        if not element_type:
            raise ValueError(f"Unknown element type for array {node.name}")

        # Get index
        index_value = self._generate_expression(node.index)
        if not isinstance(index_value.type, ir.IntType):
            raise ValueError(f"Array index must be of integer type, got {index_value.type}")

        # Convert index to i32 if needed
        if index_value.type.width != 32:
            index_value = self.builder.trunc(index_value, ir.IntType(32)) if index_value.type.width > 32 \
                else self.builder.sext(index_value, ir.IntType(32))

        # Get element pointer
        element_ptr = self.builder.gep(array_ptr, [ir.Constant(ir.IntType(32), 0), index_value])

        # Generate value and store
        value = self._generate_expression(node.value)
        value = self._convert_if_needed(value, element_type)
        self.builder.store(value, element_ptr)

    def _generate_declare_array(self, node):
        if node.size <= 0:
            raise ValueError(f"Array size must be positive, got {node.size}")

        # Extract element type from array type (array_int8 -> int8)
        element_type = node.element_type
        llvm_element_type = Type.get_ir_type(element_type)

        # Create array type and allocate
        array_type = ir.ArrayType(llvm_element_type, node.size)
        array_ptr = self.builder.alloca(array_type, name=node.name)

        # Store array info
        self.variables[node.name] = array_ptr
        self.variable_types[node.name] = Type.ARRAY
        self.array_sizes[node.name] = node.size
        self.array_element_types[node.name] = element_type

    def _generate_assign(self, node):
        # Get the variable pointer
        ptr = self.variables.get(node.name)
        if not ptr:
            raise ValueError(f"Variable {node.name} not declared")

        # Get the variable type
        var_type = self.variable_types.get(node.name)

        # Generate the expression value
        value = self._generate_expression(node.value)

        # Handle string assignment differently
        if var_type == Type.STRING:
            # For strings, use strcpy instead of store
            if not hasattr(self, 'strcpy'):
                strcpy_ty = ir.FunctionType(ir.PointerType(ir.IntType(8)),
                                            [ir.PointerType(ir.IntType(8)), ir.PointerType(ir.IntType(8))])
                self.strcpy = ir.Function(self.module, strcpy_ty, name="strcpy")

            # Bitcast buffer to i8* for strcpy
            dest_ptr = self.builder.bitcast(ptr, ir.PointerType(ir.IntType(8)))

            # Call strcpy(destination, source)
            self.builder.call(self.strcpy, [dest_ptr, value])
        else:
            # For other types, convert if needed and store
            value = self._convert_if_needed(value, var_type)
            self.builder.store(value, ptr)

    def _generate_declare_assign(self, node):
        if node.type == Type.STRING:
            buffer = self.builder.alloca(ir.ArrayType(ir.IntType(8), 256), name=node.name)
            ptr = self.builder.bitcast(buffer, ir.PointerType(ir.IntType(8)))
            self.variables[node.name] = buffer  # Store the buffer pointer, not the bitcast
            self.variable_types[node.name] = node.type

            if node.value:
                value = self._generate_expression(node.value)

                if not hasattr(self, 'strcpy'):
                    strcpy_ty = ir.FunctionType(ir.PointerType(ir.IntType(8)),
                                                [ir.PointerType(ir.IntType(8)), ir.PointerType(ir.IntType(8))])
                    self.strcpy = ir.Function(self.module, strcpy_ty, name="strcpy")

                self.builder.call(self.strcpy, [ptr, value])
        else:
            llvm_type = Type.get_ir_type(node.type)
            ptr = self.builder.alloca(llvm_type, name=node.name)
            self.variables[node.name] = ptr
            self.variable_types[node.name] = node.type

            if node.value:
                value = self._generate_expression(node.value)
                value = self._convert_if_needed(value, node.type)
                self.builder.store(value, ptr)

    def _generate_print(self, node):
        value = self._generate_expression(node.expression)

        if isinstance(node.expression, VariableNode):
            type_name = self.variable_types.get(node.expression.name)
        elif isinstance(node.expression, ArrayAccessNode):
            # For array elements, use the element type
            element_type = self.array_element_types.get(node.expression.name)
            type_name = element_type if element_type else self._get_type_from_value(value)
        else:
            type_name = self._get_type_from_value(value)

        if not self.printf:
            printf_ty = ir.FunctionType(ir.IntType(32), [ir.PointerType(ir.IntType(8))], var_arg=True)
            self.printf = ir.Function(self.module, printf_ty, name="printf")

        if type_name == Type.STRING:
            fmt_ptr = self._get_print_format("%s\0", "format_str_string")
            self.builder.call(self.printf, [fmt_ptr, value])
        elif "int" in type_name:
            fmt_ptr = self._get_print_format("%d\0", "format_str_int")
            self.builder.call(self.printf, [fmt_ptr, value])
        elif "float" in type_name:
            fmt_ptr = self._get_print_format("%f\0", "format_str_float")
            self.builder.call(self.printf, [fmt_ptr, value])

    def _get_print_format(self, fmt_str, name):
        fmt_arr = bytearray(fmt_str, "utf8")
        fmt_type = ir.ArrayType(ir.IntType(8), len(fmt_arr))
        fmt_var = self.builder.alloca(fmt_type, name=name)
        self.builder.store(ir.Constant(fmt_type, fmt_arr), fmt_var)
        return self.builder.bitcast(fmt_var, ir.PointerType(ir.IntType(8)))

    def _generate_read(self, node):
        if not self.scanf:
            scanf_ty = ir.FunctionType(ir.IntType(32), [ir.PointerType(ir.IntType(8))], var_arg=True)
            self.scanf = ir.Function(self.module, scanf_ty, name="scanf")

        ptr = self.variables.get(node.name)
        if not ptr:
            raise ValueError(f"Variable {node.name} not declared")

        type_name = self.variable_types.get(node.name)
        if type_name == Type.STRING:
            ptr = self.builder.bitcast(ptr, ir.PointerType(ir.IntType(8)))  # Ensure it's a writable buffer

        fmt_str = "%d\0" if "int" in type_name else "%lf\0" if "float" in type_name else "%s\0"
        fmt_arr = bytearray(fmt_str, "utf8")
        fmt_type = ir.ArrayType(ir.IntType(8), len(fmt_arr))

        fmt_var = self.builder.alloca(fmt_type, name="fmt")
        self.builder.store(ir.Constant(fmt_type, fmt_arr), fmt_var)

        fmt_ptr = self.builder.bitcast(fmt_var, ir.PointerType(ir.IntType(8)))

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

            if self.variable_types.get(node.name) == Type.STRING:
                return self.builder.bitcast(ptr, ir.PointerType(ir.IntType(8)))
            else:
                return self.builder.load(ptr, name=node.name)
        elif isinstance(node, BinaryOpNode):
            left = self._generate_expression(node.left)
            right = self._generate_expression(node.right)
            left_type = self._get_type_from_value(left)
            right_type = self._get_type_from_value(right)
            result_type = Type.get_common_type(left_type, right_type)
            left = self._convert_if_needed(left, result_type)
            right = self._convert_if_needed(right, result_type)

            if "int" in result_type:  # Check if it's any integer type
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
        elif isinstance(node, ArrayAccessNode):
            # Get array variable
            array_ptr = self.variables.get(node.name)
            if not array_ptr:
                raise ValueError(f"Array variable {node.name} not declared")

            # Get the element type
            element_type = self.array_element_types.get(node.name)
            if not element_type:
                raise ValueError(f"Unknown element type for array {node.name}")

            # Generate index expression
            index_value = self._generate_expression(node.index)

            # Ensure index is an integer
            if not isinstance(index_value.type, ir.IntType):
                raise ValueError(f"Array index must be of integer type, got {index_value.type}")

            # Convert index to i32 if needed
            if index_value.type.width != 32:
                index_value = self.builder.trunc(index_value, ir.IntType(32)) if index_value.type.width > 32 \
                    else self.builder.sext(index_value, ir.IntType(32))

            # Get element pointer
            element_ptr = self.builder.gep(array_ptr, [ir.Constant(ir.IntType(32), 0), index_value])

            # Load and return the value
            return self.builder.load(element_ptr, f"{node.name}_element")

    def _get_type_from_value(self, value):
        if value.type is ir.IntType(8):
            return Type.INT8
        elif value.type is ir.IntType(16):
            return Type.INT16
        elif value.type is ir.IntType(32):
            return Type.INT32
        elif value.type is ir.IntType(64):
            return Type.INT
        elif value.type is ir.HalfType():
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

        # Handle int to float conversions
        if "int" in source_type and "float" in target_type:
            return self.builder.sitofp(value, Type.get_ir_type(target_type), name="int_to_float")
        # Handle float to int conversions
        elif "int" in target_type and "float" in source_type:
            return self.builder.fptosi(value, Type.get_ir_type(target_type), name="float_to_int")
        # Handle float to float conversions
        elif "float" in target_type and "float" in source_type:
            target_ir_type = Type.get_ir_type(target_type)

            # Fix for HalfType conversions
            if target_type == Type.FLOAT16:
                # Any floating point to float16 requires fptrunc
                return self.builder.fptrunc(value, target_ir_type, name="float_to_half")
            elif source_type == Type.FLOAT16:
                # float16 to any larger float requires fpext
                return self.builder.fpext(value, target_ir_type, name="half_to_float")
            else:
                # Normal float conversions
                ttype = Type.get_common_type(source_type, target_type)
                if ttype == target_type:
                    # Target type is higher precision, so extend
                    return self.builder.fpext(value, target_ir_type, name="float_extend")
                else:
                    # Target type is lower precision, so truncate
                    return self.builder.fptrunc(value, target_ir_type, name="float_trunc")
        # Handle int to int conversions
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
            raise ValueError(f"Semantic error - Illegal assignment of {source_type} to {target_type}")

    def get_ir(self):
        return str(self.module)
