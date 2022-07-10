from unittest.mock import patch

import pytest

from cpp_linter_hooks.clang_format import run_clang_format


@pytest.mark.parametrize(
    ('args', 'expected_retval'), (
        (['clang-format', '-i', '--style=Google', 'testing/main.c'], 0),
        (['clang-format', '-i', '--style=Google', '--version=13', 'testing/main.c'], 0),
    ),
)
@patch('cpp_linter_hooks.clang_format.subprocess.run')
def test_run_clang_format_valid(mock_subprocess_run, args, expected_retval):
    mock_subprocess_run.return_value = expected_retval
    ret = run_clang_format(args)
    assert ret == expected_retval


@pytest.mark.parametrize(
    ('args', 'expected_retval'), (
        (['clang-format', '-i', '--style=Google', 'abc/def.c'], 1),
        (['clang-format', '-i', '--style=Google', '--version=13', 'abc/def.c'], 1),
    ),
)
@patch('cpp_linter_hooks.clang_format.subprocess.run', side_effect=FileNotFoundError)
def test_run_clang_format_invalid(mock_subprocess_run, args, expected_retval):
    mock_subprocess_run.return_value = expected_retval
    try:
        ret = run_clang_format(args)
    except FileNotFoundError:
        assert ret == expected_retval
