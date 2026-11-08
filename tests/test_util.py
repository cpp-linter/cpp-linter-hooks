"""Tests for cpp_linter_hooks.util -- finding and installing clang tool wheels."""

import errno
import logging
import os
import subprocess
import sys
import sysconfig
import textwrap
from pathlib import Path
from unittest.mock import patch

import pytest

from cpp_linter_hooks import util
from cpp_linter_hooks.util import (
    _env_paths,
    _find_installed,
    _find_installed_wheel,
    _find_versioned_install,
    _install_lock,
    _install_tool,
    _installed_wheel_version,
    _version_key,
    _version_satisfies,
    _versioned_executable,
    _versions_dir,
    resolve_install,
    resolve_install_with_diagnostics,
)

PIP = [sys.executable, "-m", "pip", "install", "--disable-pip-version-check"]


@pytest.fixture(autouse=True)
def no_installed_wheel(tmp_path):
    """Hide wheels installed in the test environment from the resolver.

    Per-version installs go to an empty temporary directory. Tests that need an
    installed wheel patch ``_installed_wheel_version`` or
    ``_find_installed_wheel`` themselves.
    """
    with (
        patch("cpp_linter_hooks.util._installed_wheel_version", return_value=None),
        patch(
            "cpp_linter_hooks.util._versions_dir",
            return_value=str(tmp_path / "versions"),
        ),
    ):
        yield


# ═══════════════════════════════════════════════════════════════════════
# _install_tool: pip picks the version, from the user's package index
# ═══════════════════════════════════════════════════════════════════════


def test_install_tool_without_version_installs_into_environment():
    completed = subprocess.CompletedProcess(args=[], returncode=0)
    with patch("subprocess.run", return_value=completed) as run:
        assert _install_tool("clang-tidy", None) is None

    run.assert_called_once_with(
        [*PIP, "clang-tidy"], capture_output=True, text=True, check=False
    )


@pytest.mark.parametrize(
    ("version", "requirement"),
    [
        ("21", "clang-tidy==21.*"),
        ("21.1", "clang-tidy==21.1.*"),
        ("19.1.0", "clang-tidy==19.1.0"),
    ],
)
def test_install_tool_lets_pip_pick_the_version(version, requirement):
    """pip resolves the version, so PIP_INDEX_URL and pip.conf mirrors work."""
    target = _base() / f"clang-tidy-{version}"
    leftover = target / "leftover"
    leftover.mkdir(parents=True)

    def pip(command, **kwargs):
        assert not leftover.exists()
        return subprocess.CompletedProcess(command, returncode=0)

    with patch("subprocess.run", side_effect=pip) as run:
        assert _install_tool("clang-tidy", version) is None

    assert run.call_args.args[0] == [*PIP, requirement, "--target", str(target)]


def test_install_tool_failure_returns_pip_error():
    completed = subprocess.CompletedProcess(
        args=[],
        returncode=1,
        stdout="",
        stderr="ERROR: No matching distribution found for clang-tidy==99.*\n",
    )
    with patch("subprocess.run", return_value=completed):
        error = _install_tool("clang-tidy", "99")

    assert error == (
        "pip could not install clang-tidy==99.*:\n"
        "ERROR: No matching distribution found for clang-tidy==99.*\n"
        "Run `pip index versions clang-tidy` to see the available versions."
    )


# ═══════════════════════════════════════════════════════════════════════
# resolve_install / resolve_install_with_diagnostics
# ═══════════════════════════════════════════════════════════════════════


def test_resolve_install_reports_pip_error(caplog):
    with (
        patch("cpp_linter_hooks.util._install_tool", return_value="pip failed"),
        caplog.at_level(logging.ERROR, logger="cpp_linter_hooks.util"),
    ):
        assert resolve_install_with_diagnostics("clang-tidy", "99") == (
            None,
            "pip failed",
        )
        assert resolve_install("clang-tidy", "99") is None

    assert "pip failed" in caplog.text


def test_resolve_install_installs_wheel_once_even_with_tool_on_path():
    """A clang-tidy elsewhere on PATH is not used; the wheel is installed once."""

    def install(tool, version):
        _fake_versioned_install(_base(), "clang-tidy", "18.1.8", dirname="18")

    with (
        patch("shutil.which", return_value="/usr/bin/clang-tidy"),
        patch("cpp_linter_hooks.util._install_tool", side_effect=install) as mock,
        patch(
            "cpp_linter_hooks.util._versioned_executable",
            side_effect=lambda tool, target: os.path.join(target, tool),
        ),
    ):
        first, _ = resolve_install_with_diagnostics("clang-tidy", "18")
        second, _ = resolve_install_with_diagnostics("clang-tidy", "18")

    assert first == second == _base() / "clang-tidy-18" / "clang-tidy"
    mock.assert_called_once_with("clang-tidy", "18")


