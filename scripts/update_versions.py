#!/usr/bin/env python3
"""
Script to update clang-format and clang-tidy versions from PyPI API.

Usage:
    python scripts/update_versions.py
"""

import json
import urllib.request
from pathlib import Path
import re
from typing import List


def fetch_versions_from_pypi(package_name: str) -> List[str]:
    """Fetch available versions for a package from PyPI API."""
    url = f"https://pypi.org/pypi/{package_name}/json"
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.loads(response.read())
            versions = list(data["releases"].keys())
            # Filter out pre-release versions and sort
            stable_versions = [
                v
                for v in versions
                if not any(char in v for char in ["a", "b", "rc", "dev"])
            ]
            return sorted(stable_versions, key=lambda x: tuple(map(int, x.split("."))))
    except Exception as e:
        print(f"Failed to fetch versions for {package_name}: {e}")
        return []


def update_versions_file():
    """Update the versions.py file with latest versions from PyPI."""
    clang_format_versions = fetch_versions_from_pypi("clang-format")
    clang_tidy_versions = fetch_versions_from_pypi("clang-tidy")

    if not clang_format_versions or not clang_tidy_versions:
        print("Failed to fetch versions from PyPI")
        return False

    versions_file = Path(__file__).parent.parent / "cpp_linter_hooks" / "versions.py"

    with open(versions_file, "r") as f:
        content = f.read()

    # Update clang-format versions
    clang_format_list = (
        "[\n" + "\n".join(f'    "{v}",' for v in clang_format_versions) + "\n]"
    )
    content = re.sub(
        r"(CLANG_FORMAT_VERSIONS = )\[.*?\]",
        rf"\1{clang_format_list}",
        content,
        flags=re.DOTALL,
    )

    # Update clang-tidy versions
    clang_tidy_list = (
        "[\n" + "\n".join(f'    "{v}",' for v in clang_tidy_versions) + "\n]"
    )
    content = re.sub(
        r"(CLANG_TIDY_VERSIONS = )\[.*?\]",
        rf"\1{clang_tidy_list}",
        content,
        flags=re.DOTALL,
    )

    with open(versions_file, "w") as f:
        f.write(content)

    print("Updated versions:")
    print(
        f"  clang-format: {len(clang_format_versions)} versions (latest: {clang_format_versions[-1]})"
    )
    print(
        f"  clang-tidy: {len(clang_tidy_versions)} versions (latest: {clang_tidy_versions[-1]})"
    )

    return True


if __name__ == "__main__":
    success = update_versions_file()
    exit(0 if success else 1)
