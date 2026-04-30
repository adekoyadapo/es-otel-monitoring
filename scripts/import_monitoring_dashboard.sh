#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "$0")/common.sh"
validate_monitoring_mode

HOST_IP="${HOST_IP:-}"
if [[ -z "${HOST_IP}" ]]; then
  HOST_IP="$(./scripts/detect_host_ip.sh 2>/dev/null || true)"
fi
export HOST_IP

if ! dashboard_import_supported; then
  echo "Skipping OTEL dashboard import for ES_VERSION ${ES_VERSION}; requires >= ${DASHBOARD_IMPORT_MIN_VERSION}"
  exit 0
fi

python3 ./scripts/build_otel_dashboard_ndjson.py >/dev/null
python3 ./scripts/build_otel_agent_dashboard_ndjson.py >/dev/null
DASHBOARD_PATH="$(current_dashboard_path)"
DASHBOARD_ID="$(current_dashboard_id)"

MONITORING_KIBANA_URL="https://kibana-monitoring.${HOST_IP}.sslip.io"

RESPONSE_FILE="$(mktemp)"
TMP_IMPORT_YAML="$(mktemp)"
TMP_IMPORT_LOG="$(mktemp)"
IMPORT_CM_NAME="otel-dashboard-import-$(date +%s)"
IMPORT_POD_NAME="${IMPORT_CM_NAME}"
cleanup() {
  rm -f "${RESPONSE_FILE}" "${TMP_IMPORT_YAML}" "${TMP_IMPORT_LOG}"
  kubectl -n lab-monitoring delete pod "${IMPORT_POD_NAME}" --ignore-not-found >/dev/null 2>&1 || true
  kubectl -n lab-monitoring delete configmap "${IMPORT_CM_NAME}" --ignore-not-found >/dev/null 2>&1 || true
}
trap cleanup EXIT

import_via_cluster() {
  kubectl -n lab-monitoring delete configmap "${IMPORT_CM_NAME}" --ignore-not-found >/dev/null 2>&1 || true
  kubectl -n lab-monitoring create configmap "${IMPORT_CM_NAME}" \
    --from-file=dashboard.ndjson="${DASHBOARD_PATH}" >/dev/null

  cat >"${TMP_IMPORT_YAML}" <<YAML
apiVersion: v1
kind: Pod
metadata:
  name: ${IMPORT_POD_NAME}
  namespace: lab-monitoring
spec:
  restartPolicy: Never
  containers:
    - name: import
      image: curlimages/curl:8.12.1
      command: ["/bin/sh", "-c"]
      args:
        - |
          curl -sk -u "elastic:\${ES_PASSWORD}" \
            -H 'kbn-xsrf: true' \
            -F file=@/dash/dashboard.ndjson \
            'https://kibana-monitoring-kb-http.lab-monitoring.svc.cluster.local:5601/api/saved_objects/_import?overwrite=true'
      env:
        - name: ES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: elasticsearch-monitoring-es-elastic-user
              key: elastic
      volumeMounts:
        - name: dash
          mountPath: /dash
  volumes:
    - name: dash
      configMap:
        name: ${IMPORT_CM_NAME}
YAML

  kubectl -n lab-monitoring delete pod "${IMPORT_POD_NAME}" --ignore-not-found >/dev/null 2>&1 || true
  kubectl create --validate=false -f "${TMP_IMPORT_YAML}" >/dev/null
  kubectl -n lab-monitoring wait --for=jsonpath='{.status.phase}'=Succeeded "pod/${IMPORT_POD_NAME}" --timeout=180s >/dev/null
  kubectl -n lab-monitoring logs "pod/${IMPORT_POD_NAME}" >"${TMP_IMPORT_LOG}"
  python3 - "${TMP_IMPORT_LOG}" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as fh:
    data = json.load(fh)

sys.exit(0 if data.get("success") else 1)
PY
}

if [[ -n "${HOST_IP}" ]]; then
  MONITORING_ELASTIC_PASSWORD="$(kubectl -n lab-monitoring get secret elasticsearch-monitoring-es-elastic-user -o jsonpath='{.data.elastic}' | base64 -d)"

  if [[ -z "${MONITORING_ELASTIC_PASSWORD}" ]]; then
    echo "Unable to read monitoring Elasticsearch password for host-side dashboard import" >&2
  else
  for _ in $(seq 1 20); do
    HTTP_CODE="$(
      curl -sk -o "${RESPONSE_FILE}" -w '%{http_code}' \
        -u "elastic:${MONITORING_ELASTIC_PASSWORD}" \
        -H 'kbn-xsrf: true' \
        -F "file=@${DASHBOARD_PATH}" \
        "${MONITORING_KIBANA_URL}/api/saved_objects/_import?overwrite=true" || true
    )"

    if [[ "${HTTP_CODE}" == "200" ]] && python3 - "${RESPONSE_FILE}" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as fh:
    data = json.load(fh)

sys.exit(0 if data.get("success") else 1)
PY
    then
      echo "Imported OTEL monitoring dashboard ${DASHBOARD_ID} into Kibana"
      exit 0
    fi

    sleep 10
  done
  fi
fi

if import_via_cluster; then
  echo "Imported OTEL monitoring dashboard ${DASHBOARD_ID} into Kibana via in-cluster fallback"
  exit 0
fi

echo "Failed to import OTEL monitoring dashboard ${DASHBOARD_ID} into Kibana" >&2
if [[ -s "${RESPONSE_FILE}" ]]; then
  cat "${RESPONSE_FILE}" >&2
fi
if [[ -s "${TMP_IMPORT_LOG}" ]]; then
  cat "${TMP_IMPORT_LOG}" >&2
fi
exit 1
