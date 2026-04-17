#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "$0")/common.sh"

HOST_IP="${HOST_IP:-$(./scripts/detect_host_ip.sh)}"
MAIN_ES_URL="https://es-main.${HOST_IP}.sslip.io"
MAIN_KIBANA_URL="https://kibana-main.${HOST_IP}.sslip.io"
MONITORING_ES_URL="https://es-monitoring.${HOST_IP}.sslip.io"
MONITORING_KIBANA_URL="https://kibana-monitoring.${HOST_IP}.sslip.io"

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

echo "[1/8] Waiting for TLS certificates"
kubectl -n lab-main wait --for=condition=Ready certificate/es-main-cert --timeout=180s
kubectl -n lab-monitoring wait --for=condition=Ready certificate/es-monitoring-cert --timeout=180s
echo "${GREEN}  OK: TLS certificates are ready${RESET}"

echo "[2/8] Verifying main Elasticsearch authentication"
MAIN_ELASTIC_PASSWORD="$(kubectl -n lab-main get secret elasticsearch-main-es-elastic-user -o jsonpath='{.data.elastic}' | base64 -d)"
AUTH_RESP="$(curl -sk -u "elastic:${MAIN_ELASTIC_PASSWORD}" "${MAIN_ES_URL}/_security/_authenticate")"
echo "${AUTH_RESP}" | grep -q '"username":"elastic"'
echo "${GREEN}  OK: main Elasticsearch auth succeeded${RESET}"

echo "[3/8] Checking main Kibana ingress"
MAIN_KIBANA_CODE="$(curl -sk -o /dev/null -w '%{http_code}' "${MAIN_KIBANA_URL}")"
if [[ "${MAIN_KIBANA_CODE}" != "200" && "${MAIN_KIBANA_CODE}" != "302" ]]; then
  fail "Main Kibana endpoint check failed. HTTP ${MAIN_KIBANA_CODE}"
fi
echo "${GREEN}  OK: main Kibana ingress returned HTTP ${MAIN_KIBANA_CODE}${RESET}"

echo "[4/8] Checking monitoring Kibana ingress"
MONITORING_KIBANA_CODE="$(curl -sk -o /dev/null -w '%{http_code}' "${MONITORING_KIBANA_URL}")"
if [[ "${MONITORING_KIBANA_CODE}" != "200" && "${MONITORING_KIBANA_CODE}" != "302" ]]; then
  fail "Monitoring Kibana endpoint check failed. HTTP ${MONITORING_KIBANA_CODE}"
fi
echo "${GREEN}  OK: monitoring Kibana ingress returned HTTP ${MONITORING_KIBANA_CODE}${RESET}"

echo "[5/8] Waiting for EDOT data streams to appear in the monitoring cluster"
MONITORING_ELASTIC_PASSWORD="$(kubectl -n lab-monitoring get secret elasticsearch-monitoring-es-elastic-user -o jsonpath='{.data.elastic}' | base64 -d)"
ES_METRICS_DATASTREAM_PRESENT=0
ES_LOGS_DATASTREAM_PRESENT=0
for _ in $(seq 1 20); do
  ES_METRICS_DATASTREAM_CODE="$(curl -sk -o /dev/null -w '%{http_code}' -u "elastic:${MONITORING_ELASTIC_PASSWORD}" "${MONITORING_ES_URL}/_data_stream/logs-elasticsearch.metrics-main")"
  ES_LOGS_DATASTREAM_CODE="$(curl -sk -o /dev/null -w '%{http_code}' -u "elastic:${MONITORING_ELASTIC_PASSWORD}" "${MONITORING_ES_URL}/_data_stream/logs-elasticsearch.logs.otel-main")"
  if [[ "${ES_METRICS_DATASTREAM_CODE}" == "200" ]]; then
    ES_METRICS_DATASTREAM_PRESENT=1
  fi
  if [[ "${ES_LOGS_DATASTREAM_CODE}" == "200" ]]; then
    ES_LOGS_DATASTREAM_PRESENT=1
  fi
  ES_METRICS_COUNT="$(curl -sk -u "elastic:${MONITORING_ELASTIC_PASSWORD}" "${MONITORING_ES_URL}/logs-elasticsearch.metrics-main/_count" | sed -n 's/.*"count":\([0-9][0-9]*\).*/\1/p')"
  ES_LOGS_COUNT="$(curl -sk -u "elastic:${MONITORING_ELASTIC_PASSWORD}" "${MONITORING_ES_URL}/logs-elasticsearch.logs.otel-main/_count" | sed -n 's/.*"count":\([0-9][0-9]*\).*/\1/p')"
  if [[ "${ES_METRICS_DATASTREAM_PRESENT}" -eq 1 && "${ES_LOGS_DATASTREAM_PRESENT}" -eq 1 && "${ES_METRICS_COUNT:-0}" -gt 0 && "${ES_LOGS_COUNT:-0}" -gt 0 ]]; then
    break
  fi
  sleep 15
done

if [[ "${ES_METRICS_DATASTREAM_PRESENT}" -ne 1 ]]; then
  fail "Metrics data stream logs-elasticsearch.metrics-main was not created in the monitoring cluster"
fi

if [[ "${ES_LOGS_DATASTREAM_PRESENT}" -ne 1 ]]; then
  fail "Logs data stream logs-elasticsearch.logs.otel-main was not created in the monitoring cluster"
fi
echo "${GREEN}  OK: expected EDOT data streams are present${RESET}"

echo "[6/8] Verifying metrics documents were shipped"
if [[ "${ES_METRICS_COUNT:-0}" -le 0 ]]; then
  fail "No Elasticsearch metrics documents were shipped to the monitoring cluster"
fi
echo "${GREEN}  OK: metrics data stream has ${ES_METRICS_COUNT} documents${RESET}"

echo "[7/8] Verifying log documents were shipped"
if [[ "${ES_LOGS_COUNT:-0}" -le 0 ]]; then
  fail "No Elasticsearch log documents were shipped to the monitoring cluster"
fi
echo "${GREEN}  OK: logs data stream has ${ES_LOGS_COUNT} documents${RESET}"

echo "[8/8] Verifying OTEL dashboard import"
if dashboard_import_supported; then
  DASHBOARD_CODE="$(curl -sk -o /dev/null -w '%{http_code}' -u "elastic:${MONITORING_ELASTIC_PASSWORD}" -H 'kbn-xsrf: true' "${MONITORING_KIBANA_URL}/api/saved_objects/dashboard/${OTEL_MONITORING_DASHBOARD_ID}")"
  if [[ "${DASHBOARD_CODE}" != "200" ]]; then
    fail "OTEL dashboard ${OTEL_MONITORING_DASHBOARD_ID} was not imported into monitoring Kibana"
  fi
  echo "${GREEN}  OK: OTEL dashboard ${OTEL_MONITORING_DASHBOARD_ID} is present${RESET}"
else
  echo "${BLUE}  SKIP: dashboard import not supported for ES_VERSION ${ES_VERSION} (requires >= ${DASHBOARD_IMPORT_MIN_VERSION})${RESET}"
fi

echo "${GREEN}All tests passed${RESET}"
