import subprocess

from cpp_linter_hooks import args
from cpp_linter_hooks import expect_version


def run_clang_format(args) -> int:
    if expect_version:
        dry_run_cmd = [f'clang-format-{expect_version}', '-dry-run', '--Werror']
        edit_cmd = [f'clang-format-{expect_version}', '-i']
    else:
        dry_run_cmd = ['clang-format', '-dry-run', '--Werror']
        edit_cmd = ["clang-format", '-i']
    for arg in args:
        if arg == expect_version or arg.startswith("--version"):
            continue
        dry_run_cmd.append(arg)
        edit_cmd.append(arg)

    retval = 0
    try:
        sp = subprocess.run(dry_run_cmd, stdout=subprocess.PIPE)
        retval = sp.returncode
        output = sp.stdout.decode("utf-8")
        if retval != 0:
            subprocess.run(edit_cmd, stdout=subprocess.PIPE)
        return retval, output
    except FileNotFoundError as e:
        return 1, e


def main() -> int:
    retval, output = run_clang_format(args)
    if retval != 0:
        print(output)
    return retval


if __name__ == "__main__":
    raise SystemExit(main())
