#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "$0")/common.sh"

HOST_IP="${HOST_IP:-$(./scripts/detect_host_ip.sh)}"
export HOST_IP

if ! dashboard_import_supported; then
  echo "Skipping OTEL dashboard import for ES_VERSION ${ES_VERSION}; requires >= ${DASHBOARD_IMPORT_MIN_VERSION}"
  exit 0
fi

python3 ./scripts/build_otel_dashboard_ndjson.py >/dev/null

MONITORING_KIBANA_URL="https://kibana-monitoring.${HOST_IP}.sslip.io"
MONITORING_ELASTIC_PASSWORD="$(kubectl -n lab-monitoring get secret elasticsearch-monitoring-es-elastic-user -o jsonpath='{.data.elastic}' | base64 -d)"

if [[ -z "${MONITORING_ELASTIC_PASSWORD}" ]]; then
  echo "Unable to read monitoring Elasticsearch password for dashboard import" >&2
  exit 1
fi

RESPONSE_FILE="$(mktemp)"
trap 'rm -f "${RESPONSE_FILE}"' EXIT

for _ in $(seq 1 20); do
  HTTP_CODE="$(
    curl -sk -o "${RESPONSE_FILE}" -w '%{http_code}' \
      -u "elastic:${MONITORING_ELASTIC_PASSWORD}" \
      -H 'kbn-xsrf: true' \
      -F "file=@${OTEL_MONITORING_DASHBOARD_PATH}" \
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
    echo "Imported OTEL monitoring dashboard into Kibana"
    exit 0
  fi

  sleep 10
done

echo "Failed to import OTEL monitoring dashboard into Kibana" >&2
cat "${RESPONSE_FILE}" >&2
exit 1
