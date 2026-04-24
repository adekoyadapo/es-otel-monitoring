#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "$0")/common.sh"

MAIN_ELASTIC_PASSWORD="$(kubectl -n lab-main get secret elasticsearch-main-es-elastic-user -o jsonpath='{.data.elastic}' | base64 -d)"
MAIN_ES_POD="$(kubectl -n lab-main get pods -l elasticsearch.k8s.elastic.co/cluster-name=elasticsearch-main -o jsonpath='{.items[0].metadata.name}')"

if [[ -z "${MAIN_ES_POD}" ]]; then
  echo "Unable to locate a main Elasticsearch pod for search-load cleanup" >&2
  exit 1
fi

DATA_STREAMS="$(
  kubectl -n lab-main exec "${MAIN_ES_POD}" -- \
    curl -sk -u "elastic:${MAIN_ELASTIC_PASSWORD}" \
      "https://localhost:9200/_data_stream/${SEARCH_LOAD_STREAM_PREFIX}-*-${SEARCH_LOAD_STREAM_NAMESPACE}" 2>/dev/null |
    python3 -c 'import json,sys; data=json.load(sys.stdin); print("\n".join(ds["name"] for ds in data.get("data_streams", [])))' || true
)"

if [[ -n "${DATA_STREAMS}" ]]; then
  while IFS= read -r data_stream; do
    [[ -z "${data_stream}" ]] && continue
    kubectl -n lab-main exec "${MAIN_ES_POD}" -- \
      curl -sk -u "elastic:${MAIN_ELASTIC_PASSWORD}" -X DELETE "https://localhost:9200/_data_stream/${data_stream}" >/dev/null
    echo "Deleted data stream ${data_stream}"
  done <<<"${DATA_STREAMS}"
fi

kubectl -n lab-main exec "${MAIN_ES_POD}" -- \
  curl -sk -u "elastic:${MAIN_ELASTIC_PASSWORD}" -X DELETE "https://localhost:9200/_index_template/${SEARCH_LOAD_STREAM_PREFIX}-logsdb" >/dev/null || true
echo "Deleted index template ${SEARCH_LOAD_STREAM_PREFIX}-logsdb"
