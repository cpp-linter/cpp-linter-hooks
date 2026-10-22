import subprocess
from unittest.mock import patch

import pytest

from cpp_linter_hooks.changed_lines import (
    _parse_added_lines,
    changed_lines,
    diff_range,
    normalize,
)

ORIGINAL = "".join(f"line {n}\n" for n in range(1, 11))


def git(repo, *args):
    """Run git in repo with a fixed identity and return its stdout."""
    return subprocess.run(
        [
            "git",
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.com",
            "-c",
            "commit.gpgsign=false",
            *args,
        ],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout


@pytest.fixture
def repo(tmp_path, monkeypatch):
    """A git repository with one commit that adds a.cpp, used as the cwd."""
    git(tmp_path, "init", "-q")
    (tmp_path / "a.cpp").write_text(ORIGINAL)
    git(tmp_path, "add", "a.cpp")
    git(tmp_path, "commit", "-q", "-m", "init")
    monkeypatch.chdir(tmp_path)
    return tmp_path


def edit(path, replacements):
    """Replace whole lines (1-based numbers) in a file."""
    lines = path.read_text().splitlines(keepends=True)
    for number, text in replacements.items():
        lines[number - 1] = text
    path.write_text("".join(lines))


def test_staged_changes_give_the_added_lines(repo):
    edit(repo / "a.cpp", {3: "changed 3\n", 7: "changed 7\n", 8: "changed 8\n"})
    git(repo, "add", "a.cpp")

    assert changed_lines(["a.cpp"]) == {"a.cpp": [[3, 3], [7, 8]]}


def test_unstaged_changes_are_ignored(repo):
    edit(repo / "a.cpp", {2: "staged\n"})
    git(repo, "add", "a.cpp")
    edit(repo / "a.cpp", {9: "not staged\n"})

    assert changed_lines(["a.cpp"]) == {"a.cpp": [[2, 2]]}


def test_new_file_counts_every_line(repo):
    (repo / "b.cpp").write_text("int x;\nint y;\n")
    git(repo, "add", "b.cpp")

    assert changed_lines(["b.cpp"]) == {"b.cpp": [[1, 2]]}


def test_deleted_lines_leave_nothing_to_report(repo):
    edit(repo / "a.cpp", {4: ""})
    git(repo, "add", "a.cpp")

    assert changed_lines(["a.cpp"]) == {"a.cpp": []}


def test_pure_rename_leaves_nothing_to_report(repo):
    git(repo, "mv", "a.cpp", "renamed.cpp")

    assert changed_lines(["renamed.cpp"]) == {"renamed.cpp": []}


def test_paths_are_returned_as_given(repo):
    (repo / "src").mkdir()
    (repo / "src" / "b.cpp").write_text("int x;\n")
    git(repo, "add", "src/b.cpp")

    assert changed_lines(["./src/b.cpp"]) == {"./src/b.cpp": [[1, 1]]}


def test_unusual_file_names(repo):
    name = "dir with space/naïve.cpp"
    (repo / "dir with space").mkdir()
    (repo / name).write_text("int x;\n")
    git(repo, "add", name)

    assert changed_lines([name]) == {name: [[1, 1]]}


def test_unchanged_file_means_every_line_is_checked(repo):
    """pre-commit run --all-files passes files without changes."""
    (repo / "b.cpp").write_text("int x;\n")
    git(repo, "add", "b.cpp")

    assert changed_lines(["a.cpp", "b.cpp"]) is None


def test_runs_from_a_subdirectory(repo, monkeypatch):
    (repo / "src").mkdir()
    (repo / "src" / "b.cpp").write_text("int x;\n")
    git(repo, "add", "src/b.cpp")
    monkeypatch.chdir(repo / "src")

    assert changed_lines(["b.cpp"]) == {"b.cpp": [[1, 1]]}


def test_first_commit(tmp_path, monkeypatch):
    git(tmp_path, "init", "-q")
    (tmp_path / "a.cpp").write_text("int x;\nint y;\n")
    git(tmp_path, "add", "a.cpp")
    monkeypatch.chdir(tmp_path)

    assert changed_lines(["a.cpp"]) == {"a.cpp": [[1, 2]]}


def test_pushed_range_from_pre_commit_variables(repo, monkeypatch):
    base = git(repo, "rev-parse", "HEAD").strip()
    edit(repo / "a.cpp", {5: "pushed 5\n"})
    git(repo, "commit", "-q", "-am", "second")
    head = git(repo, "rev-parse", "HEAD").strip()
    edit(repo / "a.cpp", {1: "staged, not pushed\n"})
    git(repo, "add", "a.cpp")
    monkeypatch.setenv("PRE_COMMIT_FROM_REF", base)
    monkeypatch.setenv("PRE_COMMIT_TO_REF", head)

    assert changed_lines(["a.cpp"]) == {"a.cpp": [[5, 5]]}


def test_outside_a_git_repository(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path.parent))
    (tmp_path / "a.cpp").write_text("int x;\n")

    assert changed_lines(["a.cpp"]) is None


@pytest.mark.parametrize(
    "error", (FileNotFoundError("git"), subprocess.TimeoutExpired("git", 60))
)
def test_without_git(repo, error):
    with patch("cpp_linter_hooks.changed_lines.subprocess.run", side_effect=error):
        assert changed_lines(["a.cpp"]) is None


def test_hunk_diff_failure(repo):
    edit(repo / "a.cpp", {2: "changed\n"})
    git(repo, "add", "a.cpp")
    real_run = subprocess.run

    def fail_hunks(command, **kwargs):
        if "-U0" in command:
            return subprocess.CompletedProcess(command, 128, b"", b"fatal")
        return real_run(command, **kwargs)

    with patch("cpp_linter_hooks.changed_lines.subprocess.run", fail_hunks):
        assert changed_lines(["a.cpp"]) is None


def test_no_files():
    assert changed_lines([]) is None


def test_diff_range(monkeypatch):
    assert diff_range() == ["--cached"]
    monkeypatch.setenv("PRE_COMMIT_FROM_REF", "origin/main")
    assert diff_range() == ["--cached"]
    monkeypatch.setenv("PRE_COMMIT_TO_REF", "HEAD")
    assert diff_range() == ["origin/main...HEAD"]


@pytest.mark.parametrize(
    ("path", "expected"),
    (("a.cpp", "a.cpp"), ("./src/a.cpp", "src/a.cpp"), ("././a.cpp", "a.cpp")),
)
def test_normalize(path, expected):
    assert normalize(path) == expected


def test_parse_added_lines():
    lines = [
        "diff --git a/a.cpp b/a.cpp",
        "--- a/a.cpp",
        "+++ b/a.cpp",
        "@@ -3 +3 @@",
        "@@ -10,0 +11,4 @@ int main() {",
        "@@ -20,2 +23,0 @@",
        "diff --git a/gone.cpp b/gone.cpp",
        "--- a/gone.cpp",
        "+++ /dev/null",
        "@@ -1,2 +0,0 @@",
        "diff --git a/b.cpp b/b.cpp",
        "--- a/b.cpp",
        '+++ "b/sp\\303\\251cial \\"q\\".cpp"',
        "@@ -0,0 +1,2 @@",
    ]

    assert _parse_added_lines("\n".join(lines)) == {
        "a.cpp": [[3, 3], [11, 14]],
        'spécial "q".cpp': [[1, 2]],
    }
