from .types import Type

OPERATOR_PRECEDENCE = {
    '+': 1,
    '-': 1,
    '*': 2,
    '/': 2,
    '^': 3,
    '&&': 4,
    '||': 5,
    '(': 0,
    ')': 0
}


class ASTNode:
    def __init__(self, line: int, column: int):
        self.line = line
        self.column = column

    def __repr__(self):
        return self.__str__()


class NumberNode(ASTNode):
    def __init__(self, value, line: int, column: int):
        super().__init__(line, column)
        self.value = value
        if isinstance(value, float):
            self.type = self._get_float_for_value(value)
        else:
            self.type = self._get_int_for_value(value)

    def _get_float_for_value(self, value):
        return Type.FLOAT64  # Default to the highest precision for non-decimal floats

    def _get_int_for_value(self, value):
        int_value = int(value)
        if -128 <= int_value <= 127:
            return Type.INT8
        elif -32768 <= int_value <= 32767:
            return Type.INT16
        elif -2147483648 <= int_value <= 2147483647:
            return Type.INT32
        else:
            return Type.INT64

    def __str__(self):
        return f"Number({self.value}, {self.type})"


class BooleanNode(ASTNode):
    def __init__(self, value, line: int, column: int):
        super().__init__(line, column)
        self.value = value
        self.type = Type.BOOL

    def __str__(self):
        return f"Boolean({'true' if self.value else 'false'})"


class StringValueNode(ASTNode):
    def __init__(self, value, line: int, column: int):
        super().__init__(line, column)
        self.value = value

    def __str__(self):
        return f"String({self.value})"


class VariableNode(ASTNode):
    def __init__(self, name, line: int, column: int):
        super().__init__(line, column)
        self.name = name

    def __str__(self):
        return f"Variable({self.name})"


class ArrayAccessNode(ASTNode):
    def __init__(self, name, index, line: int, column: int):
        super().__init__(line, column)
        self.name = name
        self.index = index

    def __str__(self):
        return f"ArrayAccess({self.name}[{self.index}])"


class MatrixAccessNode(ASTNode):
    def __init__(self, name, row_index, col_index, line: int, column: int):
        super().__init__(line, column)
        self.name = name
        self.row_index = row_index
        self.col_index = col_index

    def __str__(self):
        return f"MatrixAccess({self.name}[{self.row_index}][{self.col_index}])"


class BinaryOpNode(ASTNode):
    def __init__(self, left, op, right, line: int, column: int):
        super().__init__(line, column)
        self.left = left
        self.op = op
        self.right = right
        self.precedence = OPERATOR_PRECEDENCE.get(op, 0)

    def __str__(self):
        return f"({self.left} {self.op} {self.right})"


class LogicalOpNode(ASTNode):
    def __init__(self, left, op, right, line: int, column: int):
        super().__init__(line, column)
        self.left = left
        self.op = op
        self.right = right
        self.precedence = OPERATOR_PRECEDENCE.get(op, 0)

    def __str__(self):
        return f"({self.left} {self.op} {self.right})"


class LogicalNotNode(ASTNode):
    def __init__(self, expr, line: int, column: int):
        super().__init__(line, column)
        self.expr = expr

    def __str__(self):
        return f"!({self.expr})"


class ComparisonNode(ASTNode):
    def __init__(self, left, op, right, line: int, column: int):
        super().__init__(line, column)
        self.left = left
        self.op = op
        self.right = right

    def __str__(self):
        return f"({self.left} {self.op} {self.right})"


class AssignNode(ASTNode):
    def __init__(self, name, value, line: int, column: int):
        super().__init__(line, column)
        self.name = name
        self.value = value

    def __str__(self):
        return f"{self.name} = {self.value}"


class ArrayAssignNode(ASTNode):
    def __init__(self, name, index, value, line: int, column: int):
        super().__init__(line, column)
        self.name = name
        self.index = index
        self.value = value

    def __str__(self):
        return f"{self.name}[{self.index}] = {self.value}"


class MatrixAssignNode(ASTNode):
    def __init__(self, name, row_index, col_index, value, line: int, column: int):
        super().__init__(line, column)
        self.name = name
        self.row_index = row_index
        self.col_index = col_index
        self.value = value

    def __str__(self):
        return f"{self.name}[{self.row_index}][{self.col_index}] = {self.value}"


class DeclareAssignNode(ASTNode):
    def __init__(self, type_name, name, line: int, column: int, value=None):
        super().__init__(line, column)
        self.type = type_name
        self.name = name
        self.value = value

    def __str__(self):
        return f"{self.type} {self.name} = {self.value if self.value is not None else 'uninitialized'}"


class DeclareArrayNode(ASTNode):
    def __init__(self, type_name, name, size, line: int, column: int):
        super().__init__(line, column)
        self.type = type_name
        self.name = name
        self.size = size
        self.element_type = type_name.split('_')[1] if '_' in type_name else Type.INT

    def __str__(self):
        return f"{self.type} {self.name}[{self.size}]"


class DeclareMatrixNode(ASTNode):
    def __init__(self, type_name, name, rows, cols, line: int, column: int):
        super().__init__(line, column)
        self.type = type_name
        self.name = name
        self.rows = rows
        self.cols = cols
        self.element_type = type_name.split('_')[1] if '_' in type_name else Type.INT

    def __str__(self):
        return f"{self.type} {self.name}[{self.rows}][{self.cols}]"


class ReadNode(ASTNode):
    def __init__(self, name, line: int, column: int):
        super().__init__(line, column)
        self.name = name

    def __str__(self):
        return f"read {self.name}"


class PrintNode(ASTNode):
    def __init__(self, expression, line: int, column: int):
        super().__init__(line, column)
        self.expression = expression

    def __str__(self):
        return f"print {self.expression}"


