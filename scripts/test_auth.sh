#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "$0")/common.sh"
validate_monitoring_mode

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

echo "[1/11] Waiting for TLS certificates"
kubectl -n lab-main wait --for=condition=Ready certificate/es-main-cert --timeout=180s
kubectl -n lab-monitoring wait --for=condition=Ready certificate/es-monitoring-cert --timeout=180s
echo "${GREEN}  OK: TLS certificates are ready${RESET}"

echo "[2/11] Verifying main Elasticsearch authentication"
MAIN_ELASTIC_PASSWORD="$(kubectl -n lab-main get secret elasticsearch-main-es-elastic-user -o jsonpath='{.data.elastic}' | base64 -d)"
AUTH_RESP="$(curl -sk -u "elastic:${MAIN_ELASTIC_PASSWORD}" "${MAIN_ES_URL}/_security/_authenticate")"
echo "${AUTH_RESP}" | grep -q '"username":"elastic"'
echo "${GREEN}  OK: main Elasticsearch auth succeeded${RESET}"

echo "[3/11] Checking main Kibana ingress"
MAIN_KIBANA_CODE="$(curl -sk -o /dev/null -w '%{http_code}' "${MAIN_KIBANA_URL}")"
if [[ "${MAIN_KIBANA_CODE}" != "200" && "${MAIN_KIBANA_CODE}" != "302" ]]; then
  fail "Main Kibana endpoint check failed. HTTP ${MAIN_KIBANA_CODE}"
fi
echo "${GREEN}  OK: main Kibana ingress returned HTTP ${MAIN_KIBANA_CODE}${RESET}"

echo "[4/11] Checking monitoring Kibana ingress"
MONITORING_KIBANA_CODE="$(curl -sk -o /dev/null -w '%{http_code}' "${MONITORING_KIBANA_URL}")"
if [[ "${MONITORING_KIBANA_CODE}" != "200" && "${MONITORING_KIBANA_CODE}" != "302" ]]; then
  fail "Monitoring Kibana endpoint check failed. HTTP ${MONITORING_KIBANA_CODE}"
fi
echo "${GREEN}  OK: monitoring Kibana ingress returned HTTP ${MONITORING_KIBANA_CODE}${RESET}"

