import os
import sys
import subprocess
from antlr4 import FileStream, CommonTokenStream

from JohnsErrorHandler import JohnsErrorHandler
from build.JohnFKennedyLexer import JohnFKennedyLexer
from build.JohnFKennedyParser import JohnFKennedyParser
from visitor import ASTBuilder
from codegen import CodeGenerator
from ast_1 import *


def main():
    if len(sys.argv) < 2:
        print("Użycie: python src/compiler.py examples/test.jfk")
        sys.exit(1)

    input_file = sys.argv[1]
    input_stream = FileStream(input_file)
    lexer = JohnFKennedyLexer(input_stream)
    token_stream = CommonTokenStream(lexer)
    parser = JohnFKennedyParser(token_stream)
    parser.addErrorListener(JohnsErrorHandler)
    tree = parser.program()

    ast_builder = ASTBuilder()
    ast = ast_builder.visit(tree)

    print("AST:")
    for node in ast:
        print(node)

    print("AST as tree:")
    print_ast_as_tree(ast)

    codegen = CodeGenerator()
    codegen.generate_code(ast)
    llvm_ir = codegen.get_ir()
    print("\nLLVM IR:")
    print(llvm_ir)

    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)

    ir_file = os.path.join(output_dir, "output.ll")
    with open(ir_file, "w") as f:
        f.write(llvm_ir)

    asm_file = os.path.join(output_dir, "output.s")
    binary_file = os.path.join(output_dir, "output")
    subprocess.run(["llc", ir_file, "-o", asm_file], check=True)
    subprocess.run(["clang", asm_file, "-o", binary_file], check=True)
    print(f"\nKompilacja IR do kodu maszynowego zakończona!")

    print("\nUruchamiam wygenerowany program:")
    result = subprocess.run([f"./{binary_file}"], check=False)
    if result.returncode != 0:
        print(f"\nUwaga: Program zakończył się kodem {result.returncode}")

if __name__ == "__main__":
    main()
