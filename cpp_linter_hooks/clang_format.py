import subprocess

from cpp_linter_hooks import args
from cpp_linter_hooks import expect_version


def run_clang_format(args) -> int:
    if expect_version:
        command = [f'clang-format-{expect_version}', '-i']
    else:
        command = ["clang-format", '-i']
    for arg in args:
        if arg == expect_version or arg.startswith("--version"):
            continue
        command.append(arg)

    retval = 0
    output = ""
    try:
        if "--dry-run" in command:
            sp = subprocess.run(command, stdout=subprocess.PIPE)
            retval = -1  # Not a fail just identify it's a dry-run.
            output = sp.stdout.decode("utf-8")
        else:
            retval = subprocess.run(command, stdout=subprocess.PIPE).returncode
        return retval, output
    except FileNotFoundError as e:
        retval = 1
        return retval, e


def main() -> int:
    retval, output = run_clang_format(args)
    if retval != 0:
        print(output)
    return retval


if __name__ == "__main__":
    raise SystemExit(main())
