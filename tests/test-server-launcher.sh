#!/usr/bin/env bash
# Exercise the actual vendor loader with the image's pinned JVM options.
set -euo pipefail
scripts="$(cd "$(dirname "$0")/../scripts" && pwd)"
vendor_options="$(bash -c '. /opt/tak/setenv.sh >/dev/null; printf %s "$JDK_JAVA_OPTIONS"')"
for option in $vendor_options; do
  case "$option" in -Dloader.path=*) continue ;; esac
  if [[ " ${JDK_JAVA_OPTIONS:-} " != *" $option "* ]]; then
    echo "FAIL: image JVM options omit $option" >&2
    exit 1
  fi
done
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
if manager_output="$("${scripts}/user-manager.sh" --help 2>&1)"; then
  echo 'FAIL: pinned UserManager unexpectedly accepted the probe command' >&2
  exit 1
fi
grep -Fq '"--help" is not a valid command!' <<< "$manager_output"
echo 'PASS: UserManager reaches its command parser with pinned JVM options'
