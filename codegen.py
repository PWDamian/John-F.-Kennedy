import struct
import uuid

from llvmlite import ir

from ast2.nodes import BooleanNode
from ast2 import Type, AssignNode, DeclareAssignNode, PrintNode, ReadNode, NumberNode, VariableNode, BinaryOpNode, \
    StringValueNode, ArrayAccessNode, DeclareArrayNode, ArrayAssignNode, DeclareMatrixNode, MatrixAssignNode, \
    MatrixAccessNode, IfNode, ForNode, ComparisonNode


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
        self.format_str_bool = None
        self.scan_format_int = None
        self.scan_format_float = None
        self.scan_format_string = None
        self.matrix_rows = {}
        self.matrix_cols = {}
        self.matrix_element_types = {}

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
        elif isinstance(node, DeclareMatrixNode):
            self._generate_declare_matrix(node)
        elif isinstance(node, MatrixAssignNode):
            self._generate_matrix_assign(node)
        elif isinstance(node, IfNode):
            self._generate_if(node)
        elif isinstance(node, ForNode):
            self._generate_for(node)

    def _generate_declare_matrix(self, node):
        if node.rows <= 0 or node.cols <= 0:
            raise ValueError(f"Matrix dimensions must be positive, got [{node.rows}][{node.cols}]")

        # Extract element type
        element_type = node.element_type
        llvm_element_type = Type.get_ir_type(element_type)

        # Create matrix type (array of arrays) and allocate
        row_type = ir.ArrayType(llvm_element_type, node.cols)
        matrix_type = ir.ArrayType(row_type, node.rows)
        matrix_ptr = self.builder.alloca(matrix_type, name=node.name)

        # Store matrix info
        self.variables[node.name] = matrix_ptr
        self.variable_types[node.name] = Type.ARRAY  # Treat as a special kind of array
        self.matrix_rows[node.name] = node.rows
        self.matrix_cols[node.name] = node.cols
        self.matrix_element_types[node.name] = element_type

    def _generate_matrix_assign(self, node):
        # Get matrix variable
        matrix_ptr = self.variables.get(node.name)
        if not matrix_ptr:
            raise ValueError(f"Matrix variable {node.name} not declared")

        element_type = self.matrix_element_types.get(node.name)
        if not element_type:
            raise ValueError(f"Unknown element type for matrix {node.name}")

        # Get row index
        row_index = self._normalize_index(self._generate_expression(node.row_index))

        # Get column index
        col_index = self._normalize_index(self._generate_expression(node.col_index))

        # Get element pointer (need to go through two levels of arrays)
        indices = [
            ir.Constant(ir.IntType(32), 0),  # Base pointer
            row_index,  # Row index
            col_index  # Column index
        ]
        element_ptr = self.builder.gep(matrix_ptr, indices)

        # Generate value and store
        value = self._generate_expression(node.value)
        value = self._convert_if_needed(value, element_type)
        self.builder.store(value, element_ptr)

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
        index_value = self._normalize_index(index_value)

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

        # Get the variable type (internal representation)
        var_type = self.variable_types.get(node.name)
        var_type = Type._map_to_internal_type(var_type)

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
            # Map type to internal representation
            internal_type = Type._map_to_internal_type(node.type)
            llvm_type = Type.get_ir_type(internal_type)
            ptr = self.builder.alloca(llvm_type, name=node.name)
            self.variables[node.name] = ptr
            self.variable_types[node.name] = internal_type  # Store the internal type

            if node.value:
                value = self._generate_expression(node.value)
                # Convert the value to the target type if needed
                value = self._convert_if_needed(value, internal_type)
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

        # Map to internal type
        type_name = Type._map_to_internal_type(type_name)

        if not self.printf:
            printf_ty = ir.FunctionType(ir.IntType(32), [ir.PointerType(ir.IntType(8))], var_arg=True)
            self.printf = ir.Function(self.module, printf_ty, name="printf")

        if type_name == Type.STRING:
            fmt_ptr = self._get_print_format("%s\n\0", "format_str_string")
            self.builder.call(self.printf, [fmt_ptr, value])
        elif type_name == Type.BOOL:
            # For boolean values, first convert to i8 to match "%s" format
            # Use conditional select to choose between "true" and "false" strings
            if not hasattr(self, 'true_str'):
                true_data = bytearray("true\0", "utf8")
                true_arr_ty = ir.ArrayType(ir.IntType(8), len(true_data))
                self.true_str = ir.GlobalVariable(self.module, true_arr_ty, name="true_str")
                self.true_str.initializer = ir.Constant(true_arr_ty, true_data)
                self.true_str.global_constant = True
                
                false_data = bytearray("false\0", "utf8")
                false_arr_ty = ir.ArrayType(ir.IntType(8), len(false_data))
                self.false_str = ir.GlobalVariable(self.module, false_arr_ty, name="false_str")
                self.false_str.initializer = ir.Constant(false_arr_ty, false_data)
                self.false_str.global_constant = True
            
            # Convert i1 to i8 for comparison
            bool_i8 = self.builder.zext(value, ir.IntType(8))
            
            # Select the appropriate string based on the boolean value
            true_ptr = self.builder.bitcast(self.true_str, ir.PointerType(ir.IntType(8)))
            false_ptr = self.builder.bitcast(self.false_str, ir.PointerType(ir.IntType(8)))
            bool_str = self.builder.select(value, true_ptr, false_ptr)
            
            # Print the boolean value as a string
            fmt_ptr = self._get_print_format("%s\n\0", "format_str_bool")
            self.builder.call(self.printf, [fmt_ptr, bool_str])
        elif "int" in type_name:
            fmt_ptr = self._get_print_format("%d\n\0", "format_str_int")
            self.builder.call(self.printf, [fmt_ptr, value])
        elif "float" in type_name:
            # For float16 and float32, extend to float64 for printing
            if type_name in [Type.FLOAT16, Type.FLOAT32]:
                value = self.builder.fpext(value, ir.DoubleType())
            fmt_ptr = self._get_print_format("%.49f\n\0", "format_str_float")
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
            elif node.type == Type.INT or node.type == Type.INT64:
                return ir.Constant(ir.IntType(64), node.value)
            elif node.type == Type.FLOAT16:
                # For float16, convert the value directly to binary representation
                # to ensure exact values
                float_val = struct.unpack('e', struct.pack('e', node.value))[0]
                return ir.Constant(ir.HalfType(), float_val)
            elif node.type == Type.FLOAT32:
                # For float32, convert the value directly to binary representation
                float_val = struct.unpack('f', struct.pack('f', node.value))[0]
                return ir.Constant(ir.FloatType(), float_val)
            elif node.type == Type.FLOAT or node.type == Type.FLOAT64:
                # For float64, ensure exact double precision representation
                float_val = struct.unpack('d', struct.pack('d', node.value))[0]
                return ir.Constant(ir.DoubleType(), float_val)
            else:
                raise ValueError(f"Unsupported type in expr gen: {node.type}")
        elif isinstance(node, BooleanNode):
            # Handle boolean literals (true/false)
            return ir.Constant(ir.IntType(1), 1 if node.value else 0)
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
        elif isinstance(node, MatrixAccessNode):
            # Get matrix variable
            matrix_ptr = self.variables.get(node.name)
            if not matrix_ptr:
                raise ValueError(f"Matrix variable {node.name} not declared")

            # Get the element type
            element_type = self.matrix_element_types.get(node.name)
            if not element_type:
                raise ValueError(f"Unknown element type for matrix {node.name}")

            # Generate row index expression
            row_index = self._generate_expression(node.row_index)

            # Generate column index expression
            col_index = self._generate_expression(node.col_index)

            # Ensure indices are integers
            if not isinstance(row_index.type, ir.IntType):
                raise ValueError(f"Matrix row index must be of integer type, got {row_index.type}")

            if not isinstance(col_index.type, ir.IntType):
                raise ValueError(f"Matrix column index must be of integer type, got {col_index.type}")

            # Convert indices to i32 if needed
            if row_index.type.width != 32:
                row_index = self.builder.trunc(row_index, ir.IntType(32)) if row_index.type.width > 32 \
                    else self.builder.sext(row_index, ir.IntType(32))

            if col_index.type.width != 32:
                col_index = self.builder.trunc(col_index, ir.IntType(32)) if col_index.type.width > 32 \
                    else self.builder.sext(col_index, ir.IntType(32))

            # Get element pointer
            indices = [
                ir.Constant(ir.IntType(32), 0),  # Base pointer
                row_index,  # Row index
                col_index  # Column index
            ]
            element_ptr = self.builder.gep(matrix_ptr, indices)

            # Load and return the value
            return self.builder.load(element_ptr, f"{node.name}_element")
        elif isinstance(node, ComparisonNode):
            left = self._generate_expression(node.left)
            right = self._generate_expression(node.right)
            left_type = self._get_type_from_value(left)
            right_type = self._get_type_from_value(right)

            # Get common type and convert operands
            result_type = Type.get_common_type(left_type, right_type)
            left = self._convert_if_needed(left, result_type)
            right = self._convert_if_needed(right, result_type)

            # Handle integer or float comparisons
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

    def _get_type_from_value(self, value):
        if isinstance(value.type, ir.IntType):
            if value.type.width == 1:
                # Boolean type (i1)
                return Type.BOOL  # Now returning BOOL type for i1
            elif value.type.width == 8:
                return Type.INT8
            elif value.type.width == 16:
                return Type.INT16
            elif value.type.width == 32:
                return Type.INT32
            elif value.type.width == 64:
                return Type.INT  # Return backward compatibility type
        elif value.type == ir.HalfType():
            return Type.FLOAT16
        elif value.type == ir.FloatType():
            return Type.FLOAT32
        elif value.type == ir.DoubleType():
            return Type.FLOAT  # Return backward compatibility type
        elif isinstance(value.type, ir.PointerType) and value.type.pointee == ir.IntType(8):
            return Type.STRING
        else:
            raise ValueError(f"Unknown LLVM type: {value.type}")

    def _convert_if_needed(self, value, target_type):
        source_type = self._get_type_from_value(value)
        if source_type == target_type:
            return value

        # Map backward compatibility types to their internal representations
        source_type = Type._map_to_internal_type(source_type)
        target_type = Type._map_to_internal_type(target_type)

        # Handle int to float conversions
        if "int" in source_type and "float" in target_type:
            return self.builder.sitofp(value, Type.get_ir_type(target_type), name="int_to_float")
        # Handle float to int conversions
        elif "int" in target_type and "float" in source_type:
            return self.builder.fptosi(value, Type.get_ir_type(target_type), name="float_to_int")
        # Handle float to float conversions
        elif "float" in target_type and "float" in source_type:
            target_ir_type = Type.get_ir_type(target_type)
            source_ir_type = value.type

            # Get the precision levels
            source_precision = Type._numeric_hierarchy.index(source_type)
            target_precision = Type._numeric_hierarchy.index(target_type)

            if target_precision > source_precision:
                # Target type has higher precision, so extend
                return self.builder.fpext(value, target_ir_type, name="float_extend")
            else:
                # Target type has lower precision, so truncate
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
            raise ValueError(f"Cannot convert between types {source_type} and {target_type}")

    def get_ir(self):
        return str(self.module)

    def _generate_if(self, node):
        cond_value = self._generate_expression(node.condition)

        # Make sure we have a boolean result (i1 type)
        if not isinstance(cond_value.type, ir.IntType) or cond_value.type.width != 1:
            # Convert to boolean if needed - comparing with zero
            if isinstance(cond_value.type, ir.IntType):
                zero = ir.Constant(cond_value.type, 0)
                cond_value = self.builder.icmp_signed('!=', cond_value, zero)
            elif isinstance(cond_value.type, (ir.FloatType, ir.DoubleType, ir.HalfType)):
                zero = ir.Constant(cond_value.type, 0)
                cond_value = self.builder.fcmp_ordered('!=', cond_value, zero)
            else:
                # For other types, just ensure we have a boolean
                cond_value = self.builder.trunc(cond_value, ir.IntType(1))

        then_block = self.func.append_basic_block(name="if_then")
        else_block = self.func.append_basic_block(name="if_else") if node.else_body else None
        end_block = self.func.append_basic_block(name="if_end")

        self.builder.cbranch(cond_value, then_block, else_block if else_block else end_block)

        # Generate then block
        self.builder.position_at_end(then_block)
        for stmt in node.body:
            self._generate_node(stmt)
        self.builder.branch(end_block)

        # Generate else block if exists
        if else_block:
            self.builder.position_at_end(else_block)
            for stmt in node.else_body:
                self._generate_node(stmt)
            self.builder.branch(end_block)

        # Move to end block
        self.builder.position_at_end(end_block)

    def _generate_for(self, node):
        # Generate initialization (e.g., int i = 0)
        self._generate_node(node.init)

        cond_block = self.func.append_basic_block(name="for_cond")
        body_block = self.func.append_basic_block(name="for_body")
        update_block = self.func.append_basic_block(name="for_update")
        end_block = self.func.append_basic_block(name="for_end")

        self.builder.branch(cond_block)

        # Generate the loop condition
        self.builder.position_at_end(cond_block)
        cond_value = self._generate_expression(node.condition)

        # Convert condition to boolean by comparing with zero
        if isinstance(cond_value.type, ir.IntType):
            zero = ir.Constant(cond_value.type, 0)
            cond_value = self.builder.icmp_signed('!=', cond_value, zero)
        elif isinstance(cond_value.type, (ir.FloatType, ir.DoubleType, ir.HalfType)):
            zero = ir.Constant(cond_value.type, 0)
            cond_value = self.builder.fcmp_ordered('!=', cond_value, zero)

        self.builder.cbranch(cond_value, body_block, end_block)

        # Generate the body of the loop
        self.builder.position_at_end(body_block)
        for stmt in node.body:
            self._generate_node(stmt)
        self.builder.branch(update_block)

        # Generate the update (e.g., i = i + 1)
        self.builder.position_at_end(update_block)
        self._generate_node(node.update)
        self.builder.branch(cond_block)

        # End of the loop
        self.builder.position_at_end(end_block)

    def _normalize_index(self, index_value):
        if not isinstance(index_value.type, ir.IntType):
            raise ValueError(f"Index must be integer, got {index_value.type}")
        if index_value.type.width != 32:
            index_value = self.builder.trunc(index_value, ir.IntType(32)) if index_value.type.width > 32 \
                else self.builder.sext(index_value, ir.IntType(32))
        return index_value
