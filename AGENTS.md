# AGENTS.md

> **IMPORTANT**: When you modify any code in this project, also update this file if the change affects agent behavior, project structure, dependencies, git workflow, or any guidance documented here.

## Git Rules (MUST FOLLOW)

- **Never** commit directly to `main` branch.
- **Never** run `git push --force` on `main` branch.
- All code changes **must** go through a Pull Request (create a feature branch, push, open PR).
- Use conventional branch names: `feature/`, `bugfix/`, `hotfix/`, `chore/`, `release/`.

## Project in a Nutshell

A pre-commit hook repo that auto-installs and runs `clang-format` and `clang-tidy` from Python wheels. Supports Python 3.10+ (tested 3.9–3.14) on Windows, Linux, macOS.

**Entry points** (defined in `pyproject.toml`):
- `clang-format-hook` → `cpp_linter_hooks/clang_format.py:main`
- `clang-tidy-hook` → `cpp_linter_hooks/clang_tidy.py:main`

**Hook definitions**: `.pre-commit-hooks.yaml`

## Key Files

| File | Purpose |
|------|---------|
| `pyproject.toml` | Build config, deps (`pip>=26.1`, `tomli`), dev deps, entry points |
| `cpp_linter_hooks/util.py` | PyPI version resolution + pip install (prefix matching, offline fallback) |
| `cpp_linter_hooks/clang_format.py` | clang-format wrapper (`--verbose`, `--dry-run`) |
| `cpp_linter_hooks/clang_tidy.py` | clang-tidy wrapper (`--compile-commands`, `--jobs`, `--fix`, error hints) |
| `.pre-commit-hooks.yaml` | Hook metadata for pre-commit framework |
| `testing/` | Test fixtures (`main.c`, `good.c`, `.clang-format`, `.clang-tidy`, CMakeLists) |
| `examples/` | Example configs (CMake, large-project scoping) |

## Development

```bash
uv sync --dev          # Install dev deps
uv run pytest -vv      # Run tests
uv run coverage run --source=tests,cpp_linter_hooks -m pytest -vv  # With coverage
bash testing/run.sh    # Integration tests (full pre-commit pipeline)
```

## Core Patterns

- **Version resolution**: Dynamic from PyPI at runtime. No hardcoded version lists. Prefix match supported (`--version=20` → `20.1.8`).
- **Return values**: All hooks return `Tuple[int, str]` — `(0, "")` success, `(1, output)` failure, `(-1, output)` dry-run.
- **clang-tidy compile DB**: Auto-detected from `build/`, `out/`, `cmake-build-debug/`, `_build/`. Override with `--compile-commands=<dir>`, disable with `--no-compile-commands`.
- **clang-tidy parallel**: `--jobs=N` runs per-file in parallel. Forced serial when `--export-fixes`, `-fix`, or `-fix-errors` is used.

## CI

- `test.yml` — matrix (3 OS × 6 Python versions), pytest + coverage + integration tests
- `codspeed.yml` — benchmarks via CodSpeed on path-filtered changes
