# cpp-linter-hooks

[![Test](https://github.com/shenxianpeng/cpp-linter-hooks/actions/workflows/test.yml/badge.svg)](https://github.com/shenxianpeng/cpp-linter-hooks/actions/workflows/test.yml) [![codecov](https://codecov.io/gh/shenxianpeng/cpp-linter-hooks/branch/master/graph/badge.svg?token=L74Z3HZ4Y5)](https://codecov.io/gh/shenxianpeng/cpp-linter-hooks)

Using `clang-format` and `clang-tidy` hooks with [pre-commit](https://pre-commit.com/) to lint your C/C++ code.

✨Highlight✨: automatically install `clang-format` and `clang-tidy` when they do not exist.

## Usage

Add this to your `.pre-commit-config.yaml`

```yaml
repos:
  - repo: https://github.com/shenxianpeng/cpp-linter-hooks
    rev: v0.1.0  # Use the ref you want to point at
    hooks:
      - id: clang-format
        args: [--style=Google] 
      # - id: clang-tidy ## Work in progress
      #   args: [--config-file=file]
```

## Support hooks

### `clang-format`

Prevent committing unformatted C/C++ code.

* Set coding style: LLVM, GNU, Google, Chromium, Microsoft, Mozilla, WebKit with `args: [--style=LLVM]`
* Load coding style configuration file `.clang-format` with `args: [--style=file]`

### `clang-tidy`

Prevent committing typical programming errors, like style violations, interface misuse, or bugs that can be deduced.
