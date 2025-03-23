from antlr4.error.ErrorListener import ErrorListener


class JohnsErrorHandler(ErrorListener):
  def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):
    print(f"Syntax error at {line}:{column} - {msg}")
    exit(1)
    super().syntaxError(recognizer, offendingSymbol, line, column, msg, e)

  def reportAmbiguity(self, recognizer, dfa, startIndex, stopIndex, exact,
      ambigAlts, configs):
    super().reportAmbiguity(recognizer, dfa, startIndex, stopIndex, exact,
                            ambigAlts, configs)

  def reportAttemptingFullContext(self, recognizer, dfa, startIndex, stopIndex,
      conflictingAlts, configs):
    super().reportAttemptingFullContext(recognizer, dfa, startIndex, stopIndex,
                                        conflictingAlts, configs)

  def reportContextSensitivity(self, recognizer, dfa, startIndex, stopIndex,
      prediction, configs):
    super().reportContextSensitivity(recognizer, dfa, startIndex, stopIndex,
                                     prediction, configs)