grammar JohnFKennedy;

// handling errors
@members {
    from JohnsErrorHandler import JohnsErrorHandler
    self.addErrorListener(JohnsErrorHandler())
}

program : (statement)+ EOF;

statement
    : type IDENTIFIER ('=' expression)? ';'  # DeclareAssignStatement
    | IDENTIFIER '=' expression ';'          # AssignStatement
    | 'print' expression ';'                 # PrintStatement
    | 'read' IDENTIFIER ';'                  # ReadStatement
    ;

type
    : 'int8'      # Int8Type
    | 'int16'     # Int16Type
    | 'int32'     # Int32Type
    | 'int'       # IntType
    | 'float16'   # Float16Type
    | 'float32'   # Float32Type
    | 'float'     # FloatType
    | 'string'    # StringType
    ;

expression
    : addExpression
    ;

addExpression
    : multiplyExpression                          # PassThroughAddExpr
    | addExpression ('+'|'-') multiplyExpression  # AddExpr
    ;

multiplyExpression
    : primaryExpression                              # PassThroughMultiplyExpr
    | multiplyExpression ('*'|'/') primaryExpression # MultiplyExpr
    ;

primaryExpression
    : NUMBER                                # NumberExpr
    | FLOAT_NUMBER                          # FloatExpr
    | IDENTIFIER                            # IdentifierExpr
    | QSTRING                               # QstringExpr
    | '(' expression ')'                    # ParenExpr
    ;

IDENTIFIER : [a-zA-Z_][a-zA-Z_0-9]* ;
NUMBER : [0-9]+ ;
FLOAT_NUMBER : [0-9]+'.'[0-9]+ ;
WS : [ \t\r\n]+ -> skip ;
QSTRING : '"'([a-zA-Z0-9`~!@#$%^&*()_+\-=:;"'<>,.?/|] | ' ')*'"';
