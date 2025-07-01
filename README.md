# cpp-linter-hooks

[![PyPI](https://img.shields.io/pypi/v/cpp-linter-hooks?color=blue)](https://pypi.org/project/cpp-linter-hooks/)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/cpp-linter-hooks)](https://pypi.org/project/cpp-linter-hooks/)
[![codecov](https://codecov.io/gh/cpp-linter/cpp-linter-hooks/branch/main/graph/badge.svg?token=L74Z3HZ4Y5)](https://codecov.io/gh/cpp-linter/cpp-linter-hooks)
[![Test](https://github.com/cpp-linter/cpp-linter-hooks/actions/workflows/test.yml/badge.svg)](https://github.com/cpp-linter/cpp-linter-hooks/actions/workflows/test.yml)
[![CodeQL](https://github.com/cpp-linter/cpp-linter-hooks/actions/workflows/codeql.yml/badge.svg)](https://github.com/cpp-linter/cpp-linter-hooks/actions/workflows/codeql.yml)
<!-- [![PyPI - Downloads](https://img.shields.io/pypi/dw/cpp-linter-hooks)](https://pypi.org/project/cpp-linter-hooks/) -->

cpp-linter-hooks is a [pre-commit](https://pre-commit.com/) hook that uses `clang-format` and `clang-tidy` to format C/C++ code.

> [!NOTE]
> This hook automatically downloads specific versions of `clang-format` or `clang-tidy` [static-binaries](https://github.com/cpp-linter/clang-tools-static-binaries) and installs them on your system.

## Usage

To use cpp-linter-hooks, add the following configuration to your `.pre-commit-config.yaml`:

### Basic Configuration

```yaml
repos:
  - repo: https://github.com/cpp-linter/cpp-linter-hooks
    rev: v0.8.1  # Use the tag or commit you want
    hooks:
      - id: clang-format
        args: [--style=Google] # Other coding style: LLVM, GNU, Chromium, Microsoft, Mozilla, WebKit.
      - id: clang-tidy
        args: [--checks='boost-*,bugprone-*,performance-*,readability-*,portability-*,modernize-*,clang-analyzer-*,cppcoreguidelines-*']
```

### Custom Configuration

To use custom configurations like `.clang-format` and `.clang-tidy`:

```yaml
repos:
  - repo: https://github.com/cpp-linter/cpp-linter-hooks
    rev: v0.8.1
    hooks:
      - id: clang-format
        args: [--style=file]  # Loads style from .clang-format file
      - id: clang-tidy
        args: [--checks=.clang-tidy] # Loads checks from .clang-tidy file
```

To use specific versions of [clang-tools](https://github.com/cpp-linter/clang-tools-pip?tab=readme-ov-file#supported-versions):

```yaml
repos:
  - repo: https://github.com/cpp-linter/cpp-linter-hooks
    rev: v0.8.1
    hooks:
      - id: clang-format
        args: [--style=file, --version=18] # Specifies version
      - id: clang-tidy
        args: [--checks=.clang-tidy, --version=18] # Specifies version
```

> [!IMPORTANT]
> If your `pre-commit` runs longer than expected, it is highly recommended to add `files` in `.pre-commit-config.yaml` to limit the scope of the hook. This helps improve performance by reducing the number of files being checked and avoids unnecessary processing. Here's an example configuration:


```yaml
- repo: https://github.com/cpp-linter/cpp-linter-hooks
  rev: v0.8.1
  hooks:
    - id: clang-format
      args: [--style=file, --version=18]
      files: ^(src|include)/.*\.(cpp|cc|cxx|h|hpp)$ # Limits to specific dirs and file types
    - id: clang-tidy
      args: [--checks=.clang-tidy, --version=18]
      files: ^(src|include)/.*\.(cpp|cc|cxx|h|hpp)$
```

Alternatively, if you want to run the hooks manually on only the changed files, you can use the following command:

```bash
pre-commit run --files $(git diff --name-only)
```

This approach ensures that only modified files are checked, further speeding up the linting process during development.

## Output

### clang-format Example

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

Use `--dry-run` in `args` of `clang-format` to print instead of changing the format, e.g.:

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

### clang-tidy Example

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

## Contributing

We welcome contributions! Whether it's fixing issues, suggesting improvements, or submitting pull requests, your support is greatly appreciated.

## License

cpp-linter-hooks is licensed under the [MIT License](LICENSE)
