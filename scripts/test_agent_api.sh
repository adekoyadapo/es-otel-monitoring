#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "$0")/common.sh"

if [[ -t 1 ]]; then
  GREEN=$'\033[32m'
  RED=$'\033[31m'
  BLUE=$'\033[34m'
  RESET=$'\033[0m'
else
  GREEN=""
  RED=""
  BLUE=""
  RESET=""
fi

fail() {
  echo "${RED}$1${RESET}" >&2
  exit 1
}

# Port-forward both clusters for API checks
kubectl -n lab-main port-forward service/elasticsearch-main-es-http 19201:9200 \
  >/tmp/edot-apikey-agent-pf.log 2>&1 &
PF_PID="$!"
kubectl -n lab-monitoring port-forward service/elasticsearch-monitoring-es-http 19202:9200 \
  >/tmp/edot-apikey-monitoring-pf.log 2>&1 &
MONITORING_PF_PID="$!"
trap 'kill "${PF_PID}" >/dev/null 2>&1 || true; kill "${MONITORING_PF_PID}" >/dev/null 2>&1 || true' EXIT
for _ in $(seq 1 30); do
  if curl -sk "https://127.0.0.1:19201/_cluster/health" >/dev/null 2>&1; then break; fi
  sleep 1
done

MONITORING_ELASTIC_PASSWORD="$(kubectl -n lab-monitoring get secret elasticsearch-monitoring-es-elastic-user \
  -o jsonpath='{.data.elastic}' | base64 -d)"
MONITORING_ES_URL="https://127.0.0.1:19202"

echo "[1/5] Checking source cluster API key secret"
API_KEY_ENCODED="$(kubectl -n lab-main get secret es-creds-source-cluster \
  -o jsonpath='{.data.api_key}' | base64 -d 2>/dev/null || true)"
if [[ -z "${API_KEY_ENCODED}" ]]; then
  fail "Secret es-creds-source-cluster not found or api_key key is missing in lab-main"
fi
echo "${GREEN}  OK: es-creds-source-cluster secret present${RESET}"

echo "[2/5] Validating API key authenticates against source cluster"
AUTH_CODE="$(curl -sk -o /dev/null -w '%{http_code}' \
  -H "Authorization: ApiKey ${API_KEY_ENCODED}" \
  "https://127.0.0.1:19201/_security/_authenticate")"
if [[ "${AUTH_CODE}" != "200" ]]; then
  AUTH_RESP="$(curl -sk -H "Authorization: ApiKey ${API_KEY_ENCODED}" \
    "https://127.0.0.1:19201/_security/_authenticate")"
  fail "API key authentication failed (HTTP ${AUTH_CODE}). Response: ${AUTH_RESP}"
fi
echo "${GREEN}  OK: API key authenticates successfully against source cluster${RESET}"

echo "[3/5] Checking monitoring cluster API key secret"
MONITORING_API_KEY="$(kubectl -n lab-monitoring get secret es-creds-monitoring-cluster \
  -o jsonpath='{.data.api_key}' | base64 -d 2>/dev/null || true)"
if [[ -z "${MONITORING_API_KEY}" ]]; then
  fail "Secret es-creds-monitoring-cluster not found or api_key key is missing in lab-monitoring"
fi
echo "${GREEN}  OK: es-creds-monitoring-cluster secret present${RESET}"

echo "[4/5] Verifying OTEL collector pod status"
kubectl -n lab-main wait --for=condition=Available deploy/edot-main-metrics-api --timeout=60s >/dev/null
kubectl -n lab-monitoring rollout status deploy/edot-gateway --timeout=60s >/dev/null 2>&1 \
  || fail "edot-gateway is not running in lab-monitoring. Run make apikey-agent-up to redeploy."
echo "${GREEN}  OK: OTEL metrics collector and gateway are running${RESET}"

echo "[5/5] Waiting for metrics to reach the monitoring cluster"
APIKEY_PRESENT=0
APIKEY_DOC_COUNT=0
for _ in $(seq 1 36); do
  APIKEY_CODE="$(curl -sk -o /dev/null -w '%{http_code}' \
    -u "elastic:${MONITORING_ELASTIC_PASSWORD}" \
    "${MONITORING_ES_URL}/_data_stream/${APIKEY_METRICS_DATASTREAM}")"
  if [[ "${APIKEY_CODE}" == "200" ]]; then
    APIKEY_DOC_COUNT="$(curl -sk -u "elastic:${MONITORING_ELASTIC_PASSWORD}" \
      "${MONITORING_ES_URL}/${APIKEY_METRICS_DATASTREAM}/_count" \
      | python3 -c "import sys,json; print(json.load(sys.stdin).get('count',0))" 2>/dev/null || echo 0)"
    if [[ "${APIKEY_DOC_COUNT:-0}" -gt 0 ]]; then
      APIKEY_PRESENT=1
      break
    fi
  fi
  sleep 10
done
if [[ "${APIKEY_PRESENT}" -ne 1 ]]; then
  fail "No metrics found in ${APIKEY_METRICS_DATASTREAM} after 6 minutes"
fi
echo "${GREEN}  OK: data stream '${APIKEY_METRICS_DATASTREAM}' has ${APIKEY_DOC_COUNT} documents${RESET}"

check_metric_exists() {
  local field="$1"
  local count
  for _ in $(seq 1 18); do
    count="$(curl -sk -u "elastic:${MONITORING_ELASTIC_PASSWORD}" \
      -H 'Content-Type: application/json' \
      "${MONITORING_ES_URL}/${APIKEY_METRICS_DATASTREAM}/_count" \
      -d "{\"query\":{\"exists\":{\"field\":\"${field}\"}}}" 2>/dev/null \
      | python3 -c "import sys,json; print(json.load(sys.stdin).get('count',0))" 2>/dev/null || echo 0)"
    if [[ "${count:-0}" -gt 0 ]]; then return 0; fi
    sleep 10
  done
  return 1
}

for metric_field in "metrics.elasticsearch.cluster.nodes" "metrics.elasticsearch.index.documents"; do
  check_metric_exists "${metric_field}" \
    || fail "No document with non-empty field '${metric_field}' in ${APIKEY_METRICS_DATASTREAM}"
  echo "${GREEN}  OK: metric field '${metric_field}' present with data${RESET}"
done

echo "${BLUE}  Source secret  : es-creds-source-cluster (lab-main)${RESET}"
echo "${BLUE}  Gateway secret : es-creds-monitoring-cluster (lab-monitoring)${RESET}"
echo "${BLUE}  Output stream  : ${APIKEY_METRICS_DATASTREAM}${RESET}"
echo "${BLUE}  Output path    : elasticsearchreceiver → headers_setter (ApiKey) → ES main → edot-gateway → monitoring ES${RESET}"

echo "${GREEN}All API key OTEL agent tests passed${RESET}"
