"""Tests for cpp_linter_hooks.util -- dynamic PyPI version resolution."""

import json
import logging
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from cpp_linter_hooks.util import (
    _detect_installed_version,
    _get_pypi_versions,
    _install_tool,
    _is_version_installed,
    _resolve_version_from_pypi,
    resolve_install,
    resolve_install_with_diagnostics,
)

# ── sample PyPI responses for consistent test data ──────────────────────

MOCK_PYPI_FORMAT = ("22.1.5", ["22.1.5", "22.1.4", "20.1.8", "20.1.7", "18.1.8"])
MOCK_PYPI_TIDY = ("21.1.6", ["21.1.6", "21.1.1", "20.1.0", "19.1.0.1", "18.1.8"])


def _pypi_side_effect(tool: str):
    """Side-effect that maps tool names to canned PyPI responses."""
    mapping = {
        "clang-format": MOCK_PYPI_FORMAT,
        "clang-tidy": MOCK_PYPI_TIDY,
    }
    return mapping.get(tool, (None, []))


# ═══════════════════════════════════════════════════════════════════════
# _get_pypi_versions
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.benchmark
def test_get_pypi_versions_success():
    """Fetch versions from PyPI JSON API -- happy path."""
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
    """PyPI is unreachable -- return (None, [])."""
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
        # Exact match
        ("clang-format", "20.1.8", "20.1.8"),
        ("clang-tidy", "19.1.0.1", "19.1.0.1"),
        # Prefix match (latest for that prefix)
        ("clang-format", "20", "20.1.8"),
        ("clang-format", "20.1", "20.1.8"),
        ("clang-tidy", "21", "21.1.6"),
        ("clang-tidy", "21.1", "21.1.6"),
    ],
)
def test_resolve_version_from_pypi_success(tool, user_input, expected):
    with patch(
        "cpp_linter_hooks.util._get_pypi_versions", side_effect=_pypi_side_effect
    ):
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
    ],
)
def test_resolve_version_from_pypi_not_found(tool, user_input):
    with patch(
        "cpp_linter_hooks.util._get_pypi_versions", side_effect=_pypi_side_effect
    ):
        version, error = _resolve_version_from_pypi(tool, user_input)
    assert version is None
    assert error is not None
    assert f"Unsupported {tool} version '{user_input}'" in error
    assert "Latest stable version:" in error
    assert "Available versions (sample):" in error


@pytest.mark.benchmark
def test_resolve_version_from_pypi_network_down():
    """When PyPI is unreachable and no tool is installed, return an error."""
    with (
        patch("cpp_linter_hooks.util._get_pypi_versions", return_value=(None, [])),
        patch("cpp_linter_hooks.util._detect_installed_version", return_value=None),
    ):
        version, error = _resolve_version_from_pypi("clang-format", None)
    assert version is None
    assert "Could not find any stable versions" in error
    assert "network" in error.lower()


@pytest.mark.benchmark
def test_resolve_version_from_pypi_offline_fallback():
    """When PyPI is unreachable but the tool is pre-installed, use it."""
    with (
        patch("cpp_linter_hooks.util._get_pypi_versions", return_value=(None, [])),
        patch(
            "cpp_linter_hooks.util._detect_installed_version",
            return_value="18.1.8",
        ),
    ):
        version, error = _resolve_version_from_pypi("clang-format", None)
    assert version == "18.1.8"
    assert error is None


@pytest.mark.benchmark
def test_resolve_version_from_pypi_offline_no_fallback_with_version():
    """When PyPI is unreachable AND user specified a version, fail."""
    with (
        patch("cpp_linter_hooks.util._get_pypi_versions", return_value=(None, [])),
        patch(
            "cpp_linter_hooks.util._detect_installed_version",
            return_value="18.1.8",
        ),
    ):
        version, error = _resolve_version_from_pypi("clang-format", "20")
    assert version is None
    assert "Could not find any stable versions" in error


# ═══════════════════════════════════════════════════════════════════════
# _detect_installed_version
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.benchmark
def test_detect_installed_version_success():
    """Extract version from --version output."""

    def patched_run(*args, **_kwargs):
        return subprocess.CompletedProcess(
            args, returncode=0, stdout="clang-format version 18.1.8\n"
        )

    with (
        patch("shutil.which", return_value="/usr/bin/clang-format"),
        patch("subprocess.run", side_effect=patched_run),
    ):
        version = _detect_installed_version("clang-format")
    assert version == "18.1.8"


@pytest.mark.benchmark
def test_detect_installed_version_not_found():
    with patch("shutil.which", return_value=None):
        version = _detect_installed_version("clang-format")
    assert version is None


