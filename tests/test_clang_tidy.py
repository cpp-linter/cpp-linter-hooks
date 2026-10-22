import os
import subprocess
import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cpp_linter_hooks import clang_tidy
from cpp_linter_hooks.clang_tidy import (
    COMPILE_COMMANDS_HINT,
    COMPILE_DB_SEARCH_DIRS,
    MSVC_HINT,
    _append_guidance,
    _combine_outputs,
    _exec_clang_tidy,
    _find_compile_commands,
    _has_compilation_database,
    _line_filter_option,
    _looks_like_compile_db_error,
    _looks_like_msvc_error,
    _positive_int,
    _repair_check_args,
    _split_source_files,
    _strip_noise,
    main,
    parser,
    run_clang_tidy,
)


def test_all_arguments_have_help():
    missing_help = [
        action.option_strings for action in parser._actions if not action.help
    ]
    assert missing_help == []

    help_text = " ".join(parser.format_help().split())
    assert all(" ".join(action.help.split()) in help_text for action in parser._actions)


@pytest.fixture(scope="function")
def generate_compilation_database():
    subprocess.run(["mkdir", "-p", "build"], check=True)
    subprocess.run(["cmake", "-Bbuild", "testing/"], check=True)
    subprocess.run(["cmake", "-Bbuild", "testing/"], check=True)


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
        patch(
            "cpp_linter_hooks.clang_tidy.resolve_install_with_diagnostics",
            return_value=(None, None),
        ),
    )


def test_compile_commands_explicit(tmp_path):
    db_dir = tmp_path / "build"
    db_dir.mkdir()
    (db_dir / "compile_commands.json").write_text("[]")
    with (
        patch(
            "cpp_linter_hooks.clang_tidy.subprocess.run", return_value=_MOCK_RUN
        ) as mock_run,
        patch(
            "cpp_linter_hooks.clang_tidy.resolve_install_with_diagnostics",
            return_value=(None, None),
        ),
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
        patch(
            "cpp_linter_hooks.clang_tidy.resolve_install_with_diagnostics",
            return_value=(None, None),
        ),
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
        patch(
            "cpp_linter_hooks.clang_tidy.resolve_install_with_diagnostics",
            return_value=(None, None),
        ),
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
        patch(
            "cpp_linter_hooks.clang_tidy.resolve_install_with_diagnostics",
            return_value=(None, None),
        ),
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
        patch(
            "cpp_linter_hooks.clang_tidy.resolve_install_with_diagnostics",
            return_value=(None, None),
        ),
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
        patch(
            "cpp_linter_hooks.clang_tidy.resolve_install_with_diagnostics",
            return_value=(None, None),
        ),
    ):
        run_clang_tidy(["--no-compile-commands", "dummy.cpp"])
    cmd = mock_run.call_args[0][0]
    assert "-p" not in cmd


def test_compile_commands_invalid_path(tmp_path):
    # Case 1: directory does not exist
    fake_dir = tmp_path / "nonexistent"
    with patch(
        "cpp_linter_hooks.clang_tidy.resolve_install_with_diagnostics",
        return_value=(None, None),
    ):
        ret, output = run_clang_tidy([f"--compile-commands={fake_dir}", "dummy.cpp"])
    assert ret == 1
    assert "nonexistent" in output
    assert "cmake -S . -B build -DCMAKE_EXPORT_COMPILE_COMMANDS=ON" in output
    assert "meson setup builddir" in output

    # Case 2: directory exists but has no compile_commands.json
    empty_dir = tmp_path / "empty_build"
    empty_dir.mkdir()
    with patch(
        "cpp_linter_hooks.clang_tidy.resolve_install_with_diagnostics",
        return_value=(None, None),
    ):
        ret, output = run_clang_tidy([f"--compile-commands={empty_dir}", "dummy.cpp"])
    assert ret == 1
    assert "empty_build" in output
    assert "cmake -S . -B build -DCMAKE_EXPORT_COMPILE_COMMANDS=ON" in output
    assert "meson setup builddir" in output


def test_compile_commands_explicit_with_p_conflict(tmp_path, capsys):
    # --compile-commands + -p in args: warning printed, only the user's -p used
    db_dir = tmp_path / "build"
    db_dir.mkdir()
    (db_dir / "compile_commands.json").write_text("[]")
    with (
        patch(
            "cpp_linter_hooks.clang_tidy.subprocess.run", return_value=_MOCK_RUN
        ) as mock_run,
        patch(
            "cpp_linter_hooks.clang_tidy.resolve_install_with_diagnostics",
            return_value=(None, None),
        ),
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
        patch(
            "cpp_linter_hooks.clang_tidy.resolve_install_with_diagnostics",
            return_value=(None, None),
        ),
    ):
        run_clang_tidy(["--verbose", "dummy.cpp"])
    assert "build" in capsys.readouterr().err


def test_verbose_prints_compile_db_generation_hint_when_not_found(
    tmp_path, monkeypatch, capsys, real_compile_db_check
):
    monkeypatch.chdir(tmp_path)
    with (
        patch("cpp_linter_hooks.clang_tidy.subprocess.run", return_value=_MOCK_RUN),
        patch(
            "cpp_linter_hooks.clang_tidy.resolve_install_with_diagnostics",
            return_value=(None, None),
        ),
    ):
        run_clang_tidy(["--verbose", "dummy.cpp"])

    stderr = capsys.readouterr().err
    assert "No compile_commands.json was found" in stderr
    assert "cmake -S . -B build -DCMAKE_EXPORT_COMPILE_COMMANDS=ON" in stderr
    assert "meson setup builddir" in stderr


