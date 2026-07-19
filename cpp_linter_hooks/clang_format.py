"""Pre-commit hook wrapper for clang-format."""

import subprocess
import sys
from argparse import ArgumentParser
from typing import Tuple

from cpp_linter_hooks.util import resolve_install_with_diagnostics


parser = ArgumentParser()
parser.add_argument("--version", default=None)
parser.add_argument(
    "-v", "--verbose", action="store_true", help="Enable verbose output"
)


def run_clang_format(args=None) -> Tuple[int, str]:
    """Run clang-format with hook-specific arguments removed."""
    hook_args, other_args = parser.parse_known_args(args)
    _, version_error = resolve_install_with_diagnostics(
        "clang-format", hook_args.version, hook_args.verbose
    )
    if version_error is not None:
        return 1, version_error
    command = ["clang-format", "-i"]

    # Add verbose flag if requested
    if hook_args.verbose:
        command.append("--verbose")

    command.extend(other_args)

    # Auto-inject --Werror when --dry-run is used, so clang-format returns
    # non-zero when formatting changes are needed (mirrors-clang-format behavior).
    if "--dry-run" in command and "--Werror" not in command:
        command.append("--Werror")

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
    """Run clang-format as a command-line entry point."""
    retval, output = run_clang_format()  # pragma: no cover

    if retval != 0 and output.strip():  # pragma: no cover
        print(output)

    return retval  # pragma: no cover


if __name__ == "__main__":
    raise SystemExit(main())
