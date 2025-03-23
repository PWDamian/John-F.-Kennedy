from build.JohnFKennedyParser import JohnFKennedyParser
from build.JohnFKennedyVisitor import JohnFKennedyVisitor

from ast import *


class ASTBuilder(JohnFKennedyVisitor):
    def visitProgram(self, ctx: JohnFKennedyParser.ProgramContext):
        return [self.visit(stmt) for stmt in ctx.statement()]

    def visitDeclareAssignStatement(self,
                                    ctx: JohnFKennedyParser.DeclareAssignStatementContext):
        type_name = self.visit(ctx.type_())
        value = self.visit(ctx.expression()) if ctx.expression() else None
        return DeclareAssignNode(type_name, ctx.IDENTIFIER().getText(), ctx.start.line, ctx.start.column, value)

    def visitAssignStatement(self,
                             ctx: JohnFKennedyParser.AssignStatementContext):
        return AssignNode(ctx.IDENTIFIER().getText(), self.visit(ctx.expression()), ctx.start.line, ctx.start.column)

    def visitPrintStatement(self, ctx: JohnFKennedyParser.PrintStatementContext):
        return PrintNode(self.visit(ctx.expression()), ctx.start.line, ctx.start.column)

    def visitReadStatement(self, ctx: JohnFKennedyParser.ReadStatementContext):
        return ReadNode(ctx.IDENTIFIER().getText(), ctx.start.line, ctx.start.column)

    def visitNumberExpr(self, ctx: JohnFKennedyParser.NumberExprContext):
        return NumberNode(int(ctx.NUMBER().getText()), ctx.start.line, ctx.start.column)

    def visitFloatExpr(self, ctx: JohnFKennedyParser.FloatExprContext):
        return NumberNode(float(ctx.FLOAT_NUMBER().getText()), ctx.start.line, ctx.start.column)

    def visitIdentifierExpr(self, ctx: JohnFKennedyParser.IdentifierExprContext):
        return VariableNode(ctx.IDENTIFIER().getText(), ctx.start.line, ctx.start.column)

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

    def visitStringType(self, ctx: JohnFKennedyParser.StringTypeContext):
        return Type.STRING

    def visitInt8Type(self, ctx: JohnFKennedyParser.Int8TypeContext):
        return Type.INT8

    def visitInt16Type(self, ctx: JohnFKennedyParser.Int16TypeContext):
        return Type.INT16

    def visitInt32Type(self, ctx: JohnFKennedyParser.Int32TypeContext):
        return Type.INT32

    # int64
    def visitIntType(self, ctx: JohnFKennedyParser.IntTypeContext):
        return Type.INT

    def visitFloat16Type(self, ctx: JohnFKennedyParser.Float16TypeContext):
        return Type.FLOAT16

    def visitFloat32Type(self, ctx: JohnFKennedyParser.Float32TypeContext):
        return Type.FLOAT32

    # float64
    def visitFloatType(self, ctx: JohnFKennedyParser.FloatTypeContext):
        return Type.FLOAT