def test_invalid_version_returns_supported_versions():
    with patch(
        "cpp_linter_hooks.clang_tidy.resolve_install_with_diagnostics",
        return_value=(None, "Unsupported clang-tidy version '99'.\nSupported versions"),
    ):
        ret, output = run_clang_tidy(["--version=99", "dummy.cpp"])

    assert ret == 1
    assert "Unsupported clang-tidy version '99'" in output
    assert "Supported versions" in output


def test_exec_clang_tidy_appends_compile_db_hint():
    completed = MagicMock(
        returncode=1,
        stdout="",
        stderr="Error while trying to load a compilation database: missing\n",
    )
    with patch("cpp_linter_hooks.clang_tidy.subprocess.run", return_value=completed):
        ret, output = _exec_clang_tidy(["clang-tidy", "-p", "missing", "a.cpp"])

    assert ret == 1
    assert "Error while trying to load a compilation database" in output
    assert "cmake -S . -B build -DCMAKE_EXPORT_COMPILE_COMMANDS=ON" in output
    assert "meson setup builddir" in output


def test_exec_clang_tidy_appends_msvc_hint():
    completed = MagicMock(
        returncode=1,
        stdout="",
        stderr="fatal error: 'vcruntime.h' file not found\n",
    )
    with patch("cpp_linter_hooks.clang_tidy.subprocess.run", return_value=completed):
        ret, output = _exec_clang_tidy(["clang-tidy", "a.cpp"])

    assert ret == 1
    assert "Windows/MSVC clang-tidy hints" in output
    assert "Visual Studio Developer Command Prompt" in output
    assert "--extra-arg-before=--driver-mode=cl" in output


def test_no_verbose_no_extra_stderr(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    build_dir = tmp_path / "build"
    build_dir.mkdir()
    (build_dir / "compile_commands.json").write_text("[]")
    with (
        patch("cpp_linter_hooks.clang_tidy.subprocess.run", return_value=_MOCK_RUN),
        patch(
            "cpp_linter_hooks.clang_tidy.resolve_install_with_diagnostics",
            return_value=(None, None),
        ),
    ):
        run_clang_tidy(["dummy.cpp"])
    assert capsys.readouterr().err == ""


def test_jobs_one_keeps_single_invocation():
    with (
        patch(
            "cpp_linter_hooks.clang_tidy._exec_clang_tidy", return_value=(0, "")
        ) as mock_exec,
        patch(
            "cpp_linter_hooks.clang_tidy.resolve_install_with_diagnostics",
            return_value=(None, None),
        ),
    ):
        run_clang_tidy(["--jobs=1", "-p", "./build", "a.cpp", "b.cpp"])

    mock_exec.assert_called_once_with(
        ["clang-tidy", "-quiet", "-p", "./build", "a.cpp", "b.cpp"]
    )


def test_jobs_parallelizes_source_files_and_preserves_output_order():
    def fake_exec(command):
        source_file = command[-1]
        if source_file == "a.cpp":
            time.sleep(0.05)
            return 0, "a.cpp output"
        return 1, "b.cpp output"

    with (
        patch("cpp_linter_hooks.clang_tidy._exec_clang_tidy", side_effect=fake_exec),
        patch(
            "cpp_linter_hooks.clang_tidy.resolve_install_with_diagnostics",
            return_value=(None, None),
        ),
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
        patch(
            "cpp_linter_hooks.clang_tidy.resolve_install_with_diagnostics",
            return_value=(None, None),
        ),
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
        ("clang-tidy", "-quiet", "-p", "./build", "--header-filter=.*", "a.cpp"),
        ("clang-tidy", "-quiet", "-p", "./build", "--header-filter=.*", "b.hpp"),
    }


def test_jobs_with_export_fixes_forces_serial_execution():
    with (
        patch(
            "cpp_linter_hooks.clang_tidy._exec_clang_tidy", return_value=(0, "")
        ) as mock_exec,
        patch(
            "cpp_linter_hooks.clang_tidy.resolve_install_with_diagnostics",
            return_value=(None, None),
        ),
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
            "-quiet",
            "-p",
            "./build",
            "--export-fixes",
            "fixes.yaml",
            "a.cpp",
            "b.cpp",
        ]
    )


def test_fix_flag_appends_fix_to_command():
    with (
        patch(
            "cpp_linter_hooks.clang_tidy._exec_clang_tidy", return_value=(0, "")
        ) as mock_exec,
        patch(
            "cpp_linter_hooks.clang_tidy.resolve_install_with_diagnostics",
            return_value=(None, None),
        ),
    ):
        run_clang_tidy(["--fix", "-p", "./build", "dummy.cpp"])

    mock_exec.assert_called_once()
    cmd = mock_exec.call_args[0][0]
    assert "-fix" in cmd


