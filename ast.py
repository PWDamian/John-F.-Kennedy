class ASTNode:
    def __repr__(self):
        return self.__str__()


class Type:
    INT = "int"
    FLOAT = "float"


class NumberNode(ASTNode):
    def __init__(self, value, type_name=Type.INT):
        self.value = value
        self.type = type_name

    def __str__(self):
        return f"Number({self.value}, {self.type})"


class VariableNode(ASTNode):
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return f"Variable({self.name})"


class BinaryOpNode(ASTNode):
    def __init__(self, left, op, right):
        self.left = left
        self.op = op
        self.right = right

    def __str__(self):
        return f"({self.left} {self.op} {self.right})"


class AssignNode(ASTNode):
    def __init__(self, name, value):
        self.name = name
        self.value = value

    def __str__(self):
        return f"{self.name} = {self.value}"


class DeclareAssignNode(ASTNode):
    def __init__(self, type_name, name, value=None):
        self.type = type_name
        self.name = name
        self.value = value

    def __str__(self):
        return f"{self.type} {self.name} = {self.value if self.value is not None else 'uninitialized'}"


class ReadNode(ASTNode):
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return f"read {self.name}"


class PrintNode(ASTNode):
    def __init__(self, expression):
        self.expression = expression

    def __str__(self):
        return f"print {self.expression}"


def print_ast_as_tree(node, indent=0):
    prefix = "  " * indent

    if isinstance(node, list):
        print(f"{prefix}Program")
        for child in node:
            print_ast_as_tree(child, indent + 1)
    elif isinstance(node, NumberNode):
        print(f"{prefix}Number: {node.value} ({node.type})")
    elif isinstance(node, VariableNode):
        print(f"{prefix}Variable: {node.name}")
    elif isinstance(node, BinaryOpNode):
        print(f"{prefix}BinaryOp: {node.op}")
        print(f"{prefix}  Left:")
        print_ast_as_tree(node.left, indent + 2)
        print(f"{prefix}  Right:")
        print_ast_as_tree(node.right, indent + 2)
    elif isinstance(node, AssignNode):
        print(f"{prefix}Assign: {node.name}")
        print(f"{prefix}  Value:")
        print_ast_as_tree(node.value, indent + 2)
    elif isinstance(node, DeclareAssignNode):
        print(f"{prefix}DeclareAssign: {node.name} ({node.type})")
        if node.value is not None:
            print(f"{prefix}  Value:")
            print_ast_as_tree(node.value, indent + 2)
        else:
            print(f"{prefix}  Uninitialized")
    elif isinstance(node, PrintNode):
        print(f"{prefix}Print:")
        print_ast_as_tree(node.expression, indent + 1)
    elif isinstance(node, ReadNode):
        print(f"{prefix}Read: {node.name}")
    else:
        print(f"{prefix}Unknown node type: {type(node)}")
