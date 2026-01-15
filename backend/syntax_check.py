import os
import ast
import sys


def check_syntax(directory):
    print(f"Checking syntax in {directory}...")
    failed = False
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".py"):
                path = os.path.join(root, file)
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        source = f.read()
                    ast.parse(source)
                    print(f"✅ {file} - OK")
                except SyntaxError as e:
                    print(f"❌ {file} - Syntax Error: {e}")
                    failed = True
                except Exception as e:
                    print(f"⚠️ {file} - Could not read/parse: {e}")
    if failed:
        sys.exit(1)
    else:
        print("All files passed syntax check.")


if __name__ == "__main__":
    check_syntax(".")
