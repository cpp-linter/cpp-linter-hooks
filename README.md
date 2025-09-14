# cpp-linter-hooks

[![PyPI](https://img.shields.io/pypi/v/cpp-linter-hooks?color=blue)](https://pypi.org/project/cpp-linter-hooks/)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/cpp-linter-hooks)](https://pypi.org/project/cpp-linter-hooks/)
[![codecov](https://codecov.io/gh/cpp-linter/cpp-linter-hooks/branch/main/graph/badge.svg?token=L74Z3HZ4Y5)](https://codecov.io/gh/cpp-linter/cpp-linter-hooks)
[![Test](https://github.com/cpp-linter/cpp-linter-hooks/actions/workflows/test.yml/badge.svg)](https://github.com/cpp-linter/cpp-linter-hooks/actions/workflows/test.yml)
[![CodeQL](https://github.com/cpp-linter/cpp-linter-hooks/actions/workflows/codeql.yml/badge.svg)](https://github.com/cpp-linter/cpp-linter-hooks/actions/workflows/codeql.yml)

A powerful [pre-commit](https://pre-commit.com/) hook for auto-formatting and linting C/C++ code with `clang-format` and `clang-tidy`.

## Table of Contents

- [Quick Start](#quick-start)
  - [Custom Configuration Files](#custom-configuration-files)
  - [Custom Clang Tool Version](#custom-clang-tool-version)
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
    rev: v1.1.0  # Use the tag or commit you want
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
    rev: v1.1.0
    hooks:
      - id: clang-format
        args: [--style=file]  # Loads style from .clang-format file
      - id: clang-tidy
        args: [--checks=.clang-tidy] # Loads checks from .clang-tidy file
```

> [!TIP]
> By default, the latest version of [`clang-format`](https://pypi.org/project/clang-format/#history) and [`clang-tidy`](https://pypi.org/project/clang-tidy/#history) will be installed if not specified. You can specify the version using the `--version` argument in the `args` list as shown below.

### Custom Clang Tool Version

To use specific versions of clang-format and clang-tidy (using Python wheel packages):

```yaml
repos:
  - repo: https://github.com/cpp-linter/cpp-linter-hooks
    rev: v1.1.0
    hooks:
      - id: clang-format
        args: [--style=file, --version=21] # Specifies version
      - id: clang-tidy
        args: [--checks=.clang-tidy, --version=21] # Specifies version
```

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
  rev: v1.1.0
  hooks:
    - id: clang-format
      args: [--style=file, --version=21]
      files: ^(src|include)/.*\.(cpp|cc|cxx|h|hpp)$ # Limits to specific dirs and file types
    - id: clang-tidy
      args: [--checks=.clang-tidy, --version=21]
      files: ^(src|include)/.*\.(cpp|cc|cxx|h|hpp)$
```

Alternatively, if you want to run the hooks manually on only the changed files, you can use the following command:

```bash
pre-commit run --files $(git diff --name-only)
```

This approach ensures that only modified files are checked, further speeding up the linting process during development.

### Verbose Output

> [!NOTE]
> Use `-v` or `--verbose` in `args` of `clang-format` to show the list of processed files e.g.:

```yaml
repos:
  - repo: https://github.com/cpp-linter/cpp-linter-hooks
    rev: v1.1.0
    hooks:
      - id: clang-format
        args: [--style=file, --version=21, --verbose]   # Add -v or --verbose for detailed output
```

## FAQ

### What's the difference between [`cpp-linter-hooks`](https://github.com/cpp-linter/cpp-linter-hooks) and [`mirrors-clang-format`](https://github.com/pre-commit/mirrors-clang-format)?

| Feature                          | `cpp-linter-hooks`                        | `mirrors-clang-format`                 |
|----------------------------------|-------------------------------------------|----------------------------------------|
| Supports `clang-format` and `clang-tidy` | ✅ (`clang-format` & `clang-tidy`)       | ✅ (`clang-format` only)        |
| Loads style configuration        | ✅ via `--version`                        | ✅ (default behavior)                  |
| Specify `clang-format` version   | ✅ via `--version`                        | ✅ via `rev`                           |
| Supports passing code string     | ✅ via `--style`                          | ❌                                     |
| Verbose output                   | ✅ via `--verbose`                        | ❌                                     |

<!-- > [!TIP]
> In most cases, there is no significant performance difference between `cpp-linter-hooks` and `mirrors-clang-format`. See the [benchmark results](testing/benchmark.md) for details. -->

## Contributing

We welcome contributions! Whether it's fixing issues, suggesting improvements, or submitting pull requests, your support is greatly appreciated.

## License

This project is licensed under the [MIT License](LICENSE).