echo "[5/11] Waiting for EDOT data streams to appear in the monitoring cluster"
MONITORING_ELASTIC_PASSWORD="$(kubectl -n lab-monitoring get secret elasticsearch-monitoring-es-elastic-user -o jsonpath='{.data.elastic}' | base64 -d)"
ES_METRICS_DATASTREAM_PRESENT=0
ES_LOGS_DATASTREAM_PRESENT=0
DERIVED_TSDS_PRESENT=0
AGENT_METRICS_PRESENT=0
AGENT_LOGS_PRESENT=0
for _ in $(seq 1 20); do
  ES_METRICS_DATASTREAM_CODE="$(curl -sk -o /dev/null -w '%{http_code}' -u "elastic:${MONITORING_ELASTIC_PASSWORD}" "${MONITORING_ES_URL}/_data_stream/${AUTOOPS_SOURCE_DATASTREAM}")"
  ES_LOGS_DATASTREAM_CODE="$(curl -sk -o /dev/null -w '%{http_code}' -u "elastic:${MONITORING_ELASTIC_PASSWORD}" "${MONITORING_ES_URL}/_data_stream/logs-elasticsearch.logs.otel-main")"
  DERIVED_TSDS_CODE="$(curl -sk -o /dev/null -w '%{http_code}' -u "elastic:${MONITORING_ELASTIC_PASSWORD}" "${MONITORING_ES_URL}/_data_stream/${AUTOOPS_DERIVED_TSDS}")"
  AGENT_METRICS_CODE="$(curl -sk -o /dev/null -w '%{http_code}' -u "elastic:${MONITORING_ELASTIC_PASSWORD}" "${MONITORING_ES_URL}/_data_stream/${AGENT_METRICS_DATASTREAM_PATTERN}")"
  AGENT_LOGS_CODE="$(curl -sk -o /dev/null -w '%{http_code}' -u "elastic:${MONITORING_ELASTIC_PASSWORD}" "${MONITORING_ES_URL}/_data_stream/${AGENT_LOGS_DATASTREAM_PATTERN}")"
  if [[ "${ES_METRICS_DATASTREAM_CODE}" == "200" ]]; then
    ES_METRICS_DATASTREAM_PRESENT=1
  fi
  if [[ "${ES_LOGS_DATASTREAM_CODE}" == "200" ]]; then
    ES_LOGS_DATASTREAM_PRESENT=1
  fi
  if [[ "${DERIVED_TSDS_CODE}" == "200" ]]; then
    DERIVED_TSDS_PRESENT=1
  fi
  if [[ "${AGENT_METRICS_CODE}" == "200" ]]; then
    AGENT_METRICS_PRESENT=1
  fi
  if [[ "${AGENT_LOGS_CODE}" == "200" ]]; then
    AGENT_LOGS_PRESENT=1
  fi
  ES_METRICS_COUNT="$(curl -sk -u "elastic:${MONITORING_ELASTIC_PASSWORD}" "${MONITORING_ES_URL}/${AUTOOPS_SOURCE_DATASTREAM}/_count" | sed -n 's/.*"count":\([0-9][0-9]*\).*/\1/p')"
  ES_LOGS_COUNT="$(curl -sk -u "elastic:${MONITORING_ELASTIC_PASSWORD}" "${MONITORING_ES_URL}/logs-elasticsearch.logs.otel-main/_count" | sed -n 's/.*"count":\([0-9][0-9]*\).*/\1/p')"
  DERIVED_TSDS_COUNT="$(curl -sk -u "elastic:${MONITORING_ELASTIC_PASSWORD}" "${MONITORING_ES_URL}/${AUTOOPS_DERIVED_TSDS}/_count" | sed -n 's/.*"count":\([0-9][0-9]*\).*/\1/p')"
  AGENT_METRICS_COUNT="$(curl -sk -u "elastic:${MONITORING_ELASTIC_PASSWORD}" "${MONITORING_ES_URL}/${AGENT_METRICS_DATASTREAM_TARGET}/_count" | sed -n 's/.*"count":\([0-9][0-9]*\).*/\1/p')"
  AGENT_LOGS_COUNT="$(curl -sk -u "elastic:${MONITORING_ELASTIC_PASSWORD}" "${MONITORING_ES_URL}/${AGENT_LOGS_DATASTREAM_PATTERN}/_count" | sed -n 's/.*"count":\([0-9][0-9]*\).*/\1/p')"
  if monitoring_mode_autoops; then
    if [[ "${ES_METRICS_DATASTREAM_PRESENT}" -eq 1 && "${ES_LOGS_DATASTREAM_PRESENT}" -eq 1 && "${DERIVED_TSDS_PRESENT}" -eq 1 && "${ES_METRICS_COUNT:-0}" -gt 0 && "${ES_LOGS_COUNT:-0}" -gt 0 && "${DERIVED_TSDS_COUNT:-0}" -gt 0 ]]; then
      break
    fi
  else
    if [[ "${AGENT_METRICS_PRESENT}" -eq 1 && "${AGENT_LOGS_PRESENT}" -eq 1 && "${AGENT_METRICS_COUNT:-0}" -gt 0 && "${AGENT_LOGS_COUNT:-0}" -gt 0 ]]; then
      break
    fi
  fi
  sleep 15
done

if monitoring_mode_autoops; then
  if [[ "${ES_LOGS_DATASTREAM_PRESENT}" -ne 1 ]]; then
    fail "Logs data stream logs-elasticsearch.logs.otel-main was not created in the monitoring cluster"
  fi
  if [[ "${ES_METRICS_DATASTREAM_PRESENT}" -ne 1 ]]; then
    fail "Metrics source data stream ${AUTOOPS_SOURCE_DATASTREAM} was not created in the monitoring cluster"
  fi
  if [[ "${DERIVED_TSDS_PRESENT}" -ne 1 ]]; then
    fail "Derived TSDS ${AUTOOPS_DERIVED_TSDS} was not created in the monitoring cluster"
  fi
else
  if [[ "${AGENT_METRICS_PRESENT}" -ne 1 ]]; then
    fail "Elastic Agent metrics data streams matching ${AGENT_METRICS_DATASTREAM_PATTERN} were not created in the monitoring cluster"
  fi
  if [[ "${AGENT_LOGS_PRESENT}" -ne 1 ]]; then
    fail "Elastic Agent logs data streams matching ${AGENT_LOGS_DATASTREAM_PATTERN} were not created in the monitoring cluster"
  fi
fi
echo "${GREEN}  OK: expected EDOT data streams are present${RESET}"

echo "[6/11] Verifying source metrics documents were shipped"
if monitoring_mode_autoops; then
  if [[ "${ES_METRICS_COUNT:-0}" -le 0 ]]; then
    fail "No autoops source metrics documents were shipped to the monitoring cluster"
  fi
  echo "${GREEN}  OK: autoops source metrics data stream has ${ES_METRICS_COUNT} documents${RESET}"
else
  if [[ "${AGENT_METRICS_COUNT:-0}" -le 0 ]]; then
    fail "No Elastic Agent Elasticsearch metrics documents were shipped to the monitoring cluster"
  fi
  echo "${GREEN}  OK: Elastic Agent metrics data streams have ${AGENT_METRICS_COUNT} documents${RESET}"
