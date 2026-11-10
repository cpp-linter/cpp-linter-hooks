"""Shared helpers for finding and installing clang tool wheels."""

import contextlib
import logging
import os
import re
import shutil
import subprocess
import sys
import sysconfig
from functools import lru_cache
from pathlib import Path

LOG = logging.getLogger(__name__)


SOURCE_FILE_SUFFIXES = {
    ".c",
    ".cc",
    ".ccm",
    ".cp",
    ".cpp",
    ".cppm",
    ".cxx",
    ".cxxm",
    ".c++",
    ".c++m",
    ".cu",
    ".cuh",
    ".h",
    ".hh",
    ".hpp",
    ".hxx",
    ".h++",
    ".ino",
    ".ipp",
    ".inl",
    ".ixx",
    ".m",
    ".mm",
    ".tpp",
    ".txx",
}


def file_argument(arg: str) -> str:
    """Return a file name that a clang tool cannot read as an option.

    pre-commit passes file names as they are, so a file named
    ``--load=plugin.cpp`` would make clang-tidy load a plugin, and one named
    ``--files=list.cpp`` would make clang-format format the files listed in it.
    Such a name gets a ``./`` prefix.
    """
    if arg.startswith("-") and os.path.isfile(arg):
        return f"./{arg}"
    return arg


def _looks_like_source_file(path: str) -> bool:
    """Return whether a path has a recognized C or C++ source suffix."""
    return Path(path).suffix.lower() in SOURCE_FILE_SUFFIXES


def split_source_files(args: list[str]) -> tuple[list[str], list[str]]:
    """Split a clang tool's options from the source files pre-commit appends.

    Going back from the end, an argument is a source file when it has a C or
    C++ suffix, or when it is an existing file that does not follow an option,
    which could take it as its value (``--export-fixes fixes.yaml``). The
    second case covers suffixes added with ``types_or`` or ``files``.
    """
    split_idx = len(args)
    while split_idx > 0:
        arg = args[split_idx - 1]
        previous = args[split_idx - 2] if split_idx > 1 else ""
        if not _looks_like_source_file(arg) and (
            previous.startswith("-") or not os.path.isfile(arg)
        ):
            break
        split_idx -= 1
    return args[:split_idx], args[split_idx:]


@lru_cache(maxsize=1)
def _env_paths() -> dict[str, str]:
    """Return this Python environment's install paths, which never change at runtime."""
    return sysconfig.get_paths()


def _dist_name(tool: str) -> str:
    """Return the normalized distribution name, as in ``clang_format``."""
    return re.sub(r"[-_.]+", "_", tool).lower()


def _wheel_version(tool: str, site_dirs) -> str | None:
    """Return the version of the *tool* wheel installed in one of *site_dirs*.

    The version comes from the wheel's ``<name>-<version>.dist-info`` directory
    name, which needs neither the network nor a subprocess, and avoids parsing
    the large METADATA file the way ``importlib.metadata.version`` does. A wheel
    counts only once its ``RECORD`` file exists: pip writes it last, so a wheel
    another hook process is still installing is not used half-written.
    """
    prefix = f"{_dist_name(tool)}-"
    suffix = ".dist-info"
    for site_dir in site_dirs:
        try:
            names = os.listdir(site_dir)
        except OSError:
            continue
        for name in names:
            lower = name.lower()
            if (
                lower.startswith(prefix)
                and lower.endswith(suffix)
                and os.path.isfile(os.path.join(site_dir, name, "RECORD"))
            ):
                return name[len(prefix) : -len(suffix)]
    return None


def _installed_wheel_version(tool: str) -> str | None:
    """Return the version of the *tool* wheel installed in this Python environment.

    pre-commit installs ``additional_dependencies`` (and every wheel this hook
    installed on an earlier run without ``--version``) into the hook's own
    environment.
    """
    paths = _env_paths()
    return _wheel_version(tool, dict.fromkeys((paths["purelib"], paths["platlib"])))


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


def _versions_dir() -> str:
    """Return the directory that holds one install per requested ``--version``.

    pre-commit shares one hook environment between all projects on a machine
    that use the same ``rev``. Each version gets its own directory there, so
    projects that ask for different versions do not replace each other's wheel.
    """
    return os.path.join(sys.prefix, "cpp-linter-hooks")


def _versioned_executable(tool: str, target: str) -> str | None:
    """Return the executable inside a wheel installed with ``pip --target``.

    The wheel's own console script cannot run from there, because its package
    is not on ``sys.path``, so this returns the binary the wheel ships: in
    ``<package>/data/bin`` (or ``<package>/bin`` in old clang-format wheels).
    """
    package = os.path.join(target, _dist_name(tool))
    bin_dirs = (os.path.join(package, "data", "bin"), os.path.join(package, "bin"))
    return shutil.which(tool, path=os.pathsep.join(bin_dirs))


def _version_key(version: str) -> tuple[int, ...]:
    """Return a sortable key for a release version such as ``21.1.8``."""
    return tuple(int(part) for part in version.split(".") if part.isdigit())