def test_fix_flag_forces_serial_execution():
    with (
        patch(
            "cpp_linter_hooks.clang_tidy._exec_clang_tidy", return_value=(0, "")
        ) as mock_exec,
        patch(
            "cpp_linter_hooks.clang_tidy.resolve_install_with_diagnostics",
            return_value=(None, None),
        ),
    ):
        run_clang_tidy(["--fix", "--jobs=4", "-p", "./build", "a.cpp", "b.cpp"])

    mock_exec.assert_called_once()
    cmd = mock_exec.call_args[0][0]
    assert "-fix" in cmd
    assert "a.cpp" in cmd
    assert "b.cpp" in cmd


def test_fix_errors_in_args_forces_serial_execution():
    with (
        patch(
            "cpp_linter_hooks.clang_tidy._exec_clang_tidy", return_value=(0, "")
        ) as mock_exec,
        patch(
            "cpp_linter_hooks.clang_tidy.resolve_install_with_diagnostics",
            return_value=(None, None),
        ),
    ):
        run_clang_tidy(["--jobs=4", "-p", "./build", "-fix-errors", "a.cpp", "b.cpp"])

    mock_exec.assert_called_once()
    cmd = mock_exec.call_args[0][0]
    assert "-fix-errors" in cmd
    assert "a.cpp" in cmd
    assert "b.cpp" in cmd


# --- offline tests: tool resolution and clang-tidy processes are mocked ---


@pytest.fixture
def mock_resolve():
    """Skip the PyPI lookup and wheel installation."""
    with patch(
        "cpp_linter_hooks.clang_tidy.resolve_install_with_diagnostics",
        return_value=(None, None),
    ) as mock:
        yield mock


@pytest.fixture
def mock_exec(mock_resolve):
    """Capture clang-tidy invocations instead of running them."""
    with patch(
        "cpp_linter_hooks.clang_tidy._exec_clang_tidy", return_value=(0, "")
    ) as mock:
        yield mock


@pytest.mark.parametrize("jobs", ["0", "-2"])
def test_jobs_must_be_positive(mock_resolve, capsys, jobs):
    with pytest.raises(SystemExit) as exc_info:
        run_clang_tidy([f"--jobs={jobs}", "a.cpp"])

    assert exc_info.value.code == 2
    assert "--jobs must be greater than 0" in capsys.readouterr().err
    mock_resolve.assert_not_called()


def test_jobs_must_be_an_integer(mock_resolve, capsys):
    with pytest.raises(SystemExit) as exc_info:
        run_clang_tidy(["--jobs=many", "a.cpp"])

    assert exc_info.value.code == 2
    assert "--jobs" in capsys.readouterr().err
    mock_resolve.assert_not_called()


def test_positive_int_accepts_positive_values():
    assert _positive_int("1") == 1
    assert _positive_int("16") == 16


@pytest.mark.parametrize(
    ("returncode", "stdout", "stderr", "expected_retval"),
    (
        (0, "", "", 0),
        # Diagnostics suppressed in system headers do not fail the hook.
        (0, "", "1 warning generated.\nSuppressed 1 warnings.\n", 0),
        (0, "a.cpp:1:5: warning: unused variable 'x'\n", "", 1),
        (0, "", "a.cpp:1:1: error: unknown type name 'foo'\n", 1),
        (1, "", "", 1),
    ),
)
def test_exec_clang_tidy_return_value(returncode, stdout, stderr, expected_retval):
    completed = MagicMock(returncode=returncode, stdout=stdout, stderr=stderr)
    with patch(
        "cpp_linter_hooks.clang_tidy.subprocess.run", return_value=completed
    ) as mock_run:
        ret, output = _exec_clang_tidy(["clang-tidy", "a.cpp"])

    assert (ret, output) == (expected_retval, stdout + stderr)
    mock_run.assert_called_once_with(
        ["clang-tidy", "a.cpp"], capture_output=True, encoding="utf-8", check=False
    )


def test_exec_clang_tidy_handles_missing_streams():
    completed = MagicMock(returncode=0, stdout=None, stderr=None)
    with patch("cpp_linter_hooks.clang_tidy.subprocess.run", return_value=completed):
        assert _exec_clang_tidy(["clang-tidy", "a.cpp"]) == (0, "")


def test_exec_clang_tidy_reports_missing_executable():
    with patch(
        "cpp_linter_hooks.clang_tidy.subprocess.run",
        side_effect=FileNotFoundError(2, "No such file or directory", "clang-tidy"),
    ):
        ret, output = _exec_clang_tidy(["clang-tidy", "a.cpp"])

    assert ret == 1
    assert output == "[Errno 2] No such file or directory: 'clang-tidy'"


@pytest.mark.parametrize(
    ("output", "expected"),
    (
        (
            (
                "Error while trying to load a compilation database:\n"
                'Could not auto-detect compilation database for file "a.cpp"\n'
            ),
            True,
        ),
        ("No compilation database found in /src or any parent directory\n", True),
        ("error: compile_commands.json is missing\n", True),
        (
            (
                "LLVM ERROR: Could not open build/compile_commands.json: "
                "No such file or directory\n"
            ),
            True,
        ),
        ("Using compile_commands.json from build\n", False),
        ("a.cpp:1:5: warning: unused variable 'x' [misc-unused]\n", False),
        ("", False),
    ),
)
def test_looks_like_compile_db_error(output, expected):
    assert _looks_like_compile_db_error(output) is expected


