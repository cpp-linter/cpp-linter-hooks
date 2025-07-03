import pytest
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

from cpp_linter_hooks.clang_tidy import run_clang_tidy


@pytest.fixture(scope="function")
def generate_compilation_database():
    subprocess.run(["mkdir", "-p", "build"])
    subprocess.run(["cmake", "-Bbuild", "testing/"])
    subprocess.run(["cmake", "-Bbuild", "testing/"])


@pytest.mark.parametrize(
    ("args", "expected_retval"),
    (
        (['--checks="boost-*"'], 1),
        (['--checks="boost-*"', "--version=16"], 1),
        (['--checks="boost-*"', "--version=17"], 1),
        (['--checks="boost-*"', "--version=18"], 1),
        (['--checks="boost-*"', "--version=19"], 1),
        (['--checks="boost-*"', "--version=20"], 1),
    ),
)
def test_run_clang_tidy_valid(args, expected_retval):
    # copy test file to tmp_path to prevent modifying repo data
    test_file = Path("testing/main.c")
    test_file.write_bytes(Path("testing/main.c").read_bytes())
    ret, output = run_clang_tidy(args + [str(test_file)])
    assert ret == expected_retval
    print(output)


@pytest.mark.parametrize(
    ("args", "expected_retval"),
    (
        (['--checks="boost-*"'], 1),
        (['--checks="boost-*"', "--version=16"], 1),
        (['--checks="boost-*"', "--version=17"], 1),
        (['--checks="boost-*"', "--version=18"], 1),
        (['--checks="boost-*"', "--version=19"], 1),
        (['--checks="boost-*"', "--version=20"], 1),
    ),
)
def test_run_clang_tidy_invalid(args, expected_retval, tmp_path):
    # non existent file
    test_file = tmp_path / "main.c"

    ret, _ = run_clang_tidy(args + [str(test_file)])
    assert ret == expected_retval


def test_main_as_script():
    """Test the if __name__ == '__main__' behavior"""
    with patch("cpp_linter_hooks.clang_tidy.main") as mock_main:
        mock_main.return_value = 42

        # This would normally raise SystemExit, but we're mocking main()
        with pytest.raises(SystemExit) as exc_info:
            # Simulate running the script directly
            exec("if __name__ == '__main__': raise SystemExit(main())")

        assert exc_info.value.code == 42


def test_verbose_output(tmp_path, capsys):
    """Test that verbose mode produces debug output to stderr"""
    test_file = tmp_path / "test.c"
    test_file.write_text("#include <stdio.h>\nint main(){return 0;}")

    with patch("cpp_linter_hooks.clang_tidy.ensure_installed") as mock_ensure:
        mock_ensure.return_value = "/fake/clang-tidy"
        with patch(
            "cpp_linter_hooks.clang_tidy.run_subprocess_with_logging"
        ) as mock_run:
            mock_run.return_value = (0, "")

            # Test verbose mode
            retval, output = run_clang_tidy(
                ["--verbose", "--checks=boost-*", str(test_file)]
            )

            # Check that debug messages were printed to stderr
            captured = capsys.readouterr()
            assert "[DEBUG] clang-tidy version:" in captured.err
            assert "[DEBUG] clang-tidy executable:" in captured.err

            # Verify that run_subprocess_with_logging was called correctly
            mock_run.assert_called_once()
            call_args = mock_run.call_args
            assert call_args[1]["tool_name"] == "clang-tidy"
            assert call_args[1]["verbose"] == True


def test_verbose_with_warnings(tmp_path, capsys):
    """Test verbose output when there are warnings"""
    test_file = tmp_path / "test.c"

    with patch("cpp_linter_hooks.clang_tidy.ensure_installed") as mock_ensure:
        mock_ensure.return_value = "/fake/clang-tidy"
        with patch(
            "cpp_linter_hooks.clang_tidy.run_subprocess_with_logging"
        ) as mock_run:
            mock_run.return_value = (
                1,
                "warning: some issue found\ncompilation database warning",
            )

            # Test verbose mode with warnings
            retval, output = run_clang_tidy(
                ["--verbose", "--checks=boost-*", str(test_file)]
            )

            # Check return values (should be 1 due to warnings)
            assert retval == 1
            assert "warning: some issue found" in output
            assert "compilation database warning" in output

            # Verify that run_subprocess_with_logging was called correctly
            mock_run.assert_called_once()
            call_args = mock_run.call_args
            assert call_args[1]["tool_name"] == "clang-tidy"
            assert call_args[1]["verbose"] == True


def test_verbose_with_file_not_found(capsys):
    """Test verbose output when clang-tidy executable is not found"""
    with patch("cpp_linter_hooks.clang_tidy.ensure_installed") as mock_ensure:
        mock_ensure.return_value = "/fake/clang-tidy"
        with patch(
            "cpp_linter_hooks.clang_tidy.run_subprocess_with_logging"
        ) as mock_run:
            mock_run.return_value = (
                1,
                "clang-tidy executable not found: No such file or directory",
            )

            # Test verbose mode with FileNotFoundError
            retval, output = run_clang_tidy(["--verbose", "--checks=boost-*", "test.c"])

            # Check return values
            assert retval == 1
            assert "clang-tidy executable not found" in output

            # Verify that run_subprocess_with_logging was called correctly
            mock_run.assert_called_once()
            call_args = mock_run.call_args
            assert call_args[1]["tool_name"] == "clang-tidy"
            assert call_args[1]["verbose"] == True
