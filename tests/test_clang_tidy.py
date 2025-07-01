import pytest
import subprocess
from pathlib import Path

from cpp_linter_hooks.clang_tidy import run_clang_tidy


@pytest.fixture(scope='function')
def generate_compilation_database():
    subprocess.run(['mkdir', '-p', 'build'])
    subprocess.run(['cmake', '-Bbuild', 'testing/'])
    subprocess.run(['cmake', '-Bbuild', 'testing/'])


@pytest.mark.parametrize(
    ('args', 'expected_retval'), (
        (['--checks="boost-*"'], 1),
        (['--checks="boost-*"', '--version=16'], 1),
        (['--checks="boost-*"', '--version=17'], 1),
        (['--checks="boost-*"', '--version=18'], 1),
        (['--checks="boost-*"', '--version=19'], 1),
        (['--checks="boost-*"', '--version=20'], 1),
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
    ('args', 'expected_retval'), (
        (['--checks="boost-*"'], 1),
        (['--checks="boost-*"', '--version=16'], 1),
        (['--checks="boost-*"', '--version=17'], 1),
        (['--checks="boost-*"', '--version=18'], 1),
        (['--checks="boost-*"', '--version=19'], 1),
        (['--checks="boost-*"', '--version=20'], 1),
    ),
)
def test_run_clang_tidy_invalid(args, expected_retval, tmp_path):
    # non existent file
    test_file = tmp_path / "main.c"

    ret, _ = run_clang_tidy(args + [str(test_file)])
    assert ret == expected_retval
