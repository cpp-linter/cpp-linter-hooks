import pytest
from unittest.mock import patch
from pathlib import Path
import subprocess
import sys

from cpp_linter_hooks.util import (
    get_version_from_dependency,
    _resolve_version,
    _install_tool,
    _resolve_install,
    CLANG_FORMAT_VERSIONS,
    CLANG_TIDY_VERSIONS,
    DEFAULT_CLANG_FORMAT_VERSION,
    DEFAULT_CLANG_TIDY_VERSION,
)


VERSIONS = [None, "20"]
TOOLS = ["clang-format", "clang-tidy"]


# Tests for get_version_from_dependency
@pytest.mark.benchmark
def test_get_version_from_dependency_success():
    """Test get_version_from_dependency with valid pyproject.toml."""
    mock_toml_content = {
        "project": {
            "build-system": {
                "requires": [
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
        "project": {"build-system": {"requires": ["other-package==1.0.0"]}}
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
        ("20", "20.1.8"),  # Should find latest 20.x
        ("20.1", "20.1.8"),  # Should find latest 20.1.x
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
    ):
        result = _resolve_install("clang-format", "20.1.7")
        assert result == Path(mock_path)


@pytest.mark.benchmark
def test_resolve_install_tool_version_mismatch():
    """Test _resolve_install when tool has wrong version."""
    mock_path = "/usr/bin/clang-format"

    with (
        patch("shutil.which", return_value=mock_path),
        patch(
            "cpp_linter_hooks.util._install_tool", return_value=Path(mock_path)
        ) as mock_install,
        patch("cpp_linter_hooks.util.LOG") as mock_log,
    ):
        result = _resolve_install("clang-format", "20.1.7")
        assert result == Path(mock_path)

        mock_install.assert_called_once_with("clang-format", "20.1.7")


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
        mock_install.assert_called_once_with("clang-format", None)
