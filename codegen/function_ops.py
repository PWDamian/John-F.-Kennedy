from llvmlite import ir

from ast2 import Type
from codegen import type_utils


def generate_function_declaration(code_gen, node):
    # Check if the function already exists in the module
    name = node.name
    func = code_gen.module.get_global(name)

    # If function doesn't exist yet, this is an error
    if not func or not isinstance(func, ir.Function):
        raise ValueError(f"Function {name} not properly declared")

    # Check if this function already has a body
    if not func.is_declaration:
        return  # Function already defined, skip

    # Save current function and builder state
    old_func = code_gen.func
    old_builder = code_gen.builder
    old_variables = code_gen.variables.copy()

    # Use the existing function
    code_gen.func = func

    # Create entry block
    block = func.append_basic_block(name="entry")
    code_gen.builder = ir.IRBuilder(block)

    # Reset variables for new function scope
    code_gen.variables = {}

    # Set parameter names and create allocations
    for i, param in enumerate(node.parameters):
        func.args[i].name = param.name

        # Special handling for string parameters
        if param.type == Type.STRING:
            # For strings, we allocate a buffer and copy the string
            string_buf = code_gen.builder.alloca(ir.ArrayType(ir.IntType(8), 256), name=f"{param.name}_buf")
            alloc = code_gen.builder.bitcast(string_buf, ir.PointerType(ir.IntType(8)))

            # Store the pointer
            code_gen.variables[param.name] = string_buf

            # Copy the string data
            if not hasattr(code_gen, 'strcpy'):
                strcpy_ty = ir.FunctionType(ir.PointerType(ir.IntType(8)),
                                            [ir.PointerType(ir.IntType(8)), ir.PointerType(ir.IntType(8))])
                code_gen.strcpy = ir.Function(code_gen.module, strcpy_ty, name="strcpy")

            code_gen.builder.call(code_gen.strcpy, [alloc, func.args[i]])
        else:
            # Regular parameter handling
            alloc = code_gen.builder.alloca(Type.get_ir_type(param.type), name=param.name)
            code_gen.builder.store(func.args[i], alloc)
            code_gen.variables[param.name] = alloc

        code_gen.variable_types[param.name] = param.type

    # Generate code for function body
    for stmt in node.body:
        code_gen.generate_node(stmt)

    # If no terminator (return) at the end of the function, add one
    if not code_gen.builder.block.is_terminated:
        if func.function_type.return_type == ir.VoidType():
            code_gen.builder.ret_void()
        else:
            # Default return value based on return type
            if isinstance(func.function_type.return_type, ir.IntType):
                code_gen.builder.ret(ir.Constant(func.function_type.return_type, 0))
            elif isinstance(func.function_type.return_type, (ir.FloatType, ir.DoubleType, ir.HalfType)):
                code_gen.builder.ret(ir.Constant(func.function_type.return_type, 0.0))
            else:
                # Handle other types as needed
                pass

    # Restore old state
    code_gen.func = old_func
    code_gen.builder = old_builder
    code_gen.variables = old_variables


def generate_function_call(code_gen, node):
    """
    Generate code for function calls - works both as an expression and as a statement.
    Returns the result value when the function has a non-void return type.
    """
    # Get function from module
    func = code_gen.module.get_global(node.name)
    if not func or not isinstance(func, ir.Function):
        raise ValueError(f"Function '{node.name}' not declared")

    # Generate arguments
    args = []
    for i, arg_node in enumerate(node.arguments):
        # Use expression module to handle argument evaluation
        from codegen.expression import generate_expression
        arg_value = generate_expression(code_gen, arg_node)

        # If the function expects a different type, perform conversion
        if i < len(func.args):
            expected_type = func.args[i].type
            arg_type = arg_value.type

            # Special handling for string arguments (i8*)
            if (isinstance(expected_type, ir.PointerType) and
                    expected_type.pointee == ir.IntType(8) and
                    isinstance(arg_type, ir.PointerType) and
                    arg_type.pointee == ir.IntType(8)):
                # Ensure string is properly passed as a pointer
                pass
            elif arg_type != expected_type:
                arg_value = type_utils.convert_value_to_type(code_gen, arg_value, expected_type)

        args.append(arg_value)

    # Call function
    call_result = code_gen.builder.call(func, args,
                                        name=f"{node.name}_result" if func.function_type.return_type != ir.VoidType() else "")
    # Only return a value if the function does not return void
    if func.function_type.return_type != ir.VoidType():
        return call_result
    return None


def generate_return(code_gen, node):
    # Handle void return
    if node.value is None:
        if code_gen.func.function_type.return_type != ir.VoidType():
            raise ValueError("Function with non-void return type must return a value")
        code_gen.builder.ret_void()
        return

    # Generate return value
    from codegen.expression import generate_expression
    return_value = generate_expression(code_gen, node.value)
    expected_type = code_gen.func.function_type.return_type

    # Convert if types don't match
    if return_value.type != expected_type:
        return_value = type_utils.convert_value_to_type(code_gen, return_value, expected_type)

    code_gen.builder.ret(return_value)
