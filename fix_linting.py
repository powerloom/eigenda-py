#!/usr/bin/env python3
"""Fix common linting issues in the codebase."""

import os
import re


def fix_f541_issues(content):
    """Fix f-strings without placeholders."""
    # Pattern to find f-strings without any {} placeholders
    pattern = r'"([^"]*?)"'

    def replacer(match):
        string_content = match.group(1)
        if "{" not in string_content:
            # It's an f-string without placeholders, convert to regular string
            return f'"{string_content}"'
        return match.group(0)

    content = re.sub(pattern, replacer, content)

    # Same for single quotes
    pattern = r"'([^']*?)'"

    def replacer_single(match):
        string_content = match.group(1)
        if "{" not in string_content:
            return f"'{string_content}'"
        return match.group(0)

    return re.sub(pattern, replacer_single, content)


def fix_file(filepath):
    """Fix linting issues in a single file."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        original_content = content

        # Fix f-strings without placeholders
        content = fix_f541_issues(content)

        # Add newline at end of file if missing
        if content and not content.endswith("\n"):
            content += "\n"

        # Remove trailing whitespace
        lines = content.split("\n")
        lines = [line.rstrip() for line in lines]
        content = "\n".join(lines)

        if content != original_content:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"Fixed: {filepath}")
            return True
    except Exception as e:
        print(f"Error processing {filepath}: {e}")

    return False


def main():
    """Fix linting issues in Python files."""
    fixed_count = 0

    # Find all Python files
    for root, dirs, files in os.walk("."):
        # Skip directories
        if any(
            skip in root
            for skip in [
                ".git",
                "__pycache__",
                "build",
                "dist",
                ".eggs",
                ".venv",
                "venv",
                ".tox",
                ".pytest_cache",
                "htmlcov",
                "src/eigenda/grpc/",
            ]
        ):
            continue

        for file in files:
            if file.endswith(".py"):
                filepath = os.path.join(root, file)
                if fix_file(filepath):
                    fixed_count += 1

    print(f"\nFixed {fixed_count} files")


if __name__ == "__main__":
    main()
