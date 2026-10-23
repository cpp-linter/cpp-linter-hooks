# cpp-linter-hooks

[![PyPI](https://img.shields.io/pypi/v/cpp-linter-hooks?labelColor=454a63&color=007ec6)](https://pypi.org/project/cpp-linter-hooks/)
[![ci](https://img.shields.io/github/actions/workflow/status/cpp-linter/cpp-linter-hooks/test.yml?branch=main&label=ci&labelColor=454a63)](https://github.com/cpp-linter/cpp-linter-hooks/actions/workflows/test.yml)
[![coverage](https://img.shields.io/codecov/c/github/cpp-linter/cpp-linter-hooks?labelColor=454a63)](https://codecov.io/gh/cpp-linter/cpp-linter-hooks)
[![part of cpp-linter](https://img.shields.io/badge/part%20of-cpp--linter-ffc20a?labelColor=454a63)](https://cpp-linter.github.io/)

[pre-commit](https://pre-commit.com/) hooks that pip-install the clang-format and clang-tidy
version you pin, on every developer's machine.

[Website](https://cpp-linter.github.io/) ·
[Get started](https://cpp-linter.github.io/getting-started/#before-every-commit) ·
[Discussions](https://github.com/orgs/cpp-linter/discussions)

## Quick start

Add this configuration to your `.pre-commit-config.yaml` file:

```yaml
repos:
  - repo: https://github.com/cpp-linter/cpp-linter-hooks
    rev: v1.8.0
    hooks:
      - id: clang-format
        args: [--style=file]
        additional_dependencies: [clang-format==21.1.8]
      - id: clang-tidy
        additional_dependencies: [clang-tidy==21.1.6]
```

Run `pre-commit install` once in each clone. `--style=file` loads the style from your
`.clang-format` file, and clang-tidy reads your `.clang-tidy` file by itself. The clang-tidy hook
reports only problems on the lines that your commit adds or changes (see
[Only changed lines](https://github.com/cpp-linter/cpp-linter-hooks#only-changed-lines)). It needs
a `compile_commands.json`, which it looks for in `build/` and a few other directories; without one
it skips clang-tidy on your machine and fails in CI (see
[Compilation database](https://github.com/cpp-linter/cpp-linter-hooks#compilation-database)).

`additional_dependencies` pins the clang-format and clang-tidy versions, and pre-commit installs
them once, with the hook (see
[Install the tool with the hook](https://github.com/cpp-linter/cpp-linter-hooks#install-the-tool-with-the-hook)).

## Usage

### Custom clang tool version

> [!TIP]
> The `rev` tag (e.g. `v1.8.0`) is the **project** version, not the clang tool version. Without
> `additional_dependencies` or `--version`, each hook installs the newest clang-format or
> clang-tidy wheel on PyPI the first time it runs and keeps it until pre-commit rebuilds the hook
> environment, so two machines can run different LLVM versions with the same configuration. Pin
> the version in one of the two places, not both.

Instead of `additional_dependencies`, you can give the version in `--version`. The hook then
picks and installs the wheel the first time it runs:

```yaml
      - id: clang-format
        args: [--style=file, --version=21]
```

- `--version=21` installs the newest 21.x wheel, and `--version=21.1.8` pins an exact release.
  clang-tidy wheels are released separately from clang-format wheels and skip some releases, so
  give clang-tidy the major version.
- clang-format wheels cover LLVM 6 to 23 and clang-tidy wheels LLVM 13 to 23. For a version without
  a wheel, the hook fails and lists some of the versions that exist.
- Each `--version` is installed once, into its own directory in the hook environment, and later
  runs use it without contacting pypi.org. pre-commit shares the hook environment between all
  your projects that use the same `rev`, so projects that ask for different versions keep their
  own copy instead of reinstalling. A wheel from `additional_dependencies` that matches
  `--version` is used as well.
- The first run with a new `--version`, or without any version, looks the version up on pypi.org
  and installs it, so that run needs network access. pre-commit runs the hook on groups of files
  in parallel; one of them installs the wheel and the others wait for it.

### Install the tool with the hook

We recommend giving the version in `additional_dependencies`, as in the Quick start. pre-commit
then installs the clang tool once, when it creates the hook environment, the same way
[mirrors-clang-format](https://github.com/pre-commit/mirrors-clang-format) does. The hook uses
that wheel, so do not set `--version` as well.

pre-commit installs `additional_dependencies` with the hook (for example on
`pre-commit install-hooks`), through the same package index it uses for the hook itself. The hooks
then never install anything or contact pypi.org when they run, so this works:

- on [pre-commit.ci](https://pre-commit.ci/), which runs hooks without network access,
- behind a firewall or with a company PyPI mirror, where pypi.org may be blocked or slow,
- for teams and CI, where every machine gets exactly the same wheel.

If you set both and they do not match, `--version` wins and the hook installs that wheel at run
time, which needs network access.

### clang-format

To use a predefined coding style instead of your `.clang-format` file:

```yaml
      - id: clang-format
        args: [--style=Google] # Other coding style: LLVM, GNU, Chromium, Microsoft, Mozilla, WebKit.
```

When clang-format changes a file, the hook fails and pre-commit stops the commit:

```bash
clang-format.............................................................Failed
- hook id: clang-format
- files were modified by this hook
```

Here’s a sample diff showing the formatting applied with `--style=Google`:

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
> Use `--dry-run` in `args` of `clang-format` to print instead of changing the format.
> The hook fails if a file needs formatting and prints the lines to fix:

```bash
clang-format.............................................................Failed
- hook id: clang-format
- exit code: 1

main.c:2:13: error: code should be clang-formatted [-Wclang-format-violations]
int main() {for (;;) break; printf("Hello world!\n");return 0;}
            ^
main.c:2:21: error: code should be clang-formatted [-Wclang-format-violations]
int main() {for (;;) break; printf("Hello world!\n");return 0;}
                    ^
main.c:2:28: error: code should be clang-formatted [-Wclang-format-violations]
int main() {for (;;) break; printf("Hello world!\n");return 0;}
                           ^
main.c:2:54: error: code should be clang-formatted [-Wclang-format-violations]
int main() {for (;;) break; printf("Hello world!\n");return 0;}
                                                     ^
main.c:2:63: error: code should be clang-formatted [-Wclang-format-violations]
int main() {for (;;) break; printf("Hello world!\n");return 0;}
                                                              ^
```

### clang-tidy

To set the checks in `args` instead of your `.clang-tidy` file, quote the whole option: inside
`[...]`, YAML splits an unquoted value at each comma. When that happens, the hook joins the pieces
again and adds a note on how to fix the configuration. `--checks` takes check names, not a file:
clang-tidy reads the nearest `.clang-tidy` file by itself, so `--checks=.clang-tidy` does nothing.

```yaml
      - id: clang-tidy
        args: ["--checks=boost-*,bugprone-*,performance-*,readability-*,portability-*,modernize-*,clang-analyzer-*,cppcoreguidelines-*"]
```

When clang-tidy reports a warning or an error, the hook fails:

```bash
clang-tidy...............................................................Failed
- hook id: clang-tidy
- exit code: 1

/home/runner/work/cpp-linter-hooks/cpp-linter-hooks/testing/main.c:4:13: warning: statement should be inside braces [readability-braces-around-statements]
    for (;;)
            ^
             {

```

The hook passes `-quiet` to clang-tidy and drops status lines such as `522 warnings generated.`,
which count warnings in system headers that clang-tidy does not show. Add `--verbose` to `args` to
keep clang-tidy's full output.

#### Only changed lines

By default the hook reports only the problems on lines that the commit adds or changes, so old
warnings elsewhere in a file do not block your commit. It reads the changes with `git diff`:

- On `git commit` and `pre-commit run`: the staged changes.
- With `pre-commit run --from-ref A --to-ref B` and in the `pre-push` stage: the changes between
  the two commits.

The hook passes these lines to clang-tidy's `--line-filter`, so `--fix` applies only the fixes
for problems reported on those lines (a fix can still touch a nearby line, for example to add a
closing brace). Compiler errors are always reported. Files with no added lines, such as a pure rename, are
not checked.

The hook checks every line when the files it gets have no changes, for example with
`pre-commit run --all-files` on a clean working tree, when a file on disk differs from the
version the lines come from (unstaged changes in a direct run, or uncommitted changes on
`pre-push`), or outside a git repository. To always check
every line, for example in a manual stage, add `--all-lines`:

```yaml
      - id: clang-tidy
        args: [--all-lines]
```

Checking only changed lines does not make clang-tidy faster: it still analyzes the whole file.
See [Performance optimization](https://github.com/cpp-linter/cpp-linter-hooks#performance-optimization).

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
    rev: v1.8.0  # includes --fix support
    hooks:
      - id: clang-tidy
        args: [--fix]
```

### Compilation database

For CMake or Meson projects, clang-tidy works best with a `compile_commands.json`
file that records the exact compiler flags used for each file. Without it, clang-tidy
may report false positives from missing include paths or wrong compiler flags.

The hook auto-detects `compile_commands.json` in common build directories and passes `-p <dir>`
to clang-tidy automatically — no configuration needed for most projects. It looks in `build/`,
`out/`, `cmake-build-debug/`, `_build/` and `builddir/` first, then in `cmake-build-*/`,
`build-*/`, `build/*/` and `out/build/*/` (CMake presets, Visual Studio), where the most recently
written one wins. Without `-p`, clang-tidy also finds a `compile_commands.json` or
`compile_flags.txt` next to each file or in its parent directories, so a database in the
repository root works too.

```yaml
repos:
  - repo: https://github.com/cpp-linter/cpp-linter-hooks
    rev: v1.8.0
    hooks:
      - id: clang-tidy
        # Auto-detects ./build/compile_commands.json if present
```

To specify the build directory explicitly:

```yaml
      - id: clang-tidy
        args: [--compile-commands=build]
```

When no compilation database is found, clang-tidy would report missing headers instead of
problems in your code, so the hook:

- **skips clang-tidy on your machine** and passes. The message says how to generate the database;
  pre-commit shows it with `pre-commit run -v` or `verbose: true` on the hook.
- **fails in CI**, when the `CI` environment variable is set (GitHub Actions, GitLab CI and most CI
  services set it), so a broken setup does not pass unnoticed.

The hook runs clang-tidy anyway when `args` tell it how to compile: `-p`, `--extra-arg` or
`--extra-arg-before`.

To disable auto-detection and always run clang-tidy without a database (e.g. in a monorepo where
auto-detect might pick the wrong database, or for code that needs no compiler flags):

```yaml
      - id: clang-tidy
        args: [--no-compile-commands]
```

> [!NOTE]
> Generate `compile_commands.json` with CMake using `cmake -DCMAKE_EXPORT_COMPILE_COMMANDS=ON -Bbuild .`
> or add `set(CMAKE_EXPORT_COMPILE_COMMANDS ON)` to your `CMakeLists.txt`.
> `--compile-commands` takes the **directory** containing `compile_commands.json`, not the file path itself.

### Examples

Three self-contained templates plus quick snippets for other common setups.

- [CMake minimal config](https://github.com/cpp-linter/cpp-linter-hooks/tree/main/examples/cmake)
- [Meson minimal config](https://github.com/cpp-linter/cpp-linter-hooks/tree/main/examples/meson)
- [Large project `files:` regex](https://github.com/cpp-linter/cpp-linter-hooks/tree/main/examples/large-project) — scoping hooks for speed
- [Quick snippets](https://github.com/cpp-linter/cpp-linter-hooks/blob/main/examples/README.md) — Meson, clang-format-only, monorepo, CI, `compile_commands.json`

## Troubleshooting

### Performance optimization

> [!TIP]
> For large codebases, if your `pre-commit` runs longer than expected, it is highly recommended to add `files` in `.pre-commit-config.yaml` to limit the scope of the hook. This helps improve performance by reducing the number of files being checked and avoids unnecessary processing. Here's an example configuration:

```yaml
- repo: https://github.com/cpp-linter/cpp-linter-hooks
  rev: v1.8.0
  hooks:
    - id: clang-format
      args: [--style=file]
      files: ^(src|include)/.*\.(cpp|cc|cxx|h|hpp)$ # Limits to specific dirs and file types
    - id: clang-tidy
      files: ^(src|include)/.*\.(cpp|cc|cxx|h|hpp)$
```

For `clang-tidy`, you can also process multiple files in parallel by adding `--jobs`
or `-j`:

```yaml
- repo: https://github.com/cpp-linter/cpp-linter-hooks
  rev: v1.8.0
  hooks:
    - id: clang-tidy
      args: [--jobs=4]
```

> [!WARNING]
> When `args` include `--fix`, `-fix`, `-fix-errors` or `--export-fixes`, the hook ignores
> `--jobs`. pre-commit itself still runs the hook on groups of files in parallel, so each group
> overwrites a shared `--export-fixes` file and fixes to the same header can collide. Add
> `require_serial: true` to the hook to run it once for all files.

With LLVM 21 and older, clang-tidy enables the `clang-analyzer-*` checks by default unless your
`Checks` start with `-*`, and they take most of its time: in our measurements on
[fmt](https://github.com/fmtlib/fmt), more than 90%. LLVM 22 removed them from the defaults. If
clang-tidy is slow and you do not need them, add `-clang-analyzer-*` to `Checks` in `.clang-tidy`.

Alternatively, if you want to run the hooks manually on only the changed files, you can use the following command:

```bash
pre-commit run --files $(git diff --name-only)
```

This approach ensures that only modified files are checked, further speeding up the linting process during development.

### Verbose output

> [!NOTE]
> Use `-v` or `--verbose` in `args` to enable verbose output.
> For `clang-format`, it shows the list of processed files.
> For `clang-tidy`, it prints which `compile_commands.json` is being used (when auto-detected or explicitly set)
> and which lines are reported, and keeps clang-tidy's full output, without `-quiet`.
> pre-commit shows this output only when the hook fails; add `verbose: true` to the hook to see it on every run.

```yaml
repos:
  - repo: https://github.com/cpp-linter/cpp-linter-hooks
    rev: v1.8.0
    hooks:
      - id: clang-format
        args: [--style=file, --verbose]   # Shows processed files
      - id: clang-tidy
        args: [--verbose]   # Shows which compile_commands.json is used
```

## Compared with mirrors-clang-format

[mirrors-clang-format](https://github.com/pre-commit/mirrors-clang-format) is pre-commit's
mirror of the clang-format wheel.

| Feature                          | `cpp-linter-hooks`                        | `mirrors-clang-format`                 |
|----------------------------------|-------------------------------------------|----------------------------------------|
| Supports `clang-format` and `clang-tidy` | Both                              | `clang-format` only                    |
| Custom configuration files       | `.clang-format`, `.clang-tidy`            | `.clang-format`                        |
| Specify tool version             | `additional_dependencies` or `--version` | via `rev` tag (e.g. `rev: v21.1.8`)    |
| `rev` tag meaning                | Project version, not the tool version     | Equals the clang-format version directly |
| Default file types               | C, C++                                    | C, C++, C#, CUDA, Java, JavaScript, JSON, Objective-C, proto, textproto, Metal |
| Supports passing format style string | via `--style`                         | via `--style`                          |
| Verbose output                   | via `--verbose`                           | via `--verbose`                        |
| Dry-run mode                     | via `--dry-run`                           | via `--dry-run --Werror`               |
| Auto-fix mode                    | via `--fix` (clang-tidy only)             | No                                     |
| Compilation database support     | auto-detect or `--compile-commands`       | No                                     |

## Used by

These organizations run cpp-linter-hooks on their default branch:

[<img src="https://avatars.githubusercontent.com/u/48329234?s=40&v=4" width="20" height="20" alt=""> MIT ACL](https://github.com/mit-acl) ·
[<img src="https://avatars.githubusercontent.com/u/91752542?s=40&v=4" width="20" height="20" alt=""> Bazel Contrib](https://github.com/bazel-contrib) ·
[<img src="https://avatars.githubusercontent.com/u/116658140?s=40&v=4" width="20" height="20" alt=""> CodSpeed](https://github.com/CodSpeedHQ) ·
[<img src="https://avatars.githubusercontent.com/u/67697691?s=40&v=4" width="20" height="20" alt=""> doldecomp](https://github.com/doldecomp) ·
[<img src="https://avatars.githubusercontent.com/u/28489597?s=40&v=4" width="20" height="20" alt=""> HKUST Aerial Robotics](https://github.com/HKUST-Aerial-Robotics) ·
[<img src="https://avatars.githubusercontent.com/u/80915497?s=40&v=4" width="20" height="20" alt=""> Kubewarden](https://github.com/kubewarden) ·
[<img src="https://avatars.githubusercontent.com/u/68274590?s=40&v=4" width="20" height="20" alt=""> Computational Geography](https://github.com/computationalgeography) ·
[<img src="https://avatars.githubusercontent.com/u/64467378?s=40&v=4" width="20" height="20" alt=""> IMSY](https://github.com/IMSY-DKFZ) ·
[<img src="https://avatars.githubusercontent.com/u/123627659?s=40&v=4" width="20" height="20" alt=""> CONVINCE-Project](https://github.com/convince-project)

The [showcase](https://cpp-linter.github.io/showcase/) lists more projects that use cpp-linter tools.

## Sponsors

cpp-linter is maintained by two volunteers. [Sponsor the project](https://cpp-linter.github.io/sponsor/)
through [Open Collective](https://opencollective.com/cpp-linter). Silver and Gold sponsors get their logo
here.

## Contributing

See the [contributing guide](https://github.com/cpp-linter/cpp-linter-hooks/blob/main/CONTRIBUTING.md) and [open an issue](https://github.com/cpp-linter/cpp-linter-hooks/issues) for bugs and feature requests.

## License

This project is licensed under the [MIT License](https://github.com/cpp-linter/cpp-linter-hooks/blob/main/LICENSE).
