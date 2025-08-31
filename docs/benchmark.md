# Benchmarking

This document outlines the benchmarking process for comparing the performance of cpp-linter-hooks and mirrors-clang-format.

## Running the Benchmark

```bash
python3 testing/benchmark_hooks.py
```

## Results

The results of the benchmarking process will be saved to `testing/benchmark_results.txt`.

## To Do

- Run benchmark against a larger codebase, such as [TheAlgorithms/C-Plus-Plus](https://github.com/TheAlgorithms/C-Plus-Plus).
- Run benchmark with GitHub Actions for continuous integration.
