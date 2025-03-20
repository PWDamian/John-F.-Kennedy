from build.JohnFKennedyParser import JohnFKennedyParser
from build.JohnFKennedyVisitor import JohnFKennedyVisitor

from ast import *


class ASTBuilder(JohnFKennedyVisitor):
    def visitProgram(self, ctx: JohnFKennedyParser.ProgramContext):
        return [self.visit(stmt) for stmt in ctx.statement()]

    def visitDeclareAssignStatement(self, ctx: JohnFKennedyParser.DeclareAssignStatementContext):
        type_name = self.visit(ctx.type_())
        value = self.visit(ctx.expression()) if ctx.expression() else None
        return DeclareAssignNode(type_name, ctx.IDENTIFIER().getText(), value)

    def visitAssignStatement(self, ctx: JohnFKennedyParser.AssignStatementContext):
        return AssignNode(ctx.IDENTIFIER().getText(), self.visit(ctx.expression()))

    def visitPrintStatement(self, ctx: JohnFKennedyParser.PrintStatementContext):
        return PrintNode(self.visit(ctx.expression()))

    def visitReadStatement(self, ctx: JohnFKennedyParser.ReadStatementContext):
        return ReadNode(ctx.IDENTIFIER().getText())

    def visitIntType(self, ctx: JohnFKennedyParser.IntTypeContext):
        return Type.INT

    def visitFloatType(self, ctx: JohnFKennedyParser.FloatTypeContext):
        return Type.FLOAT

    def visitNumberExpr(self, ctx: JohnFKennedyParser.NumberExprContext):
        return NumberNode(int(ctx.NUMBER().getText()), Type.INT)

    def visitFloatExpr(self, ctx: JohnFKennedyParser.FloatExprContext):
        return NumberNode(float(ctx.FLOAT_NUMBER().getText()), Type.FLOAT)

    def visitIdentifierExpr(self, ctx: JohnFKennedyParser.IdentifierExprContext):
        return VariableNode(ctx.IDENTIFIER().getText())

    def visitBinaryExpr(self, ctx: JohnFKennedyParser.BinaryExprContext):
        left = self.visit(ctx.expression(0))
        op = ctx.getChild(1).getText()
        right = self.visit(ctx.expression(1))
        return BinaryOpNode(left, op, right)

    def visitParenExpr(self, ctx: JohnFKennedyParser.ParenExprContext):
        return self.visit(ctx.expression())

    def visitQstringExpr(self, ctx: JohnFKennedyParser.QstringExprContext):
        return StringValueNode(str(ctx.QSTRING().getText())[1:-1])

    def visitStringType(self, ctx: JohnFKennedyParser.StringTypeContext):
        return Type.STRING

    
    
