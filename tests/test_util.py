import logging
import pytest
from itertools import product
from unittest.mock import patch

from cpp_linter_hooks.util import ensure_installed, is_installed


VERSIONS = [None, "18"]
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


def test_is_installed_with_shutil_which(tmp_path):
    """Test is_installed when tool is found via shutil.which."""
    tool_path = tmp_path / "clang-format"
    tool_path.touch()

    with patch("shutil.which", return_value=str(tool_path)):
        result = is_installed("clang-format")
        assert result == tool_path


def test_is_installed_not_found():
    """Test is_installed when tool is not found anywhere."""
    with (
        patch("shutil.which", return_value=None),
        patch("sys.executable", "/nonexistent/python"),
    ):
        result = is_installed("clang-format")
        assert result is None


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
