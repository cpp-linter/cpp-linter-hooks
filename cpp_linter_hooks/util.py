import sys
from pathlib import Path
import logging
from typing import Optional

from clang_tools.util import Version
from clang_tools.install import is_installed as _is_installed, install_tool


LOG = logging.getLogger(__name__)


DEFAULT_CLANG_VERSION = "18"  # Default version for clang tools, can be overridden


def is_installed(tool_name: str, version: str) -> Optional[Path]:
    """Check if tool is installed.

    Checks the current python prefix and PATH via clang_tools.install.is_installed.
    """
    # check in current python prefix (usual situation when we installed into pre-commit venv)
    directory = Path(sys.executable).parent
    path = (directory / f"{tool_name}-{version}")
    if path.is_file():
        return path

    # parse the user-input version as a string
    parsed_ver = Version(version)
    # also check using clang_tools
    path = _is_installed(tool_name, parsed_ver)
    if path is not None:
        return Path(path)

    # not found
    return None


def ensure_installed(tool_name: str, version: str = DEFAULT_CLANG_VERSION) -> Path:
    """
    Ensure tool is available at given version.
    """
    LOG.info("Checking for %s, version %s", tool_name, version)
    path = is_installed(tool_name, version)
    if path is not None:
        LOG.info("%s, version %s is already installed", tool_name, version)
        return path

    LOG.info("Installing %s, version %s", tool_name, version)
    directory = Path(sys.executable).parent
    install_tool(tool_name, version, directory=str(directory), no_progress_bar=True)
    return directory / f"{tool_name}-{version}"
