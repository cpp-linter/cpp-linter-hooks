# Migration Guide: From clang-tools to Python Wheels

## Overview

Starting from version 0.9.0, `cpp-linter-hooks` has migrated from using the `clang-tools` package to using Python wheel packages for `clang-format` and `clang-tidy`. This change provides better cross-platform compatibility, easier installation, and more reliable dependency management.

## What Changed

### Dependencies
- **Before**: Used `clang-tools==0.15.1` package
- **After**: Uses `clang-format` and `clang-tidy` wheel packages from PyPI

### Installation Method
- **Before**: clang-format and clang-tidy were installed via `clang-tools` package which managed binaries
- **After**: clang-format and clang-tidy are installed as Python packages and available as executables

### Benefits of Migration

1. **Better Cross-Platform Support**: Python wheels work consistently across different operating systems
2. **Simplified Installation**: No need to manage binary installations separately
3. **More Reliable**: No more issues with binary compatibility or single threaded execution
4. **Better Version Management**: Each tool version is a separate package release

## Breaking Changes

### For End Users

- **No breaking changes**: The pre-commit hook configuration remains exactly the same
- All existing `.pre-commit-config.yaml` files will continue to work without modification

### For Developers
- The internal `ensure_installed()` function now returns the tool name instead of a Path object
- The `util.py` module has been rewritten to use `shutil.which()` instead of `clang_tools.install`
- Tests have been updated to mock the new wheel-based installation

## Migration Steps

### For End Users
No action required! Your existing configuration will continue to work.

### For Developers/Contributors
1. Update your development environment:
   ```bash
   pip install clang-format clang-tidy
   ```

2. If you were importing from the utility module:
   ```python
   # Before
   from cpp_linter_hooks.util import ensure_installed
   path = ensure_installed("clang-format", "18")
   command = [str(path), "--version"]
   
   # After
   from cpp_linter_hooks.util import ensure_installed
   tool_name = ensure_installed("clang-format", "18")
   command = [tool_name, "--version"]
   ```

## Version Support

The wheel packages support the same LLVM versions as before:
- LLVM 16, 17, 18, 19, 20+
- The `--version` argument continues to work as expected

## Troubleshooting

### Tool Not Found Error
If you encounter "command not found" errors:

1. Ensure the wheel packages are installed:
   ```bash
   pip install clang-format clang-tidy
   ```

2. Verify the tools are available:
   ```bash
   clang-format --version
   clang-tidy --version
   ```

3. Check that the tools are in your PATH:
   ```bash
   which clang-format
   which clang-tidy
   ```

### Version Mismatch
If you need a specific version, you can install it explicitly:
```bash
pip install clang-format==18.1.8
pip install clang-tidy==18.1.8
```

## Support

If you encounter any issues after the migration, please:
1. Check this migration guide
2. Search existing [issues](https://github.com/cpp-linter/cpp-linter-hooks/issues)
3. Create a new issue with:
   - Your operating system
   - Python version
   - The exact error message
   - Your `.pre-commit-config.yaml` configuration

## References

- [clang-format wheel package](https://github.com/ssciwr/clang-format-wheel)
- [clang-tidy wheel package](https://github.com/ssciwr/clang-tidy-wheel)
- [PyPI clang-format](https://pypi.org/project/clang-format/)
- [PyPI clang-tidy](https://pypi.org/project/clang-tidy/)
