# cpp-linter-hooks

[![Test](https://github.com/shenxianpeng/cpp-linter-hooks/actions/workflows/test.yml/badge.svg)](https://github.com/shenxianpeng/cpp-linter-hooks/actions/workflows/test.yml)
[![codecov](https://codecov.io/gh/shenxianpeng/cpp-linter-hooks/branch/main/graph/badge.svg?token=L74Z3HZ4Y5)](https://codecov.io/gh/shenxianpeng/cpp-linter-hooks)

Using `clang-format` and `clang-tidy` hooks with [pre-commit](https://pre-commit.com/) to lint your C/C++ code.

Highlight✨: No need to manually download and install `clang-format` or `clang-tidy` on your system.

## Usage

Add this to your `.pre-commit-config.yaml`

```yaml
repos:
  - repo: https://github.com/shenxianpeng/cpp-linter-hooks
    rev: v0.1.0  # Use the ref you want to point at
    hooks:
      - id: clang-format
        args: [--style=Google] # Other coding style: LLVM, GNU, Chromium, Microsoft, Mozilla, WebKit.
      - id: clang-tidy
        args: [--checks='boost-*,bugprone-*,performance-*,readability-*,portability-*,modernize-*,clang-analyzer-*,cppcoreguidelines-*']
```

The example of using custom config: `.clang-format` and `.clang-tidy`

```yaml
repos:
  - repo: https://github.com/shenxianpeng/cpp-linter-hooks
    rev: v0.1.0
    hooks:
      - id: clang-format
        args: [--style=file]  # to load .clang-format
      - id: clang-tidy
        args: [--config=.clang-tidy] # path/to/.clang-tidy
```

The example of using any version of [clang-tools](https://github.com/shenxianpeng/clang-tools-pip).

```yaml
repos:
  - repo: https://github.com/shenxianpeng/cpp-linter-hooks
    rev: v0.1.0
    hooks:
      - id: clang-format
        args: [--style=file, --version=13]
      - id: clang-tidy
        args: [--config=.clang-tidy, --version=12]
```

## Output

The output when catching unformatted and error code.

```
clang-format.............................................................Failed
- hook id: clang-format
- files were modified by this hook
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

The diff of the modified file.

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

## License

This project is licensed under the terms of the MIT license.
