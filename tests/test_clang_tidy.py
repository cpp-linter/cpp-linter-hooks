import pytest
import subprocess
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

from cpp_linter_hooks.clang_tidy import run_clang_tidy


@pytest.fixture(scope="function")
def generate_compilation_database():
    subprocess.run(["mkdir", "-p", "build"])
    subprocess.run(["cmake", "-Bbuild", "testing/"])
    subprocess.run(["cmake", "-Bbuild", "testing/"])


@pytest.mark.benchmark
@pytest.mark.parametrize(
    ("args", "expected_retval"),
    (
        (['--checks="boost-*"'], 1),
        (['--checks="boost-*"', "--version=16"], 1),
        (['--checks="boost-*"', "--version=17"], 1),
        (['--checks="boost-*"', "--version=18"], 1),
        (['--checks="boost-*"', "--version=19"], 1),
        (['--checks="boost-*"', "--version=20"], 1),
        (['--checks="boost-*"', "--version=21"], 1),
    ),
)
def test_run_clang_tidy_valid(args, expected_retval):
    # copy test file to tmp_path to prevent modifying repo data
    test_file = Path("testing/main.c")
    test_file.write_bytes(Path("testing/main.c").read_bytes())
    ret, output = run_clang_tidy(args + [str(test_file)])
    assert ret == expected_retval
    print(output)


@pytest.mark.benchmark
@pytest.mark.parametrize(
    ("args", "expected_retval"),
    (
        (['--checks="boost-*"'], 1),
        (['--checks="boost-*"', "--version=16"], 1),
        (['--checks="boost-*"', "--version=17"], 1),
        (['--checks="boost-*"', "--version=18"], 1),
        (['--checks="boost-*"', "--version=19"], 1),
        (['--checks="boost-*"', "--version=20"], 1),
        (['--checks="boost-*"', "--version=21"], 1),
    ),
)
def test_run_clang_tidy_invalid(args, expected_retval, tmp_path):
    # non existent file
    test_file = tmp_path / "main.c"

    ret, _ = run_clang_tidy(args + [str(test_file)])
    assert ret == expected_retval


# --- compile_commands tests (all mock subprocess.run and resolve_install) ---

_MOCK_RUN = MagicMock(returncode=0, stdout="", stderr="")


def _patch():
    return (
        patch("cpp_linter_hooks.clang_tidy.subprocess.run", return_value=_MOCK_RUN),
        patch("cpp_linter_hooks.clang_tidy.resolve_install"),
    )


def test_compile_commands_explicit(tmp_path):
    db_dir = tmp_path / "build"
    db_dir.mkdir()
    (db_dir / "compile_commands.json").write_text("[]")
    with (
        patch(
            "cpp_linter_hooks.clang_tidy.subprocess.run", return_value=_MOCK_RUN
        ) as mock_run,
        patch("cpp_linter_hooks.clang_tidy.resolve_install"),
    ):
        run_clang_tidy([f"--compile-commands={db_dir}", "dummy.cpp"])
    cmd = mock_run.call_args[0][0]
    assert "-p" in cmd
    assert cmd[cmd.index("-p") + 1] == str(db_dir)


