import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from cpp_linter_hooks.clang_format import run_clang_format, main


@pytest.mark.parametrize(
    ("args", "expected_retval"),
    (
        (["--style=Google"], (0, "")),
        (["--style=Google", "--version=16"], (0, "")),
        (["--style=Google", "--version=17"], (0, "")),
        (["--style=Google", "--version=18"], (0, "")),
        (["--style=Google", "--version=19"], (0, "")),
        (["--style=Google", "--version=20"], (0, "")),
    ),
)
def test_run_clang_format_valid(args, expected_retval, tmp_path):
    # copy test file to tmp_path to prevent modifying repo data
    test_file = tmp_path / "main.c"
    test_file.write_bytes(Path("testing/main.c").read_bytes())
    ret = run_clang_format(args + [str(test_file)])
    assert ret == expected_retval
    assert test_file.read_text() == Path("testing/good.c").read_text()


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
    ),
)
def test_run_clang_format_invalid(args, expected_retval, tmp_path):
    # non existent file
    test_file = tmp_path / "main.c"

    ret, _ = run_clang_format(args + [str(test_file)])
    assert ret == expected_retval


@pytest.mark.parametrize(
    ("args", "expected_retval"),
    (
        (
            [
                "--style=Google",
            ],
            1,
        ),
    ),
)
def test_run_clang_format_dry_run(args, expected_retval, tmp_path):
    # copy test file to tmp_path to prevent modifying repo data
    test_file = tmp_path / "main.c"
    ret, _ = run_clang_format(["--dry-run", str(test_file)])
    assert ret == -1  # Dry run should not fail


def test_main_empty_output():
    """Test main() function when clang-format returns error with empty output"""
    with patch(
        "cpp_linter_hooks.clang_format.run_clang_format"
    ) as mock_run_clang_format:
        # Mock failed run with empty output
        mock_run_clang_format.return_value = (1, "")

        with patch("builtins.print") as mock_print:
            result = main()

            # Should return 1 and print empty string
            assert result == 1
            mock_print.assert_called_once_with("")


def test_verbose_output(tmp_path, capsys):
    """Test that verbose mode produces debug output to stderr"""
    test_file = tmp_path / "test.c"
    test_file.write_text("#include <stdio.h>\nint main(){return 0;}")

    with patch("cpp_linter_hooks.clang_format.ensure_installed") as mock_ensure:
        mock_ensure.return_value = "/fake/clang-format"
        with patch(
            "cpp_linter_hooks.clang_format.run_subprocess_with_logging"
        ) as mock_run:
            mock_run.return_value = (0, "")

            # Test verbose mode
            retval, output = run_clang_format(
                ["--verbose", "--style=Google", str(test_file)]
            )

            # Check that debug messages were printed to stderr
            captured = capsys.readouterr()
            assert "[DEBUG] clang-format version:" in captured.err
            assert "[DEBUG] clang-format executable:" in captured.err

            # Verify that run_subprocess_with_logging was called correctly
            mock_run.assert_called_once()
            call_args = mock_run.call_args
            assert call_args[1]["tool_name"] == "clang-format"
            assert call_args[1]["verbose"] == True


def test_verbose_with_error(tmp_path, capsys):
    """Test verbose output when there's an error"""
    test_file = tmp_path / "test.c"

    with patch("cpp_linter_hooks.clang_format.ensure_installed") as mock_ensure:
        mock_ensure.return_value = "/fake/clang-format"
        with patch(
            "cpp_linter_hooks.clang_format.run_subprocess_with_logging"
        ) as mock_run:
            mock_run.return_value = (1, "error output\nerror in stderr")

            # Test verbose mode with error
            retval, output = run_clang_format(
                ["--verbose", "--style=Google", str(test_file)]
            )

            # Check return values
            assert retval == 1
            assert "error output" in output
            assert "error in stderr" in output

            # Verify that run_subprocess_with_logging was called correctly
            mock_run.assert_called_once()
            call_args = mock_run.call_args
            assert call_args[1]["tool_name"] == "clang-format"
            assert call_args[1]["verbose"] == True


def test_verbose_dry_run(tmp_path, capsys):
    """Test verbose output in dry-run mode"""
    test_file = tmp_path / "test.c"
    test_file.write_text("#include <stdio.h>\nint main(){return 0;}")

    with patch("cpp_linter_hooks.clang_format.ensure_installed") as mock_ensure:
        mock_ensure.return_value = "/fake/clang-format"
        with patch(
            "cpp_linter_hooks.clang_format.run_subprocess_with_logging"
        ) as mock_run:
            mock_run.return_value = (-1, "dry run output")

            # Test verbose dry-run mode
            retval, output = run_clang_format(
                ["--verbose", "--dry-run", str(test_file)]
            )

            # Check return values (dry-run should return -1)
            assert retval == -1
            assert "dry run output" in output

            # Verify that run_subprocess_with_logging was called correctly
            mock_run.assert_called_once()
            call_args = mock_run.call_args
            assert call_args[1]["tool_name"] == "clang-format"
            assert call_args[1]["verbose"] == True
            assert call_args[1]["dry_run"] == True
