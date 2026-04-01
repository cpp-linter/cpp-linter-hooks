from concurrent.futures import ThreadPoolExecutor
import subprocess
import sys
from argparse import ArgumentParser, ArgumentTypeError
from pathlib import Path
from typing import List, Optional, Tuple

from cpp_linter_hooks.util import resolve_install, DEFAULT_CLANG_TIDY_VERSION

COMPILE_DB_SEARCH_DIRS = ["build", "out", "cmake-build-debug", "_build"]
SOURCE_FILE_SUFFIXES = {
    ".c",
    ".cc",
    ".cp",
    ".cpp",
    ".cxx",
    ".c++",
    ".cu",
    ".cuh",
    ".h",
    ".hh",
    ".hpp",
    ".hxx",
    ".h++",
    ".ipp",
    ".inl",
    ".ixx",
    ".tpp",
    ".txx",
}


def _positive_int(value: str) -> int:
    jobs = int(value)
    if jobs < 1:
        raise ArgumentTypeError("--jobs must be greater than 0")
    return jobs

parser = ArgumentParser()
parser.add_argument("--version", default=DEFAULT_CLANG_TIDY_VERSION)
parser.add_argument("--compile-commands", default=None, dest="compile_commands")
parser.add_argument(
    "--no-compile-commands", action="store_true", dest="no_compile_commands"
)
parser.add_argument("-j", "--jobs", type=_positive_int, default=1)
parser.add_argument("-v", "--verbose", action="store_true")


def _find_compile_commands() -> Optional[str]:
    for d in COMPILE_DB_SEARCH_DIRS:
        if (Path(d) / "compile_commands.json").exists():
            return d
    return None


def _resolve_compile_db(
    hook_args, other_args
) -> Tuple[Optional[str], Optional[Tuple[int, str]]]:
    """Resolve the compile_commands.json directory to pass as -p to clang-tidy.

    Returns (db_path, None) on success or (None, (retval, message)) on error.
    """
    if hook_args.no_compile_commands:
        return None, None

    # Covers both "-p ./build" (two tokens) and "-p=./build" (one token)
    has_p = any(a == "-p" or a.startswith("-p=") for a in other_args)

    if hook_args.compile_commands:
        if has_p:
            print(
                "Warning: --compile-commands ignored; -p already in args",
                file=sys.stderr,
            )
            return None, None
        p = Path(hook_args.compile_commands)
        if not p.is_dir() or not (p / "compile_commands.json").exists():
            return None, (
                1,
                f"--compile-commands: no compile_commands.json"
                f" in '{hook_args.compile_commands}'",
            )
        return hook_args.compile_commands, None

    if not has_p:
        return _find_compile_commands(), None

    return None, None


def _exec_clang_tidy(command) -> Tuple[int, str]:
    """Run clang-tidy and return (retval, output)."""
    try:
        sp = subprocess.run(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding="utf-8"
        )
        output = (sp.stdout or "") + (sp.stderr or "")
        retval = (
            1 if sp.returncode != 0 or "warning:" in output or "error:" in output else 0
        )
        return retval, output
    except FileNotFoundError as e:
        return 1, str(e)


def _looks_like_source_file(path: str) -> bool:
    return Path(path).suffix.lower() in SOURCE_FILE_SUFFIXES


def _split_source_files(args: List[str]) -> Tuple[List[str], List[str]]:
    split_idx = len(args)
    source_files: List[str] = []
    for idx in range(len(args) - 1, -1, -1):
        if not _looks_like_source_file(args[idx]):
            break
        source_files.append(args[idx])
        split_idx = idx
    return args[:split_idx], list(reversed(source_files))


def _combine_outputs(results: List[Tuple[int, str]]) -> str:
    return "\n".join(output.rstrip("\n") for _, output in results if output)


def _exec_parallel_clang_tidy(
    command_prefix: List[str], source_files: List[str], jobs: int
) -> Tuple[int, str]:
    def run_file(source_file: str) -> Tuple[int, str]:
        return _exec_clang_tidy(command_prefix + [source_file])

    with ThreadPoolExecutor(max_workers=min(jobs, len(source_files))) as executor:
        results = list(executor.map(run_file, source_files))

    retval = 1 if any(retval != 0 for retval, _ in results) else 0
    return retval, _combine_outputs(results)


def run_clang_tidy(args=None) -> Tuple[int, str]:
    hook_args, other_args = parser.parse_known_args(args)
    if hook_args.version:
        resolve_install("clang-tidy", hook_args.version)

    compile_db_path, error = _resolve_compile_db(hook_args, other_args)
    if error is not None:
        return error

    if compile_db_path:
        if hook_args.verbose:
            print(
                f"Using compile_commands.json from: {compile_db_path}", file=sys.stderr
            )
        other_args = ["-p", compile_db_path] + other_args

    clang_tidy_args, source_files = _split_source_files(other_args)

    # Parallel execution is unsafe when arguments include flags that write to a
    # shared output path (e.g., --export-fixes fixes.yaml). In that case, force
    # serial execution to avoid concurrent writes/overwrites.
    unsafe_parallel = any(
        arg == "--export-fixes" or arg.startswith("--export-fixes=")
        for arg in clang_tidy_args
    )

    if hook_args.jobs > 1 and len(source_files) > 1 and not unsafe_parallel:
        return _exec_parallel_clang_tidy(
            ["clang-tidy"] + clang_tidy_args, source_files, hook_args.jobs
        )

    return _exec_clang_tidy(["clang-tidy"] + other_args)


def main() -> int:
    retval, output = run_clang_tidy()
    if retval != 0:
        print(output)
    return retval


if __name__ == "__main__":
    raise SystemExit(main())
