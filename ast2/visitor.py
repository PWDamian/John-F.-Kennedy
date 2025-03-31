from build.JohnFKennedyParser import JohnFKennedyParser
from build.JohnFKennedyVisitor import JohnFKennedyVisitor

from ast2 import *
from ast2.nodes import ParameterNode


class ASTBuilder(JohnFKennedyVisitor):
    def visitProgram(self, ctx: JohnFKennedyParser.ProgramContext):
        return [self.visit(decl) for decl in ctx.topLevelDeclaration()]

    def visitDeclareAssignStatement(self,
                                    ctx: JohnFKennedyParser.DeclareAssignStatementContext):
        type_name = self.visit(ctx.type_())
        value = self.visit(ctx.expression()) if ctx.expression() else None
        return DeclareAssignNode(type_name, ctx.IDENTIFIER().getText(), ctx.start.line, ctx.start.column, value)

    def visitDeclareArrayStatement(self,
                                   ctx: JohnFKennedyParser.DeclareArrayStatementContext):
        type_name = self.visit(ctx.arrayType())
        size = int(ctx.NUMBER().getText())
        return DeclareArrayNode(type_name, ctx.IDENTIFIER().getText(), size, ctx.start.line, ctx.start.column)

    def visitAssignStatement(self,
                             ctx: JohnFKennedyParser.AssignStatementContext):
        return AssignNode(ctx.IDENTIFIER().getText(), self.visit(ctx.expression()), ctx.start.line, ctx.start.column)

    def visitArrayAssignStatement(self,
                                  ctx: JohnFKennedyParser.ArrayAssignStatementContext):
        name = ctx.IDENTIFIER().getText()
        index = self.visit(ctx.expression(0))
        value = self.visit(ctx.expression(1))
        return ArrayAssignNode(name, index, value, ctx.start.line, ctx.start.column)

    def visitPrintStatement(self, ctx: JohnFKennedyParser.PrintStatementContext):
        return PrintNode(self.visit(ctx.expression()), ctx.start.line, ctx.start.column)

    def visitReadStatement(self, ctx: JohnFKennedyParser.ReadStatementContext):
        return ReadNode(ctx.IDENTIFIER().getText(), ctx.start.line, ctx.start.column)

    def visitNumberExpr(self, ctx: JohnFKennedyParser.NumberExprContext):
        return NumberNode(int(ctx.NUMBER().getText()), ctx.start.line, ctx.start.column)

    def visitFloatExpr(self, ctx: JohnFKennedyParser.FloatExprContext):
        return NumberNode(float(ctx.FLOAT_NUMBER().getText()), ctx.start.line, ctx.start.column)

    def visitBooleanExpr(self, ctx: JohnFKennedyParser.BooleanExprContext):
        value = ctx.BOOLEAN_LITERAL().getText()
        return BooleanNode(value == 'true', ctx.start.line, ctx.start.column)

    def visitIdentifierExpr(self, ctx: JohnFKennedyParser.IdentifierExprContext):
        return VariableNode(ctx.IDENTIFIER().getText(), ctx.start.line, ctx.start.column)

    def visitArrayAccessExpr(self, ctx: JohnFKennedyParser.ArrayAccessExprContext):
        name = ctx.IDENTIFIER().getText()
        index = self.visit(ctx.expression())
        return ArrayAccessNode(name, index, ctx.start.line, ctx.start.column)

    def visitPassThroughAddExpr(self, ctx: JohnFKennedyParser.PassThroughAddExprContext):
        return self.visit(ctx.multiplyExpression())

    def visitAddExpr(self, ctx: JohnFKennedyParser.AddExprContext):
        left = self.visit(ctx.addExpression())
        op = ctx.getChild(1).getText()
        right = self.visit(ctx.multiplyExpression())
        return BinaryOpNode(left, op, right, ctx.start.line, ctx.start.column)

    def visitPassThroughMultiplyExpr(self, ctx: JohnFKennedyParser.PassThroughMultiplyExprContext):
        return self.visit(ctx.primaryExpression())

    def visitMultiplyExpr(self, ctx: JohnFKennedyParser.MultiplyExprContext):
        left = self.visit(ctx.multiplyExpression())
        op = ctx.getChild(1).getText()
        right = self.visit(ctx.primaryExpression())
        return BinaryOpNode(left, op, right, ctx.start.line, ctx.start.column)

    def visitParenExpr(self, ctx: JohnFKennedyParser.ParenExprContext):
        return self.visit(ctx.expression())

    def visitQstringExpr(self, ctx: JohnFKennedyParser.QstringExprContext):
        return StringValueNode(str(ctx.QSTRING().getText())[1:-1], ctx.start.line, ctx.start.column)

    # Logical operator handlers
    def visitPassThroughOrExpr(self, ctx: JohnFKennedyParser.PassThroughOrExprContext):
        return self.visit(ctx.logicalXorExpression())

    def visitLogicalOrExpr(self, ctx: JohnFKennedyParser.LogicalOrExprContext):
        left = self.visit(ctx.logicalOrExpression())
        right = self.visit(ctx.logicalXorExpression())
        return LogicalOpNode(left, '||', right, ctx.start.line, ctx.start.column)

    def visitPassThroughXorExpr(self, ctx: JohnFKennedyParser.PassThroughXorExprContext):
        return self.visit(ctx.logicalAndExpression())

    def visitLogicalXorExpr(self, ctx: JohnFKennedyParser.LogicalXorExprContext):
        left = self.visit(ctx.logicalXorExpression())
        right = self.visit(ctx.logicalAndExpression())
        return LogicalOpNode(left, '^', right, ctx.start.line, ctx.start.column)

    def visitPassThroughAndExpr(self, ctx: JohnFKennedyParser.PassThroughAndExprContext):
        return self.visit(ctx.notExpression())

    def visitLogicalAndExpr(self, ctx: JohnFKennedyParser.LogicalAndExprContext):
        left = self.visit(ctx.logicalAndExpression())
        right = self.visit(ctx.notExpression())
        return LogicalOpNode(left, '&&', right, ctx.start.line, ctx.start.column)

    def visitPassThroughNotExpr(self, ctx: JohnFKennedyParser.PassThroughNotExprContext):
        return self.visit(ctx.comparisonExpression())

    def visitLogicalNotExpr(self, ctx: JohnFKennedyParser.LogicalNotExprContext):
        expr = self.visit(ctx.notExpression())
        return LogicalNotNode(expr, ctx.start.line, ctx.start.column)

    def visitVoidType(self, ctx: JohnFKennedyParser.VoidTypeContext):
        return Type.VOID

    def visitStringType(self, ctx: JohnFKennedyParser.StringTypeContext):
        return Type.STRING

    def visitBoolType(self, ctx: JohnFKennedyParser.BoolTypeContext):
        return Type.BOOL

    def visitInt8Type(self, ctx: JohnFKennedyParser.Int8TypeContext):
        return Type.INT8

    def visitInt16Type(self, ctx: JohnFKennedyParser.Int16TypeContext):
        return Type.INT16

    def visitInt32Type(self, ctx: JohnFKennedyParser.Int32TypeContext):
        return Type.INT32

    def visitInt64Type(self, ctx: JohnFKennedyParser.Int64TypeContext):
        return Type.INT64

    def visitIntType(self, ctx: JohnFKennedyParser.IntTypeContext):
        return Type.INT  # Alias for INT64

    def visitFloat16Type(self, ctx: JohnFKennedyParser.Float16TypeContext):
        return Type.FLOAT16

    def visitFloat32Type(self, ctx: JohnFKennedyParser.Float32TypeContext):
        return Type.FLOAT32

    def visitFloat64Type(self, ctx: JohnFKennedyParser.Float64TypeContext):
        return Type.FLOAT64

    def visitFloatType(self, ctx: JohnFKennedyParser.FloatTypeContext):
        return Type.FLOAT  # Alias for FLOAT64

    # Array types
    def visitArrayInt8Type(self, ctx: JohnFKennedyParser.ArrayInt8TypeContext):
        return "array_int8"

    def visitArrayInt16Type(self, ctx: JohnFKennedyParser.ArrayInt16TypeContext):
        return "array_int16"

    def visitArrayInt32Type(self, ctx: JohnFKennedyParser.ArrayInt32TypeContext):
        return "array_int32"

    def visitArrayInt64Type(self, ctx: JohnFKennedyParser.ArrayInt64TypeContext):
        return "array_int64"

    def visitArrayIntType(self, ctx: JohnFKennedyParser.ArrayIntTypeContext):
        return "array_int"  # Alias for array_int64

    def visitArrayFloat16Type(self, ctx: JohnFKennedyParser.ArrayFloat16TypeContext):
        return "array_float16"

    def visitArrayFloat32Type(self, ctx: JohnFKennedyParser.ArrayFloat32TypeContext):
        return "array_float32"

    def visitArrayFloat64Type(self, ctx: JohnFKennedyParser.ArrayFloat64TypeContext):
        return "array_float64"

    def visitArrayFloatType(self, ctx: JohnFKennedyParser.ArrayFloatTypeContext):
        return "array_float"  # Alias for array_float64

    def visitArrayStringType(self, ctx: JohnFKennedyParser.ArrayStringTypeContext):
        return "array_string"

    def visitArrayBoolType(self, ctx: JohnFKennedyParser.ArrayBoolTypeContext):
        return "array_bool"

    def visitDeclareMatrixStatement(self, ctx: JohnFKennedyParser.DeclareMatrixStatementContext):
        type_name = self.visit(ctx.matrixType())
        rows = int(ctx.NUMBER(0).getText())
        cols = int(ctx.NUMBER(1).getText())
        return DeclareMatrixNode(type_name, ctx.IDENTIFIER().getText(), rows, cols, ctx.start.line, ctx.start.column)

    def visitMatrixAssignStatement(self, ctx: JohnFKennedyParser.MatrixAssignStatementContext):
        name = ctx.IDENTIFIER().getText()
        row_index = self.visit(ctx.expression(0))
        col_index = self.visit(ctx.expression(1))
        value = self.visit(ctx.expression(2))
        return MatrixAssignNode(name, row_index, col_index, value, ctx.start.line, ctx.start.column)

    def visitMatrixAccessExpr(self, ctx: JohnFKennedyParser.MatrixAccessExprContext):
        name = ctx.IDENTIFIER().getText()
        row_index = self.visit(ctx.expression(0))
        col_index = self.visit(ctx.expression(1))
        return MatrixAccessNode(name, row_index, col_index, ctx.start.line, ctx.start.column)

    def visitMatrixInt8Type(self, ctx: JohnFKennedyParser.MatrixInt8TypeContext):
        return "matrix_int8"

    def visitMatrixInt16Type(self, ctx: JohnFKennedyParser.MatrixInt16TypeContext):
        return "matrix_int16"

    def visitMatrixInt32Type(self, ctx: JohnFKennedyParser.MatrixInt32TypeContext):
        return "matrix_int32"

    def visitMatrixInt64Type(self, ctx: JohnFKennedyParser.MatrixInt64TypeContext):
        return "matrix_int64"

    def visitMatrixIntType(self, ctx: JohnFKennedyParser.MatrixIntTypeContext):
        return "matrix_int"  # Alias for matrix_int64

    def visitMatrixFloat16Type(self, ctx: JohnFKennedyParser.MatrixFloat16TypeContext):
        return "matrix_float16"

    def visitMatrixFloat32Type(self, ctx: JohnFKennedyParser.MatrixFloat32TypeContext):
        return "matrix_float32"

    def visitMatrixFloat64Type(self, ctx: JohnFKennedyParser.MatrixFloat64TypeContext):
        return "matrix_float64"

    def visitMatrixFloatType(self, ctx: JohnFKennedyParser.MatrixFloatTypeContext):
        return "matrix_float"  # Alias for matrix_float64

    def visitMatrixBoolType(self, ctx: JohnFKennedyParser.MatrixBoolTypeContext):
        return "matrix_bool"

    def visitPassThroughComparisonExpr(self, ctx: JohnFKennedyParser.PassThroughComparisonExprContext):
        return self.visit(ctx.addExpression())

    def visitComparisonExpr(self, ctx: JohnFKennedyParser.ComparisonExprContext):
        left = self.visit(ctx.addExpression(0))
        op = ctx.getChild(1).getText()
        right = self.visit(ctx.addExpression(1))
        return ComparisonNode(left, op, right, ctx.start.line, ctx.start.column)

    def visitIfStatement(self, ctx: JohnFKennedyParser.IfStatementContext):
        condition = self.visit(ctx.expression())
        body = [self.visit(stmt) for stmt in ctx.statement()]
        else_body = [self.visit(stmt) for stmt in ctx.elseStatement().statement()] if ctx.elseStatement() else None
        return IfNode(condition, body, else_body, ctx.start.line, ctx.start.column)

    def visitForLoop(self, ctx: JohnFKennedyParser.ForLoopContext):
        init_is_assign = False
        if ctx.declareAssignStatement():
            init = self.visit(ctx.declareAssignStatement())
        elif ctx.assignStatement():
            init = self.visit(ctx.assignStatement(0))
            init_is_assign = True
        else:
            init = None

        condition = self.visit(ctx.expression())

        update_index = 1 if init_is_assign else 0
        update = self.visit(ctx.assignStatement(update_index))

        body = [self.visit(stmt) for stmt in ctx.statement()]

        return ForNode(init, condition, update, body, ctx.start.line, ctx.start.column)

    def visitFunctionDeclaration(self, ctx: JohnFKennedyParser.FunctionDeclarationContext):
        return_type = self.visit(ctx.type_())
        name = ctx.IDENTIFIER().getText()

        parameters = []
        if ctx.parameterList():
            parameters = self.visit(ctx.parameterList())

        body = [self.visit(stmt) for stmt in ctx.statement()]

        return FunctionDeclarationNode(return_type, name, parameters, body, ctx.start.line, ctx.start.column)

    def visitParameterList(self, ctx: JohnFKennedyParser.ParameterListContext):
        return [self.visit(param) for param in ctx.parameter()]

    def visitParameter(self, ctx: JohnFKennedyParser.ParameterContext):
        type_name = self.visit(ctx.type_())
        name = ctx.IDENTIFIER().getText()
        return ParameterNode(type_name, name, ctx.start.line, ctx.start.column)

    def visitReturnStatement(self, ctx: JohnFKennedyParser.ReturnStatementContext):
        value = self.visit(ctx.expression()) if ctx.expression() else None
        return ReturnNode(value, ctx.start.line, ctx.start.column)

    def visitFunctionCall(self, ctx: JohnFKennedyParser.FunctionCallContext):
        name = ctx.IDENTIFIER().getText()
        arguments = []
        if ctx.argumentList():
            arguments = self.visit(ctx.argumentList())
        return FunctionCallNode(name, arguments, ctx.start.line, ctx.start.column)

    def visitArgumentList(self, ctx: JohnFKennedyParser.ArgumentListContext):
        return [self.visit(expr) for expr in ctx.expression()]

    def visitFunctionCallStatement(self, ctx: JohnFKennedyParser.FunctionCallStatementContext):
        return self.visit(ctx.functionCall())

    def visitFunctionCallExpr(self, ctx: JohnFKennedyParser.FunctionCallExprContext):
        return self.visit(ctx.functionCall())
