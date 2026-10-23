# Meson Project

If you already have a Meson project, configure the hooks and generate a compilation database.

## .pre-commit-config.yaml

```yaml
repos:
  - repo: https://github.com/cpp-linter/cpp-linter-hooks
    rev: v1.8.1
    hooks:
      - id: clang-format
        args: [--style=file]
        files: ^(src|include)/.*\.(cpp|cc|cxx|h|hpp)$

      - id: clang-tidy
        files: ^(src|include)/.*\.(cpp|cc|cxx)$
```

## Generate the compilation database

Run from the project root, where `meson.build` lives:

```bash
meson setup builddir
pre-commit install
pre-commit run --all-files
```

Meson's default Ninja backend writes `builddir/compile_commands.json` during setup.
This gives `clang-tidy` the compiler flags and include paths for each source file.
No separate compilation step is required to generate the database. If the project
needs generated headers, build those first with `meson compile -C builddir`.

The hook auto-detects `builddir/` and `build/`. For another directory, pass
`--compile-commands=<dir>`: it takes the **directory** containing
`compile_commands.json`, not the file path.

To regenerate the database after changing build options, run
`meson setup --reconfigure builddir` before the hooks.
