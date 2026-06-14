"""Tests for cpp_linter_hooks.util – dynamic PyPI version resolution."""

import pytest
from unittest.mock import patch
from pathlib import Path
import subprocess
import sys

from cpp_linter_hooks.util import (
    _get_pypi_versions,
    _resolve_version_from_pypi,
    _is_version_installed,
    _install_tool,
    resolve_install_with_diagnostics,
    resolve_install,
)

# ── sample PyPI responses for consistent test data ──────────────────────

MOCK_PYPI_FORMAT = ("22.1.5", ["22.1.5", "22.1.4", "20.1.8", "20.1.7", "18.1.8"])
MOCK_PYPI_TIDY = ("21.1.6", ["21.1.6", "21.1.1", "20.1.0", "19.1.0.1", "18.1.8"])
MOCK_PYPI_INCLUDE_CLEANER = ("22.1.7", ["22.1.7", "22.1.5"])
MOCK_PYPI_APPLY_REPLACEMENTS = ("17.0.6", ["17.0.6", "16.0.0"])


def _pypi_side_effect(tool: str):
    """Side-effect that maps tool names to canned PyPI responses."""
    mapping = {
        "clang-format": MOCK_PYPI_FORMAT,
        "clang-tidy": MOCK_PYPI_TIDY,
        "clang-include-cleaner": MOCK_PYPI_INCLUDE_CLEANER,
        "clang-apply-replacements": MOCK_PYPI_APPLY_REPLACEMENTS,
    }
    return mapping.get(tool, (None, []))


# ═══════════════════════════════════════════════════════════════════════
# _get_pypi_versions
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.benchmark
def test_get_pypi_versions_success():
    """Fetch versions from PyPI JSON API – happy path."""
    _get_pypi_versions.cache_clear()
    mock_data = {
        "releases": {
            "22.1.5": [],
            "22.1.4": [],
            "20.1.8": [],
            "22.1.0-rc1": [],  # pre-release, should be filtered
            "22.1.0a3": [],  # alpha, should be filtered
        }
    }
    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.return_value.__enter__.return_value.read.return_value = (
            __import__("json").dumps(mock_data).encode()
        )
        latest, versions = _get_pypi_versions("clang-format")

    assert latest == "22.1.5"
    assert "22.1.0-rc1" not in versions
    assert "22.1.0a3" not in versions
    assert versions == ["22.1.5", "22.1.4", "20.1.8"]
    # Verify cache works
    latest2, versions2 = _get_pypi_versions("clang-format")
    assert latest2 == latest
    assert versions2 == versions


@pytest.mark.benchmark
def test_get_pypi_versions_network_failure():
    """PyPI is unreachable – return (None, [])."""
    _get_pypi_versions.cache_clear()
    with patch("urllib.request.urlopen", side_effect=OSError("network down")):
        latest, versions = _get_pypi_versions("clang-format")
    assert latest is None
    assert versions == []


@pytest.mark.benchmark
def test_get_pypi_versions_all_prerelease():
    """Only pre-release versions exist on PyPI."""
    _get_pypi_versions.cache_clear()
    mock_data = {"releases": {"22.1.0-rc1": [], "22.1.0a3": []}}
    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.return_value.__enter__.return_value.read.return_value = (
            __import__("json").dumps(mock_data).encode()
        )
        latest, versions = _get_pypi_versions("clang-tidy")
    assert latest is None
    assert versions == []


# ═══════════════════════════════════════════════════════════════════════
# _resolve_version_from_pypi
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.benchmark
@pytest.mark.parametrize(
    "tool,user_input,expected",
    [
        # No version → latest
        ("clang-format", None, "22.1.5"),
        ("clang-tidy", None, "21.1.6"),
        ("clang-include-cleaner", None, "22.1.7"),
        ("clang-apply-replacements", None, "17.0.6"),
        # Exact match
        ("clang-format", "20.1.8", "20.1.8"),
        ("clang-tidy", "19.1.0.1", "19.1.0.1"),
        # Prefix match (latest for that prefix)
        ("clang-format", "20", "20.1.8"),
        ("clang-format", "20.1", "20.1.8"),
        ("clang-tidy", "21", "21.1.6"),
        ("clang-tidy", "21.1", "21.1.6"),
        ("clang-include-cleaner", "22", "22.1.7"),
        ("clang-apply-replacements", "16", "16.0.0"),
    ],
)
def test_resolve_version_from_pypi_success(tool, user_input, expected):
    with patch("cpp_linter_hooks.util._get_pypi_versions", side_effect=_pypi_side_effect):
        version, error = _resolve_version_from_pypi(tool, user_input)
    assert error is None
    assert version == expected


