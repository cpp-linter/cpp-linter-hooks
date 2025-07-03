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


def run_clang_tidy(args=None) -> Tuple[int, str]:
    hook_args, other_args = parser.parse_known_args(args)
    path = ensure_installed("clang-tidy", hook_args.version)
    command = [str(path)]
    command.extend(other_args)

    verbose = hook_args.verbose

    # Log initial debug information
    debug_print(f"clang-tidy version: {hook_args.version}", verbose)
    debug_print(f"clang-tidy executable: {path}", verbose)

    # Use the utility function for subprocess execution
    return run_subprocess_with_logging(
        command=command, tool_name="clang-tidy", verbose=verbose, dry_run=False
    )


def main() -> int:
    retval, output = run_clang_tidy()
    if retval != 0:  # pragma: no cover
        print(output)  # pragma: no cover
    return retval


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
