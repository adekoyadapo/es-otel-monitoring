#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "$0")/common.sh"

HOST_IP="${HOST_IP:-$(./scripts/detect_host_ip.sh)}"
export HOST_IP

ROOT_CA_B64="$(kubectl -n cert-manager get secret lab-root-ca-secret -o jsonpath='{.data.tls\.crt}')"
MAIN_ELASTIC_PASSWORD="$(kubectl -n lab-main get secret elasticsearch-main-es-elastic-user -o jsonpath='{.data.elastic}' | base64 -d)"
MONITORING_ELASTIC_PASSWORD="$(kubectl -n lab-monitoring get secret elasticsearch-monitoring-es-elastic-user -o jsonpath='{.data.elastic}' | base64 -d)"

if [[ -z "${ROOT_CA_B64}" || -z "${MAIN_ELASTIC_PASSWORD}" || -z "${MONITORING_ELASTIC_PASSWORD}" ]]; then
  echo "Unable to read one or more bootstrap secrets for EDOT" >&2
  exit 1
fi

kubectl create namespace lab-main --dry-run=client -o yaml | kubectl apply -f -
kubectl create namespace lab-monitoring --dry-run=client -o yaml | kubectl apply -f -

ROOT_CA_FILE="$(mktemp)"
trap 'rm -f "${ROOT_CA_FILE}"' EXIT
printf '%s' "${ROOT_CA_B64}" | base64 -d > "${ROOT_CA_FILE}"

kubectl -n lab-main create secret generic edot-root-ca \
  --from-file=ca.crt="${ROOT_CA_FILE}" \
  --dry-run=client -o yaml | kubectl apply -f -

kubectl -n lab-monitoring create secret generic edot-root-ca \
  --from-file=ca.crt="${ROOT_CA_FILE}" \
  --dry-run=client -o yaml | kubectl apply -f -

create_role_and_user() {
  local url="$1"
  local elastic_password="$2"
  local role_name="$3"
  local role_body="$4"
  local username="$5"
  local user_password="$6"
  local user_roles_json="$7"
  local role_code=""
  local user_code=""

  for _ in $(seq 1 20); do
    role_code="$(
      curl -sk -o /dev/null -w '%{http_code}' -u "elastic:${elastic_password}" \
        -H 'Content-Type: application/json' \
        -X PUT "${url}/_security/role/${role_name}" \
        -d "${role_body}" || true
    )"
    if [[ "${role_code}" == "200" ]]; then
      break
    fi
    sleep 3
  done

  if [[ "${role_code}" != "200" ]]; then
    echo "Failed to create role ${role_name} on ${url}" >&2
    exit 1
  fi

  for _ in $(seq 1 20); do
    user_code="$(
      curl -sk -o /dev/null -w '%{http_code}' -u "elastic:${elastic_password}" \
        -H 'Content-Type: application/json' \
        -X POST "${url}/_security/user/${username}" \
        -d "{\"password\":\"${user_password}\",\"roles\":${user_roles_json}}" || true
    )"
    if [[ "${user_code}" == "200" ]]; then
      break
    fi
    sleep 3
  done

  if [[ "${user_code}" != "200" ]]; then
    echo "Failed to create user ${username} on ${url}" >&2
    exit 1
  fi
}

create_role_and_user \
  "https://es-main.${HOST_IP}.sslip.io" \
  "${MAIN_ELASTIC_PASSWORD}" \
  "edot_metrics_reader" \
  '{"cluster":["monitor"],"indices":[{"names":["*"],"privileges":["monitor","view_index_metadata"]}]}' \
  "edot_metrics_reader" \
  "EdotMetrics123!" \
  '["edot_metrics_reader"]'

create_role_and_user \
  "https://es-main.${HOST_IP}.sslip.io" \
  "${MAIN_ELASTIC_PASSWORD}" \
  "main_search_load_writer" \
  "{\"cluster\":[\"monitor\",\"manage_index_templates\"],\"indices\":[{\"names\":[\"${SEARCH_LOAD_STREAM_PREFIX}-*-${SEARCH_LOAD_STREAM_NAMESPACE}\"],\"privileges\":[\"auto_configure\",\"create_doc\",\"read\",\"view_index_metadata\"]}]}" \
  "main_search_load_writer" \
  "MainSearchLoad123!" \
  '["main_search_load_writer"]'

