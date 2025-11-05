import sys
import shutil
import subprocess
from pathlib import Path
import logging
from typing import Optional, List

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

from cpp_linter_hooks.versions import CLANG_FORMAT_VERSIONS, CLANG_TIDY_VERSIONS

LOG = logging.getLogger(__name__)


def get_version_from_dependency(tool: str) -> Optional[str]:
    """Get the version of a tool from the pyproject.toml dependencies."""
    pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
    if not pyproject_path.exists():
        return None
    with open(pyproject_path, "rb") as f:
        data = tomllib.load(f)
    # Check [project].dependencies
    dependencies = data.get("project", {}).get("dependencies", [])
    for dep in dependencies:
        if dep.startswith(f"{tool}=="):
            return dep.split("==")[1]
    return None


DEFAULT_CLANG_FORMAT_VERSION = get_version_from_dependency("clang-format")
DEFAULT_CLANG_TIDY_VERSION = get_version_from_dependency("clang-tidy")


def _resolve_version(versions: List[str], user_input: Optional[str]) -> Optional[str]:
    """Resolve the latest matching version based on user input and available versions."""
    if user_input is None:
        return None
    if user_input in versions:
        return user_input

    try:
        # filter versions that start with the user input
        matched_versions = [v for v in versions if v.startswith(user_input)]
        if not matched_versions:
            raise ValueError

        # define a function to parse version strings into tuples for comparison
        def parse_version(v: str):
            return tuple(map(int, v.split(".")))

        # return the latest version
        return max(matched_versions, key=parse_version)

    except ValueError:
        LOG.warning("Version %s not found in available versions", user_input)
        return None


def _install_tool(tool: str, version: str) -> Optional[Path]:
    """Install a tool using pip, logging output on failure."""
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", f"{tool}=={version}"],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return shutil.which(tool)
    LOG.error("pip failed to install %s %s", tool, version)
    LOG.error(result.stdout)
    LOG.error(result.stderr)
    return None


def resolve_install(tool: str, version: Optional[str]) -> Optional[Path]:
    """Resolve the installation of a tool, checking for version and installing if necessary."""
    user_version = _resolve_version(
        CLANG_FORMAT_VERSIONS if tool == "clang-format" else CLANG_TIDY_VERSIONS,
        version,
    )
    if user_version is None:
        user_version = (
            DEFAULT_CLANG_FORMAT_VERSION
            if tool == "clang-format"
            else DEFAULT_CLANG_TIDY_VERSION
        )

    return _install_tool(tool, user_version)
