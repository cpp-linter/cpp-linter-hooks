#!/usr/bin/env python3
"""Script to extract default clang-format and clang-tidy versions from pyproject.toml."""

import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from cpp_linter_hooks.util import DEFAULT_CLANG_FORMAT_VERSION, DEFAULT_CLANG_TIDY_VERSION

def main():
    """Print the default tool versions."""
    print(f"Default clang-format version: {DEFAULT_CLANG_FORMAT_VERSION}")
    print(f"Default clang-tidy version: {DEFAULT_CLANG_TIDY_VERSION}")
    
    # Also output in a format suitable for GitHub Actions
    print(f"CLANG_FORMAT_VERSION={DEFAULT_CLANG_FORMAT_VERSION}")
    print(f"CLANG_TIDY_VERSION={DEFAULT_CLANG_TIDY_VERSION}")

if __name__ == "__main__":
    main()