@pytest.mark.parametrize(
    ("output", "expected"),
    (
        ("error: unable to find a Visual Studio installation\n", True),
        ("error: unable to execute command: program not executable 'cl.exe'\n", True),
        ("fatal error: 'windows.h' file not found\n", True),
        ("fatal error: 'sal.h' file not found\n", True),
        ("error: unknown argument: '/EHsc'\n", True),
        ("clang-tidy: error: unsupported option '/Zc:__cplusplus'\n", True),
        ("warning: argument unused during compilation: '/MP'\n", True),
        ("fatal error: 'stdio.h' file not found\n", False),
        ("cl.exe compiled a.cpp\n", False),
        ("", False),
    ),
)
def test_looks_like_msvc_error(output, expected):
    assert _looks_like_msvc_error(output) is expected


def test_append_guidance_leaves_unrelated_output_untouched():
    output = "a.cpp:1:5: warning: unused variable 'x'\n"

    assert _append_guidance(output) == output


def test_append_guidance_does_not_repeat_an_existing_hint():
    output = "error: compile_commands.json not found\n\n" + COMPILE_COMMANDS_HINT

    assert _append_guidance(output) == output


def test_append_guidance_appends_every_matching_hint():
    output = (
        "Error while trying to load a compilation database\n"
        "fatal error: 'vcruntime.h' file not found\n\n"
    )

    assert _append_guidance(output) == (
        "Error while trying to load a compilation database\n"
        "fatal error: 'vcruntime.h' file not found\n\n"
        f"{COMPILE_COMMANDS_HINT}\n\n{MSVC_HINT}"
    )


@pytest.mark.parametrize(
    ("args", "expected"),
    (
        ([], ([], [])),
        (["-p", "build"], (["-p", "build"], [])),
        (["--quiet", "a.cpp", "b.hpp"], (["--quiet"], ["a.cpp", "b.hpp"])),
        (["a.cpp", "--checks=-*", "b.cc"], (["a.cpp", "--checks=-*"], ["b.cc"])),
        (
            ["--export-fixes", "fixes.yaml", "MAIN.C", "kernel.CU"],
            (["--export-fixes", "fixes.yaml"], ["MAIN.C", "kernel.CU"]),
        ),
        (["src/Makefile"], (["src/Makefile"], [])),
    ),
)
def test_split_source_files(args, expected):
    assert _split_source_files(args) == expected


def test_combine_outputs_skips_empty_results():
    results = [(0, "a.cpp: ok\n"), (0, ""), (1, "b.cpp:1:1: warning: x\n\n")]

    assert _combine_outputs(results) == "a.cpp: ok\nb.cpp:1:1: warning: x"


def test_hook_options_are_not_passed_to_clang_tidy(mock_resolve, mock_exec, capsys):
    run_clang_tidy(
        [
            "--version=21",
            "--jobs=1",
            "--no-compile-commands",
            "--verbose",
            "--checks=-*,bugprone-*",
            "a.cpp",
        ]
    )

    mock_resolve.assert_called_once_with("clang-tidy", "21", True)
    mock_exec.assert_called_once_with(["clang-tidy", "--checks=-*,bugprone-*", "a.cpp"])
    assert capsys.readouterr().err == ""


def test_jobs_with_single_source_file_runs_once(mock_exec):
    run_clang_tidy(["--jobs=4", "-p", "./build", "a.cpp"])

    mock_exec.assert_called_once_with(
        ["clang-tidy", "-quiet", "-p", "./build", "a.cpp"]
    )


def test_jobs_parallel_run_succeeds_when_every_file_passes(mock_exec):
    ret = run_clang_tidy(["--jobs=2", "-p", "./build", "a.cpp", "b.cpp", "c.cpp"])

    assert ret == (0, "")
    assert sorted(call.args[0][-1] for call in mock_exec.call_args_list) == [
        "a.cpp",
        "b.cpp",
        "c.cpp",
    ]


def test_jobs_with_export_fixes_equals_form_forces_serial_execution(mock_exec):
    run_clang_tidy(
        ["--jobs=4", "-p", "./build", "--export-fixes=fixes.yaml", "a.cpp", "b.cpp"]
    )

    mock_exec.assert_called_once_with(
        [
            "clang-tidy",
            "-quiet",
            "-p",
            "./build",
            "--export-fixes=fixes.yaml",
            "a.cpp",
            "b.cpp",
        ]
    )


def test_fix_flag_is_inserted_before_source_files(mock_exec):
    run_clang_tidy(["--fix", "-p", "./build", "a.cpp", "b.cpp"])

    mock_exec.assert_called_once_with(
        ["clang-tidy", "-quiet", "-p", "./build", "-fix", "a.cpp", "b.cpp"]
    )


@pytest.mark.parametrize("existing", ["-fix", "-fix-errors"])
def test_fix_flag_does_not_add_a_second_fix_option(mock_exec, existing):
    run_clang_tidy(["--fix", "-p", "./build", existing, "a.cpp"])

    mock_exec.assert_called_once_with(
        ["clang-tidy", "-quiet", "-p", "./build", existing, "a.cpp"]
    )


@pytest.mark.parametrize("db_dir", COMPILE_DB_SEARCH_DIRS)
def test_compile_commands_auto_detect_each_search_dir(
    tmp_path, monkeypatch, mock_exec, db_dir
):
    monkeypatch.chdir(tmp_path)
    (tmp_path / db_dir).mkdir()
    (tmp_path / db_dir / "compile_commands.json").write_text("[]")

    run_clang_tidy(["a.cpp"])

    mock_exec.assert_called_once_with(["clang-tidy", "-quiet", "-p", db_dir, "a.cpp"])


