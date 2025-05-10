import traceback

from llvmlite import ir

from ast2 import AssignNode, DeclareAssignNode, PrintNode, ReadNode, DeclareArrayNode, ArrayAssignNode, \
    DeclareMatrixNode, MatrixAssignNode, IfNode, ForNode, FunctionDeclarationNode, FunctionCallNode, ReturnNode, \
    Type, StructDeclarationNode, DeclareStructNode, StructFieldAssignNode, StructFieldAccessNode
from codegen import flow_ops, array_ops, io_ops, matrix_ops, variables, function_ops, struct_ops


def is_declare_node(node):
    return (isinstance(node, DeclareAssignNode)
            or isinstance(node, DeclareMatrixNode)
            or isinstance(node, DeclareArrayNode)
            or isinstance(node, DeclareStructNode))


class CodeGenerator:
    def __init__(self):
        self.module = ir.Module(name="JohnFKennedy")
        self.module.triple = "x86_64-pc-linux-gnu"
        self.builder = None
        self.func = None
        self.array_sizes = {}
        self.array_element_types = {}
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
        self.block_counter = 0
        self.in_function = False
        self.functions = {}
        self.scopes = [{}]
        self.global_variables = {}

    def push_scope(self):
        self.scopes.append({})

    def pop_scope(self):
        if len(self.scopes) > 1:
            self.scopes.pop()

    def declare_variable(self, name, var_ptr, var_type):
        self.scopes[-1][name] = (var_ptr, var_type)
        if len(self.scopes) == 1:
            self.global_variables[name] = (var_ptr, var_type)

    def get_variable(self, name):
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name][0]

        if name in self.global_variables:
            return self.global_variables[name][0]

        raise ValueError(f"Variable {name} not declared")

    def get_variable_type(self, name):
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name][1]

        if name in self.global_variables:
            return self.global_variables[name][1]

        raise ValueError(f"Variable {name} not declared")

    def generate_code(self, ast):
        # First pass: register function and struct types
        for node in ast:
            if isinstance(node, FunctionDeclarationNode):
                self.functions[node.name] = node
            if isinstance(node, StructDeclarationNode):
                struct_ops.generate_struct_declaration(self, node)

        self._create_function_declarations()

        # Second pass: handle variable declarations
        for node in ast:
            if (is_declare_node(node)) and not isinstance(node, FunctionDeclarationNode):
                # Only emit declarations without initializers or with constant initializers
                is_const_init = False
                if hasattr(node, 'value') and node.value is not None:
                    # Check if the initializer is a constant (number or string literal)
                    from ast2 import NumberNode, StringValueNode, BooleanNode
                    is_const_init = isinstance(node.value, (NumberNode, StringValueNode, BooleanNode))
                if not hasattr(node, 'value') or node.value is None or is_const_init:
                    try:
                        if self.builder is None:
                            self._create_main_function()
                        self.generate_node(node)
                    except Exception as e:
                        if None not in [node.line, node.column]:
                            print(f"Error at {node.line}:{node.column}:")
                        else:
                            print(node)
                        print(f"\tMessage: {str(e)} for node `{node}`")
                        traceback.print_exc()
                        exit(1)

        # Third pass: handle function definitions
        for node in ast:
            if isinstance(node, FunctionDeclarationNode):
                try:
                    self.generate_node(node)
                except Exception as e:
                    if None not in [node.line, node.column]:
                        print(f"Error at {node.line}:{node.column}:")
                    else:
                        print(node)
                    print(f"\tMessage: {str(e)} for node `{node}`")
                    traceback.print_exc()
                    exit(1)

        # Fourth pass: handle statements in main
        if 'main' not in self.functions:
            if self.func is None or self.func.name != "main":
                self._create_main_function()

            # First, emit all assignment and matrix assignment statements
            for node in ast:
                if isinstance(node, AssignNode) or isinstance(node, MatrixAssignNode):
                    try:
                        self.generate_node(node)
                    except Exception as e:
                        if None not in [node.line, node.column]:
                            print(f"Error at {node.line}:{node.column}:")
                        else:
                            print(node)
                        print(f"\tMessage: {str(e)} for node `{node}`")
                        traceback.print_exc()
                        exit(1)

            # Then, emit all other statements, including declarations with non-constant initializers
            for node in ast:
                is_nonconst_decl = False
                if (is_declare_node(node)) and not isinstance(node, FunctionDeclarationNode):
                    if hasattr(node, 'value') and node.value is not None:
                        from ast2 import NumberNode, StringValueNode, BooleanNode
                        is_nonconst_decl = not isinstance(node.value, (NumberNode, StringValueNode, BooleanNode))
                if (not isinstance(node, FunctionDeclarationNode) and not isinstance(node, StructDeclarationNode) and not (
                        is_declare_node(node) and not isinstance(node, FunctionDeclarationNode) and not is_nonconst_decl) and not isinstance(node, AssignNode) and not isinstance(node, MatrixAssignNode)) or is_nonconst_decl:
                    try:
                        self.generate_node(node)
                    except Exception as e:
                        if None not in [node.line, node.column]:
                            print(f"Error at {node.line}:{node.column}:")
                        else:
                            print(node)
                        print(f"\tMessage: {str(e)} for node `{node}`")
                        traceback.print_exc()
                        exit(1)

        if 'main' not in self.functions and not self.builder.block.is_terminated:
            self.builder.ret(ir.Constant(ir.IntType(32), 0))

    def _create_function_declarations(self):
        for name, func_node in self.functions.items():
            return_type = Type.get_ir_type(func_node.return_type)
            param_types = [Type.get_ir_type(param.type) for param in func_node.parameters]
            func_type = ir.FunctionType(return_type, param_types)
            if name not in self.module.globals:
                ir.Function(self.module, func_type, name=name)

    def _create_main_function(self):
        func_type = ir.FunctionType(ir.IntType(32), [])
        self.func = ir.Function(self.module, func_type, name="main")
        block = self.func.append_basic_block(name="entry")
        self.builder = ir.IRBuilder(block)

    def generate_node(self, node):
        if isinstance(node, AssignNode):
            variables.generate_assign(self, node)
        elif isinstance(node, DeclareAssignNode):
            variables.generate_declare_assign(self, node)
        elif isinstance(node, PrintNode):
            io_ops.generate_print(self, node)
        elif isinstance(node, ReadNode):
            io_ops.generate_read(self, node)
        elif isinstance(node, DeclareArrayNode):
            array_ops.generate_declare_array(self, node)
        elif isinstance(node, ArrayAssignNode):
            array_ops.generate_array_assign(self, node)
        elif isinstance(node, DeclareMatrixNode):
            matrix_ops.generate_declare_matrix(self, node)
        elif isinstance(node, MatrixAssignNode):
            matrix_ops.generate_matrix_assign(self, node)
        elif isinstance(node, IfNode):
            flow_ops.generate_if(self, node)
        elif isinstance(node, ForNode):
            flow_ops.generate_for(self, node)
        elif isinstance(node, FunctionDeclarationNode):
            function_ops.generate_function_declaration(self, node)
        elif isinstance(node, FunctionCallNode):
            function_ops.generate_function_call(self, node)
        elif isinstance(node, ReturnNode):
            function_ops.generate_return(self, node)
        elif isinstance(node, StructDeclarationNode):
            struct_ops.generate_struct_declaration(self, node)
        elif isinstance(node, DeclareStructNode):
            struct_ops.generate_declare_struct(self, node)
        elif isinstance(node, StructFieldAssignNode):
            struct_ops.generate_struct_field_assign(self, node)
        elif isinstance(node, StructFieldAccessNode):
            # Return the result of the field access
            return struct_ops.generate_struct_field_access(self, node)

    def get_ir(self):
        return str(self.module)
