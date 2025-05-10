import argparse
import glob
import os
import subprocess
from enum import Enum

from antlr4 import FileStream, CommonTokenStream
from build.JohnFKennedyLexer import JohnFKennedyLexer
from build.JohnFKennedyParser import JohnFKennedyParser

from JohnsErrorHandler import JohnsErrorHandler
from ast2 import *
from ast2.visitor import ASTBuilder
from codegen.codegen import CodeGenerator


class TestType(Enum):
    NORMAL = "normal"  # Tests that need input
    AUTO = "auto"  # Tests that run without input
    ALL = "all"  # Run all tests


def compile_jfk_file(input_file, show_ast=True, show_llvm=True, run_binary=True, input_values=None):
    """Compile a single JFK file and optionally run it with provided input"""
    print(f"\n=== Compiling {input_file} ===\n")

    input_stream = FileStream(input_file)
    try:
        lexer = JohnFKennedyLexer(input_stream)
        token_stream = CommonTokenStream(lexer)
        parser = JohnFKennedyParser(token_stream)
        parser.addErrorListener(JohnsErrorHandler)
        tree = parser.program()

        ast_builder = ASTBuilder()
        ast = ast_builder.visit(tree)

        if show_ast:
            print("AST:")
            for node in ast:
                print(node)

            print("\nAST as tree:")
            print_ast_as_tree(ast)

        codegen = CodeGenerator()
        codegen.generate_code(ast)
        llvm_ir = codegen.get_ir()

        if show_llvm:
            print("\nLLVM IR:")
            print(llvm_ir)
    except Exception as e:
        print(f"Error during compilation: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

    base_name = os.path.basename(input_file).split('.')[0]
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)

    ir_file = os.path.join(output_dir, f"{base_name}.ll")
    with open(ir_file, "w") as f:
        f.write(llvm_ir)

    asm_file = os.path.join(output_dir, f"{base_name}.s")
    binary_file = os.path.join(output_dir, base_name)

    try:
        subprocess.run(["llc", ir_file, "-o", asm_file], check=True)
        subprocess.run(["clang", asm_file, "-o", binary_file], check=True)
        print(f"Kompilacja IR do kodu maszynowego zakończona!")

        if run_binary:
            print(f"\nUruchamiam wygenerowany program: {binary_file}")

            if input_values:
                # Run with provided input
                process = subprocess.Popen(
                    [f"./{binary_file}"],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                stdout, stderr = process.communicate(input=input_values)

                print("\nOutput:")
                print(stdout)

                if stderr:
                    print("\nErrors:")
                    print(stderr)

                if process.returncode != 0:
                    print(f"\nUwaga: Program zakończył się kodem {process.returncode}")

            else:
                # Run normally if no input provided
                result = subprocess.run([f"./{binary_file}"], check=False)
                if result.returncode != 0:
                    print(f"\nUwaga: Program zakończył się kodem {result.returncode}")

    except subprocess.CalledProcessError as e:
        print(f"RuntimeError: {e}")
        return False

    return True


def find_test_files(test_dir, test_type):
    """Find test files based on test type"""
    if test_type == TestType.AUTO:
        pattern = os.path.join(test_dir, "auto_*.jfk")
    elif test_type == TestType.NORMAL:
        pattern = os.path.join(test_dir, "normal_*.jfk")
    else:  # ALL
        pattern = os.path.join(test_dir, "*.jfk")

    return sorted(glob.glob(pattern))


def load_input_data(test_file):
    """Load input data for a test if available"""
    input_file = test_file.replace('.jfk', '.input')
    if os.path.exists(input_file):
        with open(input_file, 'r') as f:
            return f.read()
    return None


def main():
    # Set up command line arguments
    parser = argparse.ArgumentParser(description='JFK Compiler and Test Runner')
    group = parser.add_mutually_exclusive_group()

    group.add_argument('file', nargs='?', help='Single JFK file to compile')
    group.add_argument('-d', '--directory', help='Directory containing test files')

    parser.add_argument('-t', '--type', choices=['normal', 'auto', 'all'],
                        default='all', help='Type of tests to run')
    parser.add_argument('--show-ast', action='store_true', help='Display AST output')
    parser.add_argument('--show-llvm', action='store_true', help='Display LLVM IR output')
    parser.add_argument('--no-run', action='store_true', help='Do not run the compiled binary')

    args = parser.parse_args()

    if args.file:
        input_values = load_input_data(args.file)
        compile_jfk_file(args.file, args.show_ast, args.show_llvm, not args.no_run, input_values)

    elif args.directory:
        test_type = TestType(args.type)
        test_files = find_test_files(args.directory, test_type)

        if not test_files:
            print(f"No test files found in {args.directory} with type {test_type.value}")
            return

        failed_tests = []
        for test_file in test_files:
            input_values = load_input_data(test_file)
            if not compile_jfk_file(test_file, args.show_ast, args.show_llvm, not args.no_run, input_values):
                failed_tests.append(test_file)

        print(f"\n=== Test Summary ===")
        print(f"Tests run: {len(test_files)}")
        print(f"Tests passed: {len(test_files) - len(failed_tests)}")
        print(f"Tests failed: {len(failed_tests)}")
        if failed_tests:
            print("\nFailed tests:")
            for test in failed_tests:
                print(f"- {test}")

    else:
        print("Please provide a file to compile or use -d to specify a test directory")
        parser.print_help()


if __name__ == "__main__":
    main()
