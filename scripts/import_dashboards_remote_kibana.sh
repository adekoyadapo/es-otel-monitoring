#!/usr/bin/env bash
# Import repo dashboard NDJSON bundles into remote Kibana (e.g. Elastic Cloud Serverless).
#
# Usage:
#   export KIBANA_URL='https://otel-demo-a5630c.kb.us-east-1.aws.elastic.cloud'
#   export KIBANA_API_KEY='<base64 API key with Kibana saved object / dashboard write privileges>'
#   # optional: rebuild NDJSON from templates first
#   # export REBUILD=1
#   ./scripts/import_dashboards_remote_kibana.sh
#
# API key: create in Kibana → Stack Management → API keys (or reuse one that can call
# POST /api/saved_objects/_import). Do not paste keys into chat.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "${ROOT}"

: "${KIBANA_URL:?Set KIBANA_URL to your Kibana base URL (no path after host)}"
: "${KIBANA_API_KEY:?Set KIBANA_API_KEY to a base64-encoded API key}"

KIBANA_URL="${KIBANA_URL%/}"

if [[ "${REBUILD:-}" == "1" ]]; then
  python3 ./scripts/build_otel_dashboard_ndjson.py >/dev/null
  python3 ./scripts/build_otel_agent_dashboard_ndjson.py >/dev/null
  python3 ./scripts/build_otel_contrib_dashboard_ndjson.py >/dev/null
fi

FILES=(
  "dashboards/elasticsearch-otel-monitoring-main.ndjson"
  "dashboards/elasticsearch-otel-monitoring-agent.ndjson"
  "dashboards/elasticsearch-otel-monitoring-contrib.ndjson"
)

# Optional -k (macOS bash + `set -u` errors on `"${empty[@]}"`; use explicit branches).
import_one() {
  local path="$1"
  local response
  response="$(mktemp)"
  local http_code
  if [[ "${KIBANA_INSECURE:-}" == "1" ]]; then
    http_code="$(
      curl -sS -k -o "${response}" -w '%{http_code}' \
        -X POST "${KIBANA_URL}/api/saved_objects/_import?overwrite=true" \
        -H "Authorization: ApiKey ${KIBANA_API_KEY}" \
        -H 'kbn-xsrf: remote-import' \
        -F "file=@${path}"
    )" || true
  else
    http_code="$(
      curl -sS -o "${response}" -w '%{http_code}' \
        -X POST "${KIBANA_URL}/api/saved_objects/_import?overwrite=true" \
        -H "Authorization: ApiKey ${KIBANA_API_KEY}" \
        -H 'kbn-xsrf: remote-import' \
        -F "file=@${path}"
    )" || true
  fi

  if [[ "${http_code}" != "200" ]]; then
    echo "Import failed for ${path} (HTTP ${http_code})" >&2
    cat "${response}" >&2
    rm -f "${response}"
    return 1
  fi

  if ! python3 - "${response}" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as fh:
    data = json.load(fh)
if not data.get("success"):
    print(json.dumps(data, indent=2), file=sys.stderr)
    sys.exit(1)
PY
  then
    rm -f "${response}"
    return 1
  fi
  rm -f "${response}"
  echo "Imported ${path}"
}

for f in "${FILES[@]}"; do
  if [[ ! -f "${f}" ]]; then
    echo "Missing ${f}" >&2
    exit 1
  fi
  import_one "${f}"
done

echo "All dashboard bundles imported into ${KIBANA_URL}"
