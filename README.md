# John F. Kennedy

A simple programming language compiler implemented in Python, using ANTLR4 for parsing and LLVM for code generation.

## Setup

```sh
./build.sh
```

## Tests

### Running

- **Single test file:**
    ```sh
    python compiler.py tests/auto_void_function.jfk
    ```

- **All automatic tests (no input):**
    ```sh
    python compiler.py -d tests -t auto
    ```

- **All tests that require input:**
    ```sh
    python compiler.py -d tests -t normal
    ```

- **All tests:**
    ```sh
    python compiler.py -d tests -t all
    ```

### Additional Options

- **Show AST:**
    ```sh
    python compiler.py --show-ast2
    ```

- **Show LLVM IR:**
    ```sh
    python compiler.py --show-llvm
    ```

- **Do not run the binary:**
    ```sh
    python compiler.py --no-run
    ```

### File Naming

- `auto_*.jfk`: Tests that don't require user input.
- `normal_*.jfk`: Tests that need user input.
- `*.input`: Optional input files (must match the JFK filename).