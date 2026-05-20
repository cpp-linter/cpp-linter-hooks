# Large Project — `files:` Regex

Use `files:` to limit hooks to relevant directories.  This is the #1 perf lever.

## One-size-fits-most

```yaml
      - id: clang-format
        files: ^(src|include)/.*\.(cpp|cc|cxx|h|hpp)$
```

## Common patterns

```yaml
# Exclude generated code
files: ^src/(?!generated/|proto/).*\.(cpp|hpp)$

# Library (public headers + private src)
files: ^(include|src)/.*\.(cpp|cc|cxx|h|hpp|hxx)$

# Application (no public headers)
files: ^src/.*\.(cpp|cc|cxx|h|hpp)$

# Qt (skip moc_)
files: ^src/(?!moc_|ui_).*\.(cpp|h)$

# CUDA
files: ^src/.*\.(cpp|cc|cxx|cu|cuh|h|hpp)$

# Embedded / bare-metal C
files: \.(c|h|s|S)$
```

## Perf tips

- **Don't lint headers directly with `clang-tidy`** — they're processed when a `.cpp` includes them.  Restrict to `files: ^src/.*\.cpp$`.
- **Use `--jobs=N` for `clang-tidy`** — start with `N=2`, go up to CPU core count.
- **`--dry-run` for `clang-format` in CI** — fail with a readable diff instead of auto-committing formatting.
