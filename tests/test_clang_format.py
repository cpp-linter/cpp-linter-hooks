import pytest
from pathlib import Path

from cpp_linter_hooks.clang_format import run_clang_format


@pytest.mark.parametrize(
    ('args', 'expected_retval'), (
        (['--style=Google'], (0, "")),
        (['--style=Google', '--version=16'], (0, "")),
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
    ('args', 'expected_retval'), (
        (['--style=Google',], 1),
        (['--style=Google', '--version=16'], 1),
    ),
)
def test_run_clang_format_invalid(args, expected_retval, tmp_path):
    # non existent file
    test_file = tmp_path / "main.c"

    ret, _ = run_clang_format(args + [str(test_file)])
    assert ret == expected_retval
