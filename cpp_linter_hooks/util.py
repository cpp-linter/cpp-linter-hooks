import sys
import shutil
import subprocess
from pathlib import Path
import logging
from typing import Optional, List

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

LOG = logging.getLogger(__name__)


def get_version_from_dependency(tool: str) -> Optional[str]:
    """Get the version of a tool from the pyproject.toml dependencies."""
    pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
    if not pyproject_path.exists():
        return None
    with open(pyproject_path, "rb") as f:
        data = tomllib.load(f)
    # First try project.optional-dependencies.tools
    optional_deps = data.get("project", {}).get("optional-dependencies", {})
    tools_deps = optional_deps.get("tools", [])
    for dep in tools_deps:
        if dep.startswith(f"{tool}=="):
            return dep.split("==")[1]

    # Fallback to project.dependencies for backward compatibility
    dependencies = data.get("project", {}).get("dependencies", [])
    for dep in dependencies:
        if dep.startswith(f"{tool}=="):
            return dep.split("==")[1]
    return None


DEFAULT_CLANG_FORMAT_VERSION = get_version_from_dependency("clang-format")
DEFAULT_CLANG_TIDY_VERSION = get_version_from_dependency("clang-tidy")


CLANG_FORMAT_VERSIONS = [
    "6.0.1",
    "7.1.0",
    "8.0.1",
    "9.0.0",
    "10.0.1",
    "10.0.1.1",
    "11.0.1",
    "11.0.1.1",
    "11.0.1.2",
    "11.1.0",
    "11.1.0.1",
    "11.1.0.2",
    "12.0.1",
    "12.0.1.1",
    "12.0.1.2",
    "13.0.0",
    "13.0.1",
    "13.0.1.1",
    "14.0.0",
    "14.0.1",
    "14.0.3",
    "14.0.4",
    "14.0.5",
    "14.0.6",
    "15.0.4",
    "15.0.6",
    "15.0.7",
    "16.0.0",
    "16.0.1",
    "16.0.2",
    "16.0.3",
    "16.0.4",
    "16.0.5",
    "16.0.6",
    "17.0.1",
    "17.0.2",
    "17.0.3",
    "17.0.4",
    "17.0.5",
    "17.0.6",
    "18.1.0",
    "18.1.1",
    "18.1.2",
    "18.1.3",
    "18.1.4",
    "18.1.5",
    "18.1.6",
    "18.1.7",
    "18.1.8",
    "19.1.0",
    "19.1.1",
    "19.1.2",
    "19.1.3",
    "19.1.4",
    "19.1.5",
    "19.1.6",
    "19.1.7",
    "20.1.0",
    "20.1.3",
    "20.1.4",
    "20.1.5",
    "20.1.6",
    "20.1.7",
    "20.1.8",
    "21.1.0",
]

CLANG_TIDY_VERSIONS = [
    "13.0.1.1",
    "14.0.6",
    "15.0.2",
    "15.0.2.1",
    "16.0.4",
    "17.0.1",
    "18.1.1",
    "18.1.8",
    "19.1.0",
    "19.1.0.1",
    "20.1.0",
]


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


def _get_runtime_version(tool: str) -> Optional[str]:
    """Get the runtime version of a tool."""
    try:
        output = subprocess.check_output([tool, "--version"], text=True)
        if tool == "clang-tidy":
            lines = output.strip().splitlines()
            if len(lines) > 1:
                return lines[1].split()[-1]
        elif tool == "clang-format":
            return output.strip().split()[-1]
    except Exception:
        return None


def _install_tool(tool: str, version: str) -> Optional[Path]:
    """Install a tool using pip."""
    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", f"{tool}=={version}"]
        )
        return shutil.which(tool)
    except subprocess.CalledProcessError:
        LOG.error("Failed to install %s==%s", tool, version)
        return None


def _resolve_install(tool: str, version: Optional[str]) -> Optional[Path]:
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

    # Additional safety check in case DEFAULT versions are None
    if user_version is None:
        user_version = (
            DEFAULT_CLANG_FORMAT_VERSION
            if tool == "clang-format"
            else DEFAULT_CLANG_TIDY_VERSION
        )

    path = shutil.which(tool)
    if path:
        runtime_version = _get_runtime_version(tool)
        if runtime_version and user_version not in runtime_version:
            LOG.info(
                "%s version mismatch (%s != %s), reinstalling...",
                tool,
                runtime_version,
                user_version,
            )
            return _install_tool(tool, user_version)
        return Path(path)

    return _install_tool(tool, user_version)


def is_installed(tool: str) -> Optional[Path]:
    """Check if a tool is installed and return its path."""
    path = shutil.which(tool)
    if path:
        return Path(path)
    return None


def ensure_installed(tool: str, version: Optional[str] = None) -> str:
    """Ensure a tool is installed, resolving its version if necessary."""
    LOG.info("Ensuring %s is installed", tool)
    tool_path = _resolve_install(tool, version)
    if tool_path:
        LOG.info("%s available at %s", tool, tool_path)
        return tool
    LOG.warning("%s not found and could not be installed", tool)
    return tool
