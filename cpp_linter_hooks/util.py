import sys
import shutil
from pathlib import Path
import logging
from typing import Optional

LOG = logging.getLogger(__name__)

DEFAULT_CLANG_VERSION = "20"  # Default version for clang tools, can be overridden


def is_installed(tool_name: str, version: str = "") -> Optional[Path]:
    """Check if tool is installed.

    With wheel packages, the tools are installed as regular Python packages
    and available via shutil.which().
    """
    # Check if tool is available in PATH
    tool_path = shutil.which(tool_name)
    if tool_path is not None:
        return Path(tool_path)

    # Check if tool is available in current Python environment
    if sys.executable:
        python_dir = Path(sys.executable).parent
        tool_path = python_dir / tool_name
        if tool_path.is_file():
            return tool_path

        # Also check Scripts directory on Windows
        scripts_dir = python_dir / "Scripts"
        if scripts_dir.exists():
            tool_path = scripts_dir / tool_name
            if tool_path.is_file():
                return tool_path
            # Try with .exe extension on Windows
            tool_path = scripts_dir / f"{tool_name}.exe"
            if tool_path.is_file():
                return tool_path

    return None


def ensure_installed(tool_name: str, version: str = "") -> str:
    """
    Ensure tool is available. With wheel packages, we assume the tools are
    installed as dependencies and available in PATH.

    Returns the tool name (not path) since the wheel packages install the tools
    as executables that can be called directly.
    """
    LOG.info("Checking for %s", tool_name)
    path = is_installed(tool_name, version)
    if path is not None:
        LOG.info("%s is available at %s", tool_name, path)
        return tool_name  # Return tool name for direct execution

    # If not found, we'll still return the tool name and let subprocess handle the error
    LOG.warning(
        "%s not found in PATH. Make sure the %s wheel package is installed.",
        tool_name,
        tool_name,
    )
    return tool_name
