#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "$0")/common.sh"

# Always regenerate JWT credentials so the collector starts with a fresh token.
JWT_ENV_FILE="${JWT_ENV_FILE:-/tmp/edot-jwt-test.env}"
rm -f "${JWT_ENV_FILE}"
bash "$(dirname "$0")/deploy_jwt_test.sh"

# shellcheck disable=SC1090
source "${JWT_ENV_FILE}"

# ── Gateway ──────────────────────────────────────────────────────────────────
# The JWT OTEL collector forwards metrics to the gateway via OTLP. Deploy the
# gateway if it is not already running (agent mode deletes it by default).
if ! kubectl -n lab-monitoring get deploy edot-gateway >/dev/null 2>&1; then
  echo "Deploying edot-gateway (required for JWT OTEL output)..."
  sed "s/__ELASTIC_AGENT_VERSION__/${ELASTIC_AGENT_VERSION}/g" \
    manifests/edot/gateway.yaml | kubectl apply -f -
  kubectl -n lab-monitoring rollout status deploy/edot-gateway --timeout=180s
fi

# Remove any standard collectors from previous autoops or agent runs so the JWT
# workflow is isolated and does not compete for the same stream names.
kubectl -n lab-main delete deploy edot-main-metrics --ignore-not-found
kubectl -n lab-main delete ds edot-main-logs --ignore-not-found
kubectl -n lab-monitoring delete cronjob edot-autoops-tsds-deriver --ignore-not-found

# ── JWT credentials secret ───────────────────────────────────────────────────
kubectl -n lab-main create secret generic agent-jwt-mint-credentials \
  --from-literal=JWT_KEY_B64="${JWT_KEY_B64}" \
  --from-literal=JWT_ISSUER="${JWT_TEST_ISSUER}" \
  --from-literal=JWT_AUDIENCE="${JWT_TEST_AUDIENCE}" \
  --from-literal=JWT_PRINCIPAL="${JWT_TEST_PRINCIPAL}" \
  --from-literal=JWT_KEY_ID="${JWT_TEST_KEY_ID}" \
  --from-literal=JWT_SHARED_SECRET="${JWT_SHARED_SECRET}" \
  --dry-run=client -o yaml | kubectl apply -f -

# ── JWT OTEL metrics collector ────────────────────────────────────────────────
# Separate JWT path. Standard collectors are removed first so the JWT workflow
# does not clash with any previous autoops or agent run.
kubectl -n lab-main delete pod -l app.kubernetes.io/name=edot-main-metrics-jwt --ignore-not-found --wait=false || true
kubectl -n lab-main delete ds edot-main-logs-jwt --ignore-not-found || true
sed "s/__ELASTIC_AGENT_VERSION__/${ELASTIC_AGENT_VERSION}/g" \
  manifests/edot/main-metrics-otel-jwt.yaml | kubectl apply -f -

kubectl -n lab-main rollout restart deploy/edot-main-metrics-jwt >/dev/null

kubectl -n lab-main wait --for=condition=Available deploy/edot-main-metrics-jwt --timeout=600s || {
  echo "JWT metrics Deployment did not become available in time. Debugging:" >&2
  kubectl -n lab-main get pods -l app.kubernetes.io/name=edot-main-metrics-jwt -o wide >&2 || true
  kubectl -n lab-main describe deploy edot-main-metrics-jwt >&2 || true
  kubectl -n lab-main logs -l app.kubernetes.io/name=edot-main-metrics-jwt --tail=200 >&2 || true
  exit 1
}

bash "$(dirname "$0")/import_jwt_dashboard.sh"

echo "JWT OTEL collector deployment is ready."
echo "Run ./scripts/test_agent_jwt.sh to validate end-to-end."
