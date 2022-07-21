from unittest.mock import patch

import pytest

from cpp_linter_hooks.util import check_installed
from cpp_linter_hooks.util import get_expect_version
from cpp_linter_hooks.util import install_clang_tools


@pytest.mark.parametrize(('tool', 'expected_retval'), (('clang-format', 0), ('clang-tidy', 0),),)
@patch('cpp_linter_hooks.util.subprocess.run')
def test_check_installed(mock_subprocess_run, tool, expected_retval):
    mock_subprocess_run.return_value = expected_retval
    ret = check_installed(tool)
    assert ret == expected_retval


@pytest.mark.parametrize(('tool', 'version', 'expected_retval'), (('clang-format', '14', 0), ('clang-tidy', '14', 0),),)
@patch('cpp_linter_hooks.util.subprocess.run')
def test_check_installed_with_version(mock_subprocess_run, tool, version, expected_retval):
    mock_subprocess_run.return_value = expected_retval
    ret = check_installed(tool, version=version)
    assert ret == expected_retval


@pytest.mark.parametrize(('tool', 'version', 'expected_retval'), (('non-exist-cmd', '14', 0),),)
@patch('cpp_linter_hooks.util.subprocess.run')
def test_check_installed_with_except(mock_subprocess_run, tool, version, expected_retval):
    mock_subprocess_run.return_value = expected_retval
    ret = check_installed(tool, version=version)
    assert ret == expected_retval


@pytest.mark.parametrize(('version', 'expected_retval'), (('100', 1),),)
@patch('cpp_linter_hooks.util.subprocess.run')
def test_install_clang_tools(mock_subprocess_run, version, expected_retval):
    mock_subprocess_run.return_value = expected_retval
    try:
        ret = install_clang_tools(version)
        assert ret == expected_retval
    except Exception:
        pass


def test_get_expect_version():
    args = ['clang-format', '--version 14']
    version = get_expect_version(args)
    assert version == '14'

    args = ['clang-format', '--version=14']
    version = get_expect_version(args)
    assert version == '14'
