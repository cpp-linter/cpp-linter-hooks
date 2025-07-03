rm -f result.txt
git restore testing/main.c

for config in testing/pre-commit-config.yaml testing/pre-commit-config-version.yaml testing/pre-commit-config-verbose.yaml; do
    pre-commit clean
    pre-commit run -c $config --files testing/main.c | tee -a result.txt || true
    git restore testing/main.c
done

failed_cases=`grep -c "Failed" result.txt`

echo $failed_cases " cases failed."

if [ $failed_cases -eq 9 ]; then
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