@pytest.mark.benchmark
@pytest.mark.parametrize(
    "tool,user_input",
    [
        ("clang-format", "99"),
        ("clang-format", "20.99"),
        ("clang-tidy", "99"),
        ("clang-tidy", "22.99"),
        ("clang-include-cleaner", "99"),
        ("clang-apply-replacements", "99"),
    ],
)
def test_resolve_version_from_pypi_not_found(tool, user_input):
    with patch("cpp_linter_hooks.util._get_pypi_versions", side_effect=_pypi_side_effect):
        version, error = _resolve_version_from_pypi(tool, user_input)
    assert version is None
    assert error is not None
    assert f"Unsupported {tool} version '{user_input}'" in error
    assert "Latest stable version:" in error
    assert "Available versions (sample):" in error


@pytest.mark.benchmark
def test_resolve_version_from_pypi_network_down():
    """When PyPI is unreachable, return a user-friendly error."""
    with patch("cpp_linter_hooks.util._get_pypi_versions", return_value=(None, [])):
        version, error = _resolve_version_from_pypi("clang-format", None)
    assert version is None
    assert "Could not find any stable versions" in error
    assert "network" in error.lower()


# ═══════════════════════════════════════════════════════════════════════
# _is_version_installed
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.benchmark
def test_is_version_installed_not_in_path():
    with patch("shutil.which", return_value=None):
        result = _is_version_installed("clang-format", "20.1.7")
    assert result is None


@pytest.mark.benchmark
def test_is_version_installed_version_matches():
    mock_path = "/usr/bin/clang-format"

    def patched_run(*args, **kwargs):
        return subprocess.CompletedProcess(
            args, returncode=0, stdout="clang-format version 20.1.7"
        )

    with (
        patch("shutil.which", return_value=mock_path),
        patch("subprocess.run", side_effect=patched_run),
    ):
        result = _is_version_installed("clang-format", "20.1.7")
    assert result == Path(mock_path)


@pytest.mark.benchmark
def test_is_version_installed_version_mismatch():
    mock_path = "/usr/bin/clang-format"

    def patched_run(*args, **kwargs):
        return subprocess.CompletedProcess(
            args, returncode=0, stdout="clang-format version 22.1.0"
        )

    with (
        patch("shutil.which", return_value=mock_path),
        patch("subprocess.run", side_effect=patched_run),
    ):
        result = _is_version_installed("clang-format", "20.1.7")
    assert result is None


# ═══════════════════════════════════════════════════════════════════════
# _install_tool
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.benchmark
def test_install_tool_success():
    mock_path = "/usr/bin/clang-format"

    def patched_run(*args, **kwargs):
        return subprocess.CompletedProcess(args, returncode=0)

    with (
        patch("subprocess.run", side_effect=patched_run) as mock_run,
        patch("shutil.which", return_value=mock_path),
    ):
        result = _install_tool("clang-format", "20.1.7")
        assert result == mock_path

    mock_run.assert_called_once_with(
        [sys.executable, "-m", "pip", "install", "clang-format==20.1.7"],
        capture_output=True,
        text=True,
    )


@pytest.mark.benchmark
def test_install_tool_failure():
    def patched_run(*args, **kwargs):
        return subprocess.CompletedProcess(
            args, returncode=1, stderr="Error", stdout="Installation failed"
        )

    with (
        patch("subprocess.run", side_effect=patched_run),
        patch("cpp_linter_hooks.util.LOG"),
    ):
        result = _install_tool("clang-format", "20.1.7")
    assert result is None


@pytest.mark.benchmark
def test_install_tool_success_but_not_found():
    def patched_run(*args, **kwargs):
        return subprocess.CompletedProcess(args, returncode=0)

    with (
        patch("subprocess.run", side_effect=patched_run),
        patch("shutil.which", return_value=None),
    ):
        result = _install_tool("clang-format", "20.1.7")
    assert result is None


# ═══════════════════════════════════════════════════════════════════════
# resolve_install / resolve_install_with_diagnostics
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.benchmark
def test_resolve_install_tool_already_installed_correct_version():
    mock_path = "/usr/bin/clang-format"

    def patched_run(*args, **kwargs):
        return subprocess.CompletedProcess(
            args, returncode=0, stdout="clang-format version 20.1.8"
        )

    with (
        patch("shutil.which", return_value=mock_path),
        patch("subprocess.run", side_effect=patched_run),
        patch("cpp_linter_hooks.util._get_pypi_versions", side_effect=_pypi_side_effect),
    ):
        result = resolve_install("clang-format", "20.1.8")
    assert Path(result) == Path(mock_path)


