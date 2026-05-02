#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "$0")/common.sh"

if [[ -f /tmp/edot-jwt-test.env ]]; then
  # shellcheck disable=SC1091
  source /tmp/edot-jwt-test.env
fi

sed \
  -e "s/__ES_VERSION__/${ES_VERSION}/g" \
  -e "s/__MAIN_ES_NODES__/${MAIN_ES_NODES}/g" \
  -e "s/__MAIN_ES_CPU__/${MAIN_ES_CPU}/g" \
  -e "s/__MAIN_ES_MEMORY__/${MAIN_ES_MEMORY}/g" \
  manifests/elastic/elasticsearch-main.yaml | kubectl apply -f -

if [[ -n "${JWT_TEST_SECRET_NAME:-}" ]]; then
  kubectl -n lab-main delete secret "${JWT_TEST_SECRET_NAME}" --ignore-not-found
fi

if [[ -n "${JWT_TEST_ROLE_MAPPING_NAME:-}" ]]; then
  kubectl -n lab-main wait --for=condition=Ready pod -l elasticsearch.k8s.elastic.co/cluster-name=elasticsearch-main --timeout=900s

  kubectl -n lab-main port-forward service/elasticsearch-main-es-http 19201:9200 >/tmp/edot-jwt-main-pf.log 2>&1 &
  PF_PID="$!"
  trap 'kill "${PF_PID}" >/dev/null 2>&1 || true' EXIT
  for _ in $(seq 1 30); do
    if curl -sk "https://127.0.0.1:19201/_cluster/health" >/dev/null 2>&1; then
      break
    fi
    sleep 1
  done

  MAIN_ES_URL="https://127.0.0.1:19201"
  MAIN_ELASTIC_PASSWORD="${MAIN_ELASTIC_PASSWORD:-$(kubectl -n lab-main get secret elasticsearch-main-es-elastic-user -o jsonpath='{.data.elastic}' | base64 -d)}"
  curl -sk -u "elastic:${MAIN_ELASTIC_PASSWORD}" -X DELETE "${MAIN_ES_URL}/_security/role_mapping/${JWT_TEST_ROLE_MAPPING_NAME}" >/dev/null || true
  curl -sk -u "elastic:${MAIN_ELASTIC_PASSWORD}" -X DELETE "${MAIN_ES_URL}/_security/role/${JWT_TEST_ROLE_NAME}" >/dev/null || true
fi

kubectl -n lab-main wait --for=condition=Ready pod -l kibana.k8s.elastic.co/name=kibana-main --timeout=420s

rm -f /tmp/edot-jwt-test.env

echo "JWT overlay removed"
