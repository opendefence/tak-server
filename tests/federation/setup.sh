#!/usr/bin/env bash
# Provision only the two labelled federation fixture namespaces.
set -euo pipefail
umask 077
root=$(cd "$(dirname "$0")/../.." && pwd)
kubeconfig=${1:?Usage: setup.sh KUBECONFIG IMAGE}
image=${2:?Supply the image already loaded into the test cluster}
test -f "$kubeconfig"
kubectl() { command kubectl --kubeconfig "$kubeconfig" "$@"; }

for namespace in tak-federation-a tak-federation-b; do
  if kubectl get namespace "$namespace" >/dev/null 2>&1; then
    owner=$(kubectl get namespace "$namespace" -o 'jsonpath={.metadata.labels.opendefence\.io/test}')
    [[ "$owner" == federation ]] || { echo "Refusing unowned namespace $namespace" >&2; exit 1; }
  else
    kubectl create namespace "$namespace"
    kubectl label namespace "$namespace" opendefence.io/test=federation
  fi
  work="$root/outputs/federation/$namespace"
  mkdir -p "$work"
  host="tak-server.$namespace.svc"
  kubectl -n "$namespace" apply -f "$root/k8s/local/passwords.yaml"
  kubectl -n "$namespace" wait --for=condition=Ready externalsecret/tak-database-runtime externalsecret/tak-store-passwords --timeout=180s
  kubectl -n "$namespace" apply -f "$root/k8s/local/database.yaml"
  kubectl -n "$namespace" wait --for=condition=Ready cluster/tak-database --timeout=600s

  cat > "$work/kustomization.yaml" <<EOF
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
namespace: $namespace
resources:
  - $root/k8s/local/certificates.yaml
  - $root/tests/federation/identities.yaml
patches:
  - target: {kind: Certificate, name: 'tak-(https-identity|client-trust|federation-bootstrap|probe-identity|federation-issuer)'}
    patch: |-
      - op: replace
        path: /spec/issuerRef
        value: {kind: Issuer, name: federation-ca}
  - target: {kind: Certificate, name: 'tak-(cot|https)-identity'}
    patch: |-
      - op: replace
        path: /spec/commonName
        value: $host
      - op: replace
        path: /spec/dnsNames
        value: [$host]
EOF
  kubectl kustomize "$work" --load-restrictor LoadRestrictionsNone | kubectl apply -f -
  kubectl -n "$namespace" wait --for=condition=Ready certificates --all --timeout=300s

  for stage in schema grants base; do
    cat > "$work/kustomization.yaml" <<EOF
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
namespace: $namespace
resources:
  - ../../../k8s/$stage
images:
  - name: tak-server
    newName: ${image%:*}
    newTag: ${image##*:}
EOF
    if [[ "$stage" == base ]]; then
      cat >> "$work/kustomization.yaml" <<EOF
configMapGenerator:
  - name: tak-settings
    behavior: merge
    literals: [TAK_SERVER_ADDRESS=$host]
EOF
    fi
    kubectl kustomize "$work" --load-restrictor LoadRestrictionsNone | kubectl apply -f -
    case "$stage" in
      schema) kubectl -n "$namespace" wait --for=condition=complete job/tak-schema-5-8-92 --timeout=900s ;;
      grants) kubectl -n "$namespace" wait --for=condition=complete job/tak-grants-5-8-92 --timeout=180s ;;
      base)
        kubectl -n "$namespace" rollout status statefulset/tak-server --timeout=600s
        kubectl -n "$namespace" wait --for=condition=complete job/tak-admin-bootstrap --timeout=180s
        ;;
    esac
  done

  for identity in tak-probe-identity federation-client tak-cot-identity; do
    for key in tls.crt tls.key ca.crt; do
      # The runner needs no server private key.
      [[ "$identity/$key" == tak-cot-identity/tls.key ]] && continue
      kubectl -n "$namespace" get secret "$identity" -o "go-template={{index .data \"$key\" | base64decode}}" > "$work/$identity.$key"
    done
  done
  kubectl -n "$namespace" exec -i tak-server-0 -c messaging -- sh -ceu '
    certificate=$(mktemp)
    trap '\''rm -f "$certificate"'\'' EXIT
    cat > "$certificate"
    TAK_MESSAGING_HOST=tak-ignite /opt/scripts/user-manager.sh certmod -g federation-test "$certificate"
  ' < "$work/federation-client.tls.crt"
done
echo "Federation fixtures ready. Private credentials are in outputs/federation."
