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
cpp-linter-hooks     | 12.473           | 1.738            | 11.334           | 15.514           | 5
mirrors-clang-format | 4.960            | 0.229            | 4.645            | 5.284            | 5

Results saved to testing/benchmark_results.txt
```
