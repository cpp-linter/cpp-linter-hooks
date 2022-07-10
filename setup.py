from setuptools import setup, find_packages

setup(
    name='cpp_linter_hooks',
    description='Automatically check c/c++ with clang-format and clang-tidy',
    url='https://github.com/shenxianpeng/cpp-linter-hooks',
    version='0.0.1',
    author="Peter Shen",
    author_email="xianpeng.shen@gmail.com",
    license="MIT",
    keywords="clang clang-tidy clang-format pre-commit pre-commit-hooks",
    packages=find_packages(),
    install_requires=['clang-tools>=0.2.2'],
    entry_points={
        "console_scripts": [
            "clang-format-hook=cpp_linter_hooks.clang_format:main",
            "clang-tidy-hook=cpp_linter_hooks.clang_tidy:main",
        ]
    },
)
