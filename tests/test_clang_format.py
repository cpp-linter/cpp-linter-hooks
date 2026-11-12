import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from cpp_linter_hooks import clang_format
from cpp_linter_hooks.clang_format import main, parser, run_clang_format


def test_all_arguments_have_help():
    missing_help = [
        action.option_strings for action in parser._actions if not action.help
    ]
    assert missing_help == []

    help_text = " ".join(parser.format_help().split())
    assert all(" ".join(action.help.split()) in help_text for action in parser._actions)


@pytest.mark.benchmark
@pytest.mark.parametrize(
    ("args", "expected_retval"),
    (
        (["--style=Google"], (0, "")),
        (["--style=Google", "--version=16"], (0, "")),
        (["--style=Google", "--version=17"], (0, "")),
        (["--style=Google", "--version=18"], (0, "")),
        (["--style=Google", "--version=19"], (0, "")),
        (["--style=Google", "--version=20"], (0, "")),
        (["--style=Google", "--version=21"], (0, "")),
    ),
)
def test_run_clang_format_valid(args, expected_retval, tmp_path):
    # copy test file to tmp_path to prevent modifying repo data
    test_file = tmp_path / "main.c"
    test_file.write_bytes(Path("testing/main.c").read_bytes())
    ret = run_clang_format(args + [str(test_file)])
    assert ret == expected_retval
    assert test_file.read_text() == Path("testing/good.c").read_text()


@pytest.mark.benchmark
@pytest.mark.parametrize(
    ("args", "expected_retval"),
    (
        (
            [
                "--style=Google",
            ],
            1,
        ),
        (["--style=Google", "--version=16"], 1),
        (["--style=Google", "--version=17"], 1),
        (["--style=Google", "--version=18"], 1),
        (["--style=Google", "--version=19"], 1),
        (["--style=Google", "--version=20"], 1),
        (["--style=Google", "--version=21"], 1),
    ),
)
def test_run_clang_format_invalid(args, expected_retval, tmp_path):
    # non existent file
    test_file = tmp_path / "main.c"

    ret, _ = run_clang_format(args + [str(test_file)])
    assert ret == expected_retval


@pytest.mark.benchmark
def test_run_clang_format_dry_run_unformatted(tmp_path):
    """Dry-run detects unformatted files and returns non-zero."""
    test_file = tmp_path / "main.c"
    test_file.write_bytes(Path("testing/main.c").read_bytes())
    ret, output = run_clang_format(["--dry-run", "--style=Google", str(test_file)])
    assert ret == 1  # Should report failure (unformatted)
    assert output.strip()  # Should report which file needs formatting


def test_run_clang_format_short_dry_run_fails_unformatted(tmp_path):
    """-n is short for --dry-run, so it also fails on unformatted files."""
    test_file = tmp_path / "main.c"
    test_file.write_bytes(Path("testing/main.c").read_bytes())
    ret, output = run_clang_format(["-n", "--style=Google", str(test_file)])
    assert ret == 1
    assert "clang-format-violations" in output


def test_run_clang_format_dry_run_on_a_file_that_is_not_utf8(tmp_path):
    """clang-format prints source lines; Latin-1 bytes must not crash the hook."""
    test_file = tmp_path / "latin1.c"
    test_file.write_bytes(b"int  x = 1; /* caf\xe9 */\n")
    ret, output = run_clang_format(["--dry-run", str(test_file)])
    assert ret == 1
    assert "caf\ufffd" in output


@pytest.mark.benchmark
def test_run_clang_format_dry_run_formatted(tmp_path):
    """Dry-run on already-formatted files returns success."""
    test_file = tmp_path / "good.c"
    test_file.write_bytes(Path("testing/good.c").read_bytes())
    ret, output = run_clang_format(["--dry-run", "--style=Google", str(test_file)])
    assert ret == 0  # Already formatted
    assert not output.strip()  # No diff output


@pytest.mark.benchmark
def test_run_clang_format_verbose(tmp_path):
    """Test that verbose option works and provides detailed output."""
    # copy test file to tmp_path to prevent modifying repo data
    test_file = tmp_path / "main.c"
    test_file.write_bytes(Path("testing/main.c").read_bytes())

    # Test with verbose flag
    ret, _ = run_clang_format(["--verbose", "--style=Google", str(test_file)])

    # Should succeed
    assert ret == 0
    # Should have verbose output (will be printed to stderr, not returned)
    # The function should still return successfully
    assert test_file.read_text() == Path("testing/good.c").read_text()


