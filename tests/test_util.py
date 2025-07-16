import logging
import pytest
from itertools import product
from unittest.mock import patch
from pathlib import Path
import subprocess
import sys

from cpp_linter_hooks.util import (
    ensure_installed,
    is_installed,
    get_version_from_dependency,
    _resolve_version,
    _get_runtime_version,
    _install_tool,
    _resolve_install,
    CLANG_FORMAT_VERSIONS,
    CLANG_TIDY_VERSIONS,
    DEFAULT_CLANG_FORMAT_VERSION,
    DEFAULT_CLANG_TIDY_VERSION,
)


VERSIONS = [None, "20"]
TOOLS = ["clang-format", "clang-tidy"]


@pytest.mark.benchmark
@pytest.mark.parametrize(("tool", "version"), list(product(TOOLS, VERSIONS)))
def test_ensure_installed(tool, version, tmp_path, monkeypatch, caplog):
    """Test that ensure_installed returns the tool name for wheel packages."""
    with monkeypatch.context():
        # Mock shutil.which to simulate the tool being available
        with patch("shutil.which", return_value=str(tmp_path / tool)):
            # Mock _get_runtime_version to return a matching version
            mock_version = "20.1.7" if tool == "clang-format" else "20.1.0"
            with patch(
                "cpp_linter_hooks.util._get_runtime_version", return_value=mock_version
            ):
                caplog.clear()
                caplog.set_level(logging.INFO, logger="cpp_linter_hooks.util")

                if version is None:
                    result = ensure_installed(tool)
                else:
                    result = ensure_installed(tool, version=version)

                # Should return the tool name for direct execution
                assert result == tool

                # Check that we logged ensuring the tool is installed
                assert any("Ensuring" in record.message for record in caplog.records)


@pytest.mark.benchmark
def test_is_installed_with_shutil_which(tmp_path):
    """Test is_installed when tool is found via shutil.which."""
    tool_path = tmp_path / "clang-format"
    tool_path.touch()

    with patch("shutil.which", return_value=str(tool_path)):
        result = is_installed("clang-format")
        assert result == tool_path


@pytest.mark.benchmark
def test_is_installed_not_found():
    """Test is_installed when tool is not found anywhere."""
    with (
        patch("shutil.which", return_value=None),
        patch("sys.executable", "/nonexistent/python"),
    ):
        result = is_installed("clang-format")
        assert result is None


@pytest.mark.benchmark
def test_ensure_installed_tool_not_found(caplog):
    """Test ensure_installed when tool is not found."""
    with (
        patch("shutil.which", return_value=None),
        patch("cpp_linter_hooks.util._install_tool", return_value=None),
    ):
        caplog.clear()
        caplog.set_level(logging.WARNING, logger="cpp_linter_hooks.util")

        result = ensure_installed("clang-format")

        # Should still return the tool name
        assert result == "clang-format"

        # Should log a warning
        assert any(
            "not found and could not be installed" in record.message
            for record in caplog.records
        )


# Tests for get_version_from_dependency
@pytest.mark.benchmark
def test_get_version_from_dependency_success():
    """Test get_version_from_dependency with valid pyproject.toml."""
    mock_toml_content = {
        "project": {
            "optional-dependencies": {
                "tools": [
                    "clang-format==20.1.7",
                    "clang-tidy==20.1.0",
                    "other-package==1.0.0",
                ]
            }
        }
    }

    with (
        patch("pathlib.Path.exists", return_value=True),
        patch("cpp_linter_hooks.util.tomllib.load", return_value=mock_toml_content),
    ):
        result = get_version_from_dependency("clang-format")
        assert result == "20.1.7"

        result = get_version_from_dependency("clang-tidy")
        assert result == "20.1.0"


@pytest.mark.benchmark
def test_get_version_from_dependency_missing_file():
    """Test get_version_from_dependency when pyproject.toml doesn't exist."""
    with patch("pathlib.Path.exists", return_value=False):
        result = get_version_from_dependency("clang-format")
        assert result is None


@pytest.mark.benchmark
def test_get_version_from_dependency_missing_dependency():
    """Test get_version_from_dependency with missing dependency."""
    mock_toml_content = {
        "project": {"optional-dependencies": {"tools": ["other-package==1.0.0"]}}
    }

    with (
        patch("pathlib.Path.exists", return_value=True),
        patch("cpp_linter_hooks.util.tomllib.load", return_value=mock_toml_content),
    ):
        result = get_version_from_dependency("clang-format")
        assert result is None


@pytest.mark.benchmark
def test_get_version_from_dependency_malformed_toml():
    """Test get_version_from_dependency with malformed toml."""
    mock_toml_content = {}

    with (
        patch("pathlib.Path.exists", return_value=True),
        patch("cpp_linter_hooks.util.tomllib.load", return_value=mock_toml_content),
    ):
        result = get_version_from_dependency("clang-format")
        assert result is None


