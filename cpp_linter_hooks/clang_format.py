"""Pre-commit hook wrapper for clang-format."""

import subprocess
import sys
from argparse import ArgumentParser

from cpp_linter_hooks.util import resolve_install_with_diagnostics, turns_on

parser = ArgumentParser()
parser.add_argument(
    "--version",
    default=None,
    help=(
        "Version of clang-format to install and run; defaults to the latest "
        "stable wheel on PyPI"
    ),
)
parser.add_argument(
    "-v", "--verbose", action="store_true", help="Enable verbose output"
)

# clang-format's spellings of --dry-run and --Werror.
DRY_RUN_OPTIONS = ("-n", "-dry-run", "--dry-run")
WERROR_OPTIONS = ("-Werror", "--Werror")


def run_clang_format(args=None) -> tuple[int, str]:
    """Run clang-format with hook-specific arguments removed."""
    hook_args, other_args = parser.parse_known_args(args)
    tool_path, version_error = resolve_install_with_diagnostics(
        "clang-format", hook_args.version, hook_args.verbose
    )
    if version_error is not None:
        return 1, version_error
    # Run the executable that was resolved, not whatever comes first on PATH.
    command = [str(tool_path) if tool_path else "clang-format", "-i"]

    # Add verbose flag if requested
    if hook_args.verbose:
        command.append("--verbose")

    # Auto-inject --Werror when --dry-run (or -n) is used, so clang-format returns
    # non-zero when formatting changes are needed (mirrors-clang-format behavior).
    # A --Werror the user set, even --Werror=false, is kept as it is. It goes
    # before the user's arguments, which may end the options with "--".
    if turns_on(other_args, DRY_RUN_OPTIONS) and not any(
        arg.partition("=")[0] in WERROR_OPTIONS for arg in other_args
    ):
        command.append("--Werror")

    command.extend(other_args)

    try:
        # Run the clang-format command with captured output
        sp = subprocess.run(
            command,
            capture_output=True,
            encoding="utf-8",
            # clang-format prints source lines, which may not be UTF-8.
            errors="replace",
            check=False,
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
    retval, output = run_clang_format()

    if retval != 0 and output.strip():
        print(output)

    return retval


if __name__ == "__main__":
    raise SystemExit(main())