@pytest.mark.benchmark
def test_run_clang_format_verbose_error(tmp_path):
    """Test that verbose option provides useful error information."""
    test_file = tmp_path / "main.c"
    test_file.write_bytes(Path("testing/main.c").read_bytes())

    # Test with verbose flag and invalid style
    ret, output = run_clang_format(
        ["--verbose", "--style=InvalidStyle", str(test_file)]
    )

    # Should fail
    assert ret != 0
    # Should have error message in output
    assert "Invalid value for -style" in output


def test_run_clang_format_invalid_version_returns_supported_versions():
    with patch(
        "cpp_linter_hooks.clang_format.resolve_install_with_diagnostics",
        return_value=(
            None,
            "Unsupported clang-format version '99'.\nSupported versions",
        ),
    ):
        ret, output = run_clang_format(["--version=99", "dummy.cpp"])

    assert ret == 1
    assert "Unsupported clang-format version '99'" in output
    assert "Supported versions" in output


def test_run_clang_format_verbose_passes_version_diagnostics():
    with (
        patch(
            "cpp_linter_hooks.clang_format.resolve_install_with_diagnostics",
            return_value=(None, None),
        ) as mock_resolve,
        patch("cpp_linter_hooks.clang_format.subprocess.run") as mock_run,
    ):
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = ""
        mock_run.return_value.stderr = ""
        ret, output = run_clang_format(["--verbose", "--version=21", "dummy.cpp"])

    assert (ret, output) == (0, "")
    mock_resolve.assert_called_once_with("clang-format", "21", True)


def test_main_returns_success_without_output(monkeypatch, capsys):
    monkeypatch.setattr(
        "cpp_linter_hooks.clang_format.run_clang_format", lambda: (0, "")
    )

    assert main() == 0
    assert capsys.readouterr().out == ""


def test_main_prints_failure_output(monkeypatch, capsys):
    monkeypatch.setattr(
        "cpp_linter_hooks.clang_format.run_clang_format",
        lambda: (1, "formatting failed"),
    )

    assert main() == 1
    assert capsys.readouterr().out == "formatting failed\n"


# --- offline tests: tool resolution and the clang-format process are mocked ---


@pytest.fixture
def mock_clang_format():
    """Mock tool resolution and the clang-format process."""
    with (
        patch(
            "cpp_linter_hooks.clang_format.resolve_install_with_diagnostics",
            return_value=(None, None),
        ) as mock_resolve,
        patch("cpp_linter_hooks.clang_format.subprocess.run") as mock_run,
    ):
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr=""
        )
        yield mock_resolve, mock_run


