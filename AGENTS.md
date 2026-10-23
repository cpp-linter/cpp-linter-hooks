# AGENTS.md

> **IMPORTANT**: When you modify any code in this project, also update this file if the change affects agent behavior, git workflow, or any guidance documented here.

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

## Development

```bash
uv sync --dev          # Install dev deps
uv run pytest -vv      # Run tests
uv run coverage run --source=tests,cpp_linter_hooks -m pytest -vv  # With coverage
bash testing/run.sh    # Integration tests (full pre-commit pipeline)
```
