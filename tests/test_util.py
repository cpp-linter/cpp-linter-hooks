import logging
import sys
import pytest
from itertools import product

from cpp_linter_hooks.util import ensure_installed, DEFAULT_CLANG_VERSION


VERSIONS = [None, "16"]
TOOLS = ["clang-format", "clang-tidy"]


@pytest.mark.parametrize(("tool", "version"), list(product(TOOLS, VERSIONS)))
def test_ensure_installed(tool, version, tmp_path, monkeypatch, caplog):

    bin_path = tmp_path / "bin"
    with monkeypatch.context() as m:
        m.setattr(sys, "executable", str(bin_path / "python"))

        for run in range(2):
            # clear any existing log messages
            caplog.clear()
            caplog.set_level(logging.INFO, logger="cpp_linter_hooks.util")

            if version is not None:
                ensure_installed(tool, version=version)
            else:
                ensure_installed(tool)

            bin_version = version or DEFAULT_CLANG_VERSION
            assert (bin_path / f"{tool}-{bin_version}").is_file()

            # first run should install
            assert caplog.record_tuples[0][2] == f"Checking for {tool}, version {bin_version}"
            if run == 0:
                assert caplog.record_tuples[1][2] == f"Installing {tool}, version {bin_version}"
            # second run should just confirm it's already installed
            else:
                assert caplog.record_tuples[1][2] == f"{tool}, version {bin_version} is already installed"
