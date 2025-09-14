# cpp-linter-hooks

`cpp-linter-hooks` is a Python package that provides pre-commit hooks for C/C++ code formatting and linting using `clang-format` and `clang-tidy`. The hooks automatically install specific versions of these tools as Python wheel packages and format/lint C/C++ code.

Always reference these instructions first and fallback to search or bash commands only when you encounter unexpected information that does not match the info here.

## Working Effectively

### Bootstrap and Setup
- **Install dependencies**: 
  - `python -m pip install --upgrade pip` -- takes ~5 seconds
  - `pip install .[dev]` -- takes ~10 seconds to install development dependencies
  - `pip install .[tools]` -- installs clang-format==21.1.0 and clang-tidy==21.1.0, takes ~2 seconds (may fail due to network timeouts in sandboxed environments)
  - **Alternative for clang tools**: `pip install clang-format==21.1.0 clang-tidy==21.1.0` -- more reliable installation method

### Build and Test Process  
- **NEVER CANCEL builds or test commands**: The test suite takes 5.5 minutes. Set timeout to 10+ minutes.
- **Run tests**: `coverage run --source=tests,cpp_linter_hooks -m pytest -vv` -- takes 5.5 minutes. NEVER CANCEL.
- **Coverage report**: `coverage report` -- shows test coverage (typically 94%+)
- **Python linting**: 
  - `pip install ruff` (if not already installed)
  - `ruff check .` -- takes <1 second, must pass
  - `ruff format --check .` -- takes <1 second, checks code formatting

### Testing the Hooks Manually
- **Test clang-format hook directly**: 
  - `clang-format-hook --version 21 --verbose /path/to/test.c` -- formats C/C++ files
  - Requires `--version` parameter to avoid version checking issues
- **Test clang-tidy hook directly**: 
  - `clang-tidy-hook --version 21 /path/to/test.c` -- analyzes C/C++ files
  - May show compilation database warnings (normal for standalone files)

### Pre-commit Environment Issues
- **Known Issue**: Pre-commit environment setup may fail with network timeouts in sandboxed environments when downloading clang tools
- **Workaround**: Test hooks directly using the manual commands above
- **CI Environment**: The GitHub Actions CI works correctly with longer timeouts

## Validation

### Required Validation Steps
- **ALWAYS run the full test suite** after making changes: `coverage run --source=tests,cpp_linter_hooks -m pytest -vv` (5.5 minutes)
- **ALWAYS run Python linting** before committing: `ruff check .` and `ruff format --check .`
- **ALWAYS test both hooks manually** with sample C++ files using the direct hook commands
- **Test end-to-end scenarios**: Create a malformed C++ file, run clang-format hook, verify it gets formatted correctly

### Manual Testing Scenario
```bash
# Create test file with poor formatting
echo '#include <stdio.h>
int main() {for (;;) break; printf("Hello world!\n");return 0;}' > /tmp/test.c

# Test clang-format (should reformat the file)
clang-format-hook --version 21 --verbose /tmp/test.c

# Verify file was formatted (should show properly indented code)
cat /tmp/test.c

# Test clang-tidy (should run without errors)
clang-tidy-hook --version 21 /tmp/test.c
```

## Project Structure

### Key Directories and Files
```
.
├── cpp_linter_hooks/          # Main package source code
│   ├── __init__.py
│   ├── clang_format.py        # clang-format hook implementation  
│   ├── clang_tidy.py         # clang-tidy hook implementation
│   └── util.py               # Shared utilities for tool installation
├── tests/                    # Unit tests (73 tests total)
│   ├── test_clang_format.py
│   ├── test_clang_tidy.py  
│   └── test_util.py
├── testing/                  # Integration testing and examples
│   ├── run.sh               # Integration test script
│   ├── main.c               # Test C file (poorly formatted)
│   ├── good.c               # Well-formatted test file
│   ├── .clang-format        # Example clang-format config
│   ├── .clang-tidy          # Example clang-tidy config
│   └── pre-commit-config*.yaml # Example pre-commit configurations
├── .github/workflows/        # CI/CD pipelines
│   ├── test.yml             # Main test workflow  
│   ├── pre-commit.yml       # Pre-commit validation
│   └── publish.yml          # Package publishing
├── pyproject.toml           # Package configuration and dependencies
├── .pre-commit-hooks.yaml   # Hook definitions for pre-commit
└── .pre-commit-config.yaml  # Repository's own pre-commit config
```

### Entry Points
- `clang-format-hook` → `cpp_linter_hooks.clang_format:main`
- `clang-tidy-hook` → `cpp_linter_hooks.clang_tidy:main`

## Common Commands Reference

### Repository Root Contents
```bash
ls -la
# .github/         - GitHub workflows and configurations
# cpp_linter_hooks/ - Main Python package source
# docs/            - Documentation (migration notes)
# testing/         - Integration tests and examples  
# tests/           - Unit tests
# pyproject.toml   - Package configuration
# .pre-commit-hooks.yaml - Hook definitions
# README.md        - Main documentation
```

### Package Configuration (pyproject.toml)
- **Python support**: 3.9-3.14
- **Main dependencies**: setuptools>=45.0.0, tomli (Python <3.11)
- **Dev dependencies**: coverage, pre-commit, pytest, pytest-codspeed
- **Optional clang tools**: clang-format==21.1.0, clang-tidy==21.1.0

### Common Workflow Times
- **Dependency installation**: ~10-15 seconds
- **Test suite execution**: 5.5 minutes (NEVER CANCEL - use 10+ minute timeouts)
- **Python linting**: <1 second
- **Hook execution**: <1 second per file
- **Coverage reporting**: <1 second

## Troubleshooting

### Version Checking Issues
- **Problem**: Hook fails with version checking TypeError
- **Solution**: Always specify `--version 21` parameter when testing hooks directly

### Network Timeout Issues  
- **Problem**: Pre-commit environment setup fails with pip timeout errors
- **Cause**: Downloading large clang tool packages in sandboxed environments
- **Workaround**: Test functionality using direct hook commands instead of pre-commit

### Test Environment Setup
- **Always install dev dependencies first**: `pip install .[dev]`
- **Separately install clang tools**: `pip install clang-format==21.1.0 clang-tidy==21.1.0`
- **Verify installation**: Check that `clang-format-hook --help` and `clang-tidy-hook --help` work

## CI/CD Pipeline Notes

- **GitHub Actions**: Uses Python 3.9-3.14 matrix testing
- **Test timeout**: Set to allow 5.5+ minutes for full test suite
- **Pre-commit CI**: May encounter timeout issues in certain environments
- **Publishing**: Automated via GitHub Actions on releases