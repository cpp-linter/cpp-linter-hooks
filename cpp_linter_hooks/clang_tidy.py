import subprocess

from cpp_linter_hooks import args
from cpp_linter_hooks import expect_version


def run_clang_tidy(args) -> int:
    if expect_version:
        command = [f'clang-tidy-{expect_version}']
    else:
        command = ["clang-tidy"]
    for arg in args:
        if arg == expect_version or arg.startswith("--version"):
            continue
        command.append(arg)

    retval = 0
    output = ""
    try:
        sp = subprocess.run(command, stdout=subprocess.PIPE)
        retval = sp.returncode
        output = sp.stdout.decode("utf-8")
        if "warning:" in output or "error:" in output:
            retval = 1
        return retval, output
    except FileNotFoundError as stderr:
        retval = 1
        return retval, stderr


def main() -> int:
    retval, output = run_clang_tidy(args)
    if retval != 0:
        print(output)
    return retval


if __name__ == "__main__":
    raise SystemExit(main())
