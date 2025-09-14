import subprocess
import sys
import os
import shutil
from argparse import ArgumentParser
from typing import Tuple

from .util import ensure_installed, DEFAULT_CLANG_FORMAT_VERSION


def _check_for_conflicts() -> None:
    """Check for potential conflicts with PyPI clang-format packages."""
    # Check if there's a conflicting clang-format script
    clang_format_path = shutil.which("clang-format")
    if clang_format_path:
        try:
            # Try to read the script to see if it contains the problematic import
            with open(clang_format_path, 'r', encoding='utf-8') as f:
                content = f.read()
                if "from clang_format import clang_format" in content:
                    print(
                        "WARNING: Detected conflicting clang-format script at: " + clang_format_path,
                        file=sys.stderr
                    )
                    print(
                        "This may cause ImportError. Consider removing conflicting packages:",
                        file=sys.stderr
                    )
                    print(
                        "  pip uninstall clang-format clang-tidy clang-tools",
                        file=sys.stderr
                    )
                    print(
                        "For more help: https://github.com/cpp-linter/cpp-linter-hooks#importerror-cannot-import-name-clang_format-from-clang_format",
                        file=sys.stderr
                    )
        except (IOError, UnicodeDecodeError):
            # If we can't read the file, ignore the check
            pass


parser = ArgumentParser()
parser.add_argument("--version", default=DEFAULT_CLANG_FORMAT_VERSION)
parser.add_argument(
    "-v", "--verbose", action="store_true", help="Enable verbose output"
)


def run_clang_format(args=None) -> Tuple[int, str]:
    hook_args, other_args = parser.parse_known_args(args)
    tool_name = ensure_installed("clang-format", hook_args.version)
    command = [tool_name, "-i"]

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
        error_msg = str(e)
        # Provide helpful error message for missing clang-format
        if "clang-format" in error_msg.lower():
            error_msg += "\nHint: The clang-format tool may not be installed or accessible."
            error_msg += f"\nThis hook will try to install clang-format version {hook_args.version}."
        return 1, error_msg
    except Exception as e:
        # Catch any other unexpected errors
        error_msg = f"Unexpected error running clang-format: {str(e)}"
        return 1, error_msg


def _print_verbose_info(command: list, retval: int, output: str) -> None:
    """Print verbose debugging information to stderr."""
    print(f"Command executed: {' '.join(command)}", file=sys.stderr)
    print(f"Exit code: {retval}", file=sys.stderr)
    if output.strip():
        print(f"Output: {output}", file=sys.stderr)


def main() -> int:
    # Check for potential conflicts early
    if os.environ.get("CLANG_FORMAT_HOOK_DEBUG"):
        _check_for_conflicts()
    
    retval, output = run_clang_format()  # pragma: no cover

    # Print output for errors, but not for dry-run mode
    if retval != 0 and retval != -1 and output.strip():  # pragma: no cover
        print(output)

    # Convert dry-run special code to success
    return 0 if retval == -1 else retval  # pragma: no cover


if __name__ == "__main__":
    raise SystemExit(main())
