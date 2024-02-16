pre-commit clean
pre-commit run --files testing/main.c | tee result.txt || true

failed_cases=`grep -c "Failed" result.txt`

if [ $failed_cases -eq 2 ]; then
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
