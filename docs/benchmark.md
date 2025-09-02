# Benchmarking

This document outlines the benchmarking process for comparing the performance of cpp-linter-hooks and mirrors-clang-format.

> About tests performance can be found at: [![CodSpeed Badge](https://img.shields.io/endpoint?url=https://codspeed.io/badge.json)](https://codspeed.io/cpp-linter/cpp-linter-hooks)

## Running the Benchmark

```bash
python3 testing/benchmark_hooks.py
```

## Results

```bash
# Updated on 2025-09-02
Benchmark Results:

Hook                 | Avg (s)          | Std (s)          | Min (s)          | Max (s)          | Runs
---------------------+------------------+------------------+------------------+------------------+-----------------
mirrors-clang-format | 0.116            | 0.003            | 0.113            | 0.118            | 5
cpp-linter-hooks     | 0.114            | 0.003            | 0.109            | 0.117            | 5

Results saved to testing/benchmark_results.txt
```
