import subprocess
from argparse import ArgumentParser
from typing import Tuple

from .util import ensure_installed, DEFAULT_CLANG_TIDY_VERSION


parser = ArgumentParser()
parser.add_argument("--version", default=DEFAULT_CLANG_TIDY_VERSION)


def run_clang_tidy(args=None) -> Tuple[int, str]:
    hook_args, other_args = parser.parse_known_args(args)
    tool_name = ensure_installed("clang-tidy", hook_args.version)
    command = [tool_name]
    command.extend(other_args)

    retval = 0
    output = ""
    try:
        sp = subprocess.run(command, stdout=subprocess.PIPE, encoding="utf-8")
        retval = sp.returncode
        output = sp.stdout
        if "warning:" in output or "error:" in output:
            retval = 1
        return retval, output
    except FileNotFoundError as e:
        error_msg = str(e)
        # Provide helpful error message for missing clang-tidy
        if "clang-tidy" in error_msg.lower():
            error_msg += "\nHint: The clang-tidy tool may not be installed or accessible."
            error_msg += f"\nThis hook will try to install clang-tidy version {hook_args.version}."
        return 1, error_msg
    except Exception as e:
        # Catch any other unexpected errors
        error_msg = f"Unexpected error running clang-tidy: {str(e)}"
        return 1, error_msg


def main() -> int:
    retval, output = run_clang_tidy()
    if retval != 0:
        print(output)
    return retval


if __name__ == "__main__":
    raise SystemExit(main())
