import pytest
from unittest.mock import patch
from cpp_linter_hooks.util import check_installed, get_expect_version


@pytest.mark.parametrize(
    ('tool', 'expected_retval'), (
        ('clang-format', 0),
        ('clang-tidy', 0),
    ),
)
@patch('cpp_linter_hooks.clang_format.subprocess.run')
def test_check_installed(mock_subprocess_run, tool, expected_retval):
    mock_subprocess_run.return_value = expected_retval
    ret = check_installed(tool)
    assert ret == expected_retval


@pytest.mark.parametrize(
    ('tool', 'version', 'expected_retval'), (
        ('clang-format', '14', 0),
        ('clang-tidy', '14', 0),
    ),
)
@patch('cpp_linter_hooks.clang_format.subprocess.run')
def test_check_installed_with_version(mock_subprocess_run, tool, version, expected_retval):
    mock_subprocess_run.return_value = expected_retval
    ret = check_installed(tool, version=version)
    assert ret == expected_retval


def test_get_expect_version():
    args = ['clang-format', '-i', '--style=Google', '--version=13']
    version = get_expect_version(args)
    assert version == '13'

    args = ['clang-format', '-i', '--style=Google', '--version = 13']
    version = get_expect_version(args)
    assert version == '13'

    args = ['clang-format', '-i', '--style=Google']
    version = get_expect_version(args)
    assert version == ""

    args = ['clang-format', '-i', '--install=13']
    version = get_expect_version(args)
    assert version == ""
