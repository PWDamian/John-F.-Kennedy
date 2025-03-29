from llvmlite import ir

from ast2 import AssignNode, DeclareAssignNode, PrintNode, ReadNode, DeclareArrayNode, ArrayAssignNode, \
    DeclareMatrixNode, MatrixAssignNode, IfNode, ForNode
from codegen import flow_ops, array_ops, io_ops, matrix_ops, variables


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

    def get_ir(self):
        return str(self.module)
