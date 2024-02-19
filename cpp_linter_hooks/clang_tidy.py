import subprocess
from pathlib import Path
import sys
from argparse import ArgumentParser
from typing import Tuple

from .util import ensure_installed, DEFAULT_CLANG_VERSION


BIN_PATH = Path(sys.executable).parent

parser = ArgumentParser()
parser.add_argument("--version", default=DEFAULT_CLANG_VERSION)



def run_clang_tidy(version, args) -> Tuple[int, str]:
    path = ensure_installed("clang-tidy", version)
    command = [str(path)]

    command.extend(args)

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
    main_args, other_args = parser.parse_known_args()
    retval, output = run_clang_tidy(version=main_args.version, args=other_args)
    if retval != 0:
        print(output)
    return retval


if __name__ == "__main__":
    raise SystemExit(main())