@pytest.mark.benchmark
def test_detect_installed_version_subprocess_error():
    with (
        patch("shutil.which", return_value="/usr/bin/clang-format"),
        patch("subprocess.run", side_effect=OSError),
    ):
        version = _detect_installed_version("clang-format")
    assert version is None


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
        check=False,
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
        patch(
            "cpp_linter_hooks.util._get_pypi_versions", side_effect=_pypi_side_effect
        ),
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
        patch(
            "cpp_linter_hooks.util._get_pypi_versions", side_effect=_pypi_side_effect
        ),
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
        patch(
            "cpp_linter_hooks.util._get_pypi_versions", side_effect=_pypi_side_effect
        ),
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
        patch(
            "cpp_linter_hooks.util._get_pypi_versions", side_effect=_pypi_side_effect
        ),
    ):
        result = resolve_install("clang-format", None)
    assert result == Path("/usr/bin/clang-format")
    mock_install.assert_called_once_with("clang-format", "22.1.5")


@pytest.mark.benchmark
def test_resolve_install_invalid_version():
    with (
        patch("shutil.which", return_value=None),
        patch("cpp_linter_hooks.util._install_tool") as mock_install,
        patch(
            "cpp_linter_hooks.util._get_pypi_versions", side_effect=_pypi_side_effect
        ),
    ):
        result = resolve_install("clang-format", "99.0.0")
    assert result is None
    mock_install.assert_not_called()


@pytest.mark.benchmark
def test_resolve_install_with_diagnostics_invalid_version():
    with patch(
        "cpp_linter_hooks.util._get_pypi_versions", side_effect=_pypi_side_effect
    ):
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
        patch(
            "cpp_linter_hooks.util._get_pypi_versions", side_effect=_pypi_side_effect
        ),
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
        patch(
            "cpp_linter_hooks.util._get_pypi_versions", side_effect=_pypi_side_effect
        ),
    ):
        path, error = resolve_install_with_diagnostics("clang-format", None, True)

    assert path == Path("/usr/bin/clang-format")
    assert error is None
    assert (
        "Using latest clang-format Python wheel version 22.1.5"
        in capsys.readouterr().err
    )


# ═══════════════════════════════════════════════════════════════════════
# Additional edge cases (offline: PyPI, pip and tool binaries are mocked)
# ═══════════════════════════════════════════════════════════════════════


@pytest.fixture
def clear_pypi_cache():
    """Isolate tests from the per-process PyPI response cache."""
    _get_pypi_versions.cache_clear()
    yield
    _get_pypi_versions.cache_clear()


def _mock_pypi_payload(mock_urlopen, payload: bytes) -> None:
    mock_urlopen.return_value.__enter__.return_value.read.return_value = payload


def test_get_pypi_versions_sorts_numerically(clear_pypi_cache):
    releases = ["9.0.0", "10.0.1", "6.0.1", "19.1.0", "19.1.0.1", "18.1.8"]
    with patch("urllib.request.urlopen") as mock_urlopen:
        _mock_pypi_payload(
            mock_urlopen,
            json.dumps({"releases": {version: [] for version in releases}}).encode(),
        )
        latest, versions = _get_pypi_versions("clang-tidy")

    mock_urlopen.assert_called_once_with(
        "https://pypi.org/pypi/clang-tidy/json", timeout=10
    )
    assert latest == "19.1.0.1"
    assert versions == ["19.1.0.1", "19.1.0", "18.1.8", "10.0.1", "9.0.0", "6.0.1"]


@pytest.mark.parametrize(
    "pre_release",
    ["23.1.0rc1", "23.1.0a2", "23.1.0b3", "23.1.0.dev1", "23.1.0-beta", "23.1.0alpha"],
)
def test_get_pypi_versions_skips_pre_releases(clear_pypi_cache, pre_release):
    with patch("urllib.request.urlopen") as mock_urlopen:
        _mock_pypi_payload(
            mock_urlopen,
            json.dumps({"releases": {"22.1.8": [], pre_release: []}}).encode(),
        )
        assert _get_pypi_versions("clang-format") == ("22.1.8", ["22.1.8"])


def test_get_pypi_versions_invalid_json(clear_pypi_cache, caplog):
    with (
        patch("urllib.request.urlopen") as mock_urlopen,
        caplog.at_level(logging.WARNING, logger="cpp_linter_hooks.util"),
    ):
        _mock_pypi_payload(mock_urlopen, b"<html>Service Unavailable</html>")
        assert _get_pypi_versions("clang-format") == (None, [])

    assert "Failed to fetch versions for clang-format from PyPI" in caplog.text


