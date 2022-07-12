# cpp-linter-hooks

[![Test](https://github.com/shenxianpeng/cpp-linter-hooks/actions/workflows/test.yml/badge.svg)](https://github.com/shenxianpeng/cpp-linter-hooks/actions/workflows/test.yml)
[![codecov](https://codecov.io/gh/shenxianpeng/cpp-linter-hooks/branch/main/graph/badge.svg?token=L74Z3HZ4Y5)](https://codecov.io/gh/shenxianpeng/cpp-linter-hooks)

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
      - id: clang-tidy
        args: [--checks='boost-*,bugprone-*,performance-*,readability-*,portability-*,modernize-*,clang-analyzer-*,cppcoreguidelines-*']
```

Use specific version. for example `clang-format` is version 13, `clang-tidy` is version 12.

```yaml
repos:
  - repo: https://github.com/shenxianpeng/cpp-linter-hooks
    rev: v0.1.0  # Use the ref you want to point at
    hooks:
      - id: clang-format
        args: [--style=Google, --version=13]
      - id: clang-tidy
        args: [--checks='boost-*,bugprone-*,performance-*,readability-*,portability-*,modernize-*,clang-analyzer-*,cppcoreguidelines-*', --version=12]
```

## Support hooks

### `clang-format`

Prevent committing unformatted C/C++ code.

* Set coding style: LLVM, GNU, Google, Chromium, Microsoft, Mozilla, WebKit with `args: [--style=LLVM]`
* Load coding style configuration file `.clang-format` with `args: [--style=file]`

output

```
clang-format.............................................................Failed
- hook id: clang-format
- files were modified by this hook
```
modified file
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

### `clang-tidy`

Prevent committing typical programming errors, like style violations, interface misuse, or bugs that can be deduced.

* Set checks like `args: [--checks='boost-*,bugprone-*,performance-*,readability-*,portability-*,modernize-*,clang-analyzer-*,cppcoreguidelines-*']`
* Or set specify the path of .clang-tidy like `args: [--checks=path/to/.clang-tidy]`


Output

```
clang-tidy...............................................................Failed
- hook id: clang-tidy
- duration: 0.48s

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
