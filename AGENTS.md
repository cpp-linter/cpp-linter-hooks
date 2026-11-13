# AGENTS.md

## Git Rules (MUST FOLLOW)

- **Never** commit directly to `main` branch.
- **Never** run `git push --force` on `main` branch.
- All code changes **must** go through a Pull Request (create a feature branch, push, open PR).
- Use conventional branch names: `feature/`, `bugfix/`, `hotfix/`, `chore/`, `release/`.

## Project in a Nutshell

A pre-commit hook repo that auto-installs and runs `clang-format` and `clang-tidy` from Python wheels.

**Hook definitions**: `.pre-commit-hooks.yaml`

## Development

```bash
uv sync --dev          # Install dev deps
uv run pytest -vv      # Run tests
uv run coverage run --source=tests,cpp_linter_hooks -m pytest -vv  # With coverage
bash testing/run.sh    # Integration tests (full pre-commit pipeline)
```
