# Test cpp-linter-hooks

## Test locally

```bash
pre-commit try-repo  ./.. clang-format  --verbose --all-files
pre-commit try-repo  ./.. clang-tidy  --verbose --all-files
```

## Benchmark

See [benchmark](./benchmark.md).
