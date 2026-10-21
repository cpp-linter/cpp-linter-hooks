"""Pre-commit hook wrapper for clang-tidy."""

import re
import subprocess
import sys
from argparse import ArgumentParser, ArgumentTypeError
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

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


# Status lines clang-tidy prints around the diagnostics. They say nothing about
# the files being checked (e.g. "537 warnings generated." comes from system
# headers), so the hook drops them unless --verbose is given. clang-tidy 18 and
# older print the "generated" lines even with -quiet.
NOISE_LINE_PATTERNS = (
    re.compile(r"^\d+ (?:warning|error)s?(?: and \d+ errors?)? generated\.$"),
    re.compile(r"^Suppressed \d+ warnings? \(.*\)\.$"),
    re.compile(
        r"^Use -header-filter=.* to display errors from all non-system headers\."
    ),
    re.compile(r"^\[\d+/\d+\] Processing file .*\.$"),
)

# Options whose value is a comma-separated list of check globs.
CHECK_GLOB_OPTIONS = (
    "--checks=",
    "-checks=",
    "--warnings-as-errors=",
    "-warnings-as-errors=",
)
CHECK_MODULES = (
    "abseil",
    "altera",
    "android",
    "boost",
    "bugprone",
    "cert",
    "clang-analyzer",
    "clang-diagnostic",
    "concurrency",
    "cppcoreguidelines",
    "darwin",
    "fuchsia",
    "google",
    "hicpp",
    "linuxkernel",
    "llvm",
    "llvmlibc",
    "misc",
    "modernize",
    "mpi",
    "objc",
    "openmp",
    "performance",
    "portability",
    "readability",
    "zircon",
)
# A single check glob such as "bugprone-*", "-modernize-use-trailing-return-type"
# or "*", optionally carrying a stray YAML quote.
CHECK_GLOB_FRAGMENT = re.compile(
    r"""^['"]?-?(?:\*[\w.*-]*|(?:"""
    + "|".join(re.escape(module) for module in CHECK_MODULES)
    + r""")-[\w.*-]*)['"]?$"""
)
QUOTES = ("'", '"')


def _positive_int(value: str) -> int:
    """Parse a positive integer for the --jobs option."""
    jobs = int(value)
    if jobs < 1:
        raise ArgumentTypeError("--jobs must be greater than 0")
    return jobs


parser = ArgumentParser()
parser.add_argument(
    "--version",
    default=None,
    help=(
        "Version of clang-tidy to install and run; defaults to the latest stable "
        "wheel on PyPI"
    ),
)
parser.add_argument(
    "--compile-commands",
    default=None,
    dest="compile_commands",
    help="Directory containing compile_commands.json to pass to clang-tidy via -p",
)
parser.add_argument(
    "--no-compile-commands",
    action="store_true",
    dest="no_compile_commands",
    help="Disable automatic compile_commands.json detection",
)
parser.add_argument(
    "-j",
    "--jobs",
    type=_positive_int,
    default=1,
    help="Number of clang-tidy processes to run in parallel (default: 1)",
)
parser.add_argument(
    "-v", "--verbose", action="store_true", help="Enable verbose output"
)
parser.add_argument("--fix", action="store_true", help="Apply fixes in place (-fix)")


def _find_compile_commands() -> str | None:
    """Return the first common directory containing compile_commands.json."""
    for d in COMPILE_DB_SEARCH_DIRS:
        if (Path(d) / "compile_commands.json").exists():
            return d
    return None


def _compile_commands_not_found_message(path: str | None = None) -> str:
    """Build a user-facing message for missing compile_commands.json files."""
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
) -> tuple[str | None, tuple[int, str] | None]:
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
    """Return whether clang-tidy output indicates a compile database problem."""
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
    """Return whether clang-tidy output indicates an MSVC setup problem."""
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
    """Append troubleshooting guidance when clang-tidy output matches known errors."""
    hints: list[str] = []
    if _looks_like_compile_db_error(output) and COMPILE_COMMANDS_HINT not in output:
        hints.append(COMPILE_COMMANDS_HINT)
    if _looks_like_msvc_error(output) and MSVC_HINT not in output:
        hints.append(MSVC_HINT)
    if not hints:
        return output
    separator = "\n\n" if output.rstrip("\n") else ""
    return output.rstrip("\n") + separator + "\n\n".join(hints)


def _exec_clang_tidy(command) -> tuple[int, str]:
    """Run clang-tidy and return (retval, output)."""
    try:
        sp = subprocess.run(command, capture_output=True, encoding="utf-8", check=False)
        output = (sp.stdout or "") + (sp.stderr or "")
        output = _append_guidance(output)
        retval = (
            1 if sp.returncode != 0 or "warning:" in output or "error:" in output else 0
        )
        return retval, output
    except FileNotFoundError as e:
        return 1, str(e)


def _strip_noise(output: str) -> str:
    """Drop clang-tidy status lines that do not point at a problem."""
    lines = output.splitlines()
    kept = [
        line
        for line in lines
        if not any(pattern.match(line) for pattern in NOISE_LINE_PATTERNS)
    ]
    if len(kept) == len(lines):
        return output
    return "\n".join(kept)


