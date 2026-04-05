#!/bin/bash

configs=(
    "pre-commit-config.yaml"
    "pre-commit-config-version.yaml"
    "pre-commit-config-verbose.yaml"
    "pre-commit-config-style.yaml"
)

for config in "${configs[@]}"; do
    echo "===================================="
    echo "Test $config"
    echo "===================================="
    uvx pre-commit clean
    uvx pre-commit run -c testing/$config --files testing/main.c | tee -a result.txt || true
    git restore testing/main.c
done

echo "=================================================================================="
echo "Print result.txt"
cat result.txt
echo "=================================================================================="

failed_cases=$(grep -c "Failed" result.txt)

echo "$failed_cases cases failed."

if [[ $failed_cases -eq 21 ]]; then
    echo "=============================="
    echo "Test cpp-linter-hooks success."
    echo "=============================="
    result="success"
    rm result.txt
    exit_code=0
else
    echo "============================="
    echo "Test cpp-linter-hooks failed."
    echo "============================="
    result="failure"
    exit_code=1
fi

# Test parallel execution with multiple source files
echo "===================================="
echo "Test pre-commit-config-parallel.yaml"
echo "===================================="
uvx pre-commit clean
uvx pre-commit run -c testing/pre-commit-config-parallel.yaml \
    --files testing/main.c testing/good.c | tee -a parallel_result.txt || true
git restore testing/main.c

parallel_failed=$(grep -c "Failed" parallel_result.txt 2>/dev/null || echo "0")
echo "$parallel_failed parallel cases failed."

if [[ $parallel_failed -ge 1 ]]; then
    echo "========================================================"
    echo "Parallel test passed (expected failures detected: $parallel_failed)."
    echo "========================================================"
    parallel_result="success"
    rm parallel_result.txt
else
    echo "==========================================="
    echo "Parallel test failed (no failures detected)."
    echo "==========================================="
    parallel_result="failure"
    exit_code=1
fi

# Add result to GitHub summary if running in GitHub Actions
if [[ -n "$GITHUB_STEP_SUMMARY" ]]; then
    {
        echo "### cpp-linter-hooks Test Result"
        echo ""
        echo "**Result:** $result"
        echo ""
        echo "**Failed cases:** $failed_cases"
        echo ""
        echo "**Parallel test:** $parallel_result"
    } >> "$GITHUB_STEP_SUMMARY"
fi

exit $exit_code
