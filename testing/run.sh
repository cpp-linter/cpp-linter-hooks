#!/bin/bash
# Pre-commit integration tests for cpp-linter-hooks.
#
# Each test runs a specific pre-commit configuration against testing/main.c
# and checks whether the expected outcome (pass or fail) is observed.
# testing/main.c is restored after every test so they are independent.
#
# These tests exercise the full pre-commit pipeline (hook definitions,
# entry points, argument passing) which the pytest unit tests do not cover.
# The hook logic itself is tested in tests/test_integration.py.

set -euo pipefail

PASS=0
FAIL=0

# run_test <description> <config-file> <files> <expect-nonzero>
#
#   description    – human-readable name shown in output
#   config-file    – path to the pre-commit config (relative to repo root)
#   files          – space-separated list of files passed to --files
#   expect-nonzero – "true" if the hook is expected to report failures,
#                    "false" if it should exit cleanly
run_test() {
    local description="$1"
    local config="$2"
    local files="$3"
    local expect_nonzero="$4"

    echo "---- $description ----"
    uvx pre-commit clean

    local output
    # shellcheck disable=SC2086  # word-splitting of $files is intentional
    if output=$(uvx pre-commit run -c "$config" --files $files 2>&1); then
        local got_nonzero=false
    else
        local got_nonzero=true
    fi

    git restore testing/main.c 2>/dev/null || true

    if [[ "$expect_nonzero" == "$got_nonzero" ]]; then
        echo "PASS: $description"
        PASS=$((PASS + 1))
    else
        echo "FAIL: $description (expect_nonzero=$expect_nonzero, got_nonzero=$got_nonzero)"
        echo "$output"
        FAIL=$((FAIL + 1))
    fi
    echo ""
}

# ── Basic config: clang-format + clang-tidy on the unformatted file ──────────
# Expected: clang-format rewrites main.c → pre-commit reports failure.
run_test \
    "basic: clang-format + clang-tidy on unformatted file" \
    "testing/pre-commit-config.yaml" \
    "testing/main.c" \
    "true"

# ── Version config: explicit versions 16–21 ──────────────────────────────────
# Expected: at least clang-format v16 rewrites the file → failure reported.
run_test \
    "versions 16-21: clang-format + clang-tidy" \
    "testing/pre-commit-config-version.yaml" \
    "testing/main.c" \
    "true"

# ── Verbose config: --verbose and -v flags ────────────────────────────────────
# Expected: clang-format rewrites main.c (verbose output goes to stderr).
run_test \
    "verbose: --verbose and -v flags" \
    "testing/pre-commit-config-verbose.yaml" \
    "testing/main.c" \
    "true"

# ── Style config: LLVM / Google / Microsoft / WebKit / Mozilla / Chromium ────
# Expected: each style reformats main.c differently → failure reported.
run_test \
    "styles: LLVM, Google, Microsoft, WebKit, Mozilla, Chromium" \
    "testing/pre-commit-config-style.yaml" \
    "testing/main.c" \
    "true"

# ── Parallel config: clang-tidy --jobs=2 on two source files ─────────────────
# Expected: clang-tidy finds issues in at least one file → failure reported.
run_test \
    "parallel: clang-tidy --jobs=2 on main.c + good.c" \
    "testing/pre-commit-config-parallel.yaml" \
    "testing/main.c testing/good.c" \
    "true"

# ── Summary ───────────────────────────────────────────────────────────────────
echo "Results: $PASS passed, $FAIL failed"

if [[ -n "${GITHUB_STEP_SUMMARY:-}" ]]; then
    {
        echo "### cpp-linter-hooks pre-commit integration test results"
        echo ""
        echo "| Result | Count |"
        echo "|--------|-------|"
        echo "| Passed | $PASS |"
        echo "| Failed | $FAIL |"
    } >> "$GITHUB_STEP_SUMMARY"
fi

[[ $FAIL -eq 0 ]]