def test_resolve_install_without_version_reports_installed_wheel(capsys):
    found = [None, None, (Path("/venv/bin/clang-tidy"), "23.1.4")]
    with (
        patch("cpp_linter_hooks.util._find_installed_wheel", side_effect=found),
        patch("cpp_linter_hooks.util._install_tool", return_value=None) as mock,
    ):
        result = resolve_install_with_diagnostics("clang-tidy", None, True)

    assert result == (Path("/venv/bin/clang-tidy"), None)
    mock.assert_called_once_with("clang-tidy", None)
    assert "Installed clang-tidy Python wheel version 23.1.4" in capsys.readouterr().err


def test_resolve_install_is_quiet_by_default(capsys):
    found = [None, None, (Path("/venv/bin/clang-tidy"), "23.1.4")]
    with (
        patch("cpp_linter_hooks.util._find_installed_wheel", side_effect=found),
        patch("cpp_linter_hooks.util._install_tool", return_value=None),
    ):
        resolve_install_with_diagnostics("clang-tidy", None)

    assert capsys.readouterr().err == ""


@pytest.mark.parametrize("version", ["v21", "21/../../victim", "21.*", "latest", ""])
def test_resolve_install_rejects_invalid_version(version):
    with patch("cpp_linter_hooks.util._install_tool") as mock:
        path, error = resolve_install_with_diagnostics("clang-tidy", version)

    assert path is None
    assert error == (
        f"Invalid clang-tidy --version '{version}': use a version number such as "
        "21 or 21.1.8."
    )
    mock.assert_not_called()


def test_resolve_install_reports_missing_executable():
    with patch("cpp_linter_hooks.util._install_tool", return_value=None):
        assert resolve_install_with_diagnostics("clang-tidy", "21") == (
            None,
            "pip installed clang-tidy, but its executable is missing.",
        )


# ═══════════════════════════════════════════════════════════════════════
# Installed wheel in the hook environment (additional_dependencies, offline)
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.parametrize(
    ("installed", "requested", "expected"),
    [
        ("21.1.6", None, True),
        ("21.1.6", "21", True),
        ("21.1.6", "21.1", True),
        ("21.1.6", "21.1.6", True),
        ("19.1.0.1", "19.1.0", True),
        ("21.1.6", "2", False),
        ("21.1.6", "21.1.1", False),
        ("21.10.0", "21.1", False),
        ("23.1.3", "21", False),
    ],
)
def test_version_satisfies(installed, requested, expected):
    assert _version_satisfies(installed, requested) is expected


def _paths(directory) -> dict[str, str]:
    """Environment paths that all point at one directory."""
    return dict.fromkeys(("purelib", "platlib", "scripts"), str(directory))


def test_env_paths_match_sysconfig():
    _env_paths.cache_clear()
    assert _env_paths() == sysconfig.get_paths()


def _installed(dist_info: Path) -> None:
    """Create a dist-info directory the way pip leaves it after an install."""
    dist_info.mkdir(parents=True)
    (dist_info / "RECORD").touch()


def test_installed_wheel_version_reads_dist_info_name(tmp_path):
    for name in (
        "clang_tidy_extra-1.0.dist-info",
        "clang_format-22.1.8.dist-info",
        "clang_tidy",
        "Clang_Tidy-21.1.6.dist-info",
    ):
        _installed(tmp_path / name)
    with patch("cpp_linter_hooks.util._env_paths", return_value=_paths(tmp_path)):
        assert _installed_wheel_version("clang-tidy") == "21.1.6"
        assert _installed_wheel_version("clang-format") == "22.1.8"


def test_installed_wheel_version_checks_platlib(tmp_path):
    purelib, platlib = tmp_path / "purelib", tmp_path / "platlib"
    purelib.mkdir()
    _installed(platlib / "clang_tidy-21.1.6.dist-info")
    paths = {"purelib": str(purelib), "platlib": str(platlib), "scripts": ""}
    with patch("cpp_linter_hooks.util._env_paths", return_value=paths):
        assert _installed_wheel_version("clang-tidy") == "21.1.6"


