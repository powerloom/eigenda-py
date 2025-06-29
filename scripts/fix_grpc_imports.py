#!/usr/bin/env python3
"""Fix double imports in generated gRPC files."""

import re
from pathlib import Path

def fix_grpc_imports():
    root = Path(__file__).parent.parent / "src" / "eigenda" / "grpc"
    
    # Pattern to match the double import issue
    pattern = re.compile(r'from (eigenda\.grpc\.[.\w]+) import eigenda\.grpc\.([.\w]+) as')
    
    # Fix both pb2 and pb2_grpc files
    for py_file in root.rglob("*.py"):
        if py_file.name.endswith("_pb2.py") or py_file.name.endswith("_pb2_grpc.py"):
            content = py_file.read_text()
            
            # Fix the double import pattern
            fixed_content = pattern.sub(r'from \1 import \2 as', content)
            
            if fixed_content != content:
                print(f"Fixing imports in {py_file.relative_to(root.parent.parent)}")
                py_file.write_text(fixed_content)

if __name__ == "__main__":
    fix_grpc_imports()
    print("Done!")