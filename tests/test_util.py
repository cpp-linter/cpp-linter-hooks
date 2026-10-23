"""Tests for cpp_linter_hooks.util -- dynamic PyPI version resolution."""

import errno
import json
import logging
import subprocess
import sys
import sysconfig
import textwrap
from pathlib import Path
from unittest.mock import patch

import pytest

from cpp_linter_hooks.util import (
    _detect_installed_version,
    _env_paths,
    _find_installed_wheel,
    _get_pypi_versions,
    _install_lock,
    _install_tool,
    _installed_wheel_version,
    _is_version_installed,
    _resolve_version_from_pypi,
    _version_satisfies,
    resolve_install,
    resolve_install_with_diagnostics,
)

# ── sample PyPI responses for consistent test data ──────────────────────

MOCK_PYPI_FORMAT = ("22.1.5", ["22.1.5", "22.1.4", "20.1.8", "20.1.7", "18.1.8"])
MOCK_PYPI_TIDY = ("21.1.6", ["21.1.6", "21.1.1", "20.1.0", "19.1.0.1", "18.1.8"])


@pytest.fixture(autouse=True)
def no_installed_wheel():
    """Hide wheels installed in the test environment from the resolver.

    Tests that need an installed wheel patch ``_installed_wheel_version`` or
    ``_find_installed_wheel`` themselves.
    """
    with patch("cpp_linter_hooks.util._installed_wheel_version", return_value=None):
        yield


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


@pytest.mark.parametrize(
    ("tool", "user_input"),
    [("clang-format", "1"), ("clang-format", "2"), ("clang-tidy", "2")],
)
def test_resolve_version_from_pypi_prefix_requires_whole_components(tool, user_input):
    """A major-version prefix must not match a longer major ("2" is not "22")."""
    with patch(
        "cpp_linter_hooks.util._get_pypi_versions", side_effect=_pypi_side_effect
    ):
        version, error = _resolve_version_from_pypi(tool, user_input)

    assert version is None
    assert f"Unsupported {tool} version '{user_input}'" in error


@pytest.mark.parametrize(
    ("user_input", "expected"),
    [("21.1", "21.1.6"), ("21", "21.10.0"), ("19.1.0", "19.1.0.1")],
)
def test_resolve_version_from_pypi_prefix_stops_at_component_boundary(
    user_input, expected
):
    versions = ["21.10.0", "21.1.6", "19.1.0.1"]
    with patch(
        "cpp_linter_hooks.util._get_pypi_versions",
        return_value=(versions[0], versions),
    ):
        assert _resolve_version_from_pypi("clang-tidy", user_input) == (expected, None)


# ═══════════════════════════════════════════════════════════════════════
# Installed wheel in the hook environment (additional_dependencies, offline)
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.parametrize(
    ("installed", "requested", "expected"),
    [
        ("21.1.6", None, True),
        ("21.1.6", "21", True),
        ("21.1.6", "21.1", True),
        ("21.1.6", "21.1.6", True),
        ("19.1.0.1", "19.1.0", True),
        ("21.1.6", "2", False),
        ("21.1.6", "21.1.1", False),
        ("21.10.0", "21.1", False),
        ("23.1.3", "21", False),
    ],
)
def test_version_satisfies(installed, requested, expected):
    assert _version_satisfies(installed, requested) is expected


def _paths(directory) -> dict[str, str]:
    """Environment paths that all point at one directory."""
    return dict.fromkeys(("purelib", "platlib", "scripts"), str(directory))


def test_env_paths_match_sysconfig():
    _env_paths.cache_clear()
    assert _env_paths() == sysconfig.get_paths()


def test_installed_wheel_version_reads_dist_info_name(tmp_path):
    for name in (
        "clang_tidy_extra-1.0.dist-info",
        "clang_format-22.1.8.dist-info",
        "clang_tidy",
        "Clang_Tidy-21.1.6.dist-info",
    ):
        (tmp_path / name).mkdir()
    with patch("cpp_linter_hooks.util._env_paths", return_value=_paths(tmp_path)):
        assert _installed_wheel_version("clang-tidy") == "21.1.6"
        assert _installed_wheel_version("clang-format") == "22.1.8"


def test_installed_wheel_version_checks_platlib(tmp_path):
    purelib, platlib = tmp_path / "purelib", tmp_path / "platlib"
    purelib.mkdir()
    (platlib / "clang_tidy-21.1.6.dist-info").mkdir(parents=True)
    paths = {"purelib": str(purelib), "platlib": str(platlib), "scripts": ""}
    with patch("cpp_linter_hooks.util._env_paths", return_value=paths):
        assert _installed_wheel_version("clang-tidy") == "21.1.6"


def test_installed_wheel_version_missing_distribution(tmp_path):
    (tmp_path / "clang_format-22.1.8.dist-info").mkdir()
    with patch("cpp_linter_hooks.util._env_paths", return_value=_paths(tmp_path)):
        assert _installed_wheel_version("clang-tidy") is None
    with patch(
        "cpp_linter_hooks.util._env_paths", return_value=_paths(tmp_path / "missing")
    ):
        assert _installed_wheel_version("clang-tidy") is None


def test_find_installed_wheel_prefers_environment_scripts_dir():
    with (
        patch("cpp_linter_hooks.util._installed_wheel_version", return_value="21.1.6"),
        patch("cpp_linter_hooks.util._env_paths", return_value=_paths("/venv/bin")),
        patch("shutil.which", return_value="/venv/bin/clang-tidy") as mock_which,
    ):
        assert _find_installed_wheel("clang-tidy", "21") == (
            Path("/venv/bin/clang-tidy"),
            "21.1.6",
        )
    mock_which.assert_called_once_with("clang-tidy", path="/venv/bin")


def test_find_installed_wheel_ignores_other_tools_on_path():
    """A clang-tidy elsewhere on PATH may be another version than the wheel."""
    with (
        patch("cpp_linter_hooks.util._installed_wheel_version", return_value="21.1.6"),
        patch("cpp_linter_hooks.util._env_paths", return_value=_paths("/venv/bin")),
        patch(
            "shutil.which",
            side_effect=lambda tool, path=None: (
                None if path == "/venv/bin" else "/usr/bin/clang-tidy"
            ),
        ),
    ):
        assert _find_installed_wheel("clang-tidy", None) is None


def test_install_tool_prefers_environment_scripts_dir():
    completed = subprocess.CompletedProcess(args=[], returncode=0)
    with (
        patch("subprocess.run", return_value=completed),
        patch("cpp_linter_hooks.util._env_paths", return_value=_paths("/venv/bin")),
        patch(
            "shutil.which",
            side_effect=lambda tool, path=None: (
                "/venv/bin/clang-tidy" if path == "/venv/bin" else "/usr/bin/clang-tidy"
            ),
        ),
    ):
        assert _install_tool("clang-tidy", "21.1.6") == "/venv/bin/clang-tidy"


@pytest.mark.parametrize(
    ("installed", "requested"), [(None, "21"), ("23.1.3", "21"), ("21.1.6", "21.1.1")]
)
def test_find_installed_wheel_rejects_missing_or_other_version(installed, requested):
    with (
        patch("cpp_linter_hooks.util._installed_wheel_version", return_value=installed),
        patch("shutil.which", return_value="/venv/bin/clang-tidy"),
    ):
        assert _find_installed_wheel("clang-tidy", requested) is None


def test_find_installed_wheel_without_executable():
    with (
        patch("cpp_linter_hooks.util._installed_wheel_version", return_value="21.1.6"),
        patch("shutil.which", return_value=None),
    ):
        assert _find_installed_wheel("clang-tidy", "21") is None


@pytest.mark.parametrize("requested", [None, "21", "21.1.6"])
def test_resolve_install_uses_matching_wheel_without_pypi(requested):
    """A matching wheel (e.g. from additional_dependencies) needs no network."""
    with (
        patch(
            "cpp_linter_hooks.util._find_installed_wheel",
            return_value=(Path("/venv/bin/clang-tidy"), "21.1.6"),
        ),
        patch("cpp_linter_hooks.util._get_pypi_versions") as mock_pypi,
        patch("cpp_linter_hooks.util._install_tool") as mock_install,
    ):
        result = resolve_install_with_diagnostics("clang-tidy", requested)

    assert result == (Path("/venv/bin/clang-tidy"), None)
    mock_pypi.assert_not_called()
    mock_install.assert_not_called()


def test_resolve_install_unpinned_keeps_installed_wheel_when_pypi_is_newer():
    """Without --version an installed wheel is not upgraded behind the user's back."""
    with (
        patch("cpp_linter_hooks.util._installed_wheel_version", return_value="21.1.6"),
        patch("shutil.which", return_value="/venv/bin/clang-tidy"),
        patch(
            "cpp_linter_hooks.util._get_pypi_versions",
            return_value=("23.1.3", ["23.1.3", "21.1.6"]),
        ) as mock_pypi,
        patch("cpp_linter_hooks.util._install_tool") as mock_install,
    ):
        path, error = resolve_install_with_diagnostics("clang-tidy", None)

    assert (path, error) == (Path("/venv/bin/clang-tidy"), None)
    mock_pypi.assert_not_called()
    mock_install.assert_not_called()


def test_resolve_install_offline_with_pinned_installed_wheel():
    """--version works offline when the hook environment already has the wheel."""
    with (
        patch("cpp_linter_hooks.util._installed_wheel_version", return_value="21.1.6"),
        patch("shutil.which", return_value="/venv/bin/clang-tidy"),
        patch("urllib.request.urlopen", side_effect=OSError("network down")),
    ):
        assert resolve_install_with_diagnostics("clang-tidy", "21") == (
            Path("/venv/bin/clang-tidy"),
            None,
        )


def test_resolve_install_other_installed_wheel_resolves_from_pypi():
    with (
        patch("cpp_linter_hooks.util._installed_wheel_version", return_value="23.1.3"),
        patch("shutil.which", return_value=None),
        patch(
            "cpp_linter_hooks.util._get_pypi_versions", side_effect=_pypi_side_effect
        ),
        patch(
            "cpp_linter_hooks.util._install_tool",
            return_value=Path("/venv/bin/clang-tidy"),
        ) as mock_install,
    ):
        result = resolve_install_with_diagnostics("clang-tidy", "21")

    assert result == (Path("/venv/bin/clang-tidy"), None)
    mock_install.assert_called_once_with("clang-tidy", "21.1.6")


def test_resolve_install_verbose_reports_installed_wheel(capsys):
    with patch(
        "cpp_linter_hooks.util._find_installed_wheel",
        return_value=(Path("/venv/bin/clang-format"), "21.1.8"),
    ):
        resolve_install_with_diagnostics("clang-format", "21", True)

    assert (
        "Using installed clang-format Python wheel version 21.1.8"
        in capsys.readouterr().err
    )


# ═══════════════════════════════════════════════════════════════════════
# _install_lock
# ═══════════════════════════════════════════════════════════════════════

LOCK_WORKER = textwrap.dedent(
    """
    import os, sys, time
    sys.prefix = sys.argv[1]
    from cpp_linter_hooks.util import _install_lock

    log = sys.argv[2]
    with _install_lock():
        with open(log, "a") as f:
            f.write("start\\n")
        time.sleep(0.2)
        with open(log, "a") as f:
            f.write("end\\n")
    """
)


def test_install_lock_serializes_processes(tmp_path):
    """Hook processes started at once take turns instead of installing together."""
    log = tmp_path / "log.txt"
    workers = [
        subprocess.Popen(
            [sys.executable, "-c", LOCK_WORKER, str(tmp_path), str(log)],
        )
        for _ in range(3)
    ]
    for worker in workers:
        assert worker.wait(timeout=60) == 0

    assert log.read_text().split() == ["start", "end"] * 3
    assert (tmp_path / ".cpp-linter-hooks-install.lock").is_file()


def test_install_lock_unlocks_on_error(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "prefix", str(tmp_path))
    with pytest.raises(RuntimeError), _install_lock():
        _crash()
    with _install_lock():
        pass


def _crash():
    raise RuntimeError("pip crashed")


@pytest.mark.parametrize(
    "error",
    [
        OSError(errno.ENOLCK, "No locks available"),
        NotImplementedError("FileSystem does not appear to support flock"),
    ],
)
def test_install_lock_runs_unlocked_without_lock_support(
    tmp_path, monkeypatch, caplog, error
):
    """File systems without lock support (e.g. some NFS mounts) run unlocked."""
    monkeypatch.setattr(sys, "prefix", str(tmp_path))
    with (
        patch("cpp_linter_hooks.util.FileLock.acquire", side_effect=error),
        caplog.at_level(logging.DEBUG, logger="cpp_linter_hooks.util"),
        _install_lock(),
    ):
        entered = True
    assert entered
    assert "Installing without a lock" in caplog.text


def test_resolve_install_runs_under_install_lock():
    events = []

    class Lock:
        def __enter__(self):
            events.append("lock")

        def __exit__(self, *exc):
            events.append("unlock")

    def install(tool, version):
        events.append("install")
        return Path("/venv/bin/clang-format")

    with (
        patch("cpp_linter_hooks.util._install_lock", return_value=Lock()),
        patch("shutil.which", return_value=None),
        patch(
            "cpp_linter_hooks.util._get_pypi_versions", side_effect=_pypi_side_effect
        ),
        patch("cpp_linter_hooks.util._install_tool", side_effect=install),
    ):
        result = resolve_install_with_diagnostics("clang-format", "20")

    assert result == (Path("/venv/bin/clang-format"), None)
    assert events == ["lock", "install", "unlock"]
