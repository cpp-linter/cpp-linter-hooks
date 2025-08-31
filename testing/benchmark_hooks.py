#!/usr/bin/env python3
"""
Benchmark script to compare performance of cpp-linter-hooks vs mirrors-clang-format.

Usage:
  python benchmark_hooks.py

Requirements:
- pre-commit must be installed and available in PATH
- Two config files:
    - testing/pre-commit-config-cpp-linter-hooks.yaml
    - testing/pre-commit-config-mirrors-clang-format.yaml
- Target files: testing/main.c (or adjust as needed)
"""

import subprocess
import time
import statistics
import glob

HOOKS = [
    {
        "name": "cpp-linter-hooks",
        "config": "testing/pre-commit-config-cpp-linter-hooks.yaml",
    },
    {
        "name": "mirrors-clang-format",
        "config": "testing/pre-commit-config-mirrors-clang-format.yaml",
    },
]

# Automatically find all C/C++ files in testing/ (and optionally src/, include/)
TARGET_FILES = (
    glob.glob("testing/**/*.c", recursive=True)
    + glob.glob("testing/**/*.cpp", recursive=True)
    + glob.glob("testing/**/*.h", recursive=True)
    + glob.glob("testing/**/*.hpp", recursive=True)
)

REPEATS = 5
RESULTS_FILE = "testing/benchmark_results.txt"


def run_hook(config, files):
    cmd = ["pre-commit", "run", "--config", config, "--files"] + files
    start = time.perf_counter()
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError:
        # Still record time even if hook fails
        pass
    end = time.perf_counter()
    return end - start


def benchmark():
    results = {}
    for hook in HOOKS:
        times = []
        print(f"Benchmarking {hook['name']}...")
        for i in range(REPEATS):
            # Clean up any changes before each run
            subprocess.run(["git", "restore"] + TARGET_FILES)
            subprocess.run(["pre-commit", "clean"])
            t = run_hook(hook["config"], TARGET_FILES)
            print(f"  Run {i + 1}: {t:.3f} seconds")
            times.append(t)
        results[hook["name"]] = times
    return results


def report(results):
    lines = []
    for name, times in results.items():
        avg = statistics.mean(times)
        std = statistics.stdev(times) if len(times) > 1 else 0.0
        min_t = min(times)
        max_t = max(times)
        lines.append(
            f"{name}: avg={avg:.3f}s, std={std:.3f}s, min={min_t:.3f}s, max={max_t:.3f}s, runs={len(times)}"
        )
    print("\nBenchmark Results:")
    print("\n".join(lines))
    with open(RESULTS_FILE, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"Results saved to {RESULTS_FILE}")


def main():
    results = benchmark()
    report(results)


if __name__ == "__main__":
    main()
