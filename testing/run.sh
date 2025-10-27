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
    pre-commit clean
    pre-commit run -c testing/$config --files testing/main.c | tee -a result.txt || true
    git restore testing/main.c
done

echo "=================================================================================="
echo "Print result.txt"
cat result.txt
echo "=================================================================================="

failed_cases=$(grep -c "Failed" result.txt)

echo "$failed_cases cases failed."

if [ $failed_cases -eq 21 ]; then
    echo "=============================="
    echo "Test cpp-linter-hooks success."
    echo "=============================="
    rm result.txt
    exit 0
else
    echo "============================="
    echo "Test cpp-linter-hooks failed."
    echo "============================="
    exit 1
fi
