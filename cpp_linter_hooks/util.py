import sys
from pathlib import Path
import logging
import subprocess
from typing import Optional, Tuple, List

from clang_tools.util import Version
from clang_tools.install import is_installed as _is_installed, install_tool


LOG = logging.getLogger(__name__)


DEFAULT_CLANG_VERSION = "18"  # Default version for clang tools, can be overridden


def debug_print(message: str, verbose: bool = False) -> None:
    """Print debug message to stderr if verbose mode is enabled."""
    if verbose:
        print(f"[DEBUG] {message}", file=sys.stderr)


def run_subprocess_with_logging(
    command: List[str], tool_name: str, verbose: bool = False, dry_run: bool = False
) -> Tuple[int, str]:
    """
    Run subprocess with comprehensive logging and error handling.

    Args:
        command: Command list to execute
        tool_name: Name of the tool (for logging)
        verbose: Enable verbose debug output
        dry_run: Whether this is a dry run (affects return code for clang-format)

    Returns:
        Tuple of (return_code, combined_output)
    """
    debug_print(f"{tool_name} command: {' '.join(command)}", verbose)

    retval = 0
    output = ""
    stderr_output = ""

    try:
        sp = subprocess.run(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding="utf-8"
        )

        output = sp.stdout
        stderr_output = sp.stderr
        retval = sp.returncode

        if dry_run and tool_name == "clang-format":
            debug_print("Dry-run mode detected", verbose)
            debug_print(f"Exit code: {retval} (converted to -1 for dry-run)", verbose)
            retval = -1  # Special handling for clang-format dry-run
        else:
            debug_print(f"Exit code: {retval}", verbose)

        # Log outputs if verbose
        if verbose and (output or stderr_output):
            debug_print(f"stdout: {repr(output)}", verbose)
            debug_print(f"stderr: {repr(stderr_output)}", verbose)

        # Combine stdout and stderr for comprehensive output
        combined_output = ""
        if output:
            combined_output += output
        if stderr_output:
            if combined_output:
                combined_output += "\n"
            combined_output += stderr_output

        # Special handling for clang-tidy warnings/errors
        if tool_name == "clang-tidy" and (
            "warning:" in combined_output or "error:" in combined_output
        ):
            if retval == 0:  # Only override if it was successful
                retval = 1
                debug_print("Found warnings/errors, setting exit code to 1", verbose)

        return retval, combined_output

    except FileNotFoundError as error:
        error_msg = f"{tool_name} executable not found: {error}"
        debug_print(f"FileNotFoundError: {error}", verbose)
        debug_print(f"Command attempted: {' '.join(command)}", verbose)
        return 1, error_msg


def is_installed(tool_name: str, version: str) -> Optional[Path]:
    """Check if tool is installed.

    Checks the current python prefix and PATH via clang_tools.install.is_installed.
    """
    # check in current python prefix (usual situation when we installed into pre-commit venv)
    directory = Path(sys.executable).parent
    path = directory / f"{tool_name}-{version}"
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