def test_installed_wheel_version_ignores_unfinished_install(tmp_path):
    """pip writes RECORD last; without it another process is still installing."""
    (tmp_path / "clang_format-22.1.8.dist-info").mkdir()
    with patch("cpp_linter_hooks.util._env_paths", return_value=_paths(tmp_path)):
        assert _installed_wheel_version("clang-format") is None


def test_installed_wheel_version_missing_distribution(tmp_path):
    _installed(tmp_path / "clang_format-22.1.8.dist-info")
    with patch("cpp_linter_hooks.util._env_paths", return_value=_paths(tmp_path)):
        assert _installed_wheel_version("clang-tidy") is None
    with patch(
        "cpp_linter_hooks.util._env_paths", return_value=_paths(tmp_path / "missing")
    ):
        assert _installed_wheel_version("clang-tidy") is None


def test_find_installed_wheel_prefers_environment_scripts_dir():
    with (
        patch("cpp_linter_hooks.util._installed_wheel_version", return_value="21.1.6"),
        patch("cpp_linter_hooks.util._env_paths", return_value=_paths("/venv/bin")),
        patch("shutil.which", return_value="/venv/bin/clang-tidy") as mock_which,
    ):
        assert _find_installed_wheel("clang-tidy", "21") == (
            Path("/venv/bin/clang-tidy"),
            "21.1.6",
        )
    mock_which.assert_called_once_with("clang-tidy", path="/venv/bin")


def test_find_installed_wheel_ignores_other_tools_on_path():
    """A clang-tidy elsewhere on PATH may be another version than the wheel."""
    with (
        patch("cpp_linter_hooks.util._installed_wheel_version", return_value="21.1.6"),
        patch("cpp_linter_hooks.util._env_paths", return_value=_paths("/venv/bin")),
        patch(
            "shutil.which",
            side_effect=lambda tool, path=None: (
                None if path == "/venv/bin" else "/usr/bin/clang-tidy"
            ),
        ),
    ):
        assert _find_installed_wheel("clang-tidy", None) is None


@pytest.mark.parametrize(
    ("installed", "requested"), [(None, "21"), ("23.1.3", "21"), ("21.1.6", "21.1.1")]
)
def test_find_installed_wheel_rejects_missing_or_other_version(installed, requested):
    with (
        patch("cpp_linter_hooks.util._installed_wheel_version", return_value=installed),
        patch("shutil.which", return_value="/venv/bin/clang-tidy"),
    ):
        assert _find_installed_wheel("clang-tidy", requested) is None


def test_find_installed_wheel_without_executable():
    with (
        patch("cpp_linter_hooks.util._installed_wheel_version", return_value="21.1.6"),
        patch("shutil.which", return_value=None),
    ):
        assert _find_installed_wheel("clang-tidy", "21") is None


@pytest.mark.parametrize("requested", [None, "21", "21.1.6"])
def test_resolve_install_uses_matching_wheel_without_network(requested):
    """A matching wheel (e.g. from additional_dependencies) needs no network."""
    with (
        patch(
            "cpp_linter_hooks.util._find_installed_wheel",
            return_value=(Path("/venv/bin/clang-tidy"), "21.1.6"),
        ),
        patch("cpp_linter_hooks.util._install_tool") as mock_install,
    ):
        result = resolve_install_with_diagnostics("clang-tidy", requested)

    assert result == (Path("/venv/bin/clang-tidy"), None)
    mock_install.assert_not_called()


def test_resolve_install_unpinned_keeps_installed_wheel():
    """Without --version an installed wheel is not upgraded behind the user's back."""
    with (
        patch("cpp_linter_hooks.util._installed_wheel_version", return_value="21.1.6"),
        patch("shutil.which", return_value="/venv/bin/clang-tidy"),
        patch("subprocess.run") as run,
    ):
        path, error = resolve_install_with_diagnostics("clang-tidy", None)

    assert (path, error) == (Path("/venv/bin/clang-tidy"), None)
    run.assert_not_called()


def test_resolve_install_verbose_reports_installed_wheel(capsys):
    with patch(
        "cpp_linter_hooks.util._find_installed_wheel",
        return_value=(Path("/venv/bin/clang-format"), "21.1.8"),
    ):
        resolve_install_with_diagnostics("clang-format", "21", True)

    assert (
        "Using installed clang-format Python wheel version 21.1.8"
        in capsys.readouterr().err
    )


# ═══════════════════════════════════════════════════════════════════════
# _install_lock
# ═══════════════════════════════════════════════════════════════════════