def test_compile_commands_auto_detect(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    build_dir = tmp_path / "build"
    build_dir.mkdir()
    (build_dir / "compile_commands.json").write_text("[]")
    with (
        patch(
            "cpp_linter_hooks.clang_tidy.subprocess.run", return_value=_MOCK_RUN
        ) as mock_run,
        patch("cpp_linter_hooks.clang_tidy.resolve_install"),
    ):
        run_clang_tidy(["dummy.cpp"])
    cmd = mock_run.call_args[0][0]
    assert "-p" in cmd
    assert cmd[cmd.index("-p") + 1] == "build"


def test_compile_commands_auto_detect_fallback(tmp_path, monkeypatch):
    # Only ./out has compile_commands.json, not ./build
    monkeypatch.chdir(tmp_path)
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    (out_dir / "compile_commands.json").write_text("[]")
    with (
        patch(
            "cpp_linter_hooks.clang_tidy.subprocess.run", return_value=_MOCK_RUN
        ) as mock_run,
        patch("cpp_linter_hooks.clang_tidy.resolve_install"),
    ):
        run_clang_tidy(["dummy.cpp"])
    cmd = mock_run.call_args[0][0]
    assert "-p" in cmd
    assert cmd[cmd.index("-p") + 1] == "out"


def test_compile_commands_none(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with (
        patch(
            "cpp_linter_hooks.clang_tidy.subprocess.run", return_value=_MOCK_RUN
        ) as mock_run,
        patch("cpp_linter_hooks.clang_tidy.resolve_install"),
    ):
        run_clang_tidy(["dummy.cpp"])
    cmd = mock_run.call_args[0][0]
    assert "-p" not in cmd


def test_compile_commands_conflict_guard(tmp_path, monkeypatch):
    # -p already in args: auto-detect should NOT fire even if build/ exists
    monkeypatch.chdir(tmp_path)
    build_dir = tmp_path / "build"
    build_dir.mkdir()
    (build_dir / "compile_commands.json").write_text("[]")
    with (
        patch(
            "cpp_linter_hooks.clang_tidy.subprocess.run", return_value=_MOCK_RUN
        ) as mock_run,
        patch("cpp_linter_hooks.clang_tidy.resolve_install"),
    ):
        run_clang_tidy(["-p", "./custom", "dummy.cpp"])
    cmd = mock_run.call_args[0][0]
    assert cmd.count("-p") == 1
    assert "./custom" in cmd


def test_compile_commands_no_flag(tmp_path, monkeypatch):
    # --no-compile-commands disables auto-detect even when build/ exists
    monkeypatch.chdir(tmp_path)
    build_dir = tmp_path / "build"
    build_dir.mkdir()
    (build_dir / "compile_commands.json").write_text("[]")
    with (
        patch(
            "cpp_linter_hooks.clang_tidy.subprocess.run", return_value=_MOCK_RUN
        ) as mock_run,
        patch("cpp_linter_hooks.clang_tidy.resolve_install"),
    ):
        run_clang_tidy(["--no-compile-commands", "dummy.cpp"])
    cmd = mock_run.call_args[0][0]
    assert "-p" not in cmd


def test_compile_commands_invalid_path(tmp_path):
    # Case 1: directory does not exist
    fake_dir = tmp_path / "nonexistent"
    with patch("cpp_linter_hooks.clang_tidy.resolve_install"):
        ret, output = run_clang_tidy([f"--compile-commands={fake_dir}", "dummy.cpp"])
    assert ret == 1
    assert "nonexistent" in output

    # Case 2: directory exists but has no compile_commands.json
    empty_dir = tmp_path / "empty_build"
    empty_dir.mkdir()
    with patch("cpp_linter_hooks.clang_tidy.resolve_install"):
        ret, output = run_clang_tidy([f"--compile-commands={empty_dir}", "dummy.cpp"])
    assert ret == 1
    assert "empty_build" in output


def test_compile_commands_explicit_with_p_conflict(tmp_path, capsys):
    # --compile-commands + -p in args: warning printed, only the user's -p used
    db_dir = tmp_path / "build"
    db_dir.mkdir()
    (db_dir / "compile_commands.json").write_text("[]")
    with (
        patch(
            "cpp_linter_hooks.clang_tidy.subprocess.run", return_value=_MOCK_RUN
        ) as mock_run,
        patch("cpp_linter_hooks.clang_tidy.resolve_install"),
    ):
        run_clang_tidy([f"--compile-commands={db_dir}", "-p", "./other", "dummy.cpp"])
    captured = capsys.readouterr()
    assert "Warning" in captured.err
    cmd = mock_run.call_args[0][0]
    assert cmd.count("-p") == 1
    assert "./other" in cmd


def test_verbose_prints_compile_db_path(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    build_dir = tmp_path / "build"
    build_dir.mkdir()
    (build_dir / "compile_commands.json").write_text("[]")
    with (
        patch("cpp_linter_hooks.clang_tidy.subprocess.run", return_value=_MOCK_RUN),
        patch("cpp_linter_hooks.clang_tidy.resolve_install"),
    ):
        run_clang_tidy(["--verbose", "dummy.cpp"])
    assert "build" in capsys.readouterr().err


def test_no_verbose_no_extra_stderr(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    build_dir = tmp_path / "build"
    build_dir.mkdir()
    (build_dir / "compile_commands.json").write_text("[]")
    with (
        patch("cpp_linter_hooks.clang_tidy.subprocess.run", return_value=_MOCK_RUN),
        patch("cpp_linter_hooks.clang_tidy.resolve_install"),
    ):
        run_clang_tidy(["dummy.cpp"])
    assert capsys.readouterr().err == ""


def test_jobs_one_keeps_single_invocation():
    with (
        patch(
            "cpp_linter_hooks.clang_tidy._exec_clang_tidy", return_value=(0, "")
        ) as mock_exec,
        patch("cpp_linter_hooks.clang_tidy.resolve_install"),
    ):
        run_clang_tidy(["--jobs=1", "-p", "./build", "a.cpp", "b.cpp"])

    mock_exec.assert_called_once_with(["clang-tidy", "-p", "./build", "a.cpp", "b.cpp"])


def test_jobs_parallelizes_source_files_and_preserves_output_order():
    def fake_exec(command):
        source_file = command[-1]
        if source_file == "a.cpp":
            time.sleep(0.05)
            return 0, "a.cpp output"
        return 1, "b.cpp output"

    with (
        patch("cpp_linter_hooks.clang_tidy._exec_clang_tidy", side_effect=fake_exec),
        patch("cpp_linter_hooks.clang_tidy.resolve_install"),
    ):
        ret, output = run_clang_tidy(
            [
                "--jobs=4",
                "-p",
                "./build",
                "--header-filter=.*",
                "a.cpp",
                "b.cpp",
            ]
        )

    assert ret == 1
    assert output == "a.cpp output\nb.cpp output"


def test_jobs_parallelizes_only_trailing_source_files():
    with (
        patch(
            "cpp_linter_hooks.clang_tidy._exec_clang_tidy", return_value=(0, "")
        ) as mock_exec,
        patch("cpp_linter_hooks.clang_tidy.resolve_install"),
    ):
        run_clang_tidy(
            [
                "--jobs=2",
                "-p",
                "./build",
                "--header-filter=.*",
                "a.cpp",
                "b.hpp",
            ]
        )

    commands = {tuple(call.args[0]) for call in mock_exec.call_args_list}
    assert commands == {
        ("clang-tidy", "-p", "./build", "--header-filter=.*", "a.cpp"),
        ("clang-tidy", "-p", "./build", "--header-filter=.*", "b.hpp"),
    }


def test_jobs_with_export_fixes_forces_serial_execution():
    with (
        patch(
            "cpp_linter_hooks.clang_tidy._exec_clang_tidy", return_value=(0, "")
        ) as mock_exec,
        patch("cpp_linter_hooks.clang_tidy.resolve_install"),
    ):
        run_clang_tidy(
            [
                "--jobs=4",
                "-p",
                "./build",
                "--export-fixes",
                "fixes.yaml",
                "a.cpp",
                "b.cpp",
            ]
        )

    mock_exec.assert_called_once_with(
        [
            "clang-tidy",
            "-p",
            "./build",
            "--export-fixes",
            "fixes.yaml",
            "a.cpp",
            "b.cpp",
        ]
    )
