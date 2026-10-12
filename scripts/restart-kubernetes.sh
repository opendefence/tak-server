#!/usr/bin/env bash
# Replace all roles together and report failure after a finite wait.
set -euo pipefail
if [[ $# != 1 ]]; then
  echo "Usage: $0 namespace" >&2
  exit 2
fi
kubectl --namespace="$1" rollout restart statefulset/tak-server
kubectl --namespace="$1" rollout status statefulset/tak-server --timeout=300s
