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


def run_clang_format(args=None) -> Tuple[int, str]:
    hook_args, other_args = parser.parse_known_args(args)
    path = ensure_installed("clang-format", hook_args.version)
    command = [str(path), "-i"]
    command.extend(other_args)

    verbose = hook_args.verbose

    if verbose:
        print(f"[DEBUG] clang-format command: {' '.join(command)}", file=sys.stderr)
        print(f"[DEBUG] clang-format version: {hook_args.version}", file=sys.stderr)
        print(f"[DEBUG] clang-format executable: {path}", file=sys.stderr)

    retval = 0
    output = ""
    stderr_output = ""

    try:
        if "--dry-run" in command:
            sp = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                encoding="utf-8",
            )
            retval = -1  # Not a fail just identify it's a dry-run.
            output = sp.stdout
            stderr_output = sp.stderr

            if verbose:
                print("[DEBUG] Dry-run mode detected", file=sys.stderr)
                print(
                    f"[DEBUG] Exit code: {sp.returncode} (converted to -1 for dry-run)",
                    file=sys.stderr,
                )
        else:
            sp = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                encoding="utf-8",
            )
            retval = sp.returncode
            output = sp.stdout
            stderr_output = sp.stderr

            if verbose:
                print(f"[DEBUG] Exit code: {retval}", file=sys.stderr)

        # Combine stdout and stderr for comprehensive output
        combined_output = ""
        if output:
            combined_output += output
        if stderr_output:
            if combined_output:
                combined_output += "\n"
            combined_output += stderr_output

        if verbose and (output or stderr_output):
            print(f"[DEBUG] stdout: {repr(output)}", file=sys.stderr)
            print(f"[DEBUG] stderr: {repr(stderr_output)}", file=sys.stderr)

        return retval, combined_output

    except FileNotFoundError as error:
        retval = 1
        error_msg = f"clang-format executable not found: {error}"

        if verbose:
            print(f"[DEBUG] FileNotFoundError: {error}", file=sys.stderr)
            print(f"[DEBUG] Command attempted: {' '.join(command)}", file=sys.stderr)

        return retval, error_msg


def main() -> int:
    retval, output = run_clang_format()
    if retval != 0:  # pragma: no cover
        print(output)  # pragma: no cover
    return retval


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
