"""Integration tests that mirror the scenarios from testing/pre-commit-config-*.yaml.

These tests call the hook functions directly and validate end-to-end behaviour
for the key scenarios exercised by the pre-commit configuration files:

* pre-commit-config.yaml          – basic style-from-file with .clang-format
* pre-commit-config-version.yaml  – explicit tool versions 16–22
* pre-commit-config-verbose.yaml  – --verbose / -v flags
* pre-commit-config-style.yaml    – LLVM, Google, Microsoft, WebKit, Mozilla, Chromium

Each scenario is a named, parametrized pytest function with explicit assertions
so failures report the exact case that broke, and new cases can be added by
extending the parametrize list.
"""

import shutil

import pytest
from pathlib import Path

from cpp_linter_hooks.clang_format import run_clang_format
from cpp_linter_hooks.clang_tidy import run_clang_tidy

TESTING_DIR = Path("testing")
MAIN_C = TESTING_DIR / "main.c"
GOOD_C = TESTING_DIR / "good.c"


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def unformatted_file(tmp_path):
    """Return a temporary copy of the unformatted source file."""
    test_file = tmp_path / "main.c"
    test_file.write_bytes(MAIN_C.read_bytes())
    return test_file


@pytest.fixture()
def clang_format_workspace(tmp_path, monkeypatch):
    """Temp directory that contains .clang-format + an unformatted main.c.

    monkeypatch.chdir ensures --style=file discovers the config file.
    """
    shutil.copy(TESTING_DIR / ".clang-format", tmp_path / ".clang-format")
    test_file = tmp_path / "main.c"
    test_file.write_bytes(MAIN_C.read_bytes())
    monkeypatch.chdir(tmp_path)
    return test_file


# ---------------------------------------------------------------------------
# pre-commit-config.yaml scenario – style-from-file
# ---------------------------------------------------------------------------


@pytest.mark.benchmark
def test_clang_format_style_from_file_reformats(clang_format_workspace):
    """--style=file reads .clang-format and reformats the unformatted file."""
    test_file = clang_format_workspace
    original = test_file.read_text()

    ret, output = run_clang_format(["--style=file", str(test_file)])

    assert ret == 0
    assert isinstance(output, str)
    assert test_file.read_text() != original, "file should have been reformatted"


@pytest.mark.benchmark
def test_clang_format_style_from_file_is_idempotent(clang_format_workspace):
    """Running --style=file twice on an already-formatted file is a no-op."""
    test_file = clang_format_workspace

    # First pass: reformat
    run_clang_format(["--style=file", str(test_file)])
    after_first = test_file.read_text()

    # Second pass: file should be unchanged
    ret, output = run_clang_format(["--style=file", str(test_file)])

    assert ret == 0
    assert isinstance(output, str)
    assert test_file.read_text() == after_first, "second pass must not change the file"


# ---------------------------------------------------------------------------
# pre-commit-config-version.yaml scenario – explicit versions 16–22
# ---------------------------------------------------------------------------


@pytest.mark.benchmark
@pytest.mark.parametrize("version", ["16", "17", "18", "19", "20", "21", "22"])
def test_clang_format_style_from_file_with_version(tmp_path, monkeypatch, version):
    """--style=file combined with an explicit --version reformats the file."""
    shutil.copy(TESTING_DIR / ".clang-format", tmp_path / ".clang-format")
    test_file = tmp_path / "main.c"
    test_file.write_bytes(MAIN_C.read_bytes())
    monkeypatch.chdir(tmp_path)

    original = test_file.read_text()
    ret, output = run_clang_format(
        ["--style=file", f"--version={version}", str(test_file)]
    )

    assert ret == 0
    assert isinstance(output, str)
    assert test_file.read_text() != original, (
        f"version {version}: file should have been reformatted"
    )


# ---------------------------------------------------------------------------
# pre-commit-config-style.yaml scenario – various style presets
# ---------------------------------------------------------------------------

STYLE_PRESETS = ["LLVM", "Google", "Microsoft", "WebKit", "Mozilla", "Chromium"]


@pytest.mark.benchmark
@pytest.mark.parametrize("style", STYLE_PRESETS)
def test_clang_format_style_preset_reformats_unformatted_file(style, unformatted_file):
    """Each style preset should reformat the unformatted main.c."""
    original = unformatted_file.read_text()

    ret, output = run_clang_format([f"--style={style}", str(unformatted_file)])

    assert ret == 0
    assert isinstance(output, str)
    assert unformatted_file.read_text() != original, (
        f"style={style}: file should have been reformatted"
    )


@pytest.mark.benchmark
@pytest.mark.parametrize("style", STYLE_PRESETS)
def test_clang_format_style_preset_is_idempotent(style, tmp_path):
    """Running clang-format twice with the same style preset is a no-op."""
    test_file = tmp_path / "main.c"
    test_file.write_bytes(MAIN_C.read_bytes())

    # First pass: reformat
    run_clang_format([f"--style={style}", str(test_file)])
    after_first = test_file.read_text()

    # Second pass: file must not change
    ret, output = run_clang_format([f"--style={style}", str(test_file)])

    assert ret == 0
    assert isinstance(output, str)
    assert test_file.read_text() == after_first, (
        f"style={style}: second pass must not change the file"
    )


@pytest.mark.benchmark
def test_clang_format_google_style_matches_good_c(unformatted_file):
    """Google-style formatting of main.c must exactly match testing/good.c."""
    ret, output = run_clang_format(["--style=Google", str(unformatted_file)])

    assert ret == 0
    assert isinstance(output, str)
    assert unformatted_file.read_text() == GOOD_C.read_text()


# ---------------------------------------------------------------------------
# pre-commit-config-verbose.yaml scenario – verbose flags
# ---------------------------------------------------------------------------


@pytest.mark.benchmark
@pytest.mark.parametrize("verbose_flag", ["--verbose", "-v"])
def test_clang_format_verbose_flag_succeeds(verbose_flag, unformatted_file):
    """Both --verbose and -v flags must be accepted and not break formatting."""
    ret, output = run_clang_format(
        [verbose_flag, "--style=Google", str(unformatted_file)]
    )

    assert ret == 0
    assert isinstance(output, str)
    assert unformatted_file.read_text() == GOOD_C.read_text()


# ---------------------------------------------------------------------------
# pre-commit-config-parallel.yaml scenario – parallel clang-tidy
# ---------------------------------------------------------------------------


@pytest.mark.benchmark
def test_clang_tidy_parallel_execution_completes(tmp_path):
    """clang-tidy --jobs=2 processes multiple source files without crashing."""
    main_file = tmp_path / "main.c"
    good_file = tmp_path / "good.c"
    main_file.write_bytes(MAIN_C.read_bytes())
    good_file.write_bytes(GOOD_C.read_bytes())

    ret, output = run_clang_tidy(
        [
            "--no-compile-commands",
            "--jobs=2",
            str(main_file),
            str(good_file),
        ]
    )

    # Return code must be a valid integer (0 = clean, 1 = issues found).
    assert isinstance(ret, int)
    assert ret in (0, 1)
