# CMake Project

If you already have a CMake project, you need **three files**:

## .pre-commit-config.yaml

```yaml
repos:
  - repo: https://github.com/cpp-linter/cpp-linter-hooks
    rev: v1.8.1
    hooks:
      - id: clang-format
        args: [--style=file]
        files: ^(src|include)/.*\.(cpp|cc|cxx|h|hpp)$

      - id: clang-tidy
        files: ^(src|include)/.*\.(cpp|cc|cxx)$
```

## .clang-tidy

clang-tidy 22 and newer run no checks without one. Choose the checks you want, for example:

```yaml
Checks: 'bugprone-*,performance-*,readability-*'
```

## CMakeLists.txt

Add one line so `clang-tidy` can see your include paths:

```cmake
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)
```

Then `cmake -B build` and `pre-commit install`.  Done.

---

`compile_commands.json` is auto-detected from `build/`, `out/`, `cmake-build-debug/`,
`_build/`, `builddir/`, `cmake-build-*/`, `build-*/`, `build/*/` or `out/build/*/`.  If your
build dir has a different name, pass it explicitly:
`args: [--compile-commands=mybuild, ...]`.  Without a database, the clang-tidy hook skips
clang-tidy on your machine and fails in CI.
