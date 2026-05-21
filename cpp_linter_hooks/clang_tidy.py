from concurrent.futures import ThreadPoolExecutor
import subprocess
import sys
from argparse import ArgumentParser, ArgumentTypeError
from pathlib import Path
from typing import List, Optional, Tuple

from cpp_linter_hooks.util import resolve_install_with_diagnostics

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
COMPILE_COMMANDS_HINT = """\
Generate compile_commands.json with one of:
  CMake: cmake -S . -B build -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
  Meson: meson setup builddir
Then run clang-tidy with --compile-commands=build or --compile-commands=builddir."""

MSVC_HINT = """\
Windows/MSVC clang-tidy hints:
  - Run from a Visual Studio Developer Command Prompt, or call vcvars64.bat first.
  - Make sure the Windows SDK and MSVC include paths are visible in that shell.
  - For MSVC-style compile databases, try --extra-arg-before=--driver-mode=cl.
  - If using CMake, generate compile_commands.json from the same toolchain."""


def _positive_int(value: str) -> int:
    jobs = int(value)
    if jobs < 1:
        raise ArgumentTypeError("--jobs must be greater than 0")
    return jobs


parser = ArgumentParser()
parser.add_argument("--version", default=None)
parser.add_argument("--compile-commands", default=None, dest="compile_commands")
parser.add_argument(
    "--no-compile-commands", action="store_true", dest="no_compile_commands"
)
parser.add_argument("-j", "--jobs", type=_positive_int, default=1)
parser.add_argument("-v", "--verbose", action="store_true")
parser.add_argument("--fix", action="store_true", help="Apply fixes in place (-fix)")


def _find_compile_commands() -> Optional[str]:
    for d in COMPILE_DB_SEARCH_DIRS:
        if (Path(d) / "compile_commands.json").exists():
            return d
    return None


def _compile_commands_not_found_message(path: Optional[str] = None) -> str:
    if path is None:
        return "No compile_commands.json was found in common build directories.\n\n" + (
            COMPILE_COMMANDS_HINT
        )
    return (
        f"--compile-commands: no compile_commands.json in '{path}'.\n\n"
        f"{COMPILE_COMMANDS_HINT}"
    )


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
                _compile_commands_not_found_message(hook_args.compile_commands),
            )
        return hook_args.compile_commands, None

    if not has_p:
        return _find_compile_commands(), None

    return None, None


def _looks_like_compile_db_error(output: str) -> bool:
    lower_output = output.lower()
    compile_db_error = "compile_commands.json" in lower_output and any(
        pattern in lower_output
        for pattern in (
            "not found",
            "no such file",
            "missing",
            "error",
            "could not",
        )
    )
    return compile_db_error or any(
        pattern in lower_output
        for pattern in (
            "error while trying to load a compilation database",
            "could not auto-detect compilation database",
            "no compilation database found",
        )
    )


def _looks_like_msvc_error(output: str) -> bool:
    lower_output = output.lower()
    cl_driver_error = "cl.exe" in lower_output and any(
        pattern in lower_output
        for pattern in ("not found", "doesn't exist", "unable to execute")
    )
    msvc_patterns = (
        "unable to find a visual studio installation",
        "visual studio installation",
        "vcruntime.h",
        "windows.h' file not found",
        "sal.h' file not found",
        "msvc",
        "unknown argument: '/",
        "unsupported option '/",
        "argument unused during compilation: '/",
    )
    return cl_driver_error or any(pattern in lower_output for pattern in msvc_patterns)


def _append_guidance(output: str) -> str:
    hints: List[str] = []
    if _looks_like_compile_db_error(output) and COMPILE_COMMANDS_HINT not in output:
        hints.append(COMPILE_COMMANDS_HINT)
    if _looks_like_msvc_error(output) and MSVC_HINT not in output:
        hints.append(MSVC_HINT)
    if not hints:
        return output
    separator = "\n\n" if output.rstrip("\n") else ""
    return output.rstrip("\n") + separator + "\n\n".join(hints)


def _exec_clang_tidy(command) -> Tuple[int, str]:
    """Run clang-tidy and return (retval, output)."""
    try:
        sp = subprocess.run(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding="utf-8"
        )
        output = (sp.stdout or "") + (sp.stderr or "")
        output = _append_guidance(output)
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
    _, version_error = resolve_install_with_diagnostics(
        "clang-tidy", hook_args.version, hook_args.verbose
    )
    if version_error is not None:
        return 1, version_error

    compile_db_path, error = _resolve_compile_db(hook_args, other_args)
    if error is not None:
        return error

    if compile_db_path:
        if hook_args.verbose:
            print(
                f"Using compile_commands.json from: {compile_db_path}", file=sys.stderr
            )
        other_args = ["-p", compile_db_path] + other_args
    elif hook_args.verbose and not hook_args.no_compile_commands:
        has_p = any(a == "-p" or a.startswith("-p=") for a in other_args)
        if not has_p:
            print(_compile_commands_not_found_message(), file=sys.stderr)

    clang_tidy_args, source_files = _split_source_files(other_args)

    if (
        hook_args.fix
        and "-fix" not in clang_tidy_args
        and "-fix-errors" not in clang_tidy_args
    ):
        clang_tidy_args.append("-fix")

    # Parallel execution is unsafe when arguments include flags that write to a
    # shared output path (e.g., --export-fixes fixes.yaml) or that apply in-place
    # fixes (-fix, -fix-errors), since multiple clang-tidy processes may attempt
    # to modify the same header file concurrently.
    unsafe_parallel = any(
        arg == "--export-fixes"
        or arg.startswith("--export-fixes=")
        or arg in ("-fix", "-fix-errors")
        for arg in clang_tidy_args
    )

    if hook_args.jobs > 1 and len(source_files) > 1 and not unsafe_parallel:
        return _exec_parallel_clang_tidy(
            ["clang-tidy"] + clang_tidy_args, source_files, hook_args.jobs
        )

    return _exec_clang_tidy(["clang-tidy"] + clang_tidy_args + source_files)


def main() -> int:
    retval, output = run_clang_tidy()
    if retval != 0:
        print(output)
    return retval


if __name__ == "__main__":
    raise SystemExit(main())
