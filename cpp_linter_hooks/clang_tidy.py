import subprocess
from cpp_linter_hooks import args, expect_version


def run_clang_tidy(args) -> int:
    if expect_version:
        command = [f'clang-tidy-{expect_version}']
    else:
        command = ["clang-tidy"]
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
    run_clang_tidy(args)


if __name__ == "__main__":
    main()
