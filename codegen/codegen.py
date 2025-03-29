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
        self.functions = {}  # Store function declarations

    def generate_code(self, ast):
        # First pass: collect function declarations
        for node in ast:
            if isinstance(node, FunctionDeclarationNode):
                self.functions[node.name] = node

        # Create forward declarations for all functions before processing main
        self._create_function_declarations()

        # Create main function if it doesn't exist
        if 'main' not in self.functions:
            self._create_main_function()

            # Process all non-function nodes in main
            for node in ast:
                if not isinstance(node, FunctionDeclarationNode):
                    try:
                        self.generate_node(node)
                    except Exception as e:
                        if None not in [node.line, node.column]:
                            print(f"Error at {node.line}:{node.column}:")
                        else:
                            print(node)
                        print(f"\tMessage: {str(e)}")
                        exit(1)

            # Add a return statement if main doesn't have one
            if not self.builder.block.is_terminated:
                self.builder.ret(ir.Constant(ir.IntType(32), 0))

        # Second pass: generate code for all functions
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
                    exit(1)

    def _create_function_declarations(self):
        """Create LLVM IR declarations for all functions before defining them"""
        for name, func_node in self.functions.items():
            # Get return type (using Type.VOID or Type.get_ir_type)
            return_type = Type.get_ir_type(func_node.return_type)

            # Get parameter types
            param_types = [Type.get_ir_type(param.type) for param in func_node.parameters]

            # Create function type and declaration
            func_type = ir.FunctionType(return_type, param_types)

            # Check if function already exists (don't recreate it)
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

    def get_ir(self):
        return str(self.module)
