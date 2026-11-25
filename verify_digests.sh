#!/bin/sh
# Verify the SHA-256 manifest for every file in this reference.
# Exits 0 only if every listed file matches. Run from the pack root.
set -e
cd "$(dirname "$0")"
sha256sum -c SHA256SUMS