LOCK_WORKER = textwrap.dedent(
    """
    import os, sys, time
    sys.prefix = sys.argv[1]
    from cpp_linter_hooks.util import _install_lock

    log = sys.argv[2]
    with _install_lock():
        with open(log, "a") as f:
            f.write("start\\n")
        time.sleep(0.2)
        with open(log, "a") as f:
            f.write("end\\n")
    """
)


def test_install_lock_serializes_processes(tmp_path):
    """Hook processes started at once take turns instead of installing together."""
    log = tmp_path / "log.txt"
    workers = [
        subprocess.Popen(
            [sys.executable, "-c", LOCK_WORKER, str(tmp_path), str(log)],
        )
        for _ in range(3)
    ]
    for worker in workers:
        assert worker.wait(timeout=60) == 0

    assert log.read_text().split() == ["start", "end"] * 3
    assert (tmp_path / ".cpp-linter-hooks-install.lock").is_file()


def test_install_lock_unlocks_on_error(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "prefix", str(tmp_path))
    with pytest.raises(RuntimeError), _install_lock():
        _crash()
    with _install_lock():
        pass


def _crash():
    raise RuntimeError("pip crashed")


@pytest.mark.parametrize(
    "error",
    [
        OSError(errno.ENOLCK, "No locks available"),
        NotImplementedError("FileSystem does not appear to support flock"),
        TimeoutError("The file lock could not be acquired"),
    ],
)
def test_install_lock_runs_unlocked_without_lock_support(
    tmp_path, monkeypatch, caplog, error
):
    """File systems without lock support (e.g. some NFS mounts) run unlocked."""
    monkeypatch.setattr(sys, "prefix", str(tmp_path))
    with (
        patch("filelock.FileLock.acquire", side_effect=error),
        caplog.at_level(logging.DEBUG, logger="cpp_linter_hooks.util"),
        _install_lock(),
    ):
        entered = True
    assert entered
    assert "Installing without a lock" in caplog.text


def test_install_lock_waits_a_limited_time(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "prefix", str(tmp_path))
    with (
        patch("filelock.FileLock.acquire") as acquire,
        patch("filelock.FileLock.release"),
        _install_lock(),
    ):
        pass
    acquire.assert_called_once_with(timeout=300)


def test_resolve_install_runs_under_install_lock():
    events = []

    class Lock:
        def __enter__(self):
            events.append("lock")

        def __exit__(self, *exc):
            events.append("unlock")

    def install(tool, version):
        events.append("install")
        _fake_versioned_install(_base(), "clang-format", "20.1.8", dirname="20")

    with (
        patch("cpp_linter_hooks.util._install_lock", return_value=Lock()),
        patch("cpp_linter_hooks.util._install_tool", side_effect=install),
    ):
        path, error = resolve_install_with_diagnostics("clang-format", "20")

    assert error is None
    assert path.parts[-5:-3] == ("clang-format-20", "clang_format")
    assert events == ["lock", "install", "unlock"]


def test_resolve_install_skips_lock_when_installed():
    with (
        patch(
            "cpp_linter_hooks.util._find_installed_wheel",
            return_value=(Path("/venv/bin/clang-format"), "20.1.8"),
        ),
        patch("cpp_linter_hooks.util._install_lock") as lock,
    ):
        result = resolve_install_with_diagnostics("clang-format", "20")

    assert result == (Path("/venv/bin/clang-format"), None)
    lock.assert_not_called()


def test_resolve_install_uses_wheel_installed_while_waiting():
    """Another hook process installed the wheel while this one waited for the lock."""
    with (
        patch(
            "cpp_linter_hooks.util._find_installed_wheel",
            side_effect=[None, (Path("/venv/bin/clang-format"), "20.1.8")],
        ),
        patch("cpp_linter_hooks.util._install_tool") as install,
    ):
        result = resolve_install_with_diagnostics("clang-format", "20")

    assert result == (Path("/venv/bin/clang-format"), None)
    install.assert_not_called()


# ═══════════════════════════════════════════════════════════════════════
# Per-version installs (--version gets its own directory)
# ═══════════════════════════════════════════════════════════════════════

EXE = ".exe" if os.name == "nt" else ""


def _base() -> Path:
    """Return the per-version directory the autouse fixture points to."""
    return Path(util._versions_dir())