fi

echo "[7/11] Verifying derived TSDS documents were shipped"
if monitoring_mode_autoops; then
  if [[ "${DERIVED_TSDS_COUNT:-0}" -le 0 ]]; then
    fail "No derived TSDS metrics documents were shipped to the monitoring cluster"
  fi
  echo "${GREEN}  OK: derived TSDS has ${DERIVED_TSDS_COUNT} documents${RESET}"
else
  echo "${BLUE}  SKIP: derived TSDS is not used in agent mode${RESET}"
fi

echo "[8/11] Verifying log documents were shipped"
if monitoring_mode_autoops; then
  if [[ "${ES_LOGS_COUNT:-0}" -le 0 ]]; then
    fail "No Elasticsearch log documents were shipped to the monitoring cluster"
  fi
  echo "${GREEN}  OK: logs data stream has ${ES_LOGS_COUNT} documents${RESET}"
else
  if [[ "${AGENT_LOGS_COUNT:-0}" -le 0 ]]; then
    fail "No Elastic Agent Elasticsearch log documents were shipped to the monitoring cluster"
  fi
  echo "${GREEN}  OK: Elastic Agent logs data streams have ${AGENT_LOGS_COUNT} documents${RESET}"
fi

echo "[9/11] Verifying synthetic search load data streams in the main cluster"
SEARCH_LOAD_READY=0
SEARCH_LOAD_TOTAL_COUNT=0
for _ in $(seq 1 20); do
  SEARCH_LOAD_READY=1
  SEARCH_LOAD_TOTAL_COUNT=0
  for stream_number in $(seq 1 "${SEARCH_LOAD_STREAM_COUNT}"); do
    STREAM_NAME="$(printf '%s-%02d-%s' "${SEARCH_LOAD_STREAM_PREFIX}" "${stream_number}" "${SEARCH_LOAD_STREAM_NAMESPACE}")"
    STREAM_CODE="$(curl -sk -o /dev/null -w '%{http_code}' -u "elastic:${MAIN_ELASTIC_PASSWORD}" "${MAIN_ES_URL}/_data_stream/${STREAM_NAME}")"
    if [[ "${STREAM_CODE}" != "200" ]]; then
      SEARCH_LOAD_READY=0
      break
    fi
    STREAM_COUNT_VALUE="$(curl -sk -u "elastic:${MAIN_ELASTIC_PASSWORD}" "${MAIN_ES_URL}/${STREAM_NAME}/_count" | sed -n 's/.*\"count\":\([0-9][0-9]*\).*/\1/p')"
    if [[ "${STREAM_COUNT_VALUE:-0}" -le 0 ]]; then
      SEARCH_LOAD_READY=0
      break
    fi
    SEARCH_LOAD_TOTAL_COUNT=$((SEARCH_LOAD_TOTAL_COUNT + STREAM_COUNT_VALUE))
  done
  if [[ "${SEARCH_LOAD_READY}" -eq 1 ]]; then
    break
  fi
  sleep 10
done

if [[ "${SEARCH_LOAD_READY}" -ne 1 ]]; then
  fail "Synthetic search load data streams were not created or did not receive documents"
fi
echo "${GREEN}  OK: synthetic logsdb data streams are present with ${SEARCH_LOAD_TOTAL_COUNT} total documents${RESET}"

echo "[10/11] Verifying synthetic search load deployment"
kubectl -n lab-main rollout status deploy/main-search-load --timeout=120s >/dev/null
echo "${GREEN}  OK: main-search-load deployment is ready${RESET}"

echo "[11/11] Verifying OTEL dashboard import"
if dashboard_import_supported; then
  DASHBOARD_ID="$(current_dashboard_id)"
  DASHBOARD_CODE="$(curl -sk -o /dev/null -w '%{http_code}' -u "elastic:${MONITORING_ELASTIC_PASSWORD}" -H 'kbn-xsrf: true' "${MONITORING_KIBANA_URL}/api/saved_objects/dashboard/${DASHBOARD_ID}")"
  if [[ "${DASHBOARD_CODE}" != "200" ]]; then
    fail "OTEL dashboard ${DASHBOARD_ID} was not imported into monitoring Kibana"
  fi
  echo "${GREEN}  OK: OTEL dashboard ${DASHBOARD_ID} is present${RESET}"
else
  echo "${BLUE}  SKIP: dashboard import not supported for ES_VERSION ${ES_VERSION} (requires >= ${DASHBOARD_IMPORT_MIN_VERSION})${RESET}"
fi

echo "${GREEN}All tests passed${RESET}"
