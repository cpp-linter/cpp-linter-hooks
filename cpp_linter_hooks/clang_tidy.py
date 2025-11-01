import subprocess
from argparse import ArgumentParser
from typing import Tuple

from cpp_linter_hooks.util import resolve_install, DEFAULT_CLANG_TIDY_VERSION


parser = ArgumentParser()
parser.add_argument("--version", default=DEFAULT_CLANG_TIDY_VERSION)


def run_clang_tidy(args=None) -> Tuple[int, str]:
    hook_args, other_args = parser.parse_known_args(args)
    if hook_args.version:
        resolve_install("clang-tidy", hook_args.version)
    command = ["clang-tidy"] + other_args

    retval = 0
    output = ""
    try:
        sp = subprocess.run(command, stdout=subprocess.PIPE, encoding="utf-8")
        retval = sp.returncode
        output = sp.stdout
        if "warning:" in output or "error:" in output:
            retval = 1
        return retval, output
    except FileNotFoundError as stderr:
        retval = 1
        return retval, str(stderr)


def main() -> int:
    retval, output = run_clang_tidy()
    if retval != 0:
        print(output)
    return retval


if __name__ == "__main__":
    raise SystemExit(main())
