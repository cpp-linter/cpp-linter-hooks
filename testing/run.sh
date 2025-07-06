#!/bin/bash
echo "==========================="
echo "Test pre-commit-config.yaml"
echo "==========================="
pre-commit clean
pre-commit run -c testing/pre-commit-config.yaml --files testing/main.c | tee -a result.txt || true
git restore testing/main.c

echo "===================================="
echo "Test pre-commit-config-version.yaml"
echo "===================================="
pre-commit clean
pre-commit run -c testing/pre-commit-config-version.yaml --files testing/main.c | tee -a result.txt || true
git restore testing/main.c

echo "===================================="
echo "Test pre-commit-config-verbose.yaml"
echo "===================================="
pre-commit clean
pre-commit run -c testing/pre-commit-config-verbose.yaml --files testing/main.c | tee -a result.txt || true
git restore testing/main.c

echo "=================================================================================="
echo "print result.txt"
cat result.txt
echo "=================================================================================="

failed_cases=`grep -c "Failed" result.txt`

echo $failed_cases " cases failed."

if [ $failed_cases -eq 9 ]; then
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
