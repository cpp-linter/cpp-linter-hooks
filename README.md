# cpp-linter-hooks

[![PyPI](https://img.shields.io/pypi/v/cpp-linter-hooks?color=blue)](https://pypi.org/project/cpp-linter-hooks/)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/cpp-linter-hooks)](https://pypi.org/project/cpp-linter-hooks/)
[![codecov](https://codecov.io/gh/cpp-linter/cpp-linter-hooks/branch/main/graph/badge.svg?token=L74Z3HZ4Y5)](https://codecov.io/gh/cpp-linter/cpp-linter-hooks)
[![Test](https://github.com/cpp-linter/cpp-linter-hooks/actions/workflows/test.yml/badge.svg)](https://github.com/cpp-linter/cpp-linter-hooks/actions/workflows/test.yml)
[![CodeQL](https://github.com/cpp-linter/cpp-linter-hooks/actions/workflows/codeql.yml/badge.svg)](https://github.com/cpp-linter/cpp-linter-hooks/actions/workflows/codeql.yml)

A pre-commit hook that automatically formats and lints your C/C++ code using `clang-format` and `clang-tidy`.

## Table of Contents

- [Quick Start](#quick-start)
  - [Custom Configuration Files](#custom-configuration-files)
  - [Custom Clang Tool Version](#custom-clang-tool-version)
  - [Compilation Database (CMake/Meson Projects)](#compilation-database-cmakemeson-projects)
- [Output](#output)
  - [clang-format Output](#clang-format-output)
  - [clang-tidy Output](#clang-tidy-output)
- [Troubleshooting](#troubleshooting)
  - [Performance Optimization](#performance-optimization)
  - [Verbose Output](#verbose-output)
- [FAQ](#faq)
  - [What's the difference between `cpp-linter-hooks` and `mirrors-clang-format`?](#whats-the-difference-between-cpp-linter-hooks-and-mirrors-clang-format)
- [Contributing](#contributing)
- [License](#license)

## Quick Start

Add this configuration to your `.pre-commit-config.yaml` file:

```yaml
repos:
  - repo: https://github.com/cpp-linter/cpp-linter-hooks
    rev: v1.2.0  # Use the tag or commit you want
    hooks:
      - id: clang-format
        args: [--style=Google] # Other coding style: LLVM, GNU, Chromium, Microsoft, Mozilla, WebKit.
      - id: clang-tidy
        args: [--checks='boost-*,bugprone-*,performance-*,readability-*,portability-*,modernize-*,clang-analyzer-*,cppcoreguidelines-*']
```

### Custom Configuration Files

To use custom configurations like `.clang-format` and `.clang-tidy`:

```yaml
repos:
  - repo: https://github.com/cpp-linter/cpp-linter-hooks
    rev: v1.2.0
    hooks:
      - id: clang-format
        args: [--style=file]  # Loads style from .clang-format file
      - id: clang-tidy
        args: [--checks=.clang-tidy] # Loads checks from .clang-tidy file
```

> [!TIP]
> The `rev` tag (e.g. `v1.2.0`) is the **project** version, not the clang tool version. Each release bundles a default version of `clang-format` and `clang-tidy` — check the [release notes](https://github.com/cpp-linter/cpp-linter-hooks/releases) to see which tool version a given `rev` ships with. To pin an exact tool version independently of the project release, use `--version` as shown below.

### Custom Clang Tool Version

To use specific versions of clang-format and clang-tidy (using Python wheel packages):

```yaml
repos:
  - repo: https://github.com/cpp-linter/cpp-linter-hooks
    rev: v1.2.0
    hooks:
      - id: clang-format
        args: [--style=file, --version=21] # Specifies version
      - id: clang-tidy
        args: [--checks=.clang-tidy, --version=21] # Specifies version
```

> [!TIP]
> For production use, always pin the tool version explicitly with `--version` (e.g. `--version=21`) so upgrades to `cpp-linter-hooks` never silently change your linter version.

### Compilation Database (CMake/Meson Projects)

For CMake or Meson projects, clang-tidy works best with a `compile_commands.json`
file that records the exact compiler flags used for each file. Without it, clang-tidy
may report false positives from missing include paths or wrong compiler flags.

The hook auto-detects `compile_commands.json` in common build directories (`build/`,
`out/`, `cmake-build-debug/`, `_build/`) and passes `-p <dir>` to clang-tidy
automatically — no configuration needed for most projects:

```yaml
repos:
  - repo: https://github.com/cpp-linter/cpp-linter-hooks
    rev: v1.2.0
    hooks:
      - id: clang-tidy
        args: [--checks=.clang-tidy]
        # Auto-detects ./build/compile_commands.json if present
```

To specify the build directory explicitly:

```yaml
      - id: clang-tidy
        args: [--compile-commands=build, --checks=.clang-tidy]
```

To disable auto-detection (e.g. in a monorepo where auto-detect might pick the wrong database):

```yaml
      - id: clang-tidy
        args: [--no-compile-commands, --checks=.clang-tidy]
```

To see which `compile_commands.json` the hook is using, add `-v`:

```yaml
      - id: clang-tidy
        args: [--compile-commands=build, -v, --checks=.clang-tidy]
```

> [!NOTE]
> Generate `compile_commands.json` with CMake using `cmake -DCMAKE_EXPORT_COMPILE_COMMANDS=ON -Bbuild .`
> or add `set(CMAKE_EXPORT_COMPILE_COMMANDS ON)` to your `CMakeLists.txt`.
> `--compile-commands` takes the **directory** containing `compile_commands.json`, not the file path itself.

## Output

### clang-format Output

```bash
clang-format.............................................................Failed
- hook id: clang-format
- files were modified by this hook
```

Here’s a sample diff showing the formatting applied:

```diff
--- a/testing/main.c
+++ b/testing/main.c
@@ -1,3 +1,6 @@
 #include <stdio.h>
-int main() {for (;;) break; printf("Hello world!\n");return 0;}
-
+int main() {
+  for (;;) break;
+  printf("Hello world!\n");
+  return 0;
+}
```
> [!NOTE]
> Use `--dry-run` in `args` of `clang-format` to print instead of changing the format, e.g.:

```bash
clang-format.............................................................Failed
- hook id: clang-format
- exit code: 255

main.c:2:11: warning: code should be clang-formatted [-Wclang-format-violations]
int main() {for (;;) break; printf("Hello world!\n");return 0;}
          ^
main.c:2:13: warning: code should be clang-formatted [-Wclang-format-violations]
int main() {for (;;) break; printf("Hello world!\n");return 0;}
            ^
main.c:2:21: warning: code should be clang-formatted [-Wclang-format-violations]
int main() {for (;;) break; printf("Hello world!\n");return 0;}
                    ^
main.c:2:28: warning: code should be clang-formatted [-Wclang-format-violations]
int main() {for (;;) break; printf("Hello world!\n");return 0;}
                           ^
main.c:2:54: warning: code should be clang-formatted [-Wclang-format-violations]
int main() {for (;;) break; printf("Hello world!\n");return 0;}
                                                     ^
main.c:2:63: warning: code should be clang-formatted [-Wclang-format-violations]
int main() {for (;;) break; printf("Hello world!\n");return 0;}
                                                              ^
```

### clang-tidy Output

```bash
clang-tidy...............................................................Failed
- hook id: clang-tidy
- exit code: 1

522 warnings generated.
Suppressed 521 warnings (521 in non-user code).
Use -header-filter=.* to display errors from all non-system headers. Use -system-headers to display errors from system headers as well.
/home/runner/work/cpp-linter-hooks/cpp-linter-hooks/testing/main.c:4:13: warning: statement should be inside braces [readability-braces-around-statements]
    for (;;)
            ^
             {

```

## Troubleshooting

### Performance Optimization

> [!TIP]
> For large codebases, if your `pre-commit` runs longer than expected, it is highly recommended to add `files` in `.pre-commit-config.yaml` to limit the scope of the hook. This helps improve performance by reducing the number of files being checked and avoids unnecessary processing. Here's an example configuration:

```yaml
- repo: https://github.com/cpp-linter/cpp-linter-hooks
  rev: v1.2.0
  hooks:
    - id: clang-format
      args: [--style=file, --version=21]
      files: ^(src|include)/.*\.(cpp|cc|cxx|h|hpp)$ # Limits to specific dirs and file types
    - id: clang-tidy
      args: [--checks=.clang-tidy, --version=21]
      files: ^(src|include)/.*\.(cpp|cc|cxx|h|hpp)$
```

For `clang-tidy`, you can also process multiple files in parallel by adding `--jobs`
or `-j`:

```yaml
- repo: https://github.com/cpp-linter/cpp-linter-hooks
  rev: v1.2.0
  hooks:
    - id: clang-tidy
      args: [--checks=.clang-tidy, --version=21, --jobs=4]
```

Alternatively, if you want to run the hooks manually on only the changed files, you can use the following command:

```bash
pre-commit run --files $(git diff --name-only)
```

This approach ensures that only modified files are checked, further speeding up the linting process during development.

### Verbose Output

> [!NOTE]
> Use `-v` or `--verbose` in `args` to enable verbose output.
> For `clang-format`, it shows the list of processed files.
> For `clang-tidy`, it prints which `compile_commands.json` is being used (when auto-detected or explicitly set).

```yaml
repos:
  - repo: https://github.com/cpp-linter/cpp-linter-hooks
    rev: v1.2.0
    hooks:
      - id: clang-format
        args: [--style=file, --version=21, --verbose]   # Shows processed files
      - id: clang-tidy
        args: [--checks=.clang-tidy, --verbose]   # Shows which compile_commands.json is used
```

## FAQ

### What's the difference between [`cpp-linter-hooks`](https://github.com/cpp-linter/cpp-linter-hooks) and [`mirrors-clang-format`](https://github.com/pre-commit/mirrors-clang-format)?

| Feature                          | `cpp-linter-hooks`                        | `mirrors-clang-format`                 |
|----------------------------------|-------------------------------------------|----------------------------------------|
| Supports `clang-format` and `clang-tidy` | ✅ (`clang-format` & `clang-tidy`)| ✅ (`clang-format` only)              |
| Custom configuration files       | ✅ `.clang-format`, `.clang-tidy`         | ✅ `.clang-format`                    |
| Specify tool version             | ✅ via `--version` arg (e.g. `--version=21`) | ✅ via `rev` tag (e.g. `rev: v21.1.8`) |
| `rev` tag meaning                | Project version — see release notes for bundled tool version | Equals the clang-format version directly |
| Supports passing format style string | ✅ via `--style`                      | ❌                                    |
| Verbose output                   | ✅ via `--verbose`                        | ❌                                    |
| Dry-run mode                     | ✅ via `--dry-run`                        | ❌                                    |
| Compilation database support     | ✅ auto-detect or `--compile-commands`    | ❌                                    |


<!-- > [!TIP]
> In most cases, there is no significant performance difference between `cpp-linter-hooks` and `mirrors-clang-format`. See the [benchmark results](testing/benchmark.md) for details. -->

## Contributing

We welcome contributions! Whether it's fixing issues, suggesting improvements, or submitting pull requests, your support is greatly appreciated.

## License

This project is licensed under the [MIT License](LICENSE).
