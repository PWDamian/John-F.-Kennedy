grammar JohnFKennedy;

// handling errors
@members {
    from JohnsErrorHandler import JohnsErrorHandler
    self.addErrorListener(JohnsErrorHandler())
}

program : (statement)+ EOF;

type
    : 'int8'      # Int8Type
    | 'int16'     # Int16Type
    | 'int32'     # Int32Type
    | 'int64'     # Int64Type
    | 'int'       # IntType      // Alias for int64
    | 'float16'   # Float16Type
    | 'float32'   # Float32Type
    | 'float64'   # Float64Type
    | 'float'     # FloatType    // Alias for float64
    | 'string'    # StringType
    ;

arrayType
    : 'array_int8'      # ArrayInt8Type
    | 'array_int16'     # ArrayInt16Type
    | 'array_int32'     # ArrayInt32Type
    | 'array_int64'     # ArrayInt64Type
    | 'array_int'       # ArrayIntType     // Alias for array_int64
    | 'array_float16'   # ArrayFloat16Type
    | 'array_float32'   # ArrayFloat32Type
    | 'array_float64'   # ArrayFloat64Type
    | 'array_float'     # ArrayFloatType   // Alias for array_float64
    | 'array_string'    # ArrayStringType
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

matrixType
    : 'matrix_int8'     # MatrixInt8Type
    | 'matrix_int16'    # MatrixInt16Type
    | 'matrix_int32'    # MatrixInt32Type
    | 'matrix_int64'    # MatrixInt64Type
    | 'matrix_int'      # MatrixIntType    // Alias for matrix_int64
    | 'matrix_float16'  # MatrixFloat16Type
    | 'matrix_float32'  # MatrixFloat32Type
    | 'matrix_float64'  # MatrixFloat64Type
    | 'matrix_float'    # MatrixFloatType  // Alias for matrix_float64
    ;

statement
    : type IDENTIFIER ('=' expression)? ';'                        # DeclareAssignStatement
    | arrayType IDENTIFIER '[' NUMBER ']' ';'                      # DeclareArrayStatement
    | matrixType IDENTIFIER '[' NUMBER ']' '[' NUMBER ']' ';'      # DeclareMatrixStatement
    | IDENTIFIER '=' expression ';'                                # AssignStatement
    | IDENTIFIER '[' expression ']' '=' expression ';'             # ArrayAssignStatement
    | IDENTIFIER '[' expression ']' '[' expression ']' '=' expression ';'  # MatrixAssignStatement
    | 'print' expression ';'                                       # PrintStatement
    | 'read' IDENTIFIER ';'                                        # ReadStatement
    ;

primaryExpression
    : NUMBER                                         # NumberExpr
    | FLOAT_NUMBER                                   # FloatExpr
    | IDENTIFIER                                     # IdentifierExpr
    | IDENTIFIER '[' expression ']'                  # ArrayAccessExpr
    | IDENTIFIER '[' expression ']' '[' expression ']'  # MatrixAccessExpr
    | QSTRING                                        # QstringExpr
    | '(' expression ')'                             # ParenExpr
    ;

IDENTIFIER : [a-zA-Z_][a-zA-Z_0-9]* ;
NUMBER : [0-9]+ ;
FLOAT_NUMBER : [0-9]+'.'[0-9]+ ;
WS : [ \t\r\n]+ -> skip ;
QSTRING : '"'([a-zA-Z0-9`~!@#$%^&*()_+\-=:;"'<>,.?/|] | ' ')*'"';