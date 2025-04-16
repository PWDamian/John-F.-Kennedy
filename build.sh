#!/bin/bash
.venv/bin/pip install -r requirements.txt
antlr4 -Dlanguage=Python3 -visitor JohnFKennedy.g4 -o build