#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "$0")/common.sh"

JWT_ENV_FILE="${JWT_ENV_FILE:-/tmp/edot-jwt-test.env}"
if [[ ! -f "${JWT_ENV_FILE}" ]]; then
  echo "JWT env file not found: ${JWT_ENV_FILE}. Run ./scripts/deploy_jwt_test.sh first." >&2
  exit 1
fi

# shellcheck disable=SC1090
source "${JWT_ENV_FILE}"

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
LICENSE_TYPE="$(curl -sk -u "elastic:${MAIN_ELASTIC_PASSWORD}" "${MAIN_ES_URL}/_license" | sed -n 's/.*"type":"\([^"]*\)".*/\1/p')"
if [[ "${LICENSE_TYPE}" == "basic" ]]; then
  echo "JWT realms are disabled on the current basic license. Use a trial or commercial license to validate this overlay." >&2
  exit 1
fi

JWT_ACCESS_TOKEN="$(python3 - "${JWT_KEY_B64}" "${JWT_TEST_ISSUER}" "${JWT_TEST_AUDIENCE}" "${JWT_TEST_PRINCIPAL}" "${JWT_TEST_KEY_ID}" <<'PY'
import base64
import hashlib
import hmac
import json
import secrets
import sys
import time

key_b64, issuer, audience, principal, kid = sys.argv[1:6]

def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")

def decode_b64url(value: str) -> bytes:
    pad = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + pad)

header = {"alg": "HS256", "typ": "JWT", "kid": kid}
now = int(time.time())
payload = {
    "iss": issuer,
    "aud": audience,
    "sub": principal,
    "iat": now,
    "nbf": now - 5,
    "exp": now + 600,
    "jti": secrets.token_urlsafe(18),
}

signing_input = f"{b64url(json.dumps(header, separators=(',', ':')).encode())}.{b64url(json.dumps(payload, separators=(',', ':')).encode())}"
secret = decode_b64url(key_b64)
signature = hmac.new(secret, signing_input.encode(), hashlib.sha256).digest()
print(f"{signing_input}.{b64url(signature)}")
PY
)"

AUTH_RESP="$(curl -sk \
  -H "Authorization: Bearer ${JWT_ACCESS_TOKEN}" \
  -H "ES-Client-Authentication: SharedSecret ${JWT_SHARED_SECRET}" \
  "${MAIN_ES_URL}/_security/_authenticate")"
echo "${AUTH_RESP}" | grep -q "\"username\":\"${JWT_TEST_PRINCIPAL}\""

CLUSTER_HEALTH_CODE="$(curl -sk -o /dev/null -w '%{http_code}' \
  -H "Authorization: Bearer ${JWT_ACCESS_TOKEN}" \
  -H "ES-Client-Authentication: SharedSecret ${JWT_SHARED_SECRET}" \
  "${MAIN_ES_URL}/_cluster/health")"
if [[ "${CLUSTER_HEALTH_CODE}" != "200" ]]; then
  echo "JWT-authenticated cluster health request failed with HTTP ${CLUSTER_HEALTH_CODE}" >&2
  exit 1
fi

echo "JWT authentication validated for ${JWT_TEST_PRINCIPAL}"
