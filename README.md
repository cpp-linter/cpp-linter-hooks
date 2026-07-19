# cpp-linter-hooks

[![PyPI](https://img.shields.io/pypi/v/cpp-linter-hooks?color=blue)](https://pypi.org/project/cpp-linter-hooks/)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/cpp-linter-hooks)](https://pypi.org/project/cpp-linter-hooks/)
[![codecov](https://codecov.io/gh/cpp-linter/cpp-linter-hooks/branch/main/graph/badge.svg?token=L74Z3HZ4Y5)](https://codecov.io/gh/cpp-linter/cpp-linter-hooks)
[![Test](https://github.com/cpp-linter/cpp-linter-hooks/actions/workflows/test.yml/badge.svg)](https://github.com/cpp-linter/cpp-linter-hooks/actions/workflows/test.yml)
[![CodeQL](https://github.com/cpp-linter/cpp-linter-hooks/actions/workflows/codeql.yml/badge.svg)](https://github.com/cpp-linter/cpp-linter-hooks/actions/workflows/codeql.yml)
[![cpp-linter hub](https://img.shields.io/badge/%F0%9F%8F%A0_cpp--linter_hub-%E2%86%90_home-22863a)](https://cpp-linter.github.io/)

A pre-commit hook repository for C/C++ projects that installs and runs
`clang-format` and `clang-tidy` through the
[pre-commit](https://pre-commit.com/) framework.

## Why cpp-linter-hooks?

Use `cpp-linter-hooks` when you want the same C/C++ formatting and linting tools
to run consistently on developer machines and in CI without requiring every
developer to install LLVM tools manually.

- Runs both `clang-format` and `clang-tidy` from one pre-commit repository.
- Installs clang tools from Python wheels for a cross-platform setup.
- Lets projects pin the clang tool version explicitly with `--version`.
- Supports project-native `.clang-format` and `.clang-tidy` configuration files.
- Auto-detects `compile_commands.json` for CMake and Meson-style build trees.
- Supports `clang-format` dry-run checks, verbose diagnostics, and opt-in
  `clang-tidy` fixes.

Compared with [`mirrors-clang-format`](https://github.com/pre-commit/mirrors-clang-format),
this project also provides `clang-tidy`, compile database discovery, explicit
tool-version selection, and richer diagnostics. See the [FAQ](#faq) for the full
comparison.

> [!TIP]
> Using GitHub Actions for CI? Check out
> **[cpp-linter-action](https://github.com/cpp-linter/cpp-linter-action)** —
> our companion GitHub Action that runs the same tools in CI with rich PR reviews,
> thread comments, step summaries, and file annotations.

## Table of Contents

- [Why cpp-linter-hooks?](#why-cpp-linter-hooks)
- [GitHub Actions? Try cpp-linter-action](#github-actions-try-cpp-linter-action)
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
- [Examples](#examples)
- [Used By](#used-by)
- [FAQ](#faq)
  - [What's the difference between `cpp-linter-hooks` and `mirrors-clang-format`?](#whats-the-difference-between-cpp-linter-hooks-and-mirrors-clang-format)
- [Contributing](#contributing)
- [License](#license)

## Quick Start

Add this configuration to your `.pre-commit-config.yaml` file:

```yaml
repos:
  - repo: https://github.com/cpp-linter/cpp-linter-hooks
    rev: v1.6.0  # Use the tag or commit you want
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
    rev: v1.6.0
    hooks:
      - id: clang-format
        args: [--style=file]  # Loads style from .clang-format file
      - id: clang-tidy
        args: [--checks=.clang-tidy] # Loads checks from .clang-tidy file
```

> [!TIP]
> The `rev` tag (e.g. `v1.6.0`) is the **project** version, not the clang tool version. Each release bundles a default version of `clang-format` and `clang-tidy` — check the [release notes](https://github.com/cpp-linter/cpp-linter-hooks/releases) to see which tool version a given `rev` ships with. To pin an exact tool version independently of the project release, use `--version` as shown below.

### Custom Clang Tool Version

To use specific versions of clang-format and clang-tidy (using Python wheel packages):

```yaml
repos:
  - repo: https://github.com/cpp-linter/cpp-linter-hooks
    rev: v1.6.0
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
    rev: v1.6.0
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

> [!NOTE]
> Add `--fix` to `args` to automatically apply clang-tidy fixes in place (equivalent to
> passing `-fix` to clang-tidy directly). This is **opt-in** and **not the default** because
> auto-fixing can modify source files in unexpected ways. A valid `compile_commands.json` is
> strongly recommended when using `--fix`.
>
> For cases where compiler errors exist alongside style issues, pass `-fix-errors` directly
> in `args` instead (clang-tidy native flag).

```yaml
repos:
  - repo: https://github.com/cpp-linter/cpp-linter-hooks
    rev: v1.6.0  # includes --fix support
    hooks:
      - id: clang-tidy
        args: [--checks=.clang-tidy, --fix]
```

> [!WARNING]
> When `--fix` (or `-fix-errors`) is active, parallel execution via `--jobs`/`-j` is
> automatically disabled to prevent concurrent writes to the same header file.

## Troubleshooting

### Performance Optimization

> [!TIP]
> For large codebases, if your `pre-commit` runs longer than expected, it is highly recommended to add `files` in `.pre-commit-config.yaml` to limit the scope of the hook. This helps improve performance by reducing the number of files being checked and avoids unnecessary processing. Here's an example configuration:

```yaml
- repo: https://github.com/cpp-linter/cpp-linter-hooks
  rev: v1.6.0
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
  rev: v1.6.0
  hooks:
    - id: clang-tidy
      args: [--checks=.clang-tidy, --version=21, --jobs=4]
```

> [!WARNING]
> When using `--jobs`/`-j`, avoid sharing options that write to a single output file
> (for example `--export-fixes=fixes.yaml`) across parallel `clang-tidy` invocations.
> If you need `--export-fixes`, ensure each job writes to a unique file path to avoid
> corrupted or overwritten outputs.
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
    rev: v1.6.0
    hooks:
      - id: clang-format
        args: [--style=file, --version=21, --verbose]   # Shows processed files
      - id: clang-tidy
        args: [--checks=.clang-tidy, --verbose]   # Shows which compile_commands.json is used
```

## Examples

Two self-contained templates plus quick snippets for other common setups.

- [CMake minimal config](examples/cmake/) — covers ~80% of C++ projects
- [Large project `files:` regex](examples/large-project/) — scoping hooks for speed
- [Quick snippets](examples/README.md) — Meson, clang-format-only, monorepo, CI, `compile_commands.json`

## Used By

<p align="center">
  <a href="https://github.com/boschresearch"><img src="https://avatars.githubusercontent.com/u/35259117?s=200&v=4" alt="Bosch Research" width="28"/></a>
  <strong>Bosch Research</strong>&nbsp;&nbsp;
  <a href="https://github.com/mit-acl"><img src="https://avatars.githubusercontent.com/u/48329234?s=200&v=4" alt="MIT ACL" width="28"/></a>
  <strong>MIT ACL</strong>&nbsp;&nbsp;
  <a href="https://github.com/bazel-contrib"><img src="https://avatars.githubusercontent.com/u/91752542?s=200&v=4" alt="bazel-contrib" width="28"/></a>
  <strong>Bazel Contrib</strong>&nbsp;&nbsp;
  <a href="https://github.com/CodSpeedHQ"><img src="https://avatars.githubusercontent.com/u/116658140?s=200&v=4" alt="CodSpeedHQ" width="28"/></a>
  <strong>CodSpeed</strong>&nbsp;&nbsp;
  <a href="https://github.com/jupyter-xeus"><img src="https://avatars.githubusercontent.com/u/58793052?s=200&v=4" alt="jupyter-xeus" width="28"/></a>
  <strong>Jupyter Xeus</strong>&nbsp;&nbsp;
  </br>
  <a href="https://github.com/rancher-sandbox"><img src="https://avatars.githubusercontent.com/u/78982867?s=200&v=4" alt="rancher-sandbox" width="28"/></a>
  <strong>Rancher Sandbox</strong>&nbsp;&nbsp;
  <a href="https://github.com/computationalgeography"><img src="https://avatars.githubusercontent.com/u/68274590?s=200&v=4" alt="computationalgeography" width="28"/></a>
  <strong>Computational Geography</strong>&nbsp;&nbsp;
  <a href="https://github.com/IMSY-DKFZ"><img src="https://avatars.githubusercontent.com/u/64467378?s=200&v=4" alt="IMSY-DKFZ" width="28"/></a>
  <strong>IMSY</strong>&nbsp;&nbsp;
  <a href="https://github.com/convince-project"><img src="https://avatars.githubusercontent.com/u/123627659?s=200&v=4" alt="CONVINCE-Project" width="28"/></a>
  <strong>CONVINCE-Project</strong>&nbsp;&nbsp;
  <strong> and <a href="https://github.com/search?q=repo%3A%20https%3A%2F%2Fgithub.com%2Fcpp-linter%2Fcpp-linter-hooks&type=code">many more</a>.</strong>
  </br></br>
  See the <a href="https://cpp-linter.github.io/">cpp-linter hub</a> for the full list of organizations using cpp-linter tools.
</p>

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
| Auto-fix mode                    | ✅ via `--fix` (clang-tidy only)          | ❌                                    |
| Compilation database support     | ✅ auto-detect or `--compile-commands`    | ❌                                    |


<!-- > [!TIP]
> In most cases, there is no significant performance difference between `cpp-linter-hooks` and `mirrors-clang-format`. See the [benchmark results](testing/benchmark.md) for details. -->

## Contributing

We welcome contributions! Whether it's fixing issues, suggesting improvements, or submitting pull requests, your support is greatly appreciated.

## License

This project is licensed under the [MIT License](LICENSE).
