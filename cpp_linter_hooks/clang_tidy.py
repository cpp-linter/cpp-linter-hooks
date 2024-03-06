import subprocess
from argparse import ArgumentParser
from typing import Tuple

from .util import ensure_installed, DEFAULT_CLANG_VERSION


parser = ArgumentParser()
parser.add_argument("--version", default=DEFAULT_CLANG_VERSION)


def run_clang_tidy(args=None) -> Tuple[int, str]:
    hook_args, other_args = parser.parse_known_args(args)
    path = ensure_installed("clang-tidy", hook_args.version)
    command = [str(path)]
    command.extend(other_args)

    retval = 0
    output = ""
    try:
        sp = subprocess.run(command, stdout=subprocess.PIPE, encoding='utf-8')
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
