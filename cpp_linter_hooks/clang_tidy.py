import subprocess
import sys
from argparse import ArgumentParser
from typing import Tuple

from .util import ensure_installed, DEFAULT_CLANG_VERSION


parser = ArgumentParser()
parser.add_argument("--version", default=DEFAULT_CLANG_VERSION)
parser.add_argument(
    "-v", "--verbose", action="store_true", help="Enable verbose output"
)


def run_clang_tidy(args=None) -> Tuple[int, str]:
    hook_args, other_args = parser.parse_known_args(args)
    path = ensure_installed("clang-tidy", hook_args.version)
    command = [str(path)]
    command.extend(other_args)

    verbose = hook_args.verbose

    if verbose:
        print(f"[DEBUG] clang-tidy command: {' '.join(command)}", file=sys.stderr)
        print(f"[DEBUG] clang-tidy version: {hook_args.version}", file=sys.stderr)
        print(f"[DEBUG] clang-tidy executable: {path}", file=sys.stderr)

    retval = 0
    output = ""
    stderr_output = ""

    try:
        sp = subprocess.run(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding="utf-8"
        )
        retval = sp.returncode
        output = sp.stdout
        stderr_output = sp.stderr

        if verbose:
            print(f"[DEBUG] Exit code: {retval}", file=sys.stderr)
            print(f"[DEBUG] stdout: {repr(output)}", file=sys.stderr)
            print(f"[DEBUG] stderr: {repr(stderr_output)}", file=sys.stderr)

        # Combine stdout and stderr for comprehensive output
        combined_output = ""
        if output:
            combined_output += output
        if stderr_output:
            if combined_output:
                combined_output += "\n"
            combined_output += stderr_output

        # Check for warnings or errors in the combined output
        if "warning:" in combined_output or "error:" in combined_output:
            retval = 1
            if verbose:
                print(
                    "[DEBUG] Found warnings/errors, setting exit code to 1",
                    file=sys.stderr,
                )

        return retval, combined_output

    except FileNotFoundError as error:
        retval = 1
        error_msg = f"clang-tidy executable not found: {error}"

        if verbose:
            print(f"[DEBUG] FileNotFoundError: {error}", file=sys.stderr)
            print(f"[DEBUG] Command attempted: {' '.join(command)}", file=sys.stderr)

        return retval, error_msg


def main() -> int:
    retval, output = run_clang_tidy()
    if retval != 0:  # pragma: no cover
        print(output)  # pragma: no cover
    return retval


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
