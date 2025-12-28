#!/bin/bash
echo "Running all tests with coverage and generating HTML report..."
# Generate a self-contained test report in the root directory
python3 -m pytest -v --cov=. --cov-report=html --html=test_report.html --self-contained-html
echo "Test run complete."
echo "HTML coverage report generated in 'htmlcov/' directory."
echo "HTML test report generated as 'test_report.html'."
