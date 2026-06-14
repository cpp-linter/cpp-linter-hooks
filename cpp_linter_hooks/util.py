"""Shared helpers for resolving and installing clang tool wheels."""

import sys
import shutil
import subprocess
from pathlib import Path
import logging
from typing import Optional, Tuple
from functools import lru_cache
import json
import urllib.request
import re

LOG = logging.getLogger(__name__)


@lru_cache(maxsize=4)
def _get_pypi_versions(tool: str) -> Tuple[Optional[str], list]:
    """Fetch (latest_version, [stable_versions_descending]) from PyPI JSON API.

    Results are cached per tool name so repeated calls within the same
    process reuse the last HTTP response.
    """
    try:
        url = f"https://pypi.org/pypi/{tool}/json"
        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.loads(response.read())
    except Exception as exc:
        LOG.warning("Failed to fetch versions for %s from PyPI: %s", tool, exc)
        return None, []

    all_versions = list(data["releases"].keys())

    # Filter out pre-release versions
    pre_release_pattern = re.compile(
        r".*(alpha|beta|rc|dev|a\d+|b\d+).*", re.IGNORECASE
    )
    stable = [v for v in all_versions if not pre_release_pattern.match(v)]

    if not stable:
        LOG.warning("No stable versions found for %s on PyPI", tool)
        return None, []

    # Sort ascending by version tuple
    stable.sort(key=lambda x: tuple(map(int, x.split("."))))

    latest = stable[-1]
    # Return descending for prefix matching (newest first)
    return latest, list(reversed(stable))


def _resolve_version_from_pypi(
    tool: str, user_input: Optional[str]
) -> Tuple[Optional[str], Optional[str]]:
    """Resolve a version dynamically from PyPI.

    Returns (resolved_version, error_message).  The error_message is
    suitable for displaying directly to the end user.
    """
    latest, versions = _get_pypi_versions(tool)

    if not versions:
        return (
            None,
            f"Could not find any stable versions of {tool} on PyPI. "
            "Check your network connection.",
        )

    if user_input is None:
        return latest, None

    # Exact match
    if user_input in versions:
        return user_input, None

    # Prefix match (e.g. "20" → "20.1.8").  Versions are newest-first,
    # so the first matching entry is the latest for that prefix.
    matched = [v for v in versions if v.startswith(user_input)]
    if matched:
        return matched[0], None

    # No match – help the user
    sample = ", ".join(versions[:15])
    return (
        None,
        f"Unsupported {tool} version '{user_input}'.\n"
        f"Latest stable version: {latest}\n"
        f"Available versions (sample): {sample}\n"
        f"Run `pip index versions {tool}` to see all available versions.",
    )


def _is_version_installed(tool: str, version: str) -> Optional[Path]:
    """Return the tool path if the installed version matches, otherwise None."""
    existing = shutil.which(tool)
    if not existing:
        return None
    result = subprocess.run([existing, "--version"], capture_output=True, text=True)
    if version in result.stdout:
        return Path(existing)
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


def resolve_install_with_diagnostics(
    tool: str, version: Optional[str], verbose: bool = False
) -> Tuple[Optional[Path], Optional[str]]:
    """Resolve/install a tool, returning a user-facing error for bad versions.

    Tool versions are resolved dynamically from PyPI — no hardcoded
    list is maintained in-tree.
    """
    user_version, error = _resolve_version_from_pypi(tool, version)
    if error is not None:
        return None, error

    if verbose:
        if version is None:
            print(
                f"Using latest {tool} Python wheel version {user_version}",
                file=sys.stderr,
            )
        elif version == user_version:
            print(f"Using {tool} Python wheel version {user_version}", file=sys.stderr)
        else:
            print(
                f"Resolved {tool} --version={version} to Python wheel version "
                f"{user_version}",
                file=sys.stderr,
            )

    return (
        _is_version_installed(tool, user_version) or _install_tool(tool, user_version),
        None,
    )


def resolve_install(tool: str, version: Optional[str]) -> Optional[Path]:
    """Resolve/install a tool, logging bad-version diagnostics."""
    path, error = resolve_install_with_diagnostics(tool, version)
    if error is not None:
        LOG.error(error)
    return path
