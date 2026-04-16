#!/usr/bin/env bash
set -euo pipefail

HOST_IP="${HOST_IP:-$(./scripts/detect_host_ip.sh)}"
MAIN_ES_URL="https://es-main.${HOST_IP}.sslip.io"
MAIN_KIBANA_URL="https://kibana-main.${HOST_IP}.sslip.io"
MONITORING_ES_URL="https://es-monitoring.${HOST_IP}.sslip.io"
MONITORING_KIBANA_URL="https://kibana-monitoring.${HOST_IP}.sslip.io"

kubectl -n lab-main wait --for=condition=Ready certificate/es-main-cert --timeout=180s
kubectl -n lab-monitoring wait --for=condition=Ready certificate/es-monitoring-cert --timeout=180s

MAIN_ELASTIC_PASSWORD="$(kubectl -n lab-main get secret elasticsearch-main-es-elastic-user -o jsonpath='{.data.elastic}' | base64 -d)"
AUTH_RESP="$(curl -sk -u "elastic:${MAIN_ELASTIC_PASSWORD}" "${MAIN_ES_URL}/_security/_authenticate")"
echo "${AUTH_RESP}" | grep -q '"username":"elastic"'

MAIN_KIBANA_CODE="$(curl -sk -o /dev/null -w '%{http_code}' "${MAIN_KIBANA_URL}")"
if [[ "${MAIN_KIBANA_CODE}" != "200" && "${MAIN_KIBANA_CODE}" != "302" ]]; then
  echo "Main Kibana endpoint check failed. HTTP ${MAIN_KIBANA_CODE}" >&2
  exit 1
fi

MONITORING_KIBANA_CODE="$(curl -sk -o /dev/null -w '%{http_code}' "${MONITORING_KIBANA_URL}")"
if [[ "${MONITORING_KIBANA_CODE}" != "200" && "${MONITORING_KIBANA_CODE}" != "302" ]]; then
  echo "Monitoring Kibana endpoint check failed. HTTP ${MONITORING_KIBANA_CODE}" >&2
  exit 1
fi

MONITORING_ELASTIC_PASSWORD="$(kubectl -n lab-monitoring get secret elasticsearch-monitoring-es-elastic-user -o jsonpath='{.data.elastic}' | base64 -d)"
for _ in $(seq 1 20); do
  ES_METRICS_COUNT="$(curl -sk -u "elastic:${MONITORING_ELASTIC_PASSWORD}" "${MONITORING_ES_URL}/logs-elasticsearch.metrics-main/_count" | sed -n 's/.*"count":\([0-9][0-9]*\).*/\1/p')"
  ES_LOGS_COUNT="$(curl -sk -u "elastic:${MONITORING_ELASTIC_PASSWORD}" "${MONITORING_ES_URL}/logs-elasticsearch.logs.otel-main/_count" | sed -n 's/.*"count":\([0-9][0-9]*\).*/\1/p')"
  if [[ "${ES_METRICS_COUNT:-0}" -gt 0 && "${ES_LOGS_COUNT:-0}" -gt 0 ]]; then
    break
  fi
  sleep 15
done

if [[ "${ES_METRICS_COUNT:-0}" -le 0 ]]; then
  echo "No Elasticsearch metrics documents were shipped to the monitoring cluster" >&2
  exit 1
fi

if [[ "${ES_LOGS_COUNT:-0}" -le 0 ]]; then
  echo "No Elasticsearch log documents were shipped to the monitoring cluster" >&2
  exit 1
fi

echo "All tests passed"