def _has_quiet_option(args: list[str]) -> bool:
    """Return whether the user already set clang-tidy's -quiet option."""
    return any(
        arg in ("-quiet", "--quiet") or arg.startswith(("-quiet=", "--quiet="))
        for arg in args
    )


def _unquote(value: str) -> str:
    """Remove one pair of matching quotes around a value."""
    if len(value) >= 2 and value[0] == value[-1] and value[0] in QUOTES:
        return value[1:-1]
    return value


def _looks_like_config_file(value: str) -> bool:
    """Return whether a --checks value names a file instead of check globs."""
    name = Path(value).name
    return name.startswith(".") or name.endswith((".yaml", ".yml")) or "/" in value


def _repair_check_args(args: list[str]) -> tuple[list[str], list[str]]:
    """Fix check lists that YAML mangled in .pre-commit-config.yaml.

    Returns (args, notes). Inside ``args: [...]`` YAML splits an unquoted
    ``--checks=-*,bugprone-*`` at each comma, and clang-tidy would then treat
    ``bugprone-*`` as a source file. Quotes written inside the value reach
    clang-tidy as part of the glob. Both are repaired here; the notes tell the
    user how to fix the configuration.
    """
    repaired: list[str] = []
    notes: list[str] = []
    idx = 0
    while idx < len(args):
        arg = args[idx]
        idx += 1
        option = next((o for o in CHECK_GLOB_OPTIONS if arg.startswith(o)), None)
        if option is None:
            repaired.append(arg)
            continue

        fragments = [arg[len(option) :]]
        while idx < len(args) and CHECK_GLOB_FRAGMENT.match(args[idx]):
            fragments.append(args[idx])
            idx += 1
        value = ",".join(fragments)
        unquoted = _unquote(value)
        fixed = f"{option}{unquoted}"
        repaired.append(fixed)

        if len(fragments) > 1:
            notes.append(
                f"Note: YAML split {option}{value} at the commas; the hook joined "
                "the pieces again. Quote the whole option in "
                f'.pre-commit-config.yaml: args: ["{fixed}"]'
            )
        elif unquoted != value:
            notes.append(
                f"Note: removed the quotes inside {arg}; clang-tidy would read them "
                "as part of the check names. Quote the whole option instead: "
                f'args: ["{fixed}"]'
            )

        if option.endswith("checks=") and _looks_like_config_file(unquoted):
            notes.append(
                f"Note: {fixed} has no effect: --checks takes check names, not a "
                "file. clang-tidy already reads the nearest .clang-tidy file for "
                "each source file, so remove this option, or use "
                "--config-file=<path> to pick a specific file."
            )
    return repaired, notes


def _append_notes(output: str, notes: list[str]) -> str:
    """Append configuration notes after clang-tidy's output."""
    if not notes:
        return output
    separator = "\n\n" if output.rstrip("\n") else ""
    return output.rstrip("\n") + separator + "\n".join(notes)


def _looks_like_source_file(path: str) -> bool:
    """Return whether a path has a recognized C or C++ source suffix."""
    return Path(path).suffix.lower() in SOURCE_FILE_SUFFIXES


def _split_source_files(args: list[str]) -> tuple[list[str], list[str]]:
    """Split clang-tidy options from trailing source file arguments."""
    split_idx = len(args)
    source_files: list[str] = []
    for idx in range(len(args) - 1, -1, -1):
        if not _looks_like_source_file(args[idx]):
            break
        source_files.append(args[idx])
        split_idx = idx
    return args[:split_idx], list(reversed(source_files))


def _combine_outputs(results: list[tuple[int, str]]) -> str:
    """Join non-empty clang-tidy outputs from multiple executions."""
    return "\n".join(output.rstrip("\n") for _, output in results if output)


def _exec_parallel_clang_tidy(
    command_prefix: list[str], source_files: list[str], jobs: int
) -> tuple[int, str]:
    """Run clang-tidy over source files in parallel and combine the results."""

    def run_file(source_file: str) -> tuple[int, str]:
        """Run clang-tidy for a single source file."""
        return _exec_clang_tidy(command_prefix + [source_file])

    with ThreadPoolExecutor(max_workers=min(jobs, len(source_files))) as executor:
        results = list(executor.map(run_file, source_files))

    retval = 1 if any(retval != 0 for retval, _ in results) else 0
    return retval, _combine_outputs(results)


def run_clang_tidy(args=None) -> tuple[int, str]:
    """Run clang-tidy with hook-specific argument handling."""
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
    clang_tidy_args, notes = _repair_check_args(clang_tidy_args)

    # -quiet hides clang-tidy's statistics about suppressed warnings; --verbose
    # keeps clang-tidy's full output.
    if not hook_args.verbose and not _has_quiet_option(clang_tidy_args):
        clang_tidy_args.insert(0, "-quiet")

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
        retval, output = _exec_parallel_clang_tidy(
            ["clang-tidy"] + clang_tidy_args, source_files, hook_args.jobs
        )
    else:
        retval, output = _exec_clang_tidy(
            ["clang-tidy"] + clang_tidy_args + source_files
        )

    if not hook_args.verbose:
        output = _strip_noise(output)
    return retval, _append_notes(output, notes)


def main() -> int:
    """Run clang-tidy as a command-line entry point."""
    retval, output = run_clang_tidy()
    if retval != 0:
        print(output)
    return retval


if __name__ == "__main__":
    raise SystemExit(main())
