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

# Delete any regular indices that match the pattern (fallback for non-datastream writes)
IDX_RESP="$(curl -sk -u "elastic:${MAIN_ELASTIC_PASSWORD}" \
  -X DELETE "https://127.0.0.1:19201/${STREAM_PATTERN}" 2>/dev/null || true)"
if [[ "${IDX_RESP}" != *'"acknowledged":true'* ]] && [[ "${IDX_RESP}" != *'index_not_found'* ]]; then
  echo "Index cleanup: ${IDX_RESP}"
fi

# Delete the index template
TMPL_RESP="$(curl -sk -u "elastic:${MAIN_ELASTIC_PASSWORD}" \
  -X DELETE "https://127.0.0.1:19201/_index_template/${SEARCH_LOAD_STREAM_PREFIX}-logsdb")"
echo "Index template deleted: ${TMPL_RESP}"
