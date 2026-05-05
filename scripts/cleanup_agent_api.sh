#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "$0")/common.sh"

# Remove API key scraper deployments
kubectl -n lab-main delete deploy edot-main-metrics-api --ignore-not-found
kubectl -n lab-main delete configmap edot-main-metrics-api-config --ignore-not-found
kubectl -n lab-main delete ds edot-main-logs-api --ignore-not-found
kubectl -n lab-main delete configmap edot-main-logs-api-config --ignore-not-found
kubectl -n lab-main delete serviceaccount edot-main-logs-api --ignore-not-found
kubectl delete clusterrole edot-main-logs-api --ignore-not-found
kubectl delete clusterrolebinding edot-main-logs-api --ignore-not-found

# Remove extra cluster namespace and all resources within it
if kubectl get namespace "${EXTRA_CLUSTER_NAMESPACE}" >/dev/null 2>&1; then
  kubectl delete namespace "${EXTRA_CLUSTER_NAMESPACE}" --ignore-not-found
fi
kubectl -n lab-main delete secret es-creds-extra-cluster --ignore-not-found

# Remove API key secrets
kubectl -n lab-main delete secret es-creds-source-cluster --ignore-not-found
kubectl -n lab-monitoring delete secret es-creds-monitoring-cluster --ignore-not-found

# Remove the gateway
kubectl -n lab-monitoring delete deploy edot-gateway --ignore-not-found
kubectl -n lab-monitoring delete service edot-gateway --ignore-not-found
kubectl -n lab-monitoring delete configmap edot-gateway-config --ignore-not-found

# Remove ingest role from monitoring cluster
MONITORING_ELASTIC_PASSWORD="$(kubectl -n lab-monitoring get secret elasticsearch-monitoring-es-elastic-user \
  -o jsonpath='{.data.elastic}' | base64 -d 2>/dev/null || true)"
if [[ -n "${MONITORING_ELASTIC_PASSWORD}" ]]; then
  kubectl -n lab-monitoring port-forward service/elasticsearch-monitoring-es-http 19202:9200 \
    >/tmp/edot-cleanup-mon-pf.log 2>&1 &
  MON_PF_PID="$!"
  trap 'kill "${MON_PF_PID}" >/dev/null 2>&1 || true' EXIT
  for _ in $(seq 1 20); do
    if curl -sk "https://127.0.0.1:19202/_cluster/health" >/dev/null 2>&1; then break; fi
    sleep 1
  done
  curl -sk -u "elastic:${MONITORING_ELASTIC_PASSWORD}" \
    -X DELETE "https://127.0.0.1:19202/_security/role/${APIKEY_INGEST_ROLE_NAME}" >/dev/null || true
  kill "${MON_PF_PID}" >/dev/null 2>&1 || true
  trap - EXIT
fi

echo "API key OTEL agent workflow removed."
