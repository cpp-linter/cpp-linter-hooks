# AGENTS.md

> **IMPORTANT**: When you modify any code in this project, also update this file if the change affects agent behavior, project structure, dependencies, git workflow, or any guidance documented here.

## Git Rules (MUST FOLLOW)

- **Never** commit directly to `main` branch.
- **Never** run `git push --force` on `main` branch.
- All code changes **must** go through a Pull Request (create a feature branch, push, open PR).
- Use conventional branch names: `feature/`, `bugfix/`, `hotfix/`, `chore/`, `release/`.

## Project in a Nutshell

A pre-commit hook repo that auto-installs and runs `clang-format` and `clang-tidy` from Python wheels. Supports Python 3.10+ (tested 3.10–3.15) on Windows, Linux, macOS.

**Entry points** (defined in `pyproject.toml`):
- `clang-format-hook` → `cpp_linter_hooks/clang_format.py:main`
- `clang-tidy-hook` → `cpp_linter_hooks/clang_tidy.py:main`

**Hook definitions**: `.pre-commit-hooks.yaml`

## Key Files

| File | Purpose |
|------|---------|
| `pyproject.toml` | Build config, deps (`pip>=26.1`), dev deps, entry points |
| `cpp_linter_hooks/util.py` | Installed-wheel check, PyPI version resolution + pip install (prefix matching, offline fallback) |
| `cpp_linter_hooks/clang_format.py` | clang-format wrapper (`--verbose`, `--dry-run`) |
| `cpp_linter_hooks/clang_tidy.py` | clang-tidy wrapper (`--compile-commands`, missing-database policy, `--jobs`, `--fix`, `--all-lines`, `-quiet` + status-line filter, `--checks` repair, error hints) |
| `cpp_linter_hooks/changed_lines.py` | Added line ranges per file from `git diff` (staged changes, or `PRE_COMMIT_FROM_REF...PRE_COMMIT_TO_REF`) |
| `.pre-commit-hooks.yaml` | Hook metadata for pre-commit framework |
| `testing/` | Test fixtures (`main.c`, `good.c`, `.clang-format`, `.clang-tidy`, CMakeLists) |
| `examples/` | Example configs (CMake, Meson, large-project scoping) |

## Development

```bash
uv sync --dev          # Install dev deps
uv run pytest -vv      # Run tests
uv run coverage run --source=tests,cpp_linter_hooks -m pytest -vv  # With coverage
bash testing/run.sh    # Integration tests (full pre-commit pipeline)
```

## Core Patterns

- **Version resolution**: A wheel already installed in the hook environment (found by its `<name>-<version>.dist-info` directory in site-packages, e.g. from `additional_dependencies`, with its executable in the environment's scripts directory) is used without network access when it matches `--version` (exact or prefix) or when no `--version` is given. Otherwise the version is resolved dynamically from PyPI at runtime. No hardcoded version lists. Prefix match supported (`--version=20` → `20.1.8`).
- **Return values**: All hooks return `tuple[int, str]` — `(retval, output)`, where `retval` is the tool's exit code (`0` on success, non-zero on failure; `--dry-run` auto-adds `--Werror` so formatting issues fail).
- **clang-tidy compile DB**: Auto-detected from `build/`, `out/`, `cmake-build-debug/`, `_build/`, `builddir/`, then `cmake-build-*/`, `build-*/`, `build/*/`, `out/build/*/` (newest wins). Override with `--compile-commands=<dir>`, disable with `--no-compile-commands`. If none is found, no `-p`/`--extra-arg*` is given and clang-tidy finds no `compile_commands.json`/`compile_flags.txt` next to the files or in their parents, the hook skips clang-tidy (retval 0, message on stderr), or fails when `CI` is set.
- **clang-tidy changed lines**: By default only diagnostics on added lines are reported, via clang-tidy's `--line-filter` (so `-fix` is limited too). Files without added lines are not checked. If any passed file has no changes (`--all-files`), differs on disk from the diffed version (index or `PRE_COMMIT_TO_REF`), or git fails, every line is checked. `--all-lines` or a user `--line-filter` turns this off. Tests: `tests/conftest.py` disables this and the missing-database check by default; use the `real_changed_lines` / `real_compile_db_check` fixtures to test them.
- **clang-tidy parallel**: `--jobs=N` runs per-file in parallel. Forced serial when `--export-fixes`, `-fix`, or `-fix-errors` is used.
- **clang-tidy output**: Without `--verbose`, the hook adds `-quiet` (unless the user set it) and strips status lines (`N warnings generated.`, `Suppressed N warnings ...`, `Use -header-filter=...`, `[1/N] Processing file ...`). With `--verbose`, output is unchanged.
- **clang-tidy check lists**: `--checks=` / `--warnings-as-errors=` lists that YAML split at commas are joined again, quotes inside the value are removed, and `--checks=<file>` (e.g. `.clang-tidy`) gets a note. Notes are appended to the output, which pre-commit shows when the hook fails.

## CI

- `test.yml` — matrix (3 OS × 6 Python versions), pytest + coverage + integration tests
- `codspeed.yml` — benchmarks via CodSpeed on path-filtered changes
