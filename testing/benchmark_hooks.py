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

import os
import subprocess
import time
import statistics
import glob

HOOKS = [
    {
        "name": "cpp-linter-hooks",
        "config": "testing/benchmark_hook_1.yaml",
    },
    {
        "name": "mirrors-clang-format",
        "config": "testing/benchmark_hook_2.yaml",
    },
]

# Automatically find all C/C++ files in testing/ (and optionally src/, include/)
TARGET_FILES = glob.glob("testing/test-examples/*.c", recursive=True)

REPEATS = 5
RESULTS_FILE = "testing/benchmark_results.txt"


def git_clone():
    try:
        subprocess.run(
            [
                "git",
                "clone",
                "--depth",
                "1",
                "https://github.com/gouravthakur39/beginners-C-program-examples.git",
                "testing/test-examples",
            ],
            check=True,
        )
    except subprocess.CalledProcessError:
        pass


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


def safe_git_restore(files):
    # Only restore files tracked by git
    tracked = []
    for f in files:
        result = subprocess.run(
            ["git", "ls-files", "--error-unmatch", f],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if result.returncode == 0:
            tracked.append(f)
    if tracked:
        subprocess.run(["git", "restore"] + tracked)


def benchmark():
    results = {}
    for hook in HOOKS:
        times = []
        print(f"\nBenchmarking {hook['name']}...")
        for i in range(REPEATS):
            safe_git_restore(TARGET_FILES)
            subprocess.run(["pre-commit", "clean"])
            t = run_hook(hook["config"], TARGET_FILES)
            print(f"  Run {i + 1}: {t:.3f} seconds")
            times.append(t)
        results[hook["name"]] = times
    return results


def report(results):
    headers = ["Hook", "Avg (s)", "Std (s)", "Min (s)", "Max (s)", "Runs"]
    col_widths = [max(len(h), 16) for h in headers]
    # Calculate max width for each column
    for name, times in results.items():
        col_widths[0] = max(col_widths[0], len(name))
    print("\nBenchmark Results:\n")
    # Print header
    header_row = " | ".join(h.ljust(w) for h, w in zip(headers, col_widths))
    print(header_row)
    print("-+-".join("-" * w for w in col_widths))
    # Print rows
    lines = []
    for name, times in results.items():
        avg = statistics.mean(times)
        std = statistics.stdev(times) if len(times) > 1 else 0.0
        min_t = min(times)
        max_t = max(times)
        row = [
            name.ljust(col_widths[0]),
            f"{avg:.3f}".ljust(col_widths[1]),
            f"{std:.3f}".ljust(col_widths[2]),
            f"{min_t:.3f}".ljust(col_widths[3]),
            f"{max_t:.3f}".ljust(col_widths[4]),
            str(len(times)).ljust(col_widths[5]),
        ]
        print(" | ".join(row))
        lines.append(" | ".join(row))
    # Save to file
    with open(RESULTS_FILE, "w") as f:
        f.write(header_row + "\n")
        f.write("-+-".join("-" * w for w in col_widths) + "\n")
        for line in lines:
            f.write(line + "\n")
    print(f"\nResults saved to {RESULTS_FILE}")

    # Write to GitHub Actions summary if available
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a") as f:
            f.write("## Benchmark Results\n\n")
            f.write(header_row + "\n")
            f.write("-+-".join("-" * w for w in col_widths) + "\n")
            for line in lines:
                f.write(line + "\n")
            f.write("\n")


def main():
    git_clone()
    results = benchmark()
    report(results)


if __name__ == "__main__":
    main()
