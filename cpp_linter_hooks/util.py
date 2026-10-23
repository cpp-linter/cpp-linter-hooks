"""Shared helpers for resolving and installing clang tool wheels."""

import contextlib
import errno
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import sysconfig
import urllib.error
import urllib.request
from functools import lru_cache
from pathlib import Path

LOG = logging.getLogger(__name__)


@lru_cache(maxsize=4)
def _get_pypi_versions(tool: str) -> tuple[str | None, list]:
    """Fetch (latest_version, [stable_versions_descending]) from PyPI JSON API.

    Results are cached per tool name so repeated calls within the same
    process reuse the last HTTP response.
    """
    try:
        url = f"https://pypi.org/pypi/{tool}/json"
        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.loads(response.read())
    except (OSError, json.JSONDecodeError) as exc:
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
    tool: str, user_input: str | None
) -> tuple[str | None, str | None]:
    """Resolve a version dynamically from PyPI.

    Returns (resolved_version, error_message).  The error_message is
    suitable for displaying directly to the end user.

    When PyPI is unreachable and no explicit version was requested,
    falls back to whatever version is already installed on the host
    so that pre-installed tools keep working offline.
    """
    latest, versions = _get_pypi_versions(tool)

    if not versions:
        if user_input is None:
            # PyPI is unreachable, but the user didn't ask for a specific
            # version – try the locally installed tool as a fallback.
            installed = _detect_installed_version(tool)
            if installed:
                LOG.info(
                    "PyPI unreachable; using locally installed %s %s",
                    tool,
                    installed,
                )
                return installed, None
        return (
            None,
            (
                f"Could not find any stable versions of {tool} on PyPI. "
                "Check your network connection."
            ),
        )

    if user_input is None:
        return latest, None

    # Exact match
    if user_input in versions:
        return user_input, None

    # Prefix match on whole version components (e.g. "20" → "20.1.8", while
    # "2" must not match "20.1.8").  Versions are newest-first, so the first
    # matching entry is the latest for that prefix.
    matched = [v for v in versions if v.startswith(f"{user_input}.")]
    if matched:
        return matched[0], None

    # No match – help the user
    sample = ", ".join(versions[:15])
    return (
        None,
        (
            f"Unsupported {tool} version '{user_input}'.\n"
            f"Latest stable version: {latest}\n"
            f"Available versions (sample): {sample}\n"
            f"Run `pip index versions {tool}` to see all available versions."
        ),
    )