def test_compile_commands_auto_detect_prefers_first_search_dir(
    tmp_path, monkeypatch, mock_exec
):
    monkeypatch.chdir(tmp_path)
    for db_dir in COMPILE_DB_SEARCH_DIRS:
        (tmp_path / db_dir).mkdir()
        (tmp_path / db_dir / "compile_commands.json").write_text("[]")

    run_clang_tidy(["a.cpp"])

    mock_exec.assert_called_once_with(
        ["clang-tidy", "-quiet", "-p", COMPILE_DB_SEARCH_DIRS[0], "a.cpp"]
    )


def test_compile_commands_p_equals_form_disables_auto_detect(
    tmp_path, monkeypatch, mock_exec
):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "build").mkdir()
    (tmp_path / "build" / "compile_commands.json").write_text("[]")

    run_clang_tidy(["-p=./custom", "a.cpp"])

    mock_exec.assert_called_once_with(["clang-tidy", "-quiet", "-p=./custom", "a.cpp"])


def test_compile_commands_explicit_path_must_be_a_directory(tmp_path, mock_exec):
    db_file = tmp_path / "compile_commands.json"
    db_file.write_text("[]")

    ret, output = run_clang_tidy([f"--compile-commands={db_file}", "a.cpp"])

    assert ret == 1
    assert f"--compile-commands: no compile_commands.json in '{db_file}'" in output
    mock_exec.assert_not_called()


def test_verbose_with_user_p_skips_missing_database_hint(
    tmp_path, monkeypatch, mock_exec, capsys
):
    monkeypatch.chdir(tmp_path)

    run_clang_tidy(["--verbose", "-p", "./custom", "a.cpp"])

    assert capsys.readouterr().err == ""
    mock_exec.assert_called_once_with(["clang-tidy", "-p", "./custom", "a.cpp"])


def test_main_prints_output_on_failure(monkeypatch, capsys):
    monkeypatch.setattr(
        "cpp_linter_hooks.clang_tidy.run_clang_tidy",
        lambda: (1, "a.cpp:1:5: warning: unused variable 'x'"),
    )

    assert main() == 1
    assert capsys.readouterr().out == "a.cpp:1:5: warning: unused variable 'x'\n"


def test_main_is_silent_on_success(monkeypatch, capsys):
    monkeypatch.setattr(
        "cpp_linter_hooks.clang_tidy.run_clang_tidy",
        lambda: (0, "1 warning generated."),
    )

    assert main() == 0
    assert capsys.readouterr().out == ""


def test_main_reads_arguments_from_command_line(monkeypatch, mock_resolve, mock_exec):
    monkeypatch.setattr(
        sys,
        "argv",
        ["clang-tidy-hook", "--version=21", "--no-compile-commands", "a.cpp"],
    )

    assert main() == 0

    mock_resolve.assert_called_once_with("clang-tidy", "21", False)
    mock_exec.assert_called_once_with(["clang-tidy", "-quiet", "a.cpp"])


# --- quiet output ---


@pytest.mark.parametrize("existing", ["-quiet", "--quiet", "--quiet=false"])
def test_quiet_is_not_added_twice(mock_exec, existing):
    run_clang_tidy([existing, "a.cpp"])

    mock_exec.assert_called_once_with(["clang-tidy", existing, "a.cpp"])


def test_verbose_does_not_add_quiet(mock_exec):
    run_clang_tidy(["--verbose", "--no-compile-commands", "a.cpp"])

    mock_exec.assert_called_once_with(["clang-tidy", "a.cpp"])


@pytest.mark.parametrize(
    "line",
    [
        "1 warning generated.",
        "537 warnings generated.",
        "1 error generated.",
        "14 warnings and 6 errors generated.",
        "1 warning and 1 error generated.",
        "Suppressed 521 warnings (521 in non-user code).",
        "Suppressed 3 warnings (2 in non-user code, 1 NOLINT).",
        (
            "Use -header-filter=.* to display errors from all non-system headers. "
            "Use -system-headers to display errors from system headers as well."
        ),
        (
            "Use -header-filter=.* or leave it as default to display errors from all "
            "non-system headers. Use -system-headers to display errors from system "
            "headers as well."
        ),
        "[1/2] Processing file /src/a.cpp.",
    ],
)
def test_strip_noise_removes_status_lines(line):
    diagnostic = "a.cpp:4:13: warning: statement should be inside braces [x]"

    assert _strip_noise(f"{line}\n{diagnostic}\n") == diagnostic


@pytest.mark.parametrize(
    "output",
    [
        "",
        "a.cpp:1:1: warning: 2 warnings generated. [x]\n",
        "Error while processing /src/a.cpp.\n",
        "Error while trying to load a compilation database:\nRunning without flags.\n",
    ],
)
def test_strip_noise_keeps_everything_else(output):
    assert _strip_noise(output) == output


def test_run_strips_noise_unless_verbose(mock_resolve):
    raw = (
        "537 warnings generated.\n"
        "Suppressed 536 warnings (536 in non-user code).\n"
        "a.cpp:4:13: warning: statement should be inside braces [x]\n"
    )
    with patch("cpp_linter_hooks.clang_tidy._exec_clang_tidy", return_value=(1, raw)):
        assert run_clang_tidy(["a.cpp"]) == (
            1,
            "a.cpp:4:13: warning: statement should be inside braces [x]",
        )
        assert run_clang_tidy(["--verbose", "--no-compile-commands", "a.cpp"]) == (
            1,
            raw,
        )