def test_run_clang_format_formats_files_in_place(mock_clang_format):
    mock_resolve, mock_run = mock_clang_format

    assert run_clang_format(["--style=Google", "a.cpp", "b.cpp"]) == (0, "")

    mock_resolve.assert_called_once_with("clang-format", None, False)
    mock_run.assert_called_once_with(
        ["clang-format", "-i", "--style=Google", "a.cpp", "b.cpp"],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


@pytest.mark.parametrize(
    ("args", "expected_command"),
    (
        (
            ["--dry-run", "a.cpp"],
            ["clang-format", "-i", "--Werror", "--dry-run", "a.cpp"],
        ),
        (
            ["--dry-run", "--Werror", "a.cpp"],
            ["clang-format", "-i", "--dry-run", "--Werror", "a.cpp"],
        ),
        (["--Werror", "a.cpp"], ["clang-format", "-i", "--Werror", "a.cpp"]),
        (["a.cpp"], ["clang-format", "-i", "a.cpp"]),
    ),
)
def test_run_clang_format_adds_werror_only_for_dry_run(
    mock_clang_format, args, expected_command
):
    _, mock_run = mock_clang_format

    run_clang_format(args)

    assert mock_run.call_args.args[0] == expected_command


def test_run_clang_format_does_not_read_a_file_name_as_an_option(
    mock_clang_format, tmp_path, monkeypatch
):
    # A file named --files=list.cpp would make clang-format format the files
    # listed in it, even outside the repository.
    monkeypatch.chdir(tmp_path)
    (tmp_path / "--files=list.cpp").write_text("/etc/hosts\n")
    _, mock_run = mock_clang_format

    run_clang_format(["--files=list.cpp"])

    assert mock_run.call_args.args[0] == ["clang-format", "-i", "./--files=list.cpp"]


def test_run_clang_format_combines_stdout_and_stderr(mock_clang_format):
    _, mock_run = mock_clang_format
    mock_run.return_value = subprocess.CompletedProcess(
        args=[], returncode=1, stdout="a.cpp needs formatting\n", stderr="error: x\n"
    )

    assert run_clang_format(["--dry-run", "a.cpp"]) == (
        1,
        "a.cpp needs formatting\nerror: x\n",
    )


def test_run_clang_format_handles_missing_streams(mock_clang_format):
    _, mock_run = mock_clang_format
    mock_run.return_value = subprocess.CompletedProcess(
        args=[], returncode=0, stdout=None, stderr=None
    )

    assert run_clang_format(["a.cpp"]) == (0, "")


def test_run_clang_format_reports_missing_executable(mock_clang_format):
    _, mock_run = mock_clang_format
    mock_run.side_effect = FileNotFoundError(
        2, "No such file or directory", "clang-format"
    )

    assert run_clang_format(["a.cpp"]) == (
        1,
        "[Errno 2] No such file or directory: 'clang-format'",
    )


def test_run_clang_format_verbose_prints_command_details(mock_clang_format, capsys):
    _, mock_run = mock_clang_format
    mock_run.return_value = subprocess.CompletedProcess(
        args=[], returncode=1, stdout="", stderr="Invalid value for -style\n"
    )

    ret, output = run_clang_format(["-v", "--style=Bogus", "a.cpp"])

    assert (ret, output) == (1, "Invalid value for -style\n")
    assert mock_run.call_args.args[0] == [
        "clang-format",
        "-i",
        "--verbose",
        "--style=Bogus",
        "a.cpp",
    ]
    stderr = capsys.readouterr().err
    assert "Command executed: clang-format -i --verbose --style=Bogus a.cpp" in stderr
    assert "Exit code: 1" in stderr
    assert "Output: Invalid value for -style" in stderr


def test_run_clang_format_verbose_omits_empty_output(mock_clang_format, capsys):
    run_clang_format(["--verbose", "a.cpp"])

    stderr = capsys.readouterr().err
    assert "Exit code: 0" in stderr
    assert "Output:" not in stderr


def test_main_reads_arguments_from_command_line(mock_clang_format, monkeypatch, capsys):
    mock_resolve, mock_run = mock_clang_format
    monkeypatch.setattr(
        sys, "argv", ["clang-format-hook", "--version=21", "--style=file", "a.cpp"]
    )

    assert main() == 0

    mock_resolve.assert_called_once_with("clang-format", "21", False)
    assert mock_run.call_args.args[0] == [
        "clang-format",
        "-i",
        "--style=file",
        "a.cpp",
    ]
    assert capsys.readouterr().out == ""


def test_main_does_not_print_blank_failure_output(monkeypatch, capsys):
    monkeypatch.setattr(
        "cpp_linter_hooks.clang_format.run_clang_format", lambda: (1, " \n")
    )

    assert main() == 1
    assert capsys.readouterr().out == ""


def test_run_clang_format_uses_the_resolved_executable(mock_clang_format):
    """The version check and the run must use the same clang-format."""
    mock_resolve, mock_run = mock_clang_format
    tool = Path("/venv/bin/clang-format")
    mock_resolve.return_value = (tool, None)

    run_clang_format(["a.cpp"])

    assert mock_run.call_args.args[0] == [str(tool), "-i", "a.cpp"]


# --- --lines-changed-only ---


@pytest.fixture
def source_files(tmp_path, monkeypatch):
    """Run in a directory with the files that pre-commit would pass."""
    monkeypatch.chdir(tmp_path)
    for name in ("a.cpp", "b.cpp", "c.cpp", "a.proto"):
        (tmp_path / name).write_text("")


def test_lines_changed_only_runs_once_per_file_with_its_lines(
    mock_clang_format, monkeypatch, source_files
):
    _, mock_run = mock_clang_format
    monkeypatch.setattr(
        clang_format,
        "changed_lines",
        lambda files: {"a.cpp": [[3, 3], [7, 8]], "b.cpp": [[1, 2]], "c.cpp": []},
    )

    assert run_clang_format(
        ["--lines-changed-only", "--style=Google", "a.cpp", "b.cpp", "c.cpp"]
    ) == (0, "")

    # c.cpp has no added lines, so it is not formatted.
    assert [call.args[0] for call in mock_run.call_args_list] == [
        ["clang-format", "-i", "--style=Google", "--lines=3:3", "--lines=7:8", "a.cpp"],
        ["clang-format", "-i", "--style=Google", "--lines=1:2", "b.cpp"],
    ]


def test_lines_changed_only_formats_every_line_when_the_lines_are_unknown(
    mock_clang_format, monkeypatch, source_files
):
    _, mock_run = mock_clang_format
    monkeypatch.setattr(clang_format, "changed_lines", lambda files: None)

    run_clang_format(["--lines-changed-only", "--style=Google", "a.cpp", "b.cpp"])

    mock_run.assert_called_once()
    assert mock_run.call_args.args[0] == [
        "clang-format",
        "-i",
        "--style=Google",
        "a.cpp",
        "b.cpp",
    ]


@pytest.mark.parametrize("lines", (["--lines=1:2"], ["-lines=1:2"], ["--lines", "1:2"]))
def test_lines_changed_only_keeps_lines_given_in_args(
    mock_clang_format, monkeypatch, lines, source_files
):
    _, mock_run = mock_clang_format
    monkeypatch.setattr(
        clang_format, "changed_lines", lambda files: {"a.cpp": [[5, 5]]}
    )

    run_clang_format(["--lines-changed-only", *lines, "a.cpp"])

    mock_run.assert_called_once()
    assert mock_run.call_args.args[0] == ["clang-format", "-i", *lines, "a.cpp"]


def test_lines_changed_only_runs_nothing_without_added_lines(
    mock_clang_format, monkeypatch, source_files
):
    _, mock_run = mock_clang_format
    monkeypatch.setattr(clang_format, "changed_lines", lambda files: {"a.cpp": []})

    assert run_clang_format(["--lines-changed-only", "a.cpp"]) == (0, "")

    mock_run.assert_not_called()


def test_lines_changed_only_reports_every_failing_file(
    mock_clang_format, monkeypatch, source_files
):
    _, mock_run = mock_clang_format
    monkeypatch.setattr(
        clang_format,
        "changed_lines",
        lambda files: {name: [[1, 1]] for name in files},
    )
    mock_run.side_effect = [
        subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
        subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="b\n"),
        subprocess.CompletedProcess(args=[], returncode=2, stdout="", stderr="c\n"),
    ]

    assert run_clang_format(
        ["--lines-changed-only", "--dry-run", "a.cpp", "b.cpp", "c.cpp"]
    ) == (1, "b\nc\n")

    assert mock_run.call_args.args[0] == [
        "clang-format",
        "-i",
        "--Werror",
        "--dry-run",
        "--lines=1:1",
        "c.cpp",
    ]


