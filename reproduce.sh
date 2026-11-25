#!/bin/sh
# One-command reproduction: run every check from the vendored data,
# then verify the SHA-256 manifest. This is the command the CI
# workflow runs on a clean checkout, and the command in the README.
set -e
cd "$(dirname "$0")"
bash scripts/run_all.sh
bash verify_digests.sh
echo "REPRODUCE OK"
