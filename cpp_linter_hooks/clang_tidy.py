import subprocess
import sys
from argparse import ArgumentParser
from pathlib import Path
from typing import Optional, Tuple

from cpp_linter_hooks.util import resolve_install, DEFAULT_CLANG_TIDY_VERSION

COMPILE_DB_SEARCH_DIRS = ["build", "out", "cmake-build-debug", "_build"]

parser = ArgumentParser()
parser.add_argument("--version", default=DEFAULT_CLANG_TIDY_VERSION)
parser.add_argument("--compile-commands", default=None, dest="compile_commands")
parser.add_argument("--no-compile-commands", action="store_true", dest="no_compile_commands")
parser.add_argument("-v", "--verbose", action="store_true")


def _find_compile_commands() -> Optional[str]:
    for d in COMPILE_DB_SEARCH_DIRS:
        if (Path(d) / "compile_commands.json").exists():
            return d
    return None


def run_clang_tidy(args=None) -> Tuple[int, str]:
    hook_args, other_args = parser.parse_known_args(args)
    if hook_args.version:
        resolve_install("clang-tidy", hook_args.version)

    # Covers both "-p ./build" (two tokens) and "-p=./build" (one token)
    has_p = any(a == "-p" or a.startswith("-p=") for a in other_args)

    compile_db_path = None
    if not hook_args.no_compile_commands:
        if hook_args.compile_commands:
            if has_p:
                print(
                    "Warning: --compile-commands ignored; -p already in args",
                    file=sys.stderr,
                )
            else:
                p = Path(hook_args.compile_commands)
                if not p.is_dir() or not (p / "compile_commands.json").exists():
                    return 1, (
                        f"--compile-commands: no compile_commands.json"
                        f" in '{hook_args.compile_commands}'"
                    )
                compile_db_path = hook_args.compile_commands
        elif not has_p:
            compile_db_path = _find_compile_commands()

    if compile_db_path:
        if hook_args.verbose:
            print(f"Using compile_commands.json from: {compile_db_path}", file=sys.stderr)
        other_args = ["-p", compile_db_path] + other_args

    command = ["clang-tidy"] + other_args

    retval = 0
    output = ""
    try:
        sp = subprocess.run(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding="utf-8"
        )
        retval = sp.returncode
        output = (sp.stdout or "") + (sp.stderr or "")
        if "warning:" in output or "error:" in output:
            retval = 1
        return retval, output
    except FileNotFoundError as stderr:
        retval = 1
        return retval, str(stderr)


def main() -> int:
    retval, output = run_clang_tidy()
    if retval != 0:
        print(output)
    return retval


if __name__ == "__main__":
    raise SystemExit(main())
