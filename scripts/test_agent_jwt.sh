#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "$0")/common.sh"

JWT_ENV_FILE="${JWT_ENV_FILE:-/tmp/edot-jwt-test.env}"
if [[ ! -f "${JWT_ENV_FILE}" ]]; then
  echo "JWT env file not found: ${JWT_ENV_FILE}. Run make jwt-agent-up first." >&2
  exit 1
fi

# shellcheck disable=SC1090
source "${JWT_ENV_FILE}"

if [[ -t 1 ]]; then
  GREEN=$'\033[32m'
  RED=$'\033[31m'
  BLUE=$'\033[34m'
  RESET=$'\033[0m'
else
  GREEN=""
  RED=""
  BLUE=""
  RESET=""
fi

fail() {
  echo "${RED}$1${RESET}" >&2
  exit 1
}

# Port-forward main ES for direct API checks
kubectl -n lab-main port-forward service/elasticsearch-main-es-http 19201:9200 >/tmp/edot-jwt-agent-pf.log 2>&1 &
PF_PID="$!"
kubectl -n lab-monitoring port-forward service/elasticsearch-monitoring-es-http 19202:9200 >/tmp/edot-jwt-monitoring-pf.log 2>&1 &
MONITORING_PF_PID="$!"
trap 'kill "${PF_PID}" >/dev/null 2>&1 || true; kill "${MONITORING_PF_PID}" >/dev/null 2>&1 || true' EXIT
for _ in $(seq 1 30); do
  if curl -sk "https://127.0.0.1:19201/_cluster/health" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

MAIN_ELASTIC_PASSWORD="${MAIN_ELASTIC_PASSWORD:-$(kubectl -n lab-main get secret elasticsearch-main-es-elastic-user -o jsonpath='{.data.elastic}' | base64 -d)}"
MONITORING_ELASTIC_PASSWORD="$(kubectl -n lab-monitoring get secret elasticsearch-monitoring-es-elastic-user -o jsonpath='{.data.elastic}' | base64 -d)"
MONITORING_ES_URL="https://127.0.0.1:19202"

echo "[1/5] Checking license"
LICENSE_TYPE=""
for _ in $(seq 1 10); do
  LICENSE_RESP="$(curl -sk -u "elastic:${MAIN_ELASTIC_PASSWORD}" "https://127.0.0.1:19201/_license" 2>/dev/null)"
  LICENSE_TYPE="$(printf '%s' "${LICENSE_RESP}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('license',{}).get('type',''))" 2>/dev/null || true)"
  if [[ -n "${LICENSE_TYPE}" ]]; then
    break
  fi
  sleep 2
done
if [[ -z "${LICENSE_TYPE}" ]]; then
  fail "Could not determine license type from /_license endpoint after retries"
fi
if [[ "${LICENSE_TYPE}" == "basic" ]]; then
  fail "JWT realms are disabled on the current basic license. Recreate the lab so the preinstalled ECK trial-license secret can take effect."
fi
echo "${GREEN}  OK: license is ${LICENSE_TYPE}${RESET}"

echo "[2/5] Verifying JWT realm is present in elasticsearch.yml"
ES_POD="$(kubectl -n lab-main get pods -l elasticsearch.k8s.elastic.co/cluster-name=elasticsearch-main -o jsonpath='{.items[0].metadata.name}')"
REALM_FOUND="$(kubectl -n lab-main exec "${ES_POD}" -- grep -c "${JWT_TEST_REALM_NAME}" /usr/share/elasticsearch/config/elasticsearch.yml 2>/dev/null || true)"
if [[ "${REALM_FOUND}" -eq 0 ]]; then
  fail "JWT realm '${JWT_TEST_REALM_NAME}' was not found in elasticsearch.yml on pod ${ES_POD}"
fi
echo "${GREEN}  OK: JWT realm '${JWT_TEST_REALM_NAME}' is present in elasticsearch.yml${RESET}"

echo "[3/5] Minting JWT and validating direct authentication"
JWT_ACCESS_TOKEN="$(python3 - "${JWT_KEY_B64}" "${JWT_TEST_ISSUER}" "${JWT_TEST_AUDIENCE}" "${JWT_TEST_PRINCIPAL}" "${JWT_TEST_KEY_ID}" <<'PY'
import base64, hashlib, hmac, json, secrets, sys, time

key_b64, issuer, audience, principal, kid = sys.argv[1:6]

def b64url(data):
    return base64.urlsafe_b64encode(data).decode().rstrip("=")

def decode_b64url(v):
    return base64.urlsafe_b64decode(v + "=" * (-len(v) % 4))

header = {"alg": "HS256", "typ": "JWT", "kid": kid}
now = int(time.time())
payload = {"iss": issuer, "aud": audience, "sub": principal, "iat": now, "nbf": now - 5, "exp": now + 600, "jti": secrets.token_urlsafe(18)}
si = (b64url(json.dumps(header, separators=(",", ":")).encode()) + "." + b64url(json.dumps(payload, separators=(",", ":")).encode()))
sig = hmac.new(decode_b64url(key_b64), si.encode(), hashlib.sha256).digest()
print(f"{si}.{b64url(sig)}")
PY
)"
AUTH_RESP="$(curl -sk \
  -H "Authorization: Bearer ${JWT_ACCESS_TOKEN}" \
  -H "ES-Client-Authentication: SharedSecret ${JWT_SHARED_SECRET}" \
  "https://127.0.0.1:19201/_security/_authenticate")"
