# Examples

- [CMake project](cmake/)
- [Meson project](meson/)
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
meson setup builddir    # builddir/ and build/ are auto-detected
```

For another directory, point explicitly: `args: [--compile-commands=mydir]`.

### clang-tidy + compile_commands.json

```yaml
      - id: clang-tidy
        args: [--compile-commands=build, --version=21, --jobs=4]
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
      - uses: actions/checkout@v7
      - uses: actions/setup-python@v7
        with: { python-version: '3.11' }
      # clang-tidy needs the compilation database in CI too: without it, the
      # hook fails when CI is set.
      - run: cmake -B build -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
      - uses: pre-commit/action@v3.0.1
```

`pre-commit/action` runs `pre-commit run --all-files`, so clang-tidy checks every line there.