@pytest.mark.benchmark
def test_resolve_install_tool_version_mismatch_reinstalls():
    mock_path = "/usr/bin/clang-format"

    def patched_run(*args, **kwargs):
        return subprocess.CompletedProcess(
            args, returncode=0, stdout="clang-format version 22.1.0"
        )

    with (
        patch("shutil.which", return_value=mock_path),
        patch("subprocess.run", side_effect=patched_run),
        patch(
            "cpp_linter_hooks.util._install_tool", return_value=Path(mock_path)
        ) as mock_install,
        patch("cpp_linter_hooks.util._get_pypi_versions", side_effect=_pypi_side_effect),
    ):
        result = resolve_install("clang-format", "20.1.8")
    assert result == Path(mock_path)
    mock_install.assert_called_once_with("clang-format", "20.1.8")


@pytest.mark.benchmark
def test_resolve_install_tool_not_installed():
    with (
        patch("shutil.which", return_value=None),
        patch(
            "cpp_linter_hooks.util._install_tool",
            return_value=Path("/usr/bin/clang-format"),
        ) as mock_install,
        patch("cpp_linter_hooks.util._get_pypi_versions", side_effect=_pypi_side_effect),
    ):
        result = resolve_install("clang-format", "20.1.8")
    assert result == Path("/usr/bin/clang-format")
    mock_install.assert_called_once_with("clang-format", "20.1.8")


@pytest.mark.benchmark
def test_resolve_install_no_version_uses_latest():
    with (
        patch("shutil.which", return_value=None),
        patch(
            "cpp_linter_hooks.util._install_tool",
            return_value=Path("/usr/bin/clang-format"),
        ) as mock_install,
        patch("cpp_linter_hooks.util._get_pypi_versions", side_effect=_pypi_side_effect),
    ):
        result = resolve_install("clang-format", None)
    assert result == Path("/usr/bin/clang-format")
    mock_install.assert_called_once_with("clang-format", "22.1.5")


@pytest.mark.benchmark
def test_resolve_install_invalid_version():
    with (
        patch("shutil.which", return_value=None),
        patch("cpp_linter_hooks.util._install_tool") as mock_install,
        patch("cpp_linter_hooks.util._get_pypi_versions", side_effect=_pypi_side_effect),
    ):
        result = resolve_install("clang-format", "99.0.0")
    assert result is None
    mock_install.assert_not_called()


@pytest.mark.benchmark
def test_resolve_install_with_diagnostics_invalid_version():
    with patch("cpp_linter_hooks.util._get_pypi_versions", side_effect=_pypi_side_effect):
        path, error = resolve_install_with_diagnostics("clang-tidy", "99")

    assert path is None
    assert error is not None
    assert "Unsupported clang-tidy version '99'" in error
    assert "Latest stable version: 21.1.6" in error
    assert "Available versions (sample):" in error


@pytest.mark.benchmark
def test_resolve_install_with_diagnostics_verbose_resolved(capsys):
    with (
        patch("shutil.which", return_value=None),
        patch(
            "cpp_linter_hooks.util._install_tool",
            return_value=Path("/usr/bin/clang-tidy"),
        ),
        patch("cpp_linter_hooks.util._get_pypi_versions", side_effect=_pypi_side_effect),
    ):
        path, error = resolve_install_with_diagnostics("clang-tidy", "21", True)

    assert path == Path("/usr/bin/clang-tidy")
    assert error is None
    assert (
        "Resolved clang-tidy --version=21 to Python wheel version 21.1.6"
        in capsys.readouterr().err
    )


@pytest.mark.benchmark
def test_resolve_install_with_diagnostics_verbose_latest(capsys):
    with (
        patch("shutil.which", return_value=None),
        patch(
            "cpp_linter_hooks.util._install_tool",
            return_value=Path("/usr/bin/clang-format"),
        ),
        patch("cpp_linter_hooks.util._get_pypi_versions", side_effect=_pypi_side_effect),
    ):
        path, error = resolve_install_with_diagnostics("clang-format", None, True)

    assert path == Path("/usr/bin/clang-format")
    assert error is None
    assert (
        "Using latest clang-format Python wheel version 22.1.5"
        in capsys.readouterr().err
    )


# ═══════════════════════════════════════════════════════════════════════
# New wheel tools
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.benchmark
def test_resolve_install_include_cleaner():
    mock_path = "/usr/bin/clang-include-cleaner"
    with (
        patch("shutil.which", return_value=None),
        patch(
            "cpp_linter_hooks.util._install_tool", return_value=Path(mock_path)
        ) as mock_install,
        patch("cpp_linter_hooks.util._get_pypi_versions", side_effect=_pypi_side_effect),
    ):
        result = resolve_install("clang-include-cleaner", "22.1.7")
    assert Path(result) == Path(mock_path)
    mock_install.assert_called_once_with("clang-include-cleaner", "22.1.7")