create_role_and_user \
  "https://es-monitoring.${HOST_IP}.sslip.io" \
  "${MONITORING_ELASTIC_PASSWORD}" \
  "edot_ingest_writer" \
  '{"cluster":["monitor"],"indices":[{"names":["logs-*","metrics-*"],"privileges":["auto_configure","create_doc","view_index_metadata"]}]}' \
  "edot_ingest_writer" \
  "EdotIngest123!" \
  '["edot_ingest_writer"]'

create_role_and_user \
  "https://es-monitoring.${HOST_IP}.sslip.io" \
  "${MONITORING_ELASTIC_PASSWORD}" \
  "edot_autoops_tsds_deriver" \
  '{"cluster":["monitor"],"indices":[{"names":["logs-elasticsearch.metrics-main"],"privileges":["read","view_index_metadata"]},{"names":["metrics-elasticsearch.autoops-main"],"privileges":["auto_configure","create_doc","view_index_metadata"]}]}' \
  "edot_autoops_tsds_deriver" \
  "EdotDerive123!" \
  '["edot_autoops_tsds_deriver"]'

kubectl -n lab-main create secret generic edot-main-source-credentials \
  --from-literal=main-elasticsearch-url="https://elasticsearch-main-es-http.lab-main.svc.cluster.local:9200" \
  --from-literal=main-elasticsearch-username="edot_metrics_reader" \
  --from-literal=main-elasticsearch-password="EdotMetrics123!" \
  --dry-run=client -o yaml | kubectl apply -f -

kubectl -n lab-main create secret generic main-search-load-credentials \
  --from-literal=main-elasticsearch-url="https://elasticsearch-main-es-http.lab-main.svc.cluster.local:9200" \
  --from-literal=main-elasticsearch-username="main_search_load_writer" \
  --from-literal=main-elasticsearch-password="MainSearchLoad123!" \
  --dry-run=client -o yaml | kubectl apply -f -

kubectl -n lab-monitoring create secret generic edot-monitoring-credentials \
  --from-literal=monitoring-elasticsearch-url="https://elasticsearch-monitoring-es-http.lab-monitoring.svc.cluster.local:9200" \
  --from-literal=monitoring-elasticsearch-username="edot_ingest_writer" \
  --from-literal=monitoring-elasticsearch-password="EdotIngest123!" \
  --dry-run=client -o yaml | kubectl apply -f -

kubectl -n lab-monitoring create secret generic edot-autoops-tsds-credentials \
  --from-literal=monitoring-elasticsearch-url="https://elasticsearch-monitoring-es-http.lab-monitoring.svc.cluster.local:9200" \
  --from-literal=monitoring-elasticsearch-username="edot_autoops_tsds_deriver" \
  --from-literal=monitoring-elasticsearch-password="EdotDerive123!" \
  --dry-run=client -o yaml | kubectl apply -f -

kubectl -n lab-monitoring create configmap edot-autoops-tsds-script \
  --from-file=derive_autoops_tsds.py=./scripts/derive_autoops_tsds.py \
  --dry-run=client -o yaml | kubectl apply -f -

kubectl apply -f manifests/edot/gateway.yaml
kubectl apply -f manifests/edot/main-metrics.yaml
kubectl apply -f manifests/edot/main-logs.yaml
kubectl apply -f manifests/edot/autoops-tsds-deriver.yaml
bash ./scripts/deploy_search_load.sh

RESET_AUTOOPS_TSDS=true bash ./scripts/install_autoops_tsds_assets.sh

kubectl -n lab-monitoring rollout status deploy/edot-gateway --timeout=300s
kubectl -n lab-main rollout status deploy/edot-main-metrics --timeout=300s
kubectl -n lab-main rollout status ds/edot-main-logs --timeout=300s
kubectl -n lab-main rollout status deploy/main-search-load --timeout=300s

TSDS_BOOTSTRAP_JOB="edot-autoops-tsds-bootstrap-$(date +%s)"
kubectl -n lab-monitoring create job --from=cronjob/edot-autoops-tsds-deriver "${TSDS_BOOTSTRAP_JOB}"
kubectl -n lab-monitoring wait --for=condition=complete "job/${TSDS_BOOTSTRAP_JOB}" --timeout=300s

bash ./scripts/import_monitoring_dashboard.sh