class IfNode(ASTNode):
    def __init__(self, condition, body, else_body, line: int, column: int):
        super().__init__(line, column)
        self.condition = condition
        self.body = body
        self.else_body = else_body

    def __str__(self):
        return f"If({self.condition}) {{ {self.body} }} else {{ {self.else_body} }}"


class ForNode(ASTNode):
    def __init__(self, init, condition, update, body, line: int, column: int):
        super().__init__(line, column)
        self.init = init
        self.condition = condition
        self.update = update
        self.body = body

    def __str__(self):
        return f"For({self.init}; {self.condition}; {self.update}) {{ {self.body} }}"


def print_ast_as_tree(node, indent=0):
    prefix = "  " * indent

    if isinstance(node, list):
        print(f"{prefix}Program")
        for child in node:
            print_ast_as_tree(child, indent + 1)
    elif isinstance(node, NumberNode):
        print(f"{prefix}Number: {node.value} ({node.type})")
    elif isinstance(node, BooleanNode):
        print(f"{prefix}Boolean: {'true' if node.value else 'false'}")
    elif isinstance(node, StringValueNode):
        print(f"{prefix}String: \"{node.value}\"")
    elif isinstance(node, VariableNode):
        print(f"{prefix}Variable: {node.name}")
    elif isinstance(node, ArrayAccessNode):
        print(f"{prefix}ArrayAccess: {node.name}")
        print(f"{prefix}  Index:")
        print_ast_as_tree(node.index, indent + 2)
    elif isinstance(node, BinaryOpNode):
        print(f"{prefix}BinaryOp: {node.op}")
        print(f"{prefix}  Left:")
        print_ast_as_tree(node.left, indent + 2)
        print(f"{prefix}  Right:")
        print_ast_as_tree(node.right, indent + 2)
    elif isinstance(node, LogicalOpNode):
        print(f"{prefix}LogicalOp: {node.op}")
        print(f"{prefix}  Left:")
        print_ast_as_tree(node.left, indent + 2)
        print(f"{prefix}  Right:")
        print_ast_as_tree(node.right, indent + 2)
    elif isinstance(node, LogicalNotNode):
        print(f"{prefix}LogicalNot:")
        print(f"{prefix}  Expression:")
        print_ast_as_tree(node.expr, indent + 2)
    elif isinstance(node, AssignNode):
        print(f"{prefix}Assign: {node.name}")
        print(f"{prefix}  Value:")
        print_ast_as_tree(node.value, indent + 2)
    elif isinstance(node, ArrayAssignNode):
        print(f"{prefix}ArrayAssign: {node.name}")
        print(f"{prefix}  Index:")
        print_ast_as_tree(node.index, indent + 2)
        print(f"{prefix}  Value:")
        print_ast_as_tree(node.value, indent + 2)
    elif isinstance(node, DeclareAssignNode):
        print(f"{prefix}DeclareAssign: {node.name} ({node.type})")
        if node.value is not None:
            print(f"{prefix}  Value:")
            print_ast_as_tree(node.value, indent + 2)
        else:
            print(f"{prefix}  Uninitialized")
    elif isinstance(node, DeclareArrayNode):
        print(f"{prefix}DeclareArray: {node.name} ({node.type}[{node.size}])")
    elif isinstance(node, PrintNode):
        print(f"{prefix}Print:")
        print_ast_as_tree(node.expression, indent + 1)
    elif isinstance(node, ReadNode):
        print(f"{prefix}Read: {node.name}")
    elif isinstance(node, MatrixAccessNode):
        print(f"{prefix}MatrixAccess: {node.name}")
        print(f"{prefix}  Row Index:")
        print_ast_as_tree(node.row_index, indent + 2)
        print(f"{prefix}  Column Index:")
        print_ast_as_tree(node.col_index, indent + 2)
    elif isinstance(node, DeclareMatrixNode):
        print(f"{prefix}DeclareMatrix: {node.name} ({node.type}[{node.rows}][{node.cols}])")
    elif isinstance(node, MatrixAssignNode):
        print(f"{prefix}MatrixAssign: {node.name}")
        print(f"{prefix}  Row Index:")
        print_ast_as_tree(node.row_index, indent + 2)
        print(f"{prefix}  Column Index:")
        print_ast_as_tree(node.col_index, indent + 2)
        print(f"{prefix}  Value:")
        print_ast_as_tree(node.value, indent + 2)
    elif isinstance(node, ComparisonNode):
        print(f"{prefix}Comparison: {node.op}")
        print(f"{prefix}  Left:")
        print_ast_as_tree(node.left, indent + 2)
        print(f"{prefix}  Right:")
        print_ast_as_tree(node.right, indent + 2)
    elif isinstance(node, IfNode):
        print(f"{prefix}If Statement:")
        print(f"{prefix}  Condition:")
        print_ast_as_tree(node.condition, indent + 2)
        print(f"{prefix}  Then Body:")
        for stmt in node.body:
            print_ast_as_tree(stmt, indent + 3)
        if node.else_body:
            print(f"{prefix}  Else Body:")
            for stmt in node.else_body:
                print_ast_as_tree(stmt, indent + 3)
    elif isinstance(node, ForNode):
        print(f"{prefix}For Loop:")
        print(f"{prefix}  Init:")
        print_ast_as_tree(node.init, indent + 2)
        print(f"{prefix}  Condition:")
        print_ast_as_tree(node.condition, indent + 2)
        print(f"{prefix}  Update:")
        print_ast_as_tree(node.update, indent + 2)
        print(f"{prefix}  Body:")
        for stmt in node.body:
            print_ast_as_tree(stmt, indent + 3)
    else:
        print(f"{prefix}Unknown node type: {type(node)}")
