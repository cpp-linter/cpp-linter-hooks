import sys
from pathlib import Path
from typing import Optional
import logging

from clang_tools.install import is_installed, install_tool


LOG = logging.getLogger(__name__)


def ensure_installed(tool_name: str, version: Optional[str] = None):
    # install version 13 by default if clang-tools not exist.
    if version is None:
        version = "13"

    LOG.info("Checking for %s, version %s", tool_name, version)
    if not is_installed(tool_name, version):
        LOG.info("Installing %s, version %s", tool_name, version)
        directory = Path(sys.executable).parent
        install_tool(tool_name, version, directory=str(directory), no_progress_bar=True)
    else:
        LOG.info("%s, version %s is already installed", tool_name, version)
