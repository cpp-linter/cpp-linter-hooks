# Benchmarking

This document outlines the benchmarking process for comparing the performance of cpp-linter-hooks and mirrors-clang-format.

> About tests performance can be found at: [![CodSpeed Badge](https://img.shields.io/endpoint?url=https://codspeed.io/badge.json)](https://codspeed.io/cpp-linter/cpp-linter-hooks)

## Run benchmark separately

```bash
rm -rf examples || true
git clone --depth 1 --quiet https://github.com/gouravthakur39/beginners-C-program-examples.git examples

pre-commit clean
hyperfine --warmup 1 -r 10 'pre-commit run --config testing/test-cpp-linter-hooks.yaml --all-files'

rm -rf examples || true
git clone --depth 1 --quiet https://github.com/gouravthakur39/beginners-C-program-examples.git examples
pre-commit clean

hyperfine --warmup 1 -r 10 'pre-commit run --config testing/test-mirrors-clang-format.yaml --all-files'
```

Results:

```bash
# Updated on 2025-09-19

Cleaned /home/sxp/.cache/pre-commit.
Benchmark 1: pre-commit run --config testing/test-cpp-linter-hooks.yaml --all-files
  Time (mean ± σ):     150.2 ms ±   1.8 ms    [User: 121.7 ms, System: 29.2 ms]
  Range (min … max):   148.3 ms … 153.9 ms    10 runs

Cleaned /home/sxp/.cache/pre-commit.
Benchmark 1: pre-commit run --config testing/test-mirrors-clang-format.yaml --all-files
  Time (mean ± σ):     122.6 ms ±   1.9 ms    [User: 98.0 ms, System: 24.7 ms]
  Range (min … max):   120.3 ms … 125.5 ms    10 runs
```

### Run benchmark comparison

Compare the results of both commands.

```bash
rm -rf examples || true
git clone --depth 1 --quiet https://github.com/gouravthakur39/beginners-C-program-examples.git examples

hyperfine -i --warmup 1 -r 20 'pre-commit run --config ../testing/test-cpp-linter-hooks.yaml --all-files' 'pre-commit run --config ../testing/test-mirrors-clang-format.yaml --all-files'
```

Results:

```bash
# Updated on 2025-09-19
Benchmark 1: pre-commit run --config ../testing/test-cpp-linter-hooks.yaml --all-files
  Time (mean ± σ):      84.1 ms ±   3.2 ms    [User: 73.5 ms, System: 10.2 ms]
  Range (min … max):    79.7 ms …  95.2 ms    20 runs

  Warning: Ignoring non-zero exit code.

Benchmark 2: pre-commit run --config ../testing/test-mirrors-clang-format.yaml --all-files
  Time (mean ± σ):      85.0 ms ±   3.0 ms    [User: 71.8 ms, System: 13.3 ms]
  Range (min … max):    81.0 ms …  91.0 ms    20 runs

  Warning: Ignoring non-zero exit code.

Summary
  'pre-commit run --config ../testing/test-cpp-linter-hooks.yaml --all-files' ran
    1.01 ± 0.05 times faster than 'pre-commit run --config ../testing/test-mirrors-clang-format.yaml --all-files'
```

> [!NOTE]
> The results may vary based on the system and environment where the benchmarks are run.
