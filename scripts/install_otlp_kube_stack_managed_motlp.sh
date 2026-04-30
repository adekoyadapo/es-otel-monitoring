#!/usr/bin/env bash
# Install Elastic's opentelemetry-kube-stack (EDOT) with Managed OTLP export to Serverless.
# Prerequisites: kubectl, helm; Helm repo open-telemetry added.
#
# 1. Create an API key in Kibana (Observability project) with ingest privileges for mOTLP.
# 2. Export (do not commit; never paste keys into chat):
#    export ELASTIC_OTLP_ENDPOINT='https://<project>.ingest.<region>.aws.elastic.cloud:443'
#    export ELASTIC_API_KEY='<base64 API key id:secret>'
# Optional:
#    export ONBOARDING_ID='<uuid from Kibana OpenTelemetry onboarding>'
set -euo pipefail

: "${ELASTIC_OTLP_ENDPOINT:?Set ELASTIC_OTLP_ENDPOINT to your Managed OTLP ingest URL}"
: "${ELASTIC_API_KEY:?Set ELASTIC_API_KEY to a base64 Elasticsearch API key}"

NAMESPACE="${NAMESPACE:-opentelemetry-operator-system}"
HELM_RELEASE="${HELM_RELEASE:-opentelemetry-kube-stack}"
CHART_VERSION="${CHART_VERSION:-0.12.4}"
VALUES_URL="${VALUES_URL:-https://raw.githubusercontent.com/elastic/elastic-agent/refs/tags/v9.3.3/deploy/helm/edot-collector/kube-stack/managed_otlp/values.yaml}"
ONBOARDING_ID="${ONBOARDING_ID:-59ae3783-4f58-4729-ad22-53c5a52a7847}"

kubectl get namespace "${NAMESPACE}" &>/dev/null || kubectl create namespace "${NAMESPACE}"

kubectl -n "${NAMESPACE}" delete secret elastic-secret-otel --ignore-not-found
kubectl -n "${NAMESPACE}" create secret generic elastic-secret-otel \
  --from-literal=elastic_otlp_endpoint="${ELASTIC_OTLP_ENDPOINT}" \
  --from-literal=elastic_api_key="${ELASTIC_API_KEY}"

helm repo add open-telemetry https://open-telemetry.github.io/opentelemetry-helm-charts 2>/dev/null || true
helm repo update open-telemetry

helm upgrade --install "${HELM_RELEASE}" open-telemetry/opentelemetry-kube-stack \
  --namespace "${NAMESPACE}" \
  --values "${VALUES_URL}" \
  --version "${CHART_VERSION}" \
  --set 'collectors.daemon.config.processors.resource\/onboarding_id.attributes[0].action=upsert' \
  --set 'collectors.daemon.config.processors.resource\/onboarding_id.attributes[0].key=onboarding.id' \
  --set "collectors.daemon.config.processors.resource\\/onboarding_id.attributes[0].value=${ONBOARDING_ID}" \
  --set 'collectors.daemon.config.service.pipelines.logs\/node.processors[8]=resource/onboarding_id' \
  --set 'collectors.daemon.config.service.pipelines.metrics\/node\/otel.processors[8]=resource/onboarding_id'

echo "Done. Check pods: kubectl get pods -n ${NAMESPACE}"
