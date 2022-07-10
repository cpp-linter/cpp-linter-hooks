import sys
from cpp_linter_hooks.util import get_expect_version, check_installed


clang_tools = ['clang-format', 'clang-tidy']
args = list(sys.argv[1:])

expect_version = get_expect_version(args)

for tool in clang_tools:
    if expect_version:
        check_installed(tool, version=expect_version)
    else:
        check_installed(tool)
