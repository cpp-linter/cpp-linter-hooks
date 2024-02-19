import subprocess
from pathlib import Path
import sys
from argparse import ArgumentParser

from .util import ensure_installed, DEFAULT_CLANG_VERSION


BIN_PATH = Path(sys.executable).parent

parser = ArgumentParser()
parser.add_argument("--version", default=DEFAULT_CLANG_VERSION)


def run_clang_format(version, args) -> int:
    command = [f'{BIN_PATH}/clang-format-{version}', '-i']
    command.extend(args)

    retval = 0
    output = ""
    try:
        if "--dry-run" in command:
            sp = subprocess.run(command, stdout=subprocess.PIPE)
            retval = -1  # Not a fail just identify it's a dry-run.
            output = sp.stdout.decode("utf-8")
        else:
            retval = subprocess.run(command, stdout=subprocess.PIPE).returncode
        return retval, output
    except FileNotFoundError as stderr:
        retval = 1
        return retval, stderr


def main() -> int:
    main_args, other_args = parser.parse_known_args()
    ensure_installed("clang-format", main_args.version)
    retval, output = run_clang_format(version=main_args.version, args=other_args)
    if retval != 0:
        print(output)
    return retval


if __name__ == "__main__":
    raise SystemExit(main())
