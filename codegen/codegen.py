import traceback

from llvmlite import ir

from ast2 import AssignNode, DeclareAssignNode, PrintNode, ReadNode, DeclareArrayNode, ArrayAssignNode, \
    DeclareMatrixNode, MatrixAssignNode, IfNode, ForNode, FunctionDeclarationNode, FunctionCallNode, ReturnNode, Type
from codegen import flow_ops, array_ops, io_ops, matrix_ops, variables, function_ops


class CodeGenerator:
    def __init__(self):
        self.module = ir.Module(name="JohnFKennedy")
        self.module.triple = "x86_64-pc-linux-gnu"
        self.builder = None
        self.func = None
        self.variables = {}
        self.variable_types = {}
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

    def declare_variable(self, name, var_ptr):
        self.scopes[-1][name] = var_ptr
        if len(self.scopes) == 1:
            self.global_variables[name] = var_ptr

    def get_variable(self, name):
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]

        if name in self.global_variables:
            return self.global_variables[name]

        return None

    def generate_code(self, ast):
        for node in ast:
            if isinstance(node, FunctionDeclarationNode):
                self.functions[node.name] = node

        self._create_function_declarations()

        for node in ast:
            if isinstance(node, DeclareAssignNode) and not isinstance(node, FunctionDeclarationNode):
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

        if 'main' not in self.functions:
            if self.func is None or self.func.name != "main":
                self._create_main_function()

            for node in ast:
                if not isinstance(node, FunctionDeclarationNode) and not (
                        isinstance(node, DeclareAssignNode) and not isinstance(node, FunctionDeclarationNode)):
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

        for node in ast:
            if isinstance(node, FunctionDeclarationNode):
                try:
                    self.generate_node(node)
                except Exception as e:
                    if None not in [node.line, node.column]:
                        print(f"Error at {node.line}:{node.column}:")
                    else:
                        print(node)
                    print(f"\tMessage: {str(e)}")
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
            self.push_scope()
            function_ops.generate_function_declaration(self, node)
            self.pop_scope()
        elif isinstance(node, FunctionCallNode):
            function_ops.generate_function_call(self, node)
        elif isinstance(node, ReturnNode):
            function_ops.generate_return(self, node)

    def get_ir(self):
        return str(self.module)