# --- check lists mangled by YAML in .pre-commit-config.yaml ---


@pytest.mark.parametrize(
    ("args", "expected"),
    [
        (
            ["--checks=-*", "bugprone-*", "performance-*"],
            ["--checks=-*,bugprone-*,performance-*"],
        ),
        (
            ["--checks=boost-*", "clang-analyzer-*", "cppcoreguidelines-*", "-p", "b"],
            ["--checks=boost-*,clang-analyzer-*,cppcoreguidelines-*", "-p", "b"],
        ),
        (
            ["--checks=*", "-modernize-use-trailing-return-type", "-llvmlibc-*"],
            ["--checks=*,-modernize-use-trailing-return-type,-llvmlibc-*"],
        ),
        (
            ["--checks='-*", "cppcoreguidelines-*'"],
            ["--checks=-*,cppcoreguidelines-*"],
        ),
        (
            ["-checks=-*", "readability-*", "--header-filter=.*"],
            ["-checks=-*,readability-*", "--header-filter=.*"],
        ),
        (
            ["--warnings-as-errors=*", "-misc-*"],
            ["--warnings-as-errors=*,-misc-*"],
        ),
    ],
)
def test_repair_check_args_joins_split_check_lists(args, expected):
    repaired, notes = _repair_check_args(args)

    assert repaired == expected
    assert len(notes) == 1
    assert "YAML split" in notes[0]
    assert f'args: ["{expected[0]}"]' in notes[0]


@pytest.mark.parametrize(
    ("arg", "expected"),
    [('--checks="boost-*"', "--checks=boost-*"), ("--checks='-*'", "--checks=-*")],
)
def test_repair_check_args_removes_quotes_inside_the_value(arg, expected):
    repaired, notes = _repair_check_args([arg])

    assert repaired == [expected]
    assert len(notes) == 1
    assert "removed the quotes" in notes[0]
    assert f'args: ["{expected}"]' in notes[0]


@pytest.mark.parametrize(
    "arg",
    [
        "--checks=.clang-tidy",
        "--checks=.clang-dity",
        "--checks=./.clang-tidy",
        "-checks=config/clang-tidy.yaml",
    ],
)
def test_repair_check_args_flags_a_config_file_given_as_checks(arg):
    repaired, notes = _repair_check_args([arg])

    assert repaired == [arg]
    assert len(notes) == 1
    assert "has no effect" in notes[0]
    assert "--config-file" in notes[0]


@pytest.mark.parametrize(
    "args",
    [
        [],
        ["--checks=-*,bugprone-*", "-p", "build"],
        ["-p", "build", "--header-filter=.*", "--extra-arg=-std=c++17"],
        ["bugprone-*"],
        ["--config-file=.clang-tidy", "--line-filter=[]"],
    ],
)
def test_repair_check_args_leaves_valid_arguments_alone(args):
    assert _repair_check_args(args) == (args, [])


def test_run_joins_split_checks_and_explains_why(mock_resolve):
    with patch(
        "cpp_linter_hooks.clang_tidy._exec_clang_tidy",
        return_value=(1, "a.cpp:1:1: warning: x [bugprone-y]\n"),
    ) as mock_exec:
        ret, output = run_clang_tidy(["--checks=-*", "bugprone-*", "a.cpp"])

    mock_exec.assert_called_once_with(
        ["clang-tidy", "-quiet", "--checks=-*,bugprone-*", "a.cpp"]
    )
    assert ret == 1
    assert output.startswith("a.cpp:1:1: warning: x [bugprone-y]\n\nNote: YAML split")


def test_run_clang_tidy_with_split_checks_runs_the_real_tool(tmp_path):
    """End to end: the pieces YAML split off are not treated as files."""
    # No #include, so the result does not depend on system headers being found.
    source = tmp_path / "braces.cpp"
    source.write_text("int f(int x) {\n  if (x)\n    return 1;\n  return 0;\n}\n")

    ret, output = run_clang_tidy(
        ["--no-compile-commands", "--checks=-*", "readability-braces-*", str(source)]
    )

    assert ret == 1
    assert "readability-braces-around-statements" in output
    assert "Error while processing" not in output
    assert "warnings generated" not in output
    assert "YAML split" in output


def test_run_uses_the_resolved_executable(mock_resolve):
    """The version check and the run must use the same clang-tidy."""
    tool = Path("/venv/bin/clang-tidy")
    mock_resolve.return_value = (tool, None)
    with patch(
        "cpp_linter_hooks.clang_tidy._exec_clang_tidy", return_value=(0, "")
    ) as mock_exec:
        run_clang_tidy(["--no-compile-commands", "a.cpp"])
        run_clang_tidy(["--no-compile-commands", "--jobs=2", "a.cpp", "b.cpp"])

    commands = [call.args[0] for call in mock_exec.call_args_list]
    assert commands[0] == [str(tool), "-quiet", "a.cpp"]
    assert sorted(command[-1] for command in commands[1:]) == ["a.cpp", "b.cpp"]
    assert all(command[0] == str(tool) for command in commands)


