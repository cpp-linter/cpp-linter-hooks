import subprocess
import sys
from argparse import ArgumentParser
from typing import Tuple

from cpp_linter_hooks.util import resolve_install, DEFAULT_CLANG_FORMAT_VERSION


parser = ArgumentParser()
parser.add_argument("--version", default=DEFAULT_CLANG_FORMAT_VERSION)
parser.add_argument(
    "-v", "--verbose", action="store_true", help="Enable verbose output"
)


def run_clang_format(args=None) -> Tuple[int, str]:
    """
    Run clang-format with the given arguments and return its exit code and combined output.
    
    Parses known hook options from `args`, optionally ensures a specific clang-format version is installed, builds and executes a clang-format command (modifying files in-place by default), and captures stdout and stderr merged into a single output string.
    
    Parameters:
        args (Optional[Sequence[str]]): Argument list to parse (typically sys.argv[1:]). If omitted, uses parser defaults.
    
    Returns:
        tuple[int, str]: A pair (retval, output) where `output` is the concatenation of stdout and stderr.
            `retval` is the subprocess return code, except:
            - `-1` when the command included `--dry-run` (special sentinel to indicate dry-run mode),
            - `1` when clang-format could not be found (FileNotFoundError converted to an exit-like code).
    """
    hook_args, other_args = parser.parse_known_args(args)
    if hook_args.version:
        resolve_install("clang-format", hook_args.version)
    command = ["clang-format", "-i"]

    # Add verbose flag if requested
    if hook_args.verbose:
        command.append("--verbose")

    command.extend(other_args)

    try:
        # Run the clang-format command with captured output
        sp = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
        )

        # Combine stdout and stderr for complete output
        output = (sp.stdout or "") + (sp.stderr or "")

        # Handle special case for dry-run mode
        if "--dry-run" in command:
            retval = -1  # Special code to identify dry-run mode
        else:
            retval = sp.returncode

        # Print verbose information if requested
        if hook_args.verbose:
            _print_verbose_info(command, retval, output)

        return retval, output

    except FileNotFoundError as e:
        return 1, str(e)


def _print_verbose_info(command: list, retval: int, output: str) -> None:
    """Print verbose debugging information to stderr."""
    print(f"Command executed: {' '.join(command)}", file=sys.stderr)
    print(f"Exit code: {retval}", file=sys.stderr)
    if output.strip():
        print(f"Output: {output}", file=sys.stderr)


def main() -> int:
    retval, output = run_clang_format()  # pragma: no cover

    # Print output for errors, but not for dry-run mode
    if retval != 0 and retval != -1 and output.strip():  # pragma: no cover
        print(output)

    # Convert dry-run special code to success
    return 0 if retval == -1 else retval  # pragma: no cover


if __name__ == "__main__":
    raise SystemExit(main())