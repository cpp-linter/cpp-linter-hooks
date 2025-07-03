from argparse import ArgumentParser
from typing import Tuple

from .util import (
    ensure_installed,
    DEFAULT_CLANG_VERSION,
    debug_print,
    run_subprocess_with_logging,
)


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

    # Log initial debug information
    debug_print(f"clang-format version: {hook_args.version}", verbose)
    debug_print(f"clang-format executable: {path}", verbose)

    # Check for dry-run mode
    dry_run = "--dry-run" in command

    # Use the utility function for subprocess execution
    return run_subprocess_with_logging(
        command=command, tool_name="clang-format", verbose=verbose, dry_run=dry_run
    )


def main() -> int:
    retval, output = run_clang_format()
    if retval != 0:  # pragma: no cover
        print(output)  # pragma: no cover
    return retval


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