# --- only changed lines are reported ---


def test_line_filter_option(monkeypatch):
    monkeypatch.setattr(clang_tidy.os, "sep", "/")
    option = _line_filter_option({"./src/a.cpp": [[3, 3], [7, 8]], "b.h": [[1, 1]]})

    assert option == (
        '--line-filter=[{"name":"src/a.cpp","lines":[[3,3],[7,8]]},'
        '{"name":"b.h","lines":[[1,1]]}]'
    )


def test_line_filter_option_lists_windows_separators(monkeypatch):
    monkeypatch.setattr(clang_tidy.os, "sep", "\\")

    option = _line_filter_option({"src/a.cpp": [[1, 2]]})

    assert option == (
        '--line-filter=[{"name":"src/a.cpp","lines":[[1,2]]},'
        '{"name":"src\\\\a.cpp","lines":[[1,2]]}]'
    )


def test_run_filters_to_changed_lines(monkeypatch, mock_exec):
    monkeypatch.setattr(
        clang_tidy, "changed_lines", lambda files: {"a.cpp": [[2, 4]], "b.cpp": []}
    )

    run_clang_tidy(["a.cpp", "b.cpp"])

    mock_exec.assert_called_once_with(
        [
            "clang-tidy",
            "-quiet",
            '--line-filter=[{"name":"a.cpp","lines":[[2,4]]}]',
            "a.cpp",
        ]
    )


def test_run_skips_clang_tidy_without_added_lines(monkeypatch, mock_exec):
    monkeypatch.setattr(clang_tidy, "changed_lines", lambda files: {"a.cpp": []})

    assert run_clang_tidy(["a.cpp"]) == (0, "")
    mock_exec.assert_not_called()


def test_run_without_added_lines_keeps_notes(monkeypatch, mock_exec):
    monkeypatch.setattr(clang_tidy, "changed_lines", lambda files: {"a.cpp": []})

    ret, output = run_clang_tidy(["--checks=.clang-tidy", "a.cpp"])

    assert ret == 0
    assert "--checks=.clang-tidy has no effect" in output


@pytest.mark.parametrize("args", (["--all-lines"], ["--line-filter=[]"]))
def test_run_checks_all_lines_when_asked(monkeypatch, mock_exec, args):
    monkeypatch.setattr(
        clang_tidy, "changed_lines", lambda files: pytest.fail("not wanted")
    )

    run_clang_tidy(args + ["a.cpp"])

    mock_exec.assert_called_once()
    assert not any(
        arg.startswith("--line-filter=[{") for arg in mock_exec.call_args.args[0]
    )


def test_verbose_says_which_lines_are_checked(monkeypatch, mock_exec, capsys):
    monkeypatch.setattr(clang_tidy, "changed_lines", lambda files: {"a.cpp": [[1, 1]]})

    run_clang_tidy(["--verbose", "a.cpp"])

    assert (
        "Reporting only lines changed in git diff --cached; use --all-lines"
        in capsys.readouterr().err
    )


def test_line_filter_reaches_each_parallel_run(monkeypatch, mock_exec):
    monkeypatch.setattr(
        clang_tidy,
        "changed_lines",
        lambda files: {"a.cpp": [[1, 1]], "b.cpp": [[2, 2]]},
    )

    run_clang_tidy(["--jobs=2", "a.cpp", "b.cpp"])

    line_filter = (
        '--line-filter=[{"name":"a.cpp","lines":[[1,1]]},'
        '{"name":"b.cpp","lines":[[2,2]]}]'
    )
    commands = sorted(call.args[0] for call in mock_exec.call_args_list)
    assert commands == [
        ["clang-tidy", "-quiet", line_filter, "a.cpp"],
        ["clang-tidy", "-quiet", line_filter, "b.cpp"],
    ]


def _git(repo, *args):
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.com",
            "-c",
            "commit.gpgsign=false",
            *args,
        ],
        cwd=repo,
        check=True,
        capture_output=True,
    )


@pytest.fixture
def braces_repo(tmp_path, monkeypatch, real_changed_lines, real_compile_db_check):
    """A git repo whose committed braces.cpp has two old brace warnings.

    The staged change adds a third one on line 6. compile_flags.txt is the
    compilation database; the file has no #include, so the result does not
    depend on system headers being found.
    """
    source = tmp_path / "braces.cpp"
    source.write_text(
        "int f(int x) {\n"
        "  if (x)\n"
        "    return 1;\n"
        "  if (x > 1)\n"
        "    return 2;\n"
        "  return 0;\n"
        "}\n"
    )
    (tmp_path / "compile_flags.txt").write_text("-std=c++17\n")
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-q", "-m", "init")
    lines = source.read_text().splitlines(keepends=True)
    lines[5] = "  if (x > 2)\n    return 3;\n  return 0;\n"
    source.write_text("".join(lines))
    _git(tmp_path, "add", "braces.cpp")
    monkeypatch.chdir(tmp_path)
    return source


CHECK_BRACES = ["--checks=-*,readability-braces-around-statements"]


def test_real_tool_reports_only_the_changed_lines(braces_repo):
    ret, output = run_clang_tidy(CHECK_BRACES + ["braces.cpp"])

    assert ret == 1
    assert "braces.cpp:6:" in output
    assert "braces.cpp:2:" not in output
    assert "braces.cpp:4:" not in output