def test_lines_changed_only_runs_a_first_file_of_another_type_alone(
    mock_clang_format, monkeypatch, source_files
):
    # types_or can add files such as a.proto; one that comes right after a
    # flag must still be a file, or two files get one --lines.
    _, mock_run = mock_clang_format
    monkeypatch.setattr(
        clang_format, "changed_lines", lambda files: {f: [[1, 1]] for f in files}
    )

    run_clang_format(["--lines-changed-only", "--dry-run", "a.proto", "b.cpp"])

    assert [call.args[0][-2:] for call in mock_run.call_args_list] == [
        ["--lines=1:1", "a.proto"],
        ["--lines=1:1", "b.cpp"],
    ]


def test_lines_changed_only_formats_only_the_staged_lines(tmp_path, monkeypatch):
    """The real clang-format leaves the unformatted lines of older commits alone."""

    def git(*args):
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
            cwd=tmp_path,
            check=True,
            capture_output=True,
        )

    source = tmp_path / "a.c"
    source.write_text("int   old  =  1;\n\nint   other  =  2;\n")
    git("init", "-q")
    git("add", "a.c")
    git("commit", "-q", "-m", "init")
    source.write_text("int   old  =  1;\n\nint   added  =  3;\n")
    git("add", "a.c")
    monkeypatch.chdir(tmp_path)

    assert run_clang_format(["--lines-changed-only", "--style=LLVM", "a.c"]) == (0, "")

    assert source.read_text() == "int   old  =  1;\n\nint added = 3;\n"
