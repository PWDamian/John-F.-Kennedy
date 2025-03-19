grammar JohnFKennedy;

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
    ;

expression
    : NUMBER                                # NumberExpr
    | FLOAT_NUMBER                          # FloatExpr
    | IDENTIFIER                            # IdentifierExpr
    | expression ('+'|'-'|'*'|'/') expression  # BinaryExpr
    | '(' expression ')'                    # ParenExpr
    ;

IDENTIFIER : [a-zA-Z_][a-zA-Z_0-9]* ;
NUMBER : [0-9]+ ;
FLOAT_NUMBER : [0-9]+'.'[0-9]+ ;
WS : [ \t\r\n]+ -> skip ;
