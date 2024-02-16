import subprocess
from pathlib import Path
import sys
from argparse import ArgumentParser

from .util import ensure_installed


BIN_PATH = Path(sys.executable).parent

parser = ArgumentParser()
parser.add_argument("--version")



def run_clang_tidy(version, args) -> int:
    if version:
        command = [f'{BIN_PATH}/clang-tidy-{version}']
    else:
        command = [f"{BIN_PATH}/clang-tidy"]

    command.extend(args)

    retval = 0
    output = ""
    try:
        sp = subprocess.run(command, stdout=subprocess.PIPE)
        retval = sp.returncode
        output = sp.stdout.decode("utf-8")
        if "warning:" in output or "error:" in output:
            retval = 1
        return retval, output
    except FileNotFoundError as stderr:
        retval = 1
        return retval, stderr


def main() -> int:
    main_args, other_args = parser.parse_known_args()
    ensure_installed("clang-tidy", main_args.version)
    retval, output = run_clang_tidy(version=main_args.version, args=other_args)
    if retval != 0:
        print(output)
    return retval


if __name__ == "__main__":
    raise SystemExit(main())
