# Meson Project

If you use Meson, set up `compile_commands.json` and hook config like this:

## .pre-commit-config.yaml

```yaml
repos:
  - repo: https://github.com/cpp-linter/cpp-linter-hooks
    rev: v1.6.0
    hooks:
      - id: clang-format
        args: [--style=file, --version=21]
        files: ^(src|include)/.*\.(cpp|cc|cxx|h|hpp)$

      - id: clang-tidy
        args: [--compile-commands=builddir, --checks=.clang-tidy, --version=21]
        files: ^(src|include)/.*\.(cpp|cc|cxx)$
```

## Generate compile database for Meson

Run:

```bash
meson setup builddir
ninja -C builddir compile_commands.json
```

Meson writes `builddir/compile_commands.json`, and `cpp-linter-hooks` reads it directly
with `--compile-commands=builddir`.

```bash
pre-commit install
pre-commit run --all-files
```
