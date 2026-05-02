#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "$0")/common.sh"

MAIN_ELASTIC_PASSWORD="$(kubectl -n lab-main get secret elasticsearch-main-es-elastic-user -o jsonpath='{.data.elastic}' | base64 -d)"
if [[ -z "${MAIN_ELASTIC_PASSWORD}" ]]; then
  echo "Unable to read bootstrap password for elasticsearch-main" >&2
  exit 1
fi

JWT_SHARED_SECRET="$(python3 - <<'PY'
import secrets
print(secrets.token_urlsafe(48))
PY
)"

JWT_KEY_B64="$(python3 - <<'PY'
import base64
import secrets
print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode().rstrip("="))
PY
)"

JWT_JWK_JSON="$(python3 - "${JWT_KEY_B64}" "${JWT_TEST_KEY_ID}" <<'PY'
import json
import sys

k = sys.argv[1]
kid = sys.argv[2]
print(json.dumps({"keys": [{"kty": "oct", "kid": kid, "alg": "HS256", "use": "sig", "k": k}]}, separators=(",", ":")))
PY
)"

kubectl -n lab-main port-forward service/elasticsearch-main-es-http 19201:9200 >/tmp/edot-jwt-main-pf.log 2>&1 &
PF_PID="$!"
trap 'kill "${PF_PID}" >/dev/null 2>&1 || true' EXIT
for _ in $(seq 1 30); do
  if curl -sk "https://127.0.0.1:19201/_cluster/health" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

LICENSE_TYPE="$(curl -sk -u "elastic:${MAIN_ELASTIC_PASSWORD}" "https://127.0.0.1:19201/_license" | sed -n 's/.*"type":"\([^"]*\)".*/\1/p')"
if [[ "${LICENSE_TYPE}" == "basic" ]]; then
  echo "JWT realms are disabled on the current basic license. Use a trial or commercial license to validate this overlay." >&2
  exit 1
fi

kubectl -n lab-main create secret generic "${JWT_TEST_SECRET_NAME}" \
  --from-literal="xpack.security.authc.realms.jwt.${JWT_TEST_REALM_NAME}.client_authentication.shared_secret=${JWT_SHARED_SECRET}" \
  --from-literal="xpack.security.authc.realms.jwt.${JWT_TEST_REALM_NAME}.hmac_jwkset=${JWT_JWK_JSON}" \
  --dry-run=client -o yaml | kubectl apply -f -

sed \
  -e "s/__ES_VERSION__/${ES_VERSION}/g" \
  -e "s/__MAIN_ES_NODES__/${MAIN_ES_NODES}/g" \
  -e "s/__MAIN_ES_CPU__/${MAIN_ES_CPU}/g" \
  -e "s/__MAIN_ES_MEMORY__/${MAIN_ES_MEMORY}/g" \
  -e "s/__JWT_TEST_REALM_NAME__/${JWT_TEST_REALM_NAME}/g" \
  -e "s/__JWT_TEST_ISSUER__/${JWT_TEST_ISSUER}/g" \
  -e "s/__JWT_TEST_AUDIENCE__/${JWT_TEST_AUDIENCE}/g" \
  -e "s/__JWT_TEST_PRINCIPAL__/${JWT_TEST_PRINCIPAL}/g" \
  manifests/jwt/elasticsearch-main-jwt.yaml | kubectl apply -f -

kubectl -n lab-main wait --for=condition=Ready pod -l elasticsearch.k8s.elastic.co/cluster-name=elasticsearch-main --timeout=900s
kubectl -n lab-main wait --for=condition=Ready pod -l kibana.k8s.elastic.co/name=kibana-main --timeout=420s

create_or_update_json() {
  local url="$1"
  local elastic_password="$2"
  local path="$3"
  local body="$4"
  local code=""

  for _ in $(seq 1 20); do
    code="$(
      curl -sk -o /dev/null -w '%{http_code}' -u "elastic:${elastic_password}" \
        -H 'Content-Type: application/json' \
        -X PUT "${url}${path}" \
        -d "${body}" || true
    )"
    if [[ "${code}" == "200" || "${code}" == "201" ]]; then
      break
    fi
    sleep 3
  done

  if [[ "${code}" != "200" && "${code}" != "201" ]]; then
    echo "Failed to apply ${path} on ${url}" >&2
    exit 1
  fi
}

create_or_update_json \
  "https://127.0.0.1:19201" \
  "${MAIN_ELASTIC_PASSWORD}" \
  "/_security/role/${JWT_TEST_ROLE_NAME}" \
  '{"cluster":["monitor"],"indices":[{"names":[".monitoring-*","metrics-*","logs-*"],"privileges":["monitor","read","view_index_metadata"]}]}'

create_or_update_json \
  "https://127.0.0.1:19201" \
  "${MAIN_ELASTIC_PASSWORD}" \
  "/_security/role_mapping/${JWT_TEST_ROLE_MAPPING_NAME}" \
  "{\"enabled\":true,\"roles\":[\"${JWT_TEST_ROLE_NAME}\"],\"rules\":{\"all\":[{\"field\":{\"realm.name\":\"${JWT_TEST_REALM_NAME}\"}},{\"field\":{\"username\":\"${JWT_TEST_PRINCIPAL}\"}}]}}"

cat >/tmp/edot-jwt-test.env <<EOF
JWT_TEST_REALM_NAME=${JWT_TEST_REALM_NAME}
JWT_TEST_ISSUER=${JWT_TEST_ISSUER}
JWT_TEST_AUDIENCE=${JWT_TEST_AUDIENCE}
JWT_TEST_PRINCIPAL=${JWT_TEST_PRINCIPAL}
JWT_TEST_ROLE_NAME=${JWT_TEST_ROLE_NAME}
JWT_TEST_ROLE_MAPPING_NAME=${JWT_TEST_ROLE_MAPPING_NAME}
JWT_TEST_KEY_ID=${JWT_TEST_KEY_ID}
JWT_SHARED_SECRET=${JWT_SHARED_SECRET}
JWT_KEY_B64=${JWT_KEY_B64}
MAIN_ELASTIC_PASSWORD=${MAIN_ELASTIC_PASSWORD}
EOF

echo "JWT test overlay installed."
echo "Run ./scripts/test_jwt_auth.sh to validate the JWT realm."
