import sys
from pathlib import Path
import logging

from clang_tools.install import is_installed, install_tool


LOG = logging.getLogger(__name__)


DEFAULT_CLANG_VERSION = "13"


def ensure_installed(tool_name: str, version: str = DEFAULT_CLANG_VERSION):
    LOG.info("Checking for %s, version %s", tool_name, version)
    if not is_installed(tool_name, version):
        LOG.info("Installing %s, version %s", tool_name, version)
        directory = Path(sys.executable).parent
        install_tool(tool_name, version, directory=str(directory), no_progress_bar=True)
    else:
        LOG.info("%s, version %s is already installed", tool_name, version)
