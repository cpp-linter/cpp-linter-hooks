# cpp-linter-hooks

[![PyPI](https://img.shields.io/pypi/v/cpp-linter-hooks)](https://pypi.org/project/cpp-linter-hooks/)
[![codecov](https://codecov.io/gh/cpp-linter/cpp-linter-hooks/branch/main/graph/badge.svg?token=L74Z3HZ4Y5)](https://codecov.io/gh/cpp-linter/cpp-linter-hooks)
[![Test](https://github.com/cpp-linter/cpp-linter-hooks/actions/workflows/test.yml/badge.svg)](https://github.com/cpp-linter/cpp-linter-hooks/actions/workflows/test.yml)
[![CodeQL](https://github.com/cpp-linter/cpp-linter-hooks/actions/workflows/codeql.yml/badge.svg)](https://github.com/cpp-linter/cpp-linter-hooks/actions/workflows/codeql.yml)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)
<!-- [![PyPI - Downloads](https://img.shields.io/pypi/dw/cpp-linter-hooks)](https://pypi.org/project/cpp-linter-hooks/) -->


Using `clang-format` and `clang-tidy` hooks with [pre-commit](https://pre-commit.com/) to lint your C/C++ code.

> [!NOTE]
> Automatically downloads a specific version of `clang-format` or `clang-tidy` [binaries](https://github.com/cpp-linter/clang-tools-static-binaries) and installs it on the system.

## Usage

Add this to your `.pre-commit-config.yaml`

```yaml
repos:
  - repo: https://github.com/cpp-linter/cpp-linter-hooks
    rev: v0.2.5  # Use the ref you want to point at
    hooks:
      - id: clang-format
        args: [--style=Google] # Other coding style: LLVM, GNU, Chromium, Microsoft, Mozilla, WebKit.
      - id: clang-tidy
        args: [--checks='boost-*,bugprone-*,performance-*,readability-*,portability-*,modernize-*,clang-analyzer-*,cppcoreguidelines-*']
```

The example of using custom config: `.clang-format` and `.clang-tidy`

```yaml
repos:
  - repo: https://github.com/cpp-linter/cpp-linter-hooks
    rev: v0.2.5
    hooks:
      - id: clang-format
        args: [--style=file]  # to load .clang-format
      - id: clang-tidy
        args: [--checks=.clang-tidy] # path/to/.clang-tidy
```

The example of using any version of [clang-tools](https://github.com/cpp-linter/clang-tools-pip?tab=readme-ov-file#supported-versions).

```yaml
repos:
  - repo: https://github.com/cpp-linter/cpp-linter-hooks
    rev: v0.2.5
    hooks:
      - id: clang-format
        args: [--style=file, --version=16]
      - id: clang-tidy
        args: [--checks=.clang-tidy, --version=16]
```

## Output

### clang-format output

```bash
clang-format.............................................................Failed
- hook id: clang-format
- files were modified by this hook
```

Here is the diff between the modified file.

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

Pass `--dry-run` to the `args` of `clang-format`(can also pass other arg which clang-format supports)

Then it will just print instead of changing the format. E.g:

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

### clang-tidy output

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

Any contribution is very welcome, including submitting issues, PRs, etc.

## License

This project is licensed under the terms of the MIT license.