@pytest.mark.parametrize(
    ("stdout", "expected"),
    [
        ("Ubuntu clang-format version 18.1.3 (1ubuntu1)\n", "18.1.3"),
        ("LLVM (http://llvm.org/):\n  LLVM version 19.1.0\n", "19.1.0"),
        ("clang-tidy version 22.1.0.1\n", "22.1.0.1"),
        ("clang-format version unknown\n", None),
    ],
)
def test_detect_installed_version_parses_version_banner(stdout, expected):
    completed = subprocess.CompletedProcess(args=[], returncode=0, stdout=stdout)
    with (
        patch("shutil.which", return_value="/usr/bin/clang-format"),
        patch("subprocess.run", return_value=completed) as mock_run,
    ):
        assert _detect_installed_version("clang-format") == expected

    mock_run.assert_called_once_with(
        ["/usr/bin/clang-format", "--version"],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )


def test_detect_installed_version_timeout():
    with (
        patch("shutil.which", return_value="/usr/bin/clang-format"),
        patch(
            "subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="clang-format", timeout=10),
        ),
    ):
        assert _detect_installed_version("clang-format") is None


def test_install_tool_failure_logs_pip_output(caplog):
    completed = subprocess.CompletedProcess(
        args=[],
        returncode=1,
        stdout="Collecting clang-format==20.1.7",
        stderr="ERROR: No matching distribution found for clang-format==20.1.7",
    )
    with (
        patch("subprocess.run", return_value=completed),
        caplog.at_level(logging.ERROR, logger="cpp_linter_hooks.util"),
    ):
        assert _install_tool("clang-format", "20.1.7") is None

    assert "pip failed to install clang-format 20.1.7" in caplog.text
    assert "Collecting clang-format==20.1.7" in caplog.text
    assert "No matching distribution found" in caplog.text


def test_resolve_install_with_diagnostics_verbose_exact_version(capsys):
    with (
        patch(
            "cpp_linter_hooks.util._get_pypi_versions", side_effect=_pypi_side_effect
        ),
        patch(
            "cpp_linter_hooks.util._is_version_installed",
            return_value=Path("/usr/bin/clang-format"),
        ) as mock_installed,
        patch("cpp_linter_hooks.util._install_tool") as mock_install,
    ):
        result = resolve_install_with_diagnostics("clang-format", "20.1.8", True)

    assert result == (Path("/usr/bin/clang-format"), None)
    assert "Using clang-format Python wheel version 20.1.8" in capsys.readouterr().err
    mock_installed.assert_called_once_with("clang-format", "20.1.8")
    mock_install.assert_not_called()


def test_resolve_install_with_diagnostics_is_quiet_by_default(capsys):
    with (
        patch(
            "cpp_linter_hooks.util._get_pypi_versions", side_effect=_pypi_side_effect
        ),
        patch("cpp_linter_hooks.util._is_version_installed", return_value=None),
        patch(
            "cpp_linter_hooks.util._install_tool",
            return_value=Path("/usr/bin/clang-tidy"),
        ) as mock_install,
    ):
        result = resolve_install_with_diagnostics("clang-tidy", "21")

    assert result == (Path("/usr/bin/clang-tidy"), None)
    assert capsys.readouterr().err == ""
    mock_install.assert_called_once_with("clang-tidy", "21.1.6")


def test_resolve_install_with_diagnostics_offline_uses_installed_tool():
    with (
        patch("cpp_linter_hooks.util._get_pypi_versions", return_value=(None, [])),
        patch("cpp_linter_hooks.util._detect_installed_version", return_value="18.1.8"),
        patch(
            "cpp_linter_hooks.util._is_version_installed",
            return_value=Path("/usr/bin/clang-format"),
        ) as mock_installed,
        patch("cpp_linter_hooks.util._install_tool") as mock_install,
    ):
        result = resolve_install_with_diagnostics("clang-format", None)

    assert result == (Path("/usr/bin/clang-format"), None)
    mock_installed.assert_called_once_with("clang-format", "18.1.8")
    mock_install.assert_not_called()


def test_resolve_install_logs_unsupported_version(caplog):
    with (
        patch(
            "cpp_linter_hooks.util._get_pypi_versions", side_effect=_pypi_side_effect
        ),
        caplog.at_level(logging.ERROR, logger="cpp_linter_hooks.util"),
    ):
        assert resolve_install("clang-format", "99") is None

    assert "Unsupported clang-format version '99'" in caplog.text
