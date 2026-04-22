#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "$0")/common.sh"

HOST_IP="${HOST_IP:-$(./scripts/detect_host_ip.sh)}"
MAIN_ES_URL="https://es-main.${HOST_IP}.sslip.io"
MAIN_ELASTIC_PASSWORD="$(kubectl -n lab-main get secret elasticsearch-main-es-elastic-user -o jsonpath='{.data.elastic}' | base64 -d)"

DATA_STREAMS="$(
  curl -sk -u "elastic:${MAIN_ELASTIC_PASSWORD}" \
    "${MAIN_ES_URL}/_cat/data_stream/${SEARCH_LOAD_STREAM_PREFIX}-*-${SEARCH_LOAD_STREAM_NAMESPACE}?h=name" || true
)"

if [[ -n "${DATA_STREAMS}" ]]; then
  while IFS= read -r data_stream; do
    [[ -z "${data_stream}" ]] && continue
    curl -sk -u "elastic:${MAIN_ELASTIC_PASSWORD}" -X DELETE "${MAIN_ES_URL}/_data_stream/${data_stream}" >/dev/null
    echo "Deleted data stream ${data_stream}"
  done <<<"${DATA_STREAMS}"
fi

curl -sk -u "elastic:${MAIN_ELASTIC_PASSWORD}" -X DELETE "${MAIN_ES_URL}/_index_template/${SEARCH_LOAD_STREAM_PREFIX}-logsdb" >/dev/null || true
echo "Deleted index template ${SEARCH_LOAD_STREAM_PREFIX}-logsdb"
