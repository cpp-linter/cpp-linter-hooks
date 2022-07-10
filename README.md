# C/C++ linter hooks for pre-commit

Linter your C/C++ code with `clang-format` and `clang-tidy` for [pre-commit](https://pre-commit.com/).

**Automaticlly install `clang-format` and `clang-tidy`** when they do not exist.

## Usage

For example

```yaml
repos:
  - repo: https://github.com/shenxianpeng/cpp-linter-hooks
    hooks:
      - id: clang-format
        args: ["--style=Google", "--version=14"]
      - id: clang-tidy
```
