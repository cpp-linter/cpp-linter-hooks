import subprocess

from cpp_linter_hooks import args
from cpp_linter_hooks import expect_version


def run_clang_tidy(args) -> str:
    if expect_version:
        command = [f'clang-tidy-{expect_version}']
    else:
        command = ["clang-tidy"]
    for arg in args:
        if arg == expect_version or arg.startswith("--version"):
            continue
        command.append(arg)
    try:
        output = subprocess.run(command, stdout=subprocess.PIPE).stdout.decode("utf-8")
    except FileNotFoundError as e:
        output = e
    return output


def main():
    result = run_clang_tidy(args)
    print(result)


if __name__ == "__main__":
    main()
