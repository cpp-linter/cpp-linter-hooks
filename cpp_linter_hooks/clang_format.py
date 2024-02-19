import subprocess
from argparse import ArgumentParser
from typing import Tuple

from .util import ensure_installed, DEFAULT_CLANG_VERSION


parser = ArgumentParser()
parser.add_argument("--version", default=DEFAULT_CLANG_VERSION)


def run_clang_format(args=None) -> Tuple[int, str]:
    hook_args, other_args = parser.parse_known_args(args)
    path = ensure_installed("clang-format", hook_args.version)
    command = [str(path), '-i']
    command.extend(other_args)

    retval = 0
    output = ""
    try:
        if "--dry-run" in command:
            sp = subprocess.run(command, stdout=subprocess.PIPE, encoding="utf-8")
            retval = -1  # Not a fail just identify it's a dry-run.
            output = sp.stdout
        else:
            retval = subprocess.run(command, stdout=subprocess.PIPE).returncode
        return retval, output
    except FileNotFoundError as stderr:
        retval = 1
        return retval, str(stderr)


def main() -> int:
    retval, output = run_clang_format()
    if retval != 0:
        print(output)
    return retval


if __name__ == "__main__":
    raise SystemExit(main())
