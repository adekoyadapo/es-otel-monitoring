#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "$0")/common.sh"

MAIN_ELASTIC_PASSWORD="$(kubectl -n lab-main get secret elasticsearch-main-es-elastic-user -o jsonpath='{.data.elastic}' | base64 -d)"
if [[ -z "${MAIN_ELASTIC_PASSWORD}" ]]; then
  echo "Unable to read main Elasticsearch password" >&2
  exit 1
fi

kubectl -n lab-main port-forward service/elasticsearch-main-es-http 19201:9200 >/tmp/edot-sload-pf.log 2>&1 &
PF_PID=$!
trap 'kill "${PF_PID}" >/dev/null 2>&1 || true' EXIT

for _ in $(seq 1 20); do
  if curl -sk "https://127.0.0.1:19201/_cluster/health" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

STREAM_PATTERN="${SEARCH_LOAD_STREAM_PREFIX}-*-${SEARCH_LOAD_STREAM_NAMESPACE}"

# Delete data streams (also removes their backing indices)
DS_RESP="$(curl -sk -u "elastic:${MAIN_ELASTIC_PASSWORD}" \
  -X DELETE "https://127.0.0.1:19201/_data_stream/${STREAM_PATTERN}")"
echo "Data streams deleted: ${DS_RESP}"

# Delete any regular indices that match the pattern (fallback for non-datastream writes).
# ES 9.x blocks wildcard DELETE on indices when action.destructive_requires_name=true,
# so we list indices first and delete only matching ones individually.
while IFS= read -r idx; do
  [[ -z "${idx}" ]] && continue
  IDX_RESP="$(curl -sk -u "elastic:${MAIN_ELASTIC_PASSWORD}" \
    -X DELETE "https://127.0.0.1:19201/${idx}" 2>/dev/null || true)"
  if [[ "${IDX_RESP}" == *'"acknowledged":true'* ]]; then
    echo "Index cleanup: deleted ${idx}"
  else
    echo "Index cleanup: failed to delete ${idx}: ${IDX_RESP}" >&2
  fi
done < <(curl -sk -u "elastic:${MAIN_ELASTIC_PASSWORD}" \
  "https://127.0.0.1:19201/_cat/indices/${STREAM_PATTERN}?h=index&format=text&ignore_unavailable=true" 2>/dev/null \
  | grep -v '^$' || true)

# Delete the index template
TMPL_RESP="$(curl -sk -u "elastic:${MAIN_ELASTIC_PASSWORD}" \
  -X DELETE "https://127.0.0.1:19201/_index_template/${SEARCH_LOAD_STREAM_PREFIX}-logsdb")"
echo "Index template deleted: ${TMPL_RESP}"
