import sys

from cpp_linter_hooks.util import check_installed
from cpp_linter_hooks.util import get_expect_version


clang_tools = ['clang-format', 'clang-tidy']
args = list(sys.argv[1:])

expect_version = get_expect_version(args)

for tool in clang_tools:
    if expect_version:
        retval = check_installed(tool, version=expect_version)
    else:
        retval = check_installed(tool)

    if retval != 0:
        raise SystemError("clang_tools not found. exit!")