def test_real_tool_reports_every_line_with_all_lines(braces_repo):
    ret, output = run_clang_tidy(CHECK_BRACES + ["--all-lines", "braces.cpp"])

    assert ret == 1
    assert "braces.cpp:2:" in output
    assert "braces.cpp:4:" in output
    assert "braces.cpp:6:" in output


def test_real_tool_fixes_only_the_changed_lines(braces_repo):
    run_clang_tidy(CHECK_BRACES + ["--fix", "braces.cpp"])

    fixed = braces_repo.read_text()
    assert "if (x > 2) {" in fixed
    assert "if (x) {" not in fixed
    assert "if (x > 1) {" not in fixed


# --- what happens without a compilation database ---


@pytest.fixture
def no_compile_db(tmp_path, monkeypatch, real_compile_db_check):
    """A directory without any compilation database, used as the cwd."""
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_missing_compile_db_skips_locally(no_compile_db, mock_exec, capsys):
    assert run_clang_tidy(["a.cpp"]) == (0, "")

    mock_exec.assert_not_called()
    stderr = capsys.readouterr().err
    assert "Skipped clang-tidy" in stderr
    assert "cmake -S . -B build -DCMAKE_EXPORT_COMPILE_COMMANDS=ON" in stderr
    assert "--no-compile-commands" in stderr


def test_missing_compile_db_skips_before_installing(no_compile_db, mock_resolve):
    run_clang_tidy(["a.cpp"])

    mock_resolve.assert_not_called()


@pytest.mark.parametrize("value", ("true", "1", "True", "yes"))
def test_missing_compile_db_fails_in_ci(no_compile_db, mock_exec, monkeypatch, value):
    monkeypatch.setenv("CI", value)

    ret, output = run_clang_tidy(["--checks=.clang-tidy", "a.cpp"])

    assert ret == 1
    assert output.startswith("clang-tidy needs a compilation database.")
    assert "--no-compile-commands" in output
    assert "--checks=.clang-tidy has no effect" in output
    mock_exec.assert_not_called()


@pytest.mark.parametrize("value", ("", "false", "0", "no"))
def test_ci_variable_set_to_false(no_compile_db, mock_exec, monkeypatch, value):
    monkeypatch.setenv("CI", value)

    assert run_clang_tidy(["a.cpp"]) == (0, "")


@pytest.mark.parametrize(
    "args",
    (
        ["--no-compile-commands"],
        ["-p", "elsewhere"],
        ["-p=elsewhere"],
        ["--extra-arg=-std=c++20"],
        ["-extra-arg=-std=c++20"],
        ["--extra-arg-before=--driver-mode=cl"],
        ["--extra-arg", "-std=c++20"],
    ),
)
def test_missing_compile_db_runs_when_flags_are_given(no_compile_db, mock_exec, args):
    run_clang_tidy(args + ["a.cpp"])

    mock_exec.assert_called_once()


@pytest.mark.parametrize("name", ("compile_commands.json", "compile_flags.txt"))
def test_database_found_in_a_parent_directory(tmp_path, name):
    (tmp_path / name).write_text("")
    (tmp_path / "src" / "deep").mkdir(parents=True)

    assert _has_compilation_database([str(tmp_path / "src" / "deep" / "a.cpp")])


def test_database_next_to_one_of_the_files(tmp_path):
    (tmp_path / "with").mkdir()
    (tmp_path / "with" / "compile_flags.txt").write_text("")

    assert _has_compilation_database(
        [str(tmp_path / "a.cpp"), str(tmp_path / "with" / "b.cpp")]
    )


def test_no_database_in_any_parent(no_compile_db):
    (no_compile_db / "src").mkdir()

    assert not _has_compilation_database(["a.cpp", "b.cpp", "src/c.cpp"])


def test_testing_dir_uses_its_compile_flags():
    assert _has_compilation_database(["testing/main.c"])


@pytest.mark.parametrize(
    "db_dir", ("cmake-build-release", "build-gcc", "build/debug", "out/build/x64-Debug")
)
def test_compile_commands_found_by_pattern(tmp_path, monkeypatch, db_dir):
    monkeypatch.chdir(tmp_path)
    (tmp_path / db_dir).mkdir(parents=True)
    (tmp_path / db_dir / "compile_commands.json").write_text("[]")

    assert _find_compile_commands() == db_dir


def test_newest_compile_commands_wins_within_a_pattern(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    for index, preset in enumerate(("release", "debug", "asan")):
        db = tmp_path / "build" / preset / "compile_commands.json"
        db.parent.mkdir(parents=True)
        db.write_text("[]")
        os.utime(db, (1_000_000 + index, 1_000_000 + index))

    assert _find_compile_commands() == "build/asan"


def test_fixed_directories_win_over_patterns(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    for db_dir in ("cmake-build-release", "builddir"):
        (tmp_path / db_dir).mkdir()
        (tmp_path / db_dir / "compile_commands.json").write_text("[]")

    assert _find_compile_commands() == "builddir"


@pytest.mark.parametrize(
    "name", ("a.mm", "a.cppm", "a.ccm", "a.cxxm", "a.c++m", "sketch.ino")
)
def test_split_source_files_knows_pre_commit_cpp_types(name):
    assert _split_source_files(["-quiet", "a.cpp", name]) == (
        ["-quiet"],
        ["a.cpp", name],
    )
