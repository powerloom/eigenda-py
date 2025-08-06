#!/usr/bin/env python3
"""Generate Python gRPC code from proto files."""

import subprocess
import sys
from pathlib import Path


def main():
    # Get project root
    root_dir = Path(__file__).parent.parent
    proto_dir = root_dir / "protos"
    output_dir = root_dir / "src" / "eigenda" / "grpc"

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Create __init__.py in grpc directory
    (output_dir / "__init__.py").write_text('"""Generated gRPC code for EigenDA."""\n')

    # Find all proto files
    proto_files = []
    for proto_file in proto_dir.rglob("*.proto"):
        # Skip vendor/third-party protos if any
        if "vendor" not in str(proto_file):
            proto_files.append(str(proto_file))

    if not proto_files:
        print("No proto files found!")
        sys.exit(1)

    print(f"Found {len(proto_files)} proto files")

    # Generate Python code
    cmd = [
        sys.executable,
        "-m",
        "grpc_tools.protoc",
        f"--proto_path={proto_dir}",
        f"--python_out={output_dir}",
        f"--grpc_python_out={output_dir}",
    ] + proto_files

    print("Running protoc...")
    print(" ".join(cmd))

    try:
        subprocess.run(cmd, check=True)
        print("Successfully generated gRPC code!")
    except subprocess.CalledProcessError as e:
        print(f"Error generating gRPC code: {e}")
        sys.exit(1)

    # Fix imports in generated files
    print("Fixing imports in generated files...")
    fix_imports(output_dir)

    print("Done!")


def fix_imports(output_dir: Path):
    """Fix relative imports in generated proto files."""
    for py_file in output_dir.rglob("*.py"):
        if py_file.name.endswith("_pb2.py") or py_file.name.endswith("_pb2_grpc.py"):
            content = py_file.read_text()

            # Fix the double import issue first
            content = content.replace(
                "from eigenda.grpc.common import eigenda.grpc.common_pb2",
                "from eigenda.grpc.common import common_pb2",
            )
            content = content.replace(
                "from eigenda.grpc.common.v2 import eigenda.grpc.common_v2_pb2",
                "from eigenda.grpc.common.v2 import common_v2_pb2",
            )

            # Fix imports to use eigenda.grpc prefix
            content = content.replace("import common", "import eigenda.grpc.common")
            content = content.replace("from common", "from eigenda.grpc.common")
            content = content.replace("import disperser", "import eigenda.grpc.disperser")
            content = content.replace("from disperser", "from eigenda.grpc.disperser")
            content = content.replace("import encoder", "import eigenda.grpc.encoder")
            content = content.replace("from encoder", "from eigenda.grpc.encoder")
            content = content.replace("import retriever", "import eigenda.grpc.retriever")
            content = content.replace("from retriever", "from eigenda.grpc.retriever")
            content = content.replace("import validator", "import eigenda.grpc.validator")
            content = content.replace("from validator", "from eigenda.grpc.validator")
            content = content.replace("import churner", "import eigenda.grpc.churner")
            content = content.replace("from churner", "from eigenda.grpc.churner")
            content = content.replace("import node", "import eigenda.grpc.node")
            content = content.replace("from node", "from eigenda.grpc.node")
            content = content.replace("import relay", "import eigenda.grpc.relay")
            content = content.replace("from relay", "from eigenda.grpc.relay")

            py_file.write_text(content)


if __name__ == "__main__":
    main()
