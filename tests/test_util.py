import logging
import sys
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
    with monkeypatch.context() as m:
        m.setattr(sys, "executable", str(tmp_path / "bin" / "python"))

        # Mock shutil.which to simulate the tool being available
        with patch("shutil.which", return_value=str(tmp_path / tool)):
            caplog.clear()
            caplog.set_level(logging.INFO, logger="cpp_linter_hooks.util")

            if version is None:
                result = ensure_installed(tool)
            else:
                result = ensure_installed(tool, version=version)

            # Should return the tool name for direct execution
            assert result == tool

            # Check that we logged checking for the tool
            assert any("Checking for" in record.message for record in caplog.records)


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
        patch("sys.executable", "/nonexistent/python"),
    ):
        caplog.clear()
        caplog.set_level(logging.WARNING, logger="cpp_linter_hooks.util")

        result = ensure_installed("clang-format")

        # Should still return the tool name
        assert result == "clang-format"

        # Should log a warning
        assert any("not found in PATH" in record.message for record in caplog.records)
