# Meson Project

If you already have a Meson project, configure the hooks and generate a compilation database.

## .pre-commit-config.yaml

```yaml
repos:
  - repo: https://github.com/cpp-linter/cpp-linter-hooks
    rev: v1.6.1
    hooks:
      - id: clang-format
        args: [--style=file, --version=21]
        files: ^(src|include)/.*\.(cpp|cc|cxx|h|hpp)$

      - id: clang-tidy
        args: [--version=21, --compile-commands=builddir]
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

`--compile-commands` takes the **directory** containing `compile_commands.json`,
not the file path. `builddir/` is not one of the auto-detected directories, so the
explicit argument above is required. If you use `meson setup build` instead,
`build/` is auto-detected and the argument can be omitted.

To regenerate the database after changing build options, run
`meson setup --reconfigure builddir` before the hooks.
