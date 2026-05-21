# CMake Project

If you already have a CMake project, you need **two files**:

## .pre-commit-config.yaml

```yaml
repos:
  - repo: https://github.com/cpp-linter/cpp-linter-hooks
    rev: v1.4.2
    hooks:
      - id: clang-format
        args: [--style=file, --version=21]
        files: ^(src|include)/.*\.(cpp|cc|cxx|h|hpp)$

      - id: clang-tidy
        args: [--checks=.clang-tidy, --version=21]
        files: ^(src|include)/.*\.(cpp|cc|cxx)$
```

## CMakeLists.txt

Add one line so `clang-tidy` can see your include paths:

```cmake
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)
```

Then `cmake -B build` and `pre-commit install`.  Done.

---

`compile_commands.json` is auto-detected from `build/`, `out/`, `cmake-build-debug/`,
or `_build/`.  If your build dir has a different name, pass it explicitly:
`args: [--compile-commands=mybuild, ...]`.
