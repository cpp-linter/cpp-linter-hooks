#!/usr/bin/env python3
"""
Benchmark script to compare performance of cpp-linter-hooks vs mirrors-clang-format.

Usage:
  python benchmark_hooks.py

Requirements:
- pre-commit must be installed and available in PATH
- Two config files:
    - testing/cpp-linter-hooks.yaml
    - testing/mirrors-clang-format.yaml
- Target files: testing/examples/*.c (or adjust as needed)
"""

import os
import subprocess
import time
import statistics

HOOKS = [
    {
        "name": "mirrors-clang-format",
        "config": "testing/benchmark_hook_2.yaml",
    },
    {
        "name": "cpp-linter-hooks",
        "config": "testing/benchmark_hook_1.yaml",
    },
]

REPEATS = 5
RESULTS_FILE = "testing/benchmark_results.txt"


def prepare_code():
    try:
        subprocess.run(["rm", "-rf", "testing/examples"], check=True)
        subprocess.run(
            [
                "git",
                "clone",
                "--depth",
                "1",
                "https://github.com/gouravthakur39/beginners-C-program-examples.git",
                "testing/examples",
            ],
            check=True,
        )
    except subprocess.CalledProcessError:
        pass


def run_hook(config):
    cmd = ["pre-commit", "run", "--config", config, "--all-files"]
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
    os.chdir("testing/examples")
    for hook in HOOKS:
        times = []
        print(f"\nBenchmarking {hook['name']}...")
        for i in range(REPEATS):
            prepare_code()
            subprocess.run(["pre-commit", "clean"])
            t = run_hook(hook["config"])
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

    # Write to GitHub Actions summary
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a") as f:
            f.write("## Benchmark Results\n\n")
            # Markdown table header
            md_header = "| " + " | ".join(headers) + " |\n"
            md_sep = "|" + "|".join(["-" * (w + 2) for w in col_widths]) + "|\n"
            f.write(md_header)
            f.write(md_sep)
            for name, times in results.items():
                avg = statistics.mean(times)
                std = statistics.stdev(times) if len(times) > 1 else 0.0
                min_t = min(times)
                max_t = max(times)
                md_row = f"| {name} | {avg:.3f} | {std:.3f} | {min_t:.3f} | {max_t:.3f} | {len(times)} |\n"
                f.write(md_row)
            f.write("\n")


def main():
    results = benchmark()
    report(results)


if __name__ == "__main__":
    main()
