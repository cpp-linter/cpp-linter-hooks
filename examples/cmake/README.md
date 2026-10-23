# CMake Project

If you already have a CMake project, you need **two files**:

## .pre-commit-config.yaml

```yaml
repos:
  - repo: https://github.com/cpp-linter/cpp-linter-hooks
    rev: v1.8.0
    hooks:
      - id: clang-format
        args: [--style=file]
        additional_dependencies: [clang-format==21.1.8]
        files: ^(src|include)/.*\.(cpp|cc|cxx|h|hpp)$

      - id: clang-tidy
        additional_dependencies: [clang-tidy==21.1.6]
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
`_build/`, `builddir/`, `cmake-build-*/`, `build-*/`, `build/*/` or `out/build/*/`.  If your
build dir has a different name, pass it explicitly:
`args: [--compile-commands=mybuild, ...]`.  Without a database, the clang-tidy hook skips
clang-tidy on your machine and fails in CI.
