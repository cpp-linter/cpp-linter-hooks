# Migration: From Clang Tools Binaries to Python Wheels

## Overview

Starting from version **v1.0.0**, `cpp-linter-hooks` has migrated from using the `clang-tools` package to using Python wheel packages for `clang-format` and `clang-tidy`. This change provides:

- **Better cross-platform compatibility**
- **Easier installation and dependency management**
- **Improved performance and reliability**
- **More predictable version management**

## What Changed

### Core Changes

| Aspect | Before (< v1.0.0) | After (≥ v1.0.0) |
|--------|-------------------|-------------------|
| **Installation** | Install from GitHub release | Install with from PyPI |
| **Distribution** | Binary packages | Python wheel packages |
| **Performance** | Standard performance | Optimized wheel packages |

### Implementation Details

- **Dependencies**: Updated to use separate `clang-format==20.1.7` and `clang-tidy==20.1.0` Python wheels
- **Installation Logic**: Enhanced with pip-based installation and runtime version checks
- **Performance**: Pre-commit hooks can now run in parallel for better speed

## Breaking Changes

**No breaking changes for end users**

- Your existing `.pre-commit-config.yaml` files will continue to work without modification
- All hook configurations remain backward compatible
- No changes required to your workflow

## Migration Steps

**No action required!** Your existing configuration will continue to work seamlessly.

However, we recommend updating to the latest version for:
- Better performance
- Enhanced reliability
- Latest features and bug fixes

## Support

If you encounter issues after migration:

1. **Check this guide**: Review the troubleshooting section above
2. **Search existing issues**: [GitHub Issues](https://github.com/cpp-linter/cpp-linter-hooks/issues)
3. **Report new issues**: Include the following information:
   - Operating system and version
   - Python version
   - `cpp-linter-hooks` version
   - Complete error message/stack trace
   - Your `.pre-commit-config.yaml` configuration

## References

### Official Packages
- [clang-format Python wheel](https://pypi.org/project/clang-format/) - PyPI package
- [clang-tidy Python wheel](https://pypi.org/project/clang-tidy/) - PyPI package

### Source Repositories
- [clang-format wheel source](https://github.com/ssciwr/clang-format-wheel) - GitHub repository
- [clang-tidy wheel source](https://github.com/ssciwr/clang-tidy-wheel) - GitHub repository

### Documentation
- [cpp-linter-hooks Documentation](https://github.com/cpp-linter/cpp-linter-hooks) - Main repository
- [Pre-commit Framework](https://pre-commit.com/) - Pre-commit documentation

---

**Happy linting!**
