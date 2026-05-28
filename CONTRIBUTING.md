# Contributing

Thanks for your interest in contributing to `cpp-linter-hooks`!

## Setup

You'll need Python 3.10+ and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/cpp-linter/cpp-linter-hooks.git
cd cpp-linter-hooks
uv sync
source .venv/bin/activate
pre-commit install
```

## Running Tests

```bash
# Run all tests
pytest

# With coverage
coverage run -m pytest && coverage report
```

## Code Style

We use [ruff](https://docs.astral.sh/ruff/) for linting and formatting. The
pre-commit hooks installed above will check your code automatically on commit.
You can also run them manually:

```bash
pre-commit run --all-files
```

## Making Changes

1. Create a branch from `main`
2. Make your changes and add tests
3. Run `pytest` to make sure everything passes
4. Open a pull request against `main`

PRs should have a clear description of what changed and why. Reference any
related issues.

## Release Process

Releases are tagged by maintainers. Versioning follows
[setuptools-scm](https://github.com/pypa/setuptools-scm) — the version is
derived from git tags automatically.
