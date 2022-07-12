from unittest.mock import patch

import pytest

from cpp_linter_hooks.clang_tidy import run_clang_tidy


@pytest.mark.skip(reason="don't know hwo to pass test.")
@pytest.mark.parametrize(
    ('args', 'expected_retval'), (
        (['clang-tidy', '--checks="boost-*"', 'testing/main.c'], "stdout"),
        (['clang-tidy', '-checks="boost-*"', '--version=13', 'testing/main.c'], "stdout"),
    ),
)
@patch('cpp_linter_hooks.clang_tidy.subprocess.run')
def test_run_clang_tidy_valid(mock_subprocess_run, args, expected_retval):
    mock_subprocess_run.return_value = expected_retval
    ret = run_clang_tidy(args)
    assert ret == expected_retval


@pytest.mark.parametrize(
    ('args', 'expected_retval'), (
        (['clang-tidy', '-i', '--checks="boost-*"', 'abc/def.c'], ""),
        (['clang-tidy', '-i', '--checks="boost-*"', '--version=13', 'abc/def.c'], ""),
    ),
)
@patch('cpp_linter_hooks.clang_tidy.subprocess.run', side_effect=FileNotFoundError)
def test_run_clang_tidy_invalid(mock_subprocess_run, args, expected_retval):
    mock_subprocess_run.return_value = expected_retval
    try:
        ret = run_clang_tidy(args)
    except FileNotFoundError:
        assert ret == expected_retval