def _find_versioned_install(tool: str, version: str) -> tuple[Path, str] | None:
    """Return (path, version) of the newest finished install that matches *version*.

    An install counts only once its ``RECORD`` file exists, so a directory left
    behind by an interrupted ``pip install`` is never used.
    """
    base = _versions_dir()
    try:
        names = os.listdir(base)
    except OSError:
        return None
    prefix = f"{tool}-"
    found = []
    for name in names:
        # Each directory is named after the --version it was installed for,
        # so only directories for a related version need to be read.
        requested = name[len(prefix) :]
        if not name.startswith(prefix) or not (
            _version_satisfies(requested, version)
            or _version_satisfies(version, requested)
        ):
            continue
        target = os.path.join(base, name)
        installed = _wheel_version(tool, [target])
        if installed is None or not _version_satisfies(installed, version):
            continue
        executable = _versioned_executable(tool, target)
        if executable:
            found.append((_version_key(installed), Path(executable), installed))
    if not found:
        return None
    _, path, installed = max(found, key=lambda item: item[0])
    return path, installed


def _find_installed(tool: str, version: str | None) -> tuple[Path, str] | None:
    """Return (path, version) of an installed tool that satisfies *version*.

    The wheel in the hook environment (from ``additional_dependencies``, or from
    a run without ``--version``) comes first; then the per-version installs.
    A run without ``--version`` never uses a per-version install, which another
    project may have asked for.
    """
    installed = _find_installed_wheel(tool, version)
    if installed is None and version is not None:
        installed = _find_versioned_install(tool, version)
    return installed


# Seconds to wait for another hook process to finish installing.
_INSTALL_LOCK_TIMEOUT = 300


@contextlib.contextmanager
def _install_lock():
    """Let one hook process at a time install tools into this environment.

    pre-commit and prek run the hook on batches of files in parallel. Without
    the lock, every batch runs ``pip install`` into the same directory at once.
    If the lock is not free within 5 minutes, or the file system does not support
    locks (some NFS mounts), the hook runs unlocked, as before. The limit also
    covers a stale lock file left by a crashed process.
    filelock is imported here because it is only needed to install, and
    importing it takes longer than a whole hook run that finds the tool.
    """
    from filelock import FileLock

    lock = FileLock(os.path.join(sys.prefix, ".cpp-linter-hooks-install.lock"))
    try:
        lock.acquire(timeout=_INSTALL_LOCK_TIMEOUT)
    except (OSError, NotImplementedError) as exc:  # filelock.Timeout is an OSError
        LOG.warning("Installing without a lock: %s", exc)
        lock = None
    try:
        yield
    finally:
        if lock is not None:
            lock.release()


def _install_tool(tool: str, version: str | None) -> str | None:
    """Install *tool* with pip and return an error message if that fails.

    pip picks the version, so it uses the package index from the user's pip
    configuration (``PIP_INDEX_URL``, ``pip.conf``). Without *version* the
    newest wheel goes into the hook environment. ``--version=21`` installs the
    newest 21.x wheel (``clang-tidy==21.*``), and ``--version=21.1.8`` that
    release, into its own directory under :func:`_versions_dir`.
    """
    command = [sys.executable, "-m", "pip", "install", "--disable-pip-version-check"]
    if version is None:
        requirement = tool
        command.append(requirement)
    else:
        # A full release such as 21.1.8 is installed exactly; a shorter one
        # such as 21 picks the newest matching release.
        exact = version.count(".") >= 2
        requirement = f"{tool}=={version}" if exact else f"{tool}=={version}.*"
        target = os.path.join(_versions_dir(), f"{tool}-{version}")
        # Remove what an interrupted install left behind; pip --target does
        # not replace an existing directory.
        shutil.rmtree(target, ignore_errors=True)
        command += [requirement, "--target", target]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode == 0:
        return None
    return (
        f"pip could not install {requirement}:\n{result.stderr.strip()}\n"
        f"Run `pip index versions {tool}` to see the available versions."
    )


def resolve_install_with_diagnostics(
    tool: str, version: str | None, verbose: bool = False
) -> tuple[Path | None, str | None]:
    """Find or install a tool, returning a user-facing error if that fails.

    A wheel already installed in the hook's environment is used as is when it
    matches ``--version`` (or when no version was given), so pinned
    ``additional_dependencies`` are kept and the hook works offline. So is an
    earlier per-version install that matches ``--version``. Otherwise pip
    installs it.

    Installing runs under :func:`_install_lock`, so when several hook processes
    start at once, one installs and the others wait and then use its wheel.
    """
    # The version also names a directory that is deleted before installing.
    if version is not None and not re.fullmatch(r"\d+(\.\d+)*", version):
        return None, (
            f"Invalid {tool} --version '{version}': use a version number such as "
            "21 or 21.1.8."
        )
    installed = _find_installed(tool, version)
    action = "Using installed"
    if installed is None:
        with _install_lock():
            # Another hook process may have installed it while this one waited.
            installed = _find_installed(tool, version)
            if installed is None:
                error = _install_tool(tool, version)
                if error is not None:
                    return None, error
                installed = _find_installed(tool, version)
                if installed is None:
                    return None, f"pip installed {tool}, but its executable is missing."
                action = "Installed"
    path, installed_version = installed
    if verbose:
        print(
            f"{action} {tool} Python wheel version {installed_version}",
            file=sys.stderr,
        )
    return path, None


def resolve_install(tool: str, version: str | None) -> Path | None:
    """Find or install a tool, logging the error if that fails."""
    path, error = resolve_install_with_diagnostics(tool, version)
    if error is not None:
        LOG.error(error)
    return path
