# cpp-linter-hooks AI Coding Guide

## Project Overview
Pre-commit hooks wrapper that auto-installs and runs clang-format and clang-tidy from Python wheels. Supports Python 3.9-3.14 across Windows, Linux, and macOS.

## Architecture

### Entry Points & Flow
- **Entry scripts**: `clang-format-hook` and `clang-tidy-hook` (defined in `pyproject.toml`)
- **Hook definitions**: `.pre-commit-hooks.yaml` configures both hooks with `types_or: [c++, c]`
- **Execution pattern**: Parse args → resolve/install tool version → subprocess.run → return (exit_code, output)

### Core Modules
- **`clang_format.py`**: Wraps clang-format with `-i` (in-place), supports `--verbose` and `--dry-run` modes
  - Returns `-1` for dry-run to distinguish from actual failures
- **`clang_tidy.py`**: Wraps clang-tidy, forces exit code 1 if "warning:" or "error:" in output
- **`util.py`**: Dynamic version resolution via PyPI JSON API + pip-based tool installation
  - `_resolve_version_from_pypi()`: Supports partial matches (e.g., "20" → "20.1.8"), resolves against PyPI in real time
  - No hardcoded version lists — versions are always up-to-date from PyPI

### Version Management Pattern
```python
# Users can specify partial versions
--version=21      # Resolves to latest 21.x.x
--version=21.1    # Resolves to latest 21.1.x
--version=21.1.8  # Exact version
```

## Development Workflows

### Local Testing
```bash
# Test hooks locally without installing
pre-commit try-repo ./.. clang-format --verbose --all-files
pre-commit try-repo ./.. clang-tidy --verbose --all-files

# Run test suite
uv run pytest -vv                    # All tests
uv run coverage run -m pytest        # With coverage
uv run pytest -m benchmark           # Performance tests only
```

### Adding/Modifying Features
1. **Update hook logic** in `cpp_linter_hooks/{clang_format,clang_tidy}.py`
2. **Add tests** in `tests/test_*.py` with `@pytest.mark.benchmark` for performance tracking
3. **Test with sample files** in `testing/` directory (use `good.c` as expected output)
4. **Update README.md** if user-facing behavior changes

### Dependency Management
- **Uses `uv`** for all dev operations (not pip directly)
- **Tool versions**: Resolved dynamically from PyPI at hook runtime — no manual updates needed
- **Version caching**: `_get_pypi_versions()` uses `lru_cache` to avoid repeated PyPI requests within a single run

## Project-Specific Conventions

### Return Value Pattern
All hook functions return `Tuple[int, str]`:
- `(0, "")` → Success
- `(1, output)` → Failure (print output)
- `(-1, output)` → Dry-run mode (clang-format only, convert to success in main)

### Testing Conventions
- Use `tmp_path` fixture to avoid modifying repo files
- Parametrize version tests: `@pytest.mark.parametrize` with versions 16-21
- Mark performance-sensitive tests with `@pytest.mark.benchmark`
- Compare formatted output against `testing/good.c` for correctness

### Argument Handling
```python
# Standard pattern in both hooks
parser = ArgumentParser()
parser.add_argument("--version", default=DEFAULT_VERSION)
hook_args, other_args = parser.parse_known_args(args)
# ... install tool if needed ...
command = ["tool-name"] + other_args  # Pass through unknown args
```

## Critical Files

- **`pyproject.toml`**: Defines entry points and dependencies
- **`util.py`**: Core version resolution + tool installation logic
- **`.pre-commit-hooks.yaml`**: Hook metadata for pre-commit framework
- **`testing/run.sh`**: Integration test script used in CI

## Integration Points

### PyPI Dependencies
- Fetches available versions from `https://pypi.org/pypi/{package}/json`
- Filters out pre-release versions using regex pattern `(alpha|beta|rc|dev|a\d+|b\d+)`
- Installs via `subprocess.run([sys.executable, "-m", "pip", "install", f"{tool}=={version}"])`

### Pre-commit Framework
- Hooks run in parallel (`require_serial: false`) for performance
- File type filtering via `types_or: [c++, c]`
- Users configure via `.pre-commit-config.yaml` with `args:` list

## Common Tasks

**Add support for a new argument:**
1. Add to ArgumentParser in hook module
2. Pass to subprocess command or handle in Python
3. Add test case in `tests/test_*.py`

**No manual version updates needed:** Tool versions are resolved dynamically from PyPI at runtime. When new versions are published to PyPI, hooks automatically discover them — no code changes required.

**Debug hook failures:**
- Add `--verbose` to clang-format args for detailed output
- Check `testing/run.sh` for integration test patterns
- Use `pre-commit run --verbose` for detailed pre-commit logs
