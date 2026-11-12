"""Pre-commit hook wrapper for clang-format."""

import os
import subprocess
import sys
from argparse import ArgumentParser

from cpp_linter_hooks.changed_lines import changed_lines
from cpp_linter_hooks.util import file_argument, resolve_install_with_diagnostics

# No abbreviations: clang-format's own --lines must not be read as a short
# form of --lines-changed-only.
parser = ArgumentParser(allow_abbrev=False)
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
parser.add_argument(
    "--lines-changed-only",
    action="store_true",
    help=(
        "Format only the lines that the commit or push changes; every line "
        "is formatted when the changed lines are unknown, for example with "
        "--all-files"
    ),
)


def _split_files(args: list[str]) -> tuple[list[str], list[str]]:
    """Split clang-format options from the files that pre-commit appends.

    pre-commit passes only existing files, so the files are the existing files
    at the end. An option that takes its value as the next argument, such as
    ``--style Google``, ends them because the value is not a file.
    """
    split = len(args)
    while split > 0 and os.path.isfile(args[split - 1]):
        split -= 1
    return args[:split], args[split:]


def _changed_lines_commands(command: list[str], args: list[str]) -> list[list[str]]:
    """Return one clang-format command per file, limited to its changed lines.

    clang-format takes ``--lines`` for one file at a time. A file with no
    added lines needs no run. When the changed lines are unknown, or the
    arguments already name lines, the one command for all files is returned.
    """
    options, files = _split_files(args)
    if any(a.lstrip("-").split("=")[0] == "lines" for a in options):
        return [[*command, *args]]
    lines = changed_lines(files)
    if lines is None:
        return [[*command, *args]]
    return [
        [*command, *options, *(f"--lines={a}:{b}" for a, b in lines[f]), f]
        for f in files
        if lines[f]
    ]


def run_clang_format(args=None) -> tuple[int, str]:
    """Run clang-format with hook-specific arguments removed."""
    hook_args, other_args = parser.parse_known_args(args)
    other_args = [file_argument(arg) for arg in other_args]
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
    if any(a in ("-n", "--dry-run") for a in other_args) and not any(
        a.startswith("--Werror") for a in other_args
    ):
        command.append("--Werror")

    commands = (
        _changed_lines_commands(command, other_args)
        if hook_args.lines_changed_only
        else [[*command, *other_args]]
    )

    retval, output = 0, ""
    try:
        for command in commands:
            sp = subprocess.run(
                command,
                capture_output=True,
                encoding="utf-8",
                # clang-format prints source lines, which may not be UTF-8.
                errors="replace",
                check=False,
            )
            # Combine stdout and stderr for complete output
            command_output = (sp.stdout or "") + (sp.stderr or "")
            if hook_args.verbose:
                _print_verbose_info(command, sp.returncode, command_output)
            retval = retval or sp.returncode
            output += command_output
    except FileNotFoundError as e:
        return 1, str(e)
    return retval, output


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