# Tests for _resolve_version
@pytest.mark.benchmark
@pytest.mark.parametrize(
    "user_input,expected",
    [
        (None, None),
        ("20", "20.1.7"),  # Should find latest 20.x
        ("20.1", "20.1.7"),  # Should find latest 20.1.x
        ("20.1.7", "20.1.7"),  # Exact match
        ("18", "18.1.8"),  # Should find latest 18.x
        ("18.1", "18.1.8"),  # Should find latest 18.1.x
        ("99", None),  # Non-existent major version
        ("20.99", None),  # Non-existent minor version
        ("invalid", None),  # Invalid version string
    ],
)
def test_resolve_version_clang_format(user_input, expected):
    """Test _resolve_version with various inputs for clang-format."""
    result = _resolve_version(CLANG_FORMAT_VERSIONS, user_input)
    assert result == expected


@pytest.mark.benchmark
@pytest.mark.parametrize(
    "user_input,expected",
    [
        (None, None),
        ("20", "20.1.0"),  # Should find latest 20.x
        ("18", "18.1.8"),  # Should find latest 18.x
        ("19", "19.1.0.1"),  # Should find latest 19.x
        ("99", None),  # Non-existent major version
    ],
)
def test_resolve_version_clang_tidy(user_input, expected):
    """Test _resolve_version with various inputs for clang-tidy."""
    result = _resolve_version(CLANG_TIDY_VERSIONS, user_input)
    assert result == expected


# Tests for _get_runtime_version
@pytest.mark.benchmark
def test_get_runtime_version_clang_format():
    """Test _get_runtime_version for clang-format."""
    mock_output = "Ubuntu clang-format version 20.1.7-1ubuntu1\n"

    with patch("subprocess.check_output", return_value=mock_output):
        result = _get_runtime_version("clang-format")
        assert result == "20.1.7-1ubuntu1"


@pytest.mark.benchmark
def test_get_runtime_version_clang_tidy():
    """Test _get_runtime_version for clang-tidy."""
    mock_output = "LLVM (http://llvm.org/):\n  LLVM version 20.1.0\n"

    with patch("subprocess.check_output", return_value=mock_output):
        result = _get_runtime_version("clang-tidy")
        assert result == "20.1.0"


@pytest.mark.benchmark
def test_get_runtime_version_exception():
    """Test _get_runtime_version when subprocess fails."""
    with patch(
        "subprocess.check_output",
        side_effect=subprocess.CalledProcessError(1, ["clang-format"]),
    ):
        result = _get_runtime_version("clang-format")
        assert result is None


@pytest.mark.benchmark
def test_get_runtime_version_clang_tidy_single_line():
    """Test _get_runtime_version for clang-tidy with single line output."""
    mock_output = "LLVM version 20.1.0\n"

    with patch("subprocess.check_output", return_value=mock_output):
        result = _get_runtime_version("clang-tidy")
        assert result is None  # Should return None for single line


# Tests for _install_tool
@pytest.mark.benchmark
def test_install_tool_success():
    """Test _install_tool successful installation."""
    mock_path = "/usr/bin/clang-format"

    with (
        patch("subprocess.check_call") as mock_check_call,
        patch("shutil.which", return_value=mock_path),
    ):
        result = _install_tool("clang-format", "20.1.7")
        assert result == mock_path

        mock_check_call.assert_called_once_with(
            [sys.executable, "-m", "pip", "install", "clang-format==20.1.7"]
        )


@pytest.mark.benchmark
def test_install_tool_failure():
    """Test _install_tool when pip install fails."""
    with (
        patch(
            "subprocess.check_call",
            side_effect=subprocess.CalledProcessError(1, ["pip"]),
        ),
        patch("cpp_linter_hooks.util.LOG") as mock_log,
    ):
        result = _install_tool("clang-format", "20.1.7")
        assert result is None

        mock_log.error.assert_called_once_with(
            "Failed to install %s==%s", "clang-format", "20.1.7"
        )


@pytest.mark.benchmark
def test_install_tool_success_but_not_found():
    """Test _install_tool when install succeeds but tool not found in PATH."""
    with patch("subprocess.check_call"), patch("shutil.which", return_value=None):
        result = _install_tool("clang-format", "20.1.7")
        assert result is None


# Tests for _resolve_install
@pytest.mark.benchmark
def test_resolve_install_tool_already_installed_correct_version():
    """Test _resolve_install when tool is already installed with correct version."""
    mock_path = "/usr/bin/clang-format"

    with (
        patch("shutil.which", return_value=mock_path),
        patch("cpp_linter_hooks.util._get_runtime_version", return_value="20.1.7"),
    ):
        result = _resolve_install("clang-format", "20.1.7")
        assert result == Path(mock_path)


