#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

echo "TeleMemetry Memory Rail Demo"
echo "Running public verified-recall benchmark..."
python3 run.py "$@"

echo
echo "Verifying result package..."
python3 verify.py results/latest

echo
echo "Result summary:"
cat results/latest/RESULT_SUMMARY.txt
