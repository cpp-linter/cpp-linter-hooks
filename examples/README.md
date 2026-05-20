# Examples

- [CMake project](cmake/) — the default for ~80% of C++ projects
- [Large project `files:` regex](large-project/) — scoping hooks for speed

## Quick snippets

### clang-format only (no build system)

```yaml
      - id: clang-format
        args: [--style=file, --version=21]
        files: \.(cpp|cc|cxx|c|h|hpp)$
```

### Meson

```bash
meson setup build    # auto-detect works with build/
```

Or point explicitly: `args: [--compile-commands=builddir, --checks=.clang-tidy]`.

### clang-tidy + compile_commands.json

```yaml
      - id: clang-tidy
        args: [--compile-commands=build, --checks=.clang-tidy, --version=21, --jobs=4]
        files: ^src/.*\.cpp$
```

Add `--fix` to auto-apply fixes.  Add `-v` to see which database is used.

### Monorepo

```yaml
      - id: clang-format
        name: clang-format (backend)
        args: [--style=file:backend/.clang-format, --version=21]
        files: ^backend/.*\.(cpp|hpp)$

      - id: clang-format
        name: clang-format (frontend)
        args: [--style=file:frontend/.clang-format, --version=21]
        files: ^frontend/.*\.(cpp|hpp)$
```

### CI (GitHub Actions)

```yaml
# .github/workflows/lint.yml
name: Lint
on: [push, pull_request]
jobs:
  pre-commit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - uses: pre-commit/action@v3.0.1
```