@pytest.mark.benchmark
def test_resolve_install_tool_version_mismatch():
    """Test _resolve_install when tool has wrong version."""
    mock_path = "/usr/bin/clang-format"

    with (
        patch("shutil.which", return_value=mock_path),
        patch("cpp_linter_hooks.util._get_runtime_version", return_value="18.1.8"),
        patch(
            "cpp_linter_hooks.util._install_tool", return_value=Path(mock_path)
        ) as mock_install,
        patch("cpp_linter_hooks.util.LOG") as mock_log,
    ):
        result = _resolve_install("clang-format", "20.1.7")
        assert result == Path(mock_path)

        mock_install.assert_called_once_with("clang-format", "20.1.7")
        mock_log.info.assert_called_once_with(
            "%s version mismatch (%s != %s), reinstalling...",
            "clang-format",
            "18.1.8",
            "20.1.7",
        )


@pytest.mark.benchmark
def test_resolve_install_tool_not_installed():
    """Test _resolve_install when tool is not installed."""
    with (
        patch("shutil.which", return_value=None),
        patch(
            "cpp_linter_hooks.util._install_tool",
            return_value=Path("/usr/bin/clang-format"),
        ) as mock_install,
    ):
        result = _resolve_install("clang-format", "20.1.7")
        assert result == Path("/usr/bin/clang-format")

        mock_install.assert_called_once_with("clang-format", "20.1.7")


@pytest.mark.benchmark
def test_resolve_install_no_version_specified():
    """Test _resolve_install when no version is specified."""
    with (
        patch("shutil.which", return_value=None),
        patch(
            "cpp_linter_hooks.util._install_tool",
            return_value=Path("/usr/bin/clang-format"),
        ) as mock_install,
    ):
        result = _resolve_install("clang-format", None)
        assert result == Path("/usr/bin/clang-format")

        mock_install.assert_called_once_with(
            "clang-format", DEFAULT_CLANG_FORMAT_VERSION
        )


@pytest.mark.benchmark
def test_resolve_install_invalid_version():
    """Test _resolve_install with invalid version."""
    with (
        patch("shutil.which", return_value=None),
        patch(
            "cpp_linter_hooks.util._install_tool",
            return_value=Path("/usr/bin/clang-format"),
        ) as mock_install,
    ):
        result = _resolve_install("clang-format", "invalid.version")
        assert result == Path("/usr/bin/clang-format")

        # Should fallback to default version
        mock_install.assert_called_once_with(
            "clang-format", DEFAULT_CLANG_FORMAT_VERSION
        )


# Tests for ensure_installed edge cases
@pytest.mark.benchmark
def test_ensure_installed_version_mismatch(caplog):
    """Test ensure_installed with version mismatch scenario."""
    mock_path = "/usr/bin/clang-format"

    with (
        patch("shutil.which", return_value=mock_path),
        patch("cpp_linter_hooks.util._get_runtime_version", return_value="18.1.8"),
        patch("cpp_linter_hooks.util._install_tool", return_value=Path(mock_path)),
    ):
        caplog.clear()
        caplog.set_level(logging.INFO, logger="cpp_linter_hooks.util")

        result = ensure_installed("clang-format", "20.1.7")
        assert result == "clang-format"

        # Should log version mismatch
        assert any("version mismatch" in record.message for record in caplog.records)


@pytest.mark.benchmark
def test_ensure_installed_no_runtime_version():
    """Test ensure_installed when runtime version cannot be determined."""
    mock_path = "/usr/bin/clang-format"

    with (
        patch("shutil.which", return_value=mock_path),
        patch("cpp_linter_hooks.util._get_runtime_version", return_value=None),
    ):
        result = ensure_installed("clang-format", "20.1.7")
        assert result == "clang-format"


# Tests for constants and defaults
@pytest.mark.benchmark
def test_default_versions():
    """Test that default versions are set correctly."""
    assert DEFAULT_CLANG_FORMAT_VERSION is not None
    assert DEFAULT_CLANG_TIDY_VERSION is not None
    assert isinstance(DEFAULT_CLANG_FORMAT_VERSION, str)
    assert isinstance(DEFAULT_CLANG_TIDY_VERSION, str)


@pytest.mark.benchmark
def test_version_lists_not_empty():
    """Test that version lists are not empty."""
    assert len(CLANG_FORMAT_VERSIONS) > 0
    assert len(CLANG_TIDY_VERSIONS) > 0
    assert all(isinstance(v, str) for v in CLANG_FORMAT_VERSIONS)
    assert all(isinstance(v, str) for v in CLANG_TIDY_VERSIONS)


@pytest.mark.benchmark
def test_resolve_install_with_none_default_version():
    """Test _resolve_install when DEFAULT versions are None."""
    with (
        patch("shutil.which", return_value=None),
        patch("cpp_linter_hooks.util.DEFAULT_CLANG_FORMAT_VERSION", None),
        patch("cpp_linter_hooks.util.DEFAULT_CLANG_TIDY_VERSION", None),
        patch(
            "cpp_linter_hooks.util._install_tool",
            return_value=Path("/usr/bin/clang-format"),
        ) as mock_install,
    ):
        result = _resolve_install("clang-format", None)
        assert result == Path("/usr/bin/clang-format")

        # Should fallback to hardcoded version when DEFAULT is None
        mock_install.assert_called_once_with("clang-format", "20.1.7")