def _fake_versioned_install(
    base: Path,
    tool: str,
    version: str,
    bin_dir=("data", "bin"),
    record=True,
    dirname=None,
) -> Path:
    """Lay out what ``pip install --target`` leaves for a clang tool wheel.

    The directory is named after the requested version (*dirname*), which
    defaults to the installed one.
    """
    target = base / f"{tool}-{dirname or version}"
    package = target / tool.replace("-", "_")
    executable = package.joinpath(*bin_dir) / f"{tool}{EXE}"
    executable.parent.mkdir(parents=True)
    executable.write_text("")
    executable.chmod(0o755)
    dist_info = target / f"{tool.replace('-', '_')}-{version}.dist-info"
    dist_info.mkdir()
    if record:
        (dist_info / "RECORD").write_text("")
    return executable


def test_versions_dir_is_in_hook_environment(monkeypatch):
    # The original function: the autouse fixture patches only the module attribute.
    monkeypatch.setattr(sys, "prefix", "/env")
    assert _versions_dir() == os.path.join("/env", "cpp-linter-hooks")


@pytest.mark.parametrize("bin_dir", [("data", "bin"), ("bin",)])
def test_versioned_executable_finds_wheel_binary(tmp_path, bin_dir):
    executable = _fake_versioned_install(tmp_path, "clang-format", "21.1.8", bin_dir)
    target = str(tmp_path / "clang-format-21.1.8")
    assert Path(_versioned_executable("clang-format", target)) == executable


def test_versioned_executable_missing(tmp_path):
    assert _versioned_executable("clang-tidy", str(tmp_path)) is None


@pytest.mark.parametrize(
    "version, expected",
    [("21.1.8", (21, 1, 8)), ("19.1.0.1", (19, 1, 0, 1)), ("10.0.1.1", (10, 0, 1, 1))],
)
def test_version_key(version, expected):
    assert _version_key(version) == expected


def test_find_versioned_install_newest_match():
    base = _base()
    _fake_versioned_install(base, "clang-tidy", "21.1.1")
    newest = _fake_versioned_install(base, "clang-tidy", "21.1.6")
    _fake_versioned_install(base, "clang-tidy", "20.1.0")
    _fake_versioned_install(base, "clang-format", "21.1.8")

    assert _find_versioned_install("clang-tidy", "21") == (newest, "21.1.6")
    assert _find_versioned_install("clang-tidy", "21.1.1")[1] == "21.1.1"
    assert _find_versioned_install("clang-tidy", "22") is None


def test_find_versioned_install_skips_unfinished_and_broken():
    base = _base()
    _fake_versioned_install(base, "clang-format", "21.1.8", record=False)
    (base / "clang-format-20.1.8").mkdir()
    assert _find_versioned_install("clang-format", "21") is None
    assert _find_versioned_install("clang-format", "20") is None


def test_find_versioned_install_without_directory():
    assert not _base().exists()
    assert _find_versioned_install("clang-format", "21") is None


def test_find_installed_pinned_uses_versioned_install():
    executable = _fake_versioned_install(_base(), "clang-format", "18.1.8")
    assert _find_installed("clang-format", "18") == (executable, "18.1.8")


def test_find_installed_unpinned_ignores_versioned_install():
    """A run without --version never picks a version another project asked for."""
    _fake_versioned_install(_base(), "clang-format", "18.1.8")
    assert _find_installed("clang-format", None) is None


def test_find_installed_prefers_environment_wheel():
    _fake_versioned_install(_base(), "clang-format", "21.1.8")
    with patch(
        "cpp_linter_hooks.util._find_installed_wheel",
        return_value=(Path("/venv/bin/clang-format"), "21.1.8"),
    ):
        assert _find_installed("clang-format", "21") == (
            Path("/venv/bin/clang-format"),
            "21.1.8",
        )


def test_find_versioned_install_reads_version_from_dist_info():
    """--version=21 installs into clang-tidy-21; a later --version=21.1.6 reuses it."""
    executable = _fake_versioned_install(_base(), "clang-tidy", "21.1.6", dirname="21")
    assert _find_versioned_install("clang-tidy", "21") == (executable, "21.1.6")
    assert _find_versioned_install("clang-tidy", "21.1.6") == (executable, "21.1.6")
    assert _find_versioned_install("clang-tidy", "21.1.1") is None


def test_resolve_install_versions_coexist_without_network():
    """Switching --version between projects reuses each install, offline."""
    base = _base()
    v18 = _fake_versioned_install(base, "clang-format", "18.1.8")
    v21 = _fake_versioned_install(base, "clang-format", "21.1.8", dirname="21")
    with patch("subprocess.run") as run:
        assert resolve_install("clang-format", "18") == v18
        assert resolve_install("clang-format", "21") == v21
        assert resolve_install("clang-format", "18.1.8") == v18
    run.assert_not_called()