def _detect_installed_version(tool: str) -> str | None:
    """Return the version of *tool* already on PATH, or None.

    Used as a fallback when PyPI is unreachable and no explicit version
    was requested.  Extracts the version string from ``<tool> --version``
    output (e.g. ``"clang-format version 18.1.8"`` → ``"18.1.8"``).
    """
    existing = shutil.which(tool)
    if not existing:
        return None
    try:
        result = subprocess.run(
            [existing, "--version"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    matches = re.findall(r"\d+\.\d+\.\d+(?:\.\d+)?", result.stdout)
    return matches[0] if matches else None


def _is_version_installed(tool: str, version: str) -> Path | None:
    """Return the tool path if the installed version matches, otherwise None."""
    existing = shutil.which(tool)
    if not existing:
        return None
    result = subprocess.run(
        [existing, "--version"], capture_output=True, text=True, check=False
    )
    if version in result.stdout:
        return Path(existing)
    return None


@lru_cache(maxsize=1)
def _env_paths() -> dict[str, str]:
    """Return this Python environment's install paths, which never change at runtime."""
    return sysconfig.get_paths()


def _installed_wheel_version(tool: str) -> str | None:
    """Return the version of the *tool* wheel installed in this Python environment.

    pre-commit installs ``additional_dependencies`` (and every wheel this hook
    installed on an earlier run) into the hook's own environment. The version
    comes from the wheel's ``<name>-<version>.dist-info`` directory name, which
    needs neither the network nor a subprocess, and avoids parsing the large
    METADATA file the way ``importlib.metadata.version`` does.
    """
    prefix = f"{re.sub(r'[-_.]+', '_', tool).lower()}-"
    suffix = ".dist-info"
    paths = _env_paths()
    site_dirs = dict.fromkeys((paths["purelib"], paths["platlib"]))
    for site_dir in site_dirs:
        try:
            names = os.listdir(site_dir)
        except OSError:
            continue
        for name in names:
            lower = name.lower()
            if lower.startswith(prefix) and lower.endswith(suffix):
                return name[len(prefix) : -len(suffix)]
    return None


def _version_satisfies(installed: str, requested: str | None) -> bool:
    """Return whether *installed* matches ``--version`` (exact or prefix)."""
    if requested is None:
        return True
    return installed == requested or installed.startswith(f"{requested}.")


def _env_executable(tool: str) -> str | None:
    """Return *tool* from this Python environment's scripts directory, if any."""
    return shutil.which(tool, path=_env_paths()["scripts"])


def _find_installed_wheel(tool: str, version: str | None) -> tuple[Path, str] | None:
    """Return (path, version) of an installed wheel that satisfies *version*.

    Only the executable the wheel installed into this environment counts: a
    tool found elsewhere on PATH may be a different version.
    """
    installed = _installed_wheel_version(tool)
    if installed is None or not _version_satisfies(installed, version):
        return None
    path = _env_executable(tool)
    if path is None:
        return None
    return Path(path), installed


# Lock file in the hook's environment, so that hook processes running at the
# same time (pre-commit and prek run batches of files in parallel) install into
# the environment one at a time.
_INSTALL_LOCK_NAME = ".cpp-linter-hooks-install.lock"
_WINDOWS = os.name == "nt"


def _lock_file(fileno: int) -> None:
    """Block until this process holds the exclusive lock on *fileno*."""
    if _WINDOWS:
        import msvcrt

        while True:
            try:
                # Locks the first byte. LK_LOCK retries for about 10 seconds,
                # then fails with EDEADLOCK (the same number as EDEADLK, which,
                # unlike EDEADLOCK, every platform's errno module defines)
                # while another process still holds it.
                msvcrt.locking(fileno, msvcrt.LK_LOCK, 1)
            except OSError as exc:
                if exc.errno != errno.EDEADLK:
                    raise
            else:
                return
    else:
        import fcntl

        fcntl.flock(fileno, fcntl.LOCK_EX)


def _unlock_file(fileno: int) -> None:
    """Release the lock taken by :func:`_lock_file`."""
    if _WINDOWS:
        import msvcrt

        msvcrt.locking(fileno, msvcrt.LK_UNLCK, 1)
    else:
        import fcntl

        fcntl.flock(fileno, fcntl.LOCK_UN)


@contextlib.contextmanager
def _install_lock():
    """Hold a lock on this Python environment while checking for and installing tools.

    Without it, parallel hook processes all see that the tool is missing and run
    ``pip install`` into the same directory at once, so one process deletes or
    overwrites files another is still writing, or runs a binary another process
    has not finished writing. The operating system releases the lock if the
    process dies. If the lock file cannot be created or locked (some network
    file systems do not support locks), the hook runs unlocked, as before.
    """
    path = os.path.join(sys.prefix, _INSTALL_LOCK_NAME)
    fileno = None
    try:
        fileno = os.open(path, os.O_RDWR | os.O_CREAT, 0o644)
        _lock_file(fileno)
    except OSError as exc:
        LOG.debug("Could not lock %s, installing without a lock: %s", path, exc)
        if fileno is not None:
            os.close(fileno)
            fileno = None
    try:
        yield
    finally:
        if fileno is not None:
            try:
                _unlock_file(fileno)
            finally:
                os.close(fileno)


def _install_tool(tool: str, version: str) -> Path | None:
    """Install a tool using pip, logging output on failure."""
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", f"{tool}=={version}"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0:
        return _env_executable(tool) or shutil.which(tool)
    LOG.error("pip failed to install %s %s", tool, version)
    LOG.error(result.stdout)
    LOG.error(result.stderr)
    return None


def resolve_install_with_diagnostics(
    tool: str, version: str | None, verbose: bool = False
) -> tuple[Path | None, str | None]:
    """Resolve/install a tool, returning a user-facing error for bad versions.

    A wheel already installed in the hook's environment is used as is when it
    matches ``--version`` (or when no version was given), so pinned
    ``additional_dependencies`` are kept and the hook works offline.
    Otherwise the version is resolved dynamically from PyPI — no hardcoded
    list is maintained in-tree.

    The check and the install run under :func:`_install_lock`, so when several
    hook processes start at once, one installs and the others wait and then use
    the wheel it installed.
    """
    with _install_lock():
        return _resolve_install_locked(tool, version, verbose)


def _resolve_install_locked(
    tool: str, version: str | None, verbose: bool
) -> tuple[Path | None, str | None]:
    """Body of :func:`resolve_install_with_diagnostics`, run under the lock."""
    installed_wheel = _find_installed_wheel(tool, version)
    if installed_wheel is not None:
        path, installed = installed_wheel
        if verbose:
            print(
                f"Using installed {tool} Python wheel version {installed}",
                file=sys.stderr,
            )
        return path, None

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


def resolve_install(tool: str, version: str | None) -> Path | None:
    """Resolve/install a tool, logging bad-version diagnostics."""
    path, error = resolve_install_with_diagnostics(tool, version)
    if error is not None:
        LOG.error(error)
    return path
