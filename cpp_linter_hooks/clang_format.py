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
    try:
        subprocess.run(command, stdout=subprocess.PIPE)
        return 0
    except FileNotFoundError:
        return 1


def main():
    run_clang_format(args)


if __name__ == "__main__":
    main()
