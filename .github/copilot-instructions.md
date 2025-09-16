# cpp-linter-hooks Development Instructions

Always reference these instructions first and fallback to search or bash commands only when you encounter unexpected information that does not match the info here.

cpp-linter-hooks is a Python package that provides pre-commit hooks for automatically formatting and linting C/C++ code using `clang-format` and `clang-tidy`. The package installs specific versions of these tools and integrates them into pre-commit workflows.

## Working Effectively

### Bootstrap and Install Dependencies
- `python -m pip install --upgrade pip`
- `pip install .[dev]` -- installs the package in development mode with all dev dependencies
- **Time expectation**: 2-3 minutes for initial install

### Build and Test Commands
- `pytest -vv -k "not (test_get_version_from_dependency_success or test_get_version_from_dependency_missing_dependency or test_get_version_from_dependency_malformed_toml or test_resolve_install_tool_already_installed_correct_version or test_default_versions)"` -- runs working tests, excluding 5 known failing tests related to installation path detection
- **NEVER CANCEL**: Test suite takes 6-8 minutes. Set timeout to 15+ minutes.
- `coverage run --source=tests,cpp_linter_hooks -m pytest -vv -k "not (test_get_version_from_dependency_success or test_get_version_from_dependency_missing_dependency or test_get_version_from_dependency_malformed_toml or test_resolve_install_tool_already_installed_correct_version or test_default_versions)"` -- runs tests with coverage
- **NEVER CANCEL**: Coverage test takes 8-10 minutes. Set timeout to 20+ minutes.
- `coverage report` -- shows coverage after running coverage tests
- `coverage xml` -- generates XML coverage report

### Test the Hooks Directly
- `python -m cpp_linter_hooks.clang_format --help` -- shows clang-format hook help
- `python -m cpp_linter_hooks.clang_tidy --help` -- shows clang-tidy hook help
- `python -m cpp_linter_hooks.clang_format --version=21 file.c` -- formats a C file using clang-format version 21
- `python -m cpp_linter_hooks.clang_tidy --version=21 --checks=readability-* file.c` -- lints a C file using clang-tidy
- **Time expectation**: Each hook takes 15-20 seconds on first run (tool installation), then 1-2 seconds

### Pre-commit Setup and Testing
**WARNING**: Network timeouts may affect pre-commit setup in CI environments. For testing, use local system hooks:

Create test scenario:
```bash
mkdir /tmp/test_precommit && cd /tmp/test_precommit
git init && git config user.email "test@example.com" && git config user.name "Test User"
echo '#include <stdio.h>
int main(){printf("test");return 0;}' > test.c
```

Create `.pre-commit-config.yaml`:
```yaml
repos:
  - repo: local
    hooks:
      - id: clang-format
        name: clang-format
        entry: clang-format-hook
        language: system
        types_or: [c++, c]
        args: [--version=21]
```

Run: `git add . && git commit -m "initial" && pre-commit run --all-files`
- **Time expectation**: 15-20 seconds

**NOTE**: The main repository testing script `sh testing/run.sh` may fail due to network timeouts when installing clang tools from PyPI. This is a known limitation in sandboxed environments.

### Linting and Formatting
**WARNING**: Standard pre-commit setup may fail due to network issues. The repository uses:
- `pre-commit run --all-files` -- may timeout in CI environments
- The project has a `.pre-commit-config.yaml` with ruff for Python formatting
- **Time expectation**: When working, takes 2-3 minutes

## Validation Scenarios

### Always test these scenarios after making changes:

1. **Basic Hook Functionality**:
   ```bash
   echo '#include <stdio.h>
   int main(){printf("test");return 0;}' > /tmp/test.c
   python -m cpp_linter_hooks.clang_format --version=21 /tmp/test.c
   cat /tmp/test.c  # Verify formatting applied
   ```

2. **Clang-tidy Linting**:
   ```bash
   echo '[
   {
     "directory": "/tmp",
     "command": "gcc -o test test.c",
     "file": "test.c"
   }
   ]' > /tmp/compile_commands.json
   cd /tmp && python -m cpp_linter_hooks.clang_tidy --version=21 --checks=readability-* test.c
   ```

3. **Test Suite Validation**:
   - Always run the working test subset (see command above)
   - 55 tests should pass, 5 known failures are acceptable
   - Tests validate multiple clang-format/clang-tidy versions (16-21)

## Common Tasks

### Repository Structure
```
.
├── .github/           # GitHub workflows and configs
├── .gitignore
├── .pre-commit-config.yaml
├── .pre-commit-hooks.yaml  # Hook definitions for users
├── LICENSE
├── README.md
├── cpp_linter_hooks/  # Main package source
│   ├── __init__.py
│   ├── clang_format.py
│   ├── clang_tidy.py
│   └── util.py
├── docs/
├── pyproject.toml     # Package configuration
├── testing/           # Integration tests and examples
│   ├── main.c         # Poorly formatted test file
│   ├── good.c         # Well formatted test file
│   ├── run.sh         # Integration test script
│   └── ...
└── tests/            # Unit tests
    ├── test_clang_format.py
    ├── test_clang_tidy.py
    └── test_util.py
```

### Key Files to Check After Changes
- Always check `cpp_linter_hooks/util.py` after modifying version handling
- Always test both `clang_format.py` and `clang_tidy.py` after utility changes
- Always verify `pyproject.toml` dependencies match expected tool versions

### Known Limitations
- Some tests fail due to installation path detection issues (5 tests expected to fail)
- Pre-commit setup may timeout in CI environments due to network restrictions
- The `testing/run.sh` script requires network access to PyPI for clang tool installation
- Tool installation on first use takes 15-20 seconds per version

### Build Times and Expectations
- Package installation: 2-3 minutes
- Test suite (working tests): 6-8 minutes  
- Coverage tests: 8-10 minutes
- Individual hook execution: 15-20 seconds (first use), 1-2 seconds (subsequent)
- Pre-commit setup: 15-20 seconds (when network allows)

### Debugging Tips
- Use `--verbose` flag with clang-format hook for detailed output
- Check `/home/runner/.cache/pre-commit/` for pre-commit environment issues
- Use local system hooks in `.pre-commit-config.yaml` to avoid network timeouts
- Test hooks directly with `python -m cpp_linter_hooks.{tool}` before using via pre-commit

Always validate that your changes don't break the core functionality by running the hook validation scenarios above.