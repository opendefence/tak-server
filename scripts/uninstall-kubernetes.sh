#!/usr/bin/env bash
set -euo pipefail
if [[ $# != 1 ]]; then
    echo "Usage: $0 namespace" >&2
    exit 2
fi
kubectl --namespace="$1" delete statefulset,job,service,networkpolicy,configmap \
    --selector=app.kubernetes.io/name=tak-server --ignore-not-found
