"""Shared fixtures for the hook tests."""

import pytest

from cpp_linter_hooks import clang_tidy

REAL_CHANGED_LINES = clang_tidy.changed_lines
REAL_HAS_COMPILATION_DATABASE = clang_tidy._has_compilation_database


@pytest.fixture(autouse=True)
def hook_environment(monkeypatch):
    """Make clang-tidy's environment checks predictable in every test.

    The tests run in CI, inside this repository's git checkout, so by default:
    - the CI and pre-commit range variables are removed,
    - every line counts as changed, so no --line-filter is added,
    - a compilation database is always found next to the source files.

    Tests of these checks use the fixtures below or set the variables.
    """
    for name in ("CI", "PRE_COMMIT_FROM_REF", "PRE_COMMIT_TO_REF"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(clang_tidy, "changed_lines", lambda files: None)
    monkeypatch.setattr(clang_tidy, "_has_compilation_database", lambda files: True)


@pytest.fixture
def real_changed_lines(monkeypatch):
    """Use git to find the changed lines, as the hook does."""
    monkeypatch.setattr(clang_tidy, "changed_lines", REAL_CHANGED_LINES)


@pytest.fixture
def real_compile_db_check(monkeypatch):
    """Look for a compilation database next to the files, as the hook does."""
    monkeypatch.setattr(
        clang_tidy, "_has_compilation_database", REAL_HAS_COMPILATION_DATABASE
    )
