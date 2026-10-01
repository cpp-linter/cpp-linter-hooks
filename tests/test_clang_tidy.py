import subprocess
import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cpp_linter_hooks.clang_tidy import (
    COMPILE_COMMANDS_HINT,
    COMPILE_DB_SEARCH_DIRS,
    MSVC_HINT,
    _append_guidance,
    _combine_outputs,
    _exec_clang_tidy,
    _looks_like_compile_db_error,
    _looks_like_msvc_error,
    _positive_int,
    _split_source_files,
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
    tmp_path, monkeypatch, capsys
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
        ("clang-tidy", "-p", "./build", "--header-filter=.*", "a.cpp"),
        ("clang-tidy", "-p", "./build", "--header-filter=.*", "b.hpp"),
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

    mock_exec.assert_called_once_with(["clang-tidy", "-p", "./build", "a.cpp"])


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
        ["clang-tidy", "-p", "./build", "--export-fixes=fixes.yaml", "a.cpp", "b.cpp"]
    )


def test_fix_flag_is_inserted_before_source_files(mock_exec):
    run_clang_tidy(["--fix", "-p", "./build", "a.cpp", "b.cpp"])

    mock_exec.assert_called_once_with(
        ["clang-tidy", "-p", "./build", "-fix", "a.cpp", "b.cpp"]
    )


@pytest.mark.parametrize("existing", ["-fix", "-fix-errors"])
def test_fix_flag_does_not_add_a_second_fix_option(mock_exec, existing):
    run_clang_tidy(["--fix", "-p", "./build", existing, "a.cpp"])

    mock_exec.assert_called_once_with(
        ["clang-tidy", "-p", "./build", existing, "a.cpp"]
    )


@pytest.mark.parametrize("db_dir", COMPILE_DB_SEARCH_DIRS)
def test_compile_commands_auto_detect_each_search_dir(
    tmp_path, monkeypatch, mock_exec, db_dir
):
    monkeypatch.chdir(tmp_path)
    (tmp_path / db_dir).mkdir()
    (tmp_path / db_dir / "compile_commands.json").write_text("[]")

    run_clang_tidy(["a.cpp"])

    mock_exec.assert_called_once_with(["clang-tidy", "-p", db_dir, "a.cpp"])


def test_compile_commands_auto_detect_prefers_first_search_dir(
    tmp_path, monkeypatch, mock_exec
):
    monkeypatch.chdir(tmp_path)
    for db_dir in COMPILE_DB_SEARCH_DIRS:
        (tmp_path / db_dir).mkdir()
        (tmp_path / db_dir / "compile_commands.json").write_text("[]")

    run_clang_tidy(["a.cpp"])

    mock_exec.assert_called_once_with(
        ["clang-tidy", "-p", COMPILE_DB_SEARCH_DIRS[0], "a.cpp"]
    )


def test_compile_commands_p_equals_form_disables_auto_detect(
    tmp_path, monkeypatch, mock_exec
):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "build").mkdir()
    (tmp_path / "build" / "compile_commands.json").write_text("[]")

    run_clang_tidy(["-p=./custom", "a.cpp"])

    mock_exec.assert_called_once_with(["clang-tidy", "-p=./custom", "a.cpp"])


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
    mock_exec.assert_called_once_with(["clang-tidy", "a.cpp"])
