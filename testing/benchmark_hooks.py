#!/usr/bin/env python3
"""
Benchmark script to compare performance of cpp-linter-hooks vs mirrors-clang-format using hyperfine.

Usage:
    python benchmark_hooks.py
    # or directly with hyperfine:
    hyperfine --warmup 1 -r 5 'pre-commit run --config ../testing/benchmark_hook_1.yaml --all-files' 'pre-commit run --config ../testing/benchmark_hook_2.yaml --all-files'

Requirements:
- pre-commit must be installed and available in PATH
- Two config files:
    - testing/cpp-linter-hooks.yaml
    - testing/mirrors-clang-format.yaml
- Target files: testing/examples/*.c (or adjust as needed)
"""

import os
import subprocess
import sys

HOOKS = [
    {
        "name": "cpp-linter-hooks",
        "config": "../testing/benchmark_hook_1.yaml",
    },
    {
        "name": "mirrors-clang-format",
        "config": "../testing/benchmark_hook_2.yaml",
    },
]

REPEATS = 5
RESULTS_FILE = "testing/benchmark_results.txt"


def prepare_code():
    try:
        subprocess.run(
            [
                "git",
                "clone",
                "--depth",
                "1",
                "https://github.com/gouravthakur39/beginners-C-program-examples.git",
                "examples",
            ],
            check=True,
        )
    except subprocess.CalledProcessError:
        pass


def run_hyperfine():
    os.chdir("examples")
    commands = [
        f"pre-commit run --config {hook['config']} --all-files" for hook in HOOKS
    ]
    hyperfine_cmd = [
        "hyperfine",
        "--warmup",
        "1",
        "-r",
        str(REPEATS),
    ] + commands
    print("Running benchmark with hyperfine:")
    print(" ".join(hyperfine_cmd))
    try:
        subprocess.run(hyperfine_cmd, check=True)
    except FileNotFoundError:
        print(
            "hyperfine is not installed. Please install it with 'cargo install hyperfine' or 'brew install hyperfine'."
        )
        sys.exit(1)
    os.chdir("..")


def main():
    prepare_code()
    run_hyperfine()


if __name__ == "__main__":
    main()