echo "${AUTH_RESP}" | grep -q "\"username\":\"${JWT_TEST_PRINCIPAL}\"" || fail "JWT authentication failed. Response: ${AUTH_RESP}"
echo "${GREEN}  OK: JWT auth validated for principal '${JWT_TEST_PRINCIPAL}'${RESET}"

echo "[4/5] Verifying JWT OTLP collector pod status and token mount"
kubectl -n lab-main wait --for=condition=Available deploy/edot-main-metrics-jwt --timeout=60s >/dev/null
POD_NAME="$(kubectl -n lab-main get pods -l app.kubernetes.io/name=edot-main-metrics-jwt -o jsonpath='{.items[0].metadata.name}')"
TOKEN_PRESENT="$(kubectl -n lab-main exec "${POD_NAME}" -c token-refresher -- sh -c 'test -s /jwt/token && echo yes || echo no' 2>/dev/null)"
if [[ "${TOKEN_PRESENT}" != "yes" ]]; then
  fail "JWT token file /jwt/token is missing or empty in pod ${POD_NAME}"
fi
# Verify gateway deployment is running
if ! kubectl -n lab-monitoring rollout status deploy/edot-gateway --timeout=60s >/dev/null 2>&1; then
  fail "edot-gateway is not running in lab-monitoring. Run make jwt-agent-up to redeploy."
fi
echo "${GREEN}  OK: JWT OTEL metrics collector is running, token file is present, gateway is up${RESET}"

echo "[5/5] Waiting for JWT OTLP metrics to reach the monitoring cluster"
JWT_PRESENT=0
JWT_DOC_COUNT=0
for _ in $(seq 1 36); do
  JWT_CODE="$(curl -sk -o /dev/null -w '%{http_code}' -u "elastic:${MONITORING_ELASTIC_PASSWORD}" "${MONITORING_ES_URL}/_data_stream/${JWT_METRICS_DATASTREAM}")"
  if [[ "${JWT_CODE}" == "200" ]]; then
    JWT_DOC_COUNT="$(curl -sk -u "elastic:${MONITORING_ELASTIC_PASSWORD}" "${MONITORING_ES_URL}/${JWT_METRICS_DATASTREAM}/_count" | python3 -c "import sys,json; print(json.load(sys.stdin).get('count',0))" 2>/dev/null || echo 0)"
    if [[ "${JWT_DOC_COUNT:-0}" -gt 0 ]]; then
      JWT_PRESENT=1
      break
    fi
  fi
  sleep 10
done
if [[ "${JWT_PRESENT}" -ne 1 ]]; then
  fail "No JWT OTLP metrics found in ${JWT_METRICS_DATASTREAM} after 6 minutes"
fi
echo "${GREEN}  OK: JWT OTLP metrics data stream '${JWT_METRICS_DATASTREAM}' has ${JWT_DOC_COUNT} documents${RESET}"

check_metric_exists() {
  local field="$1"
  local code
  code="$(curl -sk -o /dev/null -w '%{http_code}' -u "elastic:${MONITORING_ELASTIC_PASSWORD}" \
    -H 'Content-Type: application/json' \
    "${MONITORING_ES_URL}/${JWT_METRICS_DATASTREAM}/_search?size=1" \
    -d "{\"query\":{\"exists\":{\"field\":\"metrics.${field}\"}},\"_source\":[\"metrics.${field}\"]}" 2>/dev/null)"
  if [[ "${code}" != "200" ]]; then
    return 1
  fi
  local result
  result="$(curl -sk -u "elastic:${MONITORING_ELASTIC_PASSWORD}" \
    -H 'Content-Type: application/json' \
    "${MONITORING_ES_URL}/${JWT_METRICS_DATASTREAM}/_search?size=1" \
    -d "{\"query\":{\"exists\":{\"field\":\"metrics.${field}\"}},\"_source\":[\"metrics.${field}\"]}" 2>/dev/null)"
  local val
  val="$(printf '%s' "${result}" | python3 -c "import sys,json; h=json.load(sys.stdin)['hits']['hits']; print(h[0]['_source']['metrics']['${field}'] if h else '')" 2>/dev/null || true)"
  [[ -n "${val}" ]]
}

for metric_field in elasticsearch_cluster_nodes_total elasticsearch_index_docs; do
  check_metric_exists "${metric_field}" || fail "JWT OTLP metrics: no document with non-empty field 'metrics.${metric_field}' found in ${JWT_METRICS_DATASTREAM}"
  echo "${GREEN}  OK: metric field '${metric_field}' present with data${RESET}"
done

echo "${BLUE}  Token principal : ${JWT_TEST_PRINCIPAL}${RESET}"
echo "${BLUE}  Token issuer    : ${JWT_TEST_ISSUER}${RESET}"
echo "${BLUE}  Token audience  : ${JWT_TEST_AUDIENCE}${RESET}"
echo "${BLUE}  Realm name      : ${JWT_TEST_REALM_NAME}${RESET}"
echo "${BLUE}  Key ID          : ${JWT_TEST_KEY_ID}${RESET}"
echo "${BLUE}  Output stream   : ${JWT_METRICS_DATASTREAM}${RESET}"
echo "${BLUE}  Output path     : JWT metrics exporter → OTEL collector → edot-gateway → monitoring ES${RESET}"

echo "${GREEN}All JWT OTEL agent tests passed${RESET}"
