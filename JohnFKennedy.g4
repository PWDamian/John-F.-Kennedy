grammar JohnFKennedy;

// handling unexpected token np. int 0a = 1; zamiast int a = 1;
@members {
    import antlr4

    def report_fx(self, recognizer:Parser):
        self.beginErrorCondition(recognizer)
        t = recognizer.getCurrentToken()
        tokenName = self.getTokenErrorDisplay(t)
        expecting = self.getExpectedTokens(recognizer)
        msg = f"line {recognizer.getCurrentToken().line}:{recognizer.getCurrentToken().column}: extraneous input " + tokenName + " expecting " \
            + expecting.toString(recognizer.literalNames, recognizer.symbolicNames)
        raise Exception(msg)

    antlr4.error.ErrorStrategy.DefaultErrorStrategy.reportUnwantedToken = report_fx
}

program : (statement)+ EOF;

statement
    : type IDENTIFIER ('=' expression)? ';'  # DeclareAssignStatement
    | IDENTIFIER '=' expression ';'          # AssignStatement
    | 'print' expression ';'                 # PrintStatement
    | 'read' IDENTIFIER ';'                  # ReadStatement
    ;

type
    : 'int'    # IntType
    | 'float'  # FloatType
    | 'string'  # StringType
    ;

expression
    : NUMBER                                # NumberExpr
    | FLOAT_NUMBER                          # FloatExpr
    | IDENTIFIER                            # IdentifierExpr
    | QSTRING                               # QstringExpr
    | expression ('+'|'-'|'*'|'/') expression  # BinaryExpr
    | '(' expression ')'                    # ParenExpr
    ;

IDENTIFIER : [a-zA-Z_][a-zA-Z_0-9]* ;
NUMBER : [0-9]+ ;
FLOAT_NUMBER : [0-9]+'.'[0-9]+ ;
WS : [ \t\r\n]+ -> skip ;
QSTRING : '"'([a-zA-Z0-9`~!@#$%^&*()_+\-=:;"'<>,.?/|] | ' ')*'"';
