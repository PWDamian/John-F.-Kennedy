from antlr4.error.ErrorListener import ErrorListener


class JohnsErrorHandler(ErrorListener):
  def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):
    print("Syntax error")
    super().syntaxError(recognizer, offendingSymbol, line, column, msg, e)

  def reportAmbiguity(self, recognizer, dfa, startIndex, stopIndex, exact,
      ambigAlts, configs):
    print("Ambig error")
    super().reportAmbiguity(recognizer, dfa, startIndex, stopIndex, exact,
                            ambigAlts, configs)

  def reportAttemptingFullContext(self, recognizer, dfa, startIndex, stopIndex,
      conflictingAlts, configs):
    print("Attempt full ctx")
    super().reportAttemptingFullContext(recognizer, dfa, startIndex, stopIndex,
                                        conflictingAlts, configs)

  def reportContextSensitivity(self, recognizer, dfa, startIndex, stopIndex,
      prediction, configs):
    print("Cxt sensit")
    super().reportContextSensitivity(recognizer, dfa, startIndex, stopIndex,
                                     prediction, configs)