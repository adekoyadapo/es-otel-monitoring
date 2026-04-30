#!/usr/bin/env bash
# Deploy a contrib OpenTelemetryCollector that scrapes YOUR Elasticsearch workload (e.g. ES
# running in Podman on this machine) and forwards metrics through the kube-stack gateway
# into Elastic Cloud Serverless (Managed OTLP). Serverless is the telemetry sink only — do
# not point ELASTICSEARCH_URL at the Serverless Elasticsearch API.
#
# Credentials in elasticsearch-scrape-target must be valid on the Podman/local Elasticsearch
# (API key with monitor, or create a dedicated local key). The gateway still uses
# elastic-secret-otel for mOTLP ingest auth (separate).
#
# Prerequisites:
#   - opentelemetry-kube-stack installed (gateway service exists).
#   - ELASTICSEARCH_URL reachable from inside k3d (e.g. https://host.k3d.internal:9200 if ES
#     is published on the host; or your LAN IP and port Podman maps to ES).
#
# Usage (do not paste keys into chat):
#   export ELASTICSEARCH_URL='https://host.k3d.internal:9200'
#   export ELASTICSEARCH_API_KEY='<base64 API key valid ON THAT LOCAL ES>'
#   ./scripts/install_elasticsearch_scrape_collector.sh
set -euo pipefail

NAMESPACE="${NAMESPACE:-opentelemetry-operator-system}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

: "${ELASTICSEARCH_URL:?Set ELASTICSEARCH_URL to the Elasticsearch you run in Podman (reachable from k3d)}"
: "${ELASTICSEARCH_API_KEY:?Set ELASTICSEARCH_API_KEY to a base64 API key for THAT Elasticsearch}"

AUTH_HEADER="ApiKey ${ELASTICSEARCH_API_KEY}"

kubectl get namespace "${NAMESPACE}" &>/dev/null || kubectl create namespace "${NAMESPACE}"

kubectl -n "${NAMESPACE}" delete secret elasticsearch-scrape-target --ignore-not-found
kubectl -n "${NAMESPACE}" create secret generic elasticsearch-scrape-target \
  --from-literal=endpoint="${ELASTICSEARCH_URL}" \
  --from-literal=authorization="${AUTH_HEADER}"

kubectl apply -f "${ROOT}/manifests/opentelemetry-elasticsearch-scrape.yaml"

echo "Waiting for deployment rollout..."
kubectl -n "${NAMESPACE}" rollout status "deployment/opentelemetry-elasticsearch-scrape-collector" --timeout=180s

echo "Done. Logs: kubectl -n ${NAMESPACE} logs deploy/opentelemetry-elasticsearch-scrape-collector --tail=80"
echo "ECK / private CA: the manifest uses tls.insecure_skip_verify on the elasticsearch receiver (not tls.insecure)."
echo "Tune service.name / service.namespace in resource/dataset if dashboard filters need different labels."
