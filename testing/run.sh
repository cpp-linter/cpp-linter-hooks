#!/bin/bash
# 2 Failed cases are expected
pre-commit clean
pre-commit run -c testing/pre-commit-config.yaml --files testing/main.c | tee -a result.txt || true
git restore testing/main.c

# 10 Failed cases are expected
pre-commit clean
pre-commit run -c testing/pre-commit-config-version.yaml --files testing/main.c | tee -a result.txt || true
git restore testing/main.c
cat result.txt

# 2 Failed cases are expected
pre-commit clean
pre-commit run -c testing/pre-commit-config-verbose.yaml --files testing/main.c | tee -a result.txt || true
git restore testing/main.c
cat result.txt

failed_cases=`grep -c "Failed" result.txt`

echo $failed_cases " cases failed."

if [ $failed_cases -eq 10 ]; then
    echo "=============================="
    echo "Test cpp-linter-hooks success."
    echo "=============================="
    exit 0
    rm result.txt
else
    echo "============================="
    echo "Test cpp-linter-hooks failed."
    echo "============================="
    exit 1
fi
