import os
import sys


def find_null_bytes(directory):
    corrupted_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'rb') as f:
                        content = f.read()
                        if b'\x00' in content:
                            corrupted_files.append(filepath)
                            print(f"CORRUPTED: {filepath}")
                except Exception as e:
                    print(f"ERROR reading {filepath}: {e}")

    if not corrupted_files:
        print("No corrupted files found.")
    else:
        print(f"\nTotal corrupted files: {len(corrupted_files)}")

    return corrupted_files


if __name__ == "__main__":
    directory = "backend"
    find_null_bytes(directory)
