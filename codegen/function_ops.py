from llvmlite import ir

from ast2 import Type
from codegen import type_utils


def generate_function_declaration(code_gen, node):
    name = node.name
    func = code_gen.module.get_global(name)

    if not func or not isinstance(func, ir.Function):
        raise ValueError(f"Function {name} not properly declared")

    if not func.is_declaration:
        return

    old_func = code_gen.func
    old_builder = code_gen.builder

    code_gen.func = func

    block = func.append_basic_block(name="entry")
    code_gen.builder = ir.IRBuilder(block)

    code_gen.push_scope()

    for i, param in enumerate(node.parameters):
        func.args[i].name = param.name

        if param.type == Type.STRING:
            string_buf = code_gen.builder.alloca(ir.ArrayType(ir.IntType(8), 256), name=f"{param.name}_buf")
            alloc = code_gen.builder.bitcast(string_buf, ir.PointerType(ir.IntType(8)))

            code_gen.declare_variable(param.name, string_buf)

            if not hasattr(code_gen, 'strcpy'):
                strcpy_ty = ir.FunctionType(ir.PointerType(ir.IntType(8)),
                                            [ir.PointerType(ir.IntType(8)), ir.PointerType(ir.IntType(8))])
                code_gen.strcpy = ir.Function(code_gen.module, strcpy_ty, name="strcpy")

            code_gen.builder.call(code_gen.strcpy, [alloc, func.args[i]])
        else:
            alloc = code_gen.builder.alloca(Type.get_ir_type(param.type), name=param.name)
            code_gen.builder.store(func.args[i], alloc)
            code_gen.declare_variable(param.name, alloc)

        code_gen.variable_types[param.name] = param.type

    code_gen.variable_types[name] = node.return_type

    for stmt in node.body:
        code_gen.generate_node(stmt)

    if not code_gen.builder.block.is_terminated:
        if func.function_type.return_type == ir.VoidType():
            code_gen.builder.ret_void()
        else:
            if isinstance(func.function_type.return_type, ir.IntType):
                code_gen.builder.ret(ir.Constant(func.function_type.return_type, 0))
            elif isinstance(func.function_type.return_type, (ir.FloatType, ir.DoubleType, ir.HalfType)):
                code_gen.builder.ret(ir.Constant(func.function_type.return_type, 0.0))
            else:
                pass

    code_gen.pop_scope()

    code_gen.func = old_func
    code_gen.builder = old_builder


def generate_function_call(code_gen, node):
    func = code_gen.module.get_global(node.name)
    if not func or not isinstance(func, ir.Function):
        raise ValueError(f"Function '{node.name}' not declared")

    args = []
    for i, arg_node in enumerate(node.arguments):
        from codegen.expression import generate_expression
        arg_value = generate_expression(code_gen, arg_node)

        if i < len(func.args):
            expected_type = func.args[i].type
            arg_type = arg_value.type

            if (isinstance(expected_type, ir.PointerType) and
                    expected_type.pointee == ir.IntType(8) and
                    isinstance(arg_type, ir.PointerType) and
                    arg_type.pointee == ir.IntType(8)):
                pass
            elif arg_type != expected_type:
                arg_value = type_utils.convert_value_to_type(code_gen, arg_value, expected_type)

        args.append(arg_value)

    call_result = code_gen.builder.call(func, args,
                                        name=f"{node.name}_result" if func.function_type.return_type != ir.VoidType() else "")
    if func.function_type.return_type != ir.VoidType():
        return call_result
    return None


def generate_return(code_gen, node):
    if node.value is None:
        if code_gen.func.function_type.return_type != ir.VoidType():
            raise ValueError("Function with non-void return type must return a value")
        code_gen.builder.ret_void()
        return

    from codegen.expression import generate_expression
    return_value = generate_expression(code_gen, node.value)
    expected_type = code_gen.func.function_type.return_type

    if return_value.type != expected_type:
        return_value = type_utils.convert_value_to_type(code_gen, return_value, expected_type)

    code_gen.builder.ret(return_value)
