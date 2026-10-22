"""Find the lines that a commit or push changes, using git."""

import codecs
import os
import re
import subprocess
from collections.abc import Iterator
from pathlib import PurePath

# "@@ -12,3 +14,2 @@": the old side spans 3 lines; the new side starts at line
# 14 and spans 2 lines. A missing count means 1.
HUNK_HEADER = re.compile(r"^@@ -\d+(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")

LineRanges = list[list[int]]


def diff_range() -> list[str]:
    """Return the git diff arguments for the changes being checked.

    pre-commit and prek set PRE_COMMIT_FROM_REF and PRE_COMMIT_TO_REF for
    ``run --from-ref ... --to-ref ...`` and for the pre-push stage. Otherwise
    the hook checks a commit, so the changes are the staged ones.
    """
    from_ref = os.environ.get("PRE_COMMIT_FROM_REF")
    to_ref = os.environ.get("PRE_COMMIT_TO_REF")
    if from_ref and to_ref:
        return [f"{from_ref}...{to_ref}"]
    return ["--cached"]


def _git_diff(args: list[str]) -> str | None:
    """Run ``git diff`` and return its output, or None if git fails."""
    command = [
        "git",
        "-c",
        "core.quotePath=false",
        "diff",
        "--relative",
        "--no-color",
        "--no-ext-diff",
        *args,
    ]
    try:
        sp = subprocess.run(command, capture_output=True, check=False, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if sp.returncode != 0:
        return None
    return sp.stdout.decode("utf-8", errors="surrogateescape")


def normalize(path: str) -> str:
    """Return a path in the form git prints it, relative and with "/"."""
    # PurePath also drops "./" segments.
    return PurePath(path).as_posix()


def _unquote_path(path: str) -> str:
    """Undo git's C-style quoting of unusual file names."""
    if len(path) >= 2 and path[0] == path[-1] == '"':
        raw = codecs.escape_decode(path[1:-1].encode("utf-8"))[0]
        return raw.decode("utf-8", errors="surrogateescape")
    return path


def _count(group: str | None) -> int:
    """Return a hunk header's line count, which is 1 when git leaves it out."""
    return 1 if group is None else int(group)


def _skip_hunk_body(lines: Iterator[str], count: int) -> None:
    """Consume the next count lines of a hunk.

    They are skipped, not parsed, because an added line such as "++ i;"
    looks like a "+++ " file header. "\\ No newline at end of file" is not
    one of the hunk's lines.
    """
    while count > 0:
        line = next(lines, None)
        if line is None:
            return
        if line[:1] in ("+", "-", " "):
            count -= 1


def _parse_added_lines(diff: str) -> dict[str, LineRanges]:
    """Return the added line ranges of each file in a ``git diff -U0`` output."""
    ranges: dict[str, LineRanges] = {}
    current: LineRanges | None = None
    lines = iter(diff.splitlines())
    for line in lines:
        if line.startswith("+++ "):
            name = _unquote_path(line[4:].rstrip("\t"))
            current = (
                None
                if name == "/dev/null"
                else ranges.setdefault(name.removeprefix("b/"), [])
            )
            continue
        match = HUNK_HEADER.match(line)
        if match is None:
            continue
        start, count = int(match.group(2)), _count(match.group(3))
        if count > 0 and current is not None:
            current.append([start, start + count - 1])
        _skip_hunk_body(lines, _count(match.group(1)) + count)
    return ranges


def changed_lines(files: list[str]) -> dict[str, LineRanges] | None:
    """Return the added line ranges of each file, keyed by the given path.

    Returns None when the changed lines are unknown and every line should be
    checked: outside a git repository, when a file has no changes, which
    means the hook runs on files that were not changed (``--all-files`` or
    ``--files``), or when a file on disk differs from the version the lines
    come from, so the line numbers would not match what clang-tidy reads. A
    file that is changed but has no added lines, for example a pure rename,
    maps to an empty list.
    """
    if not files:
        return None
    revisions = diff_range()
    names = _git_diff(["--name-only", "-z", *revisions])
    if names is None:
        return None
    changed = set(names.split("\0"))
    normalized = {path: normalize(path) for path in files}
    if any(name not in changed for name in normalized.values()):
        return None
    # pre-commit hides unstaged changes during a commit, so the files on disk
    # match the index. A direct run, --files or a push with uncommitted
    # changes can leave them different from the diffed version.
    diffed_version = (
        [] if revisions == ["--cached"] else [os.environ["PRE_COMMIT_TO_REF"]]
    )
    if _git_diff(["--quiet", *diffed_version, "--", *files]) is None:
        return None

    diff = _git_diff(["-U0", "--src-prefix=a/", "--dst-prefix=b/", *revisions])
    if diff is None:
        return None
    added = _parse_added_lines(diff)
    return {path: added.get(name, []) for path, name in normalized.items()}
