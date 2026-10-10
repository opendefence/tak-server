#!/usr/bin/env bash
# Exercise the actual vendor loader and setenv script in a disposable image.
set -euo pipefail
scripts="$(cd "$(dirname "$0")/../scripts" && pwd)"
unset TAKCL_CORECONFIG_PATH
if output="$(bash "${scripts}/run-tak.sh" config 2>&1)"; then
  echo 'FAIL: server started without its role configuration path' >&2
  exit 1
fi
grep -q 'TAKCL_CORECONFIG_PATH is required' <<< "$output"
if grep -q 'ClassNotFoundException' <<< "$output"; then
  echo 'FAIL: vendor loader did not load the external launcher' >&2
  exit 1
fi
echo 'PASS: vendor loader reaches the external path guard before server startup'
