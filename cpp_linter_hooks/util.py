import subprocess


def check_installed(tool, version="") -> int:
    if version:
        check_version_cmd = [f'{tool}-{version} ', '--version']
        # clang-tools exist because install_requires=['clang-tools'] in setup.py
        install_tool_cmd = ['clang-tools', '-i', version]
    else:
        check_version_cmd = [tool, '--version']
        # install verison 13 by default if clang-tools not exist.
        install_tool_cmd = ['clang-tools', '-i', '13']
    try:
        retval = subprocess.run(check_version_cmd, stdout=subprocess.PIPE).returncode
    except FileNotFoundError:
        retval = subprocess.run(install_tool_cmd, stdout=subprocess.PIPE).returncode
    return retval


def get_expect_version(args) -> str:
    for arg in args:
        if arg.startswith("--version"):  # expect specific clang-tools version.
            # If --version is passed in as 2 arguments, the second is version
            if arg == "--version" and args.index(arg) != len(args) - 1:
                # when --version 14
                expect_version = args[args.index(arg) + 1]
            else:
                # when --version=14, --version='14' or --version="14"
                expect_version = arg.replace(" ", "").replace("=", "").replace("--version", "")
            return expect_version
    return ""
