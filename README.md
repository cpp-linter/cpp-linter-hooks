# cpp-linter-hooks

[![PyPI](https://img.shields.io/pypi/v/cpp-linter-hooks)](https://pypi.org/project/cpp-linter-hooks/)
[![Test](https://github.com/cpp-linter/cpp-linter-hooks/actions/workflows/test.yml/badge.svg)](https://github.com/cpp-linter/cpp-linter-hooks/actions/workflows/test.yml)
[![codecov](https://codecov.io/gh/cpp-linter/cpp-linter-hooks/branch/main/graph/badge.svg?token=L74Z3HZ4Y5)](https://codecov.io/gh/cpp-linter/cpp-linter-hooks)
<!-- [![PyPI - Downloads](https://img.shields.io/pypi/dw/cpp-linter-hooks)](https://pypi.org/project/cpp-linter-hooks/) -->


Using `clang-format` and `clang-tidy` hooks with [pre-commit](https://pre-commit.com/) to lint your C/C++ code.

Highlight✨: No need to manually download and install `clang-format` or `clang-tidy` on your system.

## Usage

Add this to your `.pre-commit-config.yaml`

```yaml
repos:
  - repo: https://github.com/cpp-linter/cpp-linter-hooks
    rev: v0.2.1  # Use the ref you want to point at
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
    rev: v0.2.1
    hooks:
      - id: clang-format
        args: [--style=file]  # to load .clang-format
      - id: clang-tidy
        args: [--checks=.clang-tidy] # path/to/.clang-tidy
```

The example of using any version of [clang-tools](https://github.com/cpp-linter/clang-tools-pip).

```yaml
repos:
  - repo: https://github.com/cpp-linter/cpp-linter-hooks
    rev: v0.2.1
    hooks:
      - id: clang-format
        args: [--style=file, --version=13]
      - id: clang-tidy
        args: [--checks=.clang-tidy, --version=12]
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

### chang-tidy output

```bash
clang-tidy...............................................................Failed
- hook id: clang-tidy
- exit code: 1

418 warnings and 1 error generated.
Error while processing /home/ubuntu/cpp-linter-hooks/testing/main.c.
Suppressed 417 warnings (417 in non-user code).
Use -header-filter=.* to display errors from all non-system headers. Use -system-headers to display errors from system headers as well.
Found compiler error(s).
/home/ubuntu/cpp-linter-hooks/testing/main.c:3:11: warning: statement should be inside braces [readability-braces-around-statements]
  for (;;) break;
          ^
           {
/usr/include/stdio.h:33:10: error: 'stddef.h' file not found [clang-diagnostic-error]
#include <stddef.h>
         ^~~~~~~~~~
```

## Contributing

Any contribution is very welcome, including submitting issues, PRs, etc.

## License

This project is licensed under the terms of the MIT license.