@pytest.mark.benchmark
def test_resolve_install_include_cleaner_default():
    with (
        patch("shutil.which", return_value=None),
        patch(
            "cpp_linter_hooks.util._install_tool",
            return_value=Path("/usr/bin/clang-include-cleaner"),
        ) as mock_install,
        patch("cpp_linter_hooks.util._get_pypi_versions", side_effect=_pypi_side_effect),
    ):
        result = resolve_install("clang-include-cleaner", None)
    assert result == Path("/usr/bin/clang-include-cleaner")
    mock_install.assert_called_once_with("clang-include-cleaner", "22.1.7")


@pytest.mark.benchmark
def test_resolve_install_include_cleaner_invalid():
    with (
        patch("shutil.which", return_value=None),
        patch("cpp_linter_hooks.util._install_tool") as mock_install,
        patch("cpp_linter_hooks.util._get_pypi_versions", side_effect=_pypi_side_effect),
    ):
        result = resolve_install("clang-include-cleaner", "99.0.0")
    assert result is None
    mock_install.assert_not_called()


@pytest.mark.benchmark
def test_resolve_install_apply_replacements():
    mock_path = "/usr/bin/clang-apply-replacements"
    with (
        patch("shutil.which", return_value=None),
        patch(
            "cpp_linter_hooks.util._install_tool", return_value=Path(mock_path)
        ) as mock_install,
        patch("cpp_linter_hooks.util._get_pypi_versions", side_effect=_pypi_side_effect),
    ):
        result = resolve_install("clang-apply-replacements", "17.0.6")
    assert Path(result) == Path(mock_path)
    mock_install.assert_called_once_with("clang-apply-replacements", "17.0.6")


@pytest.mark.benchmark
def test_resolve_install_apply_replacements_default():
    with (
        patch("shutil.which", return_value=None),
        patch(
            "cpp_linter_hooks.util._install_tool",
            return_value=Path("/usr/bin/clang-apply-replacements"),
        ) as mock_install,
        patch("cpp_linter_hooks.util._get_pypi_versions", side_effect=_pypi_side_effect),
    ):
        result = resolve_install("clang-apply-replacements", None)
    assert result == Path("/usr/bin/clang-apply-replacements")
    mock_install.assert_called_once_with("clang-apply-replacements", "17.0.6")


@pytest.mark.benchmark
def test_resolve_install_apply_replacements_invalid():
    with (
        patch("shutil.which", return_value=None),
        patch("cpp_linter_hooks.util._install_tool") as mock_install,
        patch("cpp_linter_hooks.util._get_pypi_versions", side_effect=_pypi_side_effect),
    ):
        result = resolve_install("clang-apply-replacements", "99.0.0")
    assert result is None
    mock_install.assert_not_called()


@pytest.mark.benchmark
def test_resolve_install_with_diagnostics_include_cleaner_invalid():
    with patch("cpp_linter_hooks.util._get_pypi_versions", side_effect=_pypi_side_effect):
        path, error = resolve_install_with_diagnostics("clang-include-cleaner", "99")

    assert path is None
    assert error is not None
    assert "Unsupported clang-include-cleaner version '99'" in error
    assert "Latest stable version: 22.1.7" in error


@pytest.mark.benchmark
def test_resolve_install_with_diagnostics_apply_replacements_invalid():
    with patch("cpp_linter_hooks.util._get_pypi_versions", side_effect=_pypi_side_effect):
        path, error = resolve_install_with_diagnostics("clang-apply-replacements", "99")

    assert path is None
    assert error is not None
    assert "Unsupported clang-apply-replacements version '99'" in error
    assert "Latest stable version: 17.0.6" in error


@pytest.mark.benchmark
def test_resolve_install_with_diagnostics_include_cleaner_verbose(capsys):
    with (
        patch("shutil.which", return_value=None),
        patch(
            "cpp_linter_hooks.util._install_tool",
            return_value=Path("/usr/bin/clang-include-cleaner"),
        ),
        patch("cpp_linter_hooks.util._get_pypi_versions", side_effect=_pypi_side_effect),
    ):
        path, error = resolve_install_with_diagnostics(
            "clang-include-cleaner", "22", True
        )

    assert path == Path("/usr/bin/clang-include-cleaner")
    assert error is None
    assert (
        "Resolved clang-include-cleaner --version=22 to Python wheel version 22.1.7"
        in capsys.readouterr().err
    )
