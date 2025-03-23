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

  def visitIntType(self, ctx: JohnFKennedyParser.IntTypeContext):
    return Type.INT

  def visitFloatType(self, ctx: JohnFKennedyParser.FloatTypeContext):
    return Type.FLOAT

  def visitNumberExpr(self, ctx: JohnFKennedyParser.NumberExprContext):
    print("start, stop", ctx.start, ctx.stop)
    return NumberNode(int(ctx.NUMBER().getText()), ctx.start.line, ctx.start.column, Type.INT)

  def visitFloatExpr(self, ctx: JohnFKennedyParser.FloatExprContext):
    print("start, stop", ctx.start, ctx.stop)
    return NumberNode(float(ctx.FLOAT_NUMBER().getText()), ctx.start.line, ctx.start.column, Type.FLOAT)

  def visitIdentifierExpr(self, ctx: JohnFKennedyParser.IdentifierExprContext):
    print("start, stop", ctx.start, ctx.stop)
    return VariableNode(ctx.IDENTIFIER().getText(), ctx.start.line, ctx.start.column)

  def visitBinaryExpr(self, ctx: JohnFKennedyParser.BinaryExprContext):
    print("start, stop", ctx.start, ctx.stop)
    left = self.visit(ctx.expression(0))
    op = ctx.getChild(1).getText()
    right = self.visit(ctx.expression(1))
    return BinaryOpNode(left, op, right, ctx.start.line, ctx.start.column)

  def visitParenExpr(self, ctx: JohnFKennedyParser.ParenExprContext):
    return self.visit(ctx.expression())

  def visitQstringExpr(self, ctx: JohnFKennedyParser.QstringExprContext):
    return StringValueNode(str(ctx.QSTRING().getText())[1:-1], ctx.start.line, ctx.start.column)

  def visitStringType(self, ctx: JohnFKennedyParser.StringTypeContext):
    return Type.STRING
