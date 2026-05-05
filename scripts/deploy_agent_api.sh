#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "$0")/common.sh"

# ── Helpers ───────────────────────────────────────────────────────────────────
create_or_update_json() {
  local url="$1" password="$2" path="$3" body="$4"
  local code=""
  for _ in $(seq 1 20); do
    code="$(curl -sk -o /dev/null -w '%{http_code}' -u "elastic:${password}" \
      -H 'Content-Type: application/json' -X PUT "${url}${path}" -d "${body}" || true)"
    if [[ "${code}" == "200" || "${code}" == "201" ]]; then break; fi
    sleep 3
  done
  if [[ "${code}" != "200" && "${code}" != "201" ]]; then
    echo "Failed to apply ${path} on ${url} (HTTP ${code})" >&2
    exit 1
  fi
}

create_api_key() {
  local url="$1" password="$2" name="$3" role_descriptors="$4"
  local resp encoded
  resp="$(curl -sk -u "elastic:${password}" \
    -H 'Content-Type: application/json' \
    -X POST "${url}/_security/api_key" \
    -d "{\"name\":\"${name}\",\"role_descriptors\":${role_descriptors}}")"
  encoded="$(printf '%s' "${resp}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('encoded',''))" 2>/dev/null)"
  if [[ -z "${encoded}" ]]; then
    echo "Failed to create API key '${name}': ${resp}" >&2
    exit 1
  fi
  printf '%s' "${encoded}"
}

wait_port_forward() {
  local port="$1"
  for _ in $(seq 1 30); do
    if curl -sk "https://127.0.0.1:${port}/_cluster/health" >/dev/null 2>&1; then return; fi
    sleep 1
  done
  echo "Port-forward on ${port} did not become ready" >&2
  exit 1
}

# ── Source cluster: API key for the metrics scraper ───────────────────────────
MAIN_ELASTIC_PASSWORD="$(kubectl -n lab-main get secret elasticsearch-main-es-elastic-user \
  -o jsonpath='{.data.elastic}' | base64 -d)"
[[ -z "${MAIN_ELASTIC_PASSWORD}" ]] && { echo "Cannot read main ES password" >&2; exit 1; }

kubectl -n lab-main port-forward service/elasticsearch-main-es-http 19201:9200 \
  >/tmp/edot-apikey-main-pf.log 2>&1 &
MAIN_PF_PID="$!"
trap 'kill "${MAIN_PF_PID}" >/dev/null 2>&1 || true; kill "${MON_PF_PID:-}" >/dev/null 2>&1 || true' EXIT
wait_port_forward 19201

MAIN_ES_URL="https://127.0.0.1:19201"

# Create the monitoring role on the source cluster
create_or_update_json "${MAIN_ES_URL}" "${MAIN_ELASTIC_PASSWORD}" \
  "/_security/role/${APIKEY_ROLE_NAME}" \
  '{"cluster":["monitor","manage_ilm","manage_index_templates"],"indices":[{"names":["*"],"privileges":["monitor","read","view_index_metadata"]}]}'

# Create the API key scoped to that role
SOURCE_API_KEY="$(create_api_key "${MAIN_ES_URL}" "${MAIN_ELASTIC_PASSWORD}" \
  "edot-apikey-monitor-main" \
  "{\"${APIKEY_ROLE_NAME}\":{\"cluster\":[\"monitor\",\"manage_ilm\",\"manage_index_templates\"],\"indices\":[{\"names\":[\"*\"],\"privileges\":[\"monitor\",\"read\",\"view_index_metadata\"]}]}}")"
echo "Source cluster API key created."

# Store in Kubernetes secret (lab-main namespace — used by the scraper pod)
kubectl -n lab-main create secret generic es-creds-source-cluster \
  --from-literal=api_key="${SOURCE_API_KEY}" \
  --dry-run=client -o yaml | kubectl apply -f -

# ── Monitoring cluster: API key for the gateway exporter ──────────────────────
MONITORING_ELASTIC_PASSWORD="$(kubectl -n lab-monitoring get secret elasticsearch-monitoring-es-elastic-user \
  -o jsonpath='{.data.elastic}' | base64 -d)"
[[ -z "${MONITORING_ELASTIC_PASSWORD}" ]] && { echo "Cannot read monitoring ES password" >&2; exit 1; }

kubectl -n lab-monitoring port-forward service/elasticsearch-monitoring-es-http 19202:9200 \
  >/tmp/edot-apikey-mon-pf.log 2>&1 &
MON_PF_PID="$!"
wait_port_forward 19202

MON_ES_URL="https://127.0.0.1:19202"

# Create ingest role and API key on monitoring cluster
create_or_update_json "${MON_ES_URL}" "${MONITORING_ELASTIC_PASSWORD}" \
  "/_security/role/${APIKEY_INGEST_ROLE_NAME}" \
  '{"cluster":["monitor"],"indices":[{"names":["logs-*","metrics-*"],"privileges":["auto_configure","create_doc","view_index_metadata"]}]}'

MONITORING_API_KEY="$(create_api_key "${MON_ES_URL}" "${MONITORING_ELASTIC_PASSWORD}" \
  "edot-apikey-gateway-ingest" \
  "{\"${APIKEY_INGEST_ROLE_NAME}\":{\"cluster\":[\"monitor\"],\"indices\":[{\"names\":[\"logs-*\",\"metrics-*\"],\"privileges\":[\"auto_configure\",\"create_doc\",\"view_index_metadata\"]}]}}")"
echo "Monitoring cluster API key created."

# Store in Kubernetes secret (lab-monitoring namespace — used by gateway pod)
kubectl -n lab-monitoring create secret generic es-creds-monitoring-cluster \
  --from-literal=api_key="${MONITORING_API_KEY}" \
  --dry-run=client -o yaml | kubectl apply -f -

kill "${MAIN_PF_PID}" >/dev/null 2>&1 || true
kill "${MON_PF_PID}" >/dev/null 2>&1 || true
trap - EXIT

# ── Remove any standard collectors that would compete for stream names ─────────
kubectl -n lab-main delete deploy edot-main-metrics --ignore-not-found
kubectl -n lab-main delete ds edot-main-logs --ignore-not-found
kubectl -n lab-monitoring delete cronjob edot-autoops-tsds-deriver --ignore-not-found

# ── Gateway ───────────────────────────────────────────────────────────────────
sed "s/__ELASTIC_AGENT_VERSION__/${ELASTIC_AGENT_VERSION}/g" \
  manifests/edot/gateway-apikey.yaml | kubectl apply -f -
kubectl -n lab-monitoring rollout status deploy/edot-gateway --timeout=180s

# ── API key metrics scraper ────────────────────────────────────────────────────
kubectl -n lab-main delete pod -l app.kubernetes.io/name=edot-main-metrics-api \
  --ignore-not-found --wait=false || true

sed -e "s/__OTEL_CONTRIB_COLLECTOR_VERSION__/${OTEL_CONTRIB_COLLECTOR_VERSION}/g" \
  manifests/edot/main-metrics-otel-api.yaml | kubectl apply -f -

kubectl -n lab-main rollout restart deploy/edot-main-metrics-api >/dev/null
kubectl -n lab-main wait --for=condition=Available deploy/edot-main-metrics-api \
  --timeout=600s || {
  echo "API key metrics deployment did not become available in time." >&2
  kubectl -n lab-main get pods -l app.kubernetes.io/name=edot-main-metrics-api -o wide >&2 || true
  kubectl -n lab-main describe deploy edot-main-metrics-api >&2 || true
  kubectl -n lab-main logs -l app.kubernetes.io/name=edot-main-metrics-api --tail=200 >&2 || true
  exit 1
}

# ── Logs scraper ───────────────────────────────────────────────────────────────
sed -e "s/__ELASTIC_AGENT_VERSION__/${ELASTIC_AGENT_VERSION}/g" \
  manifests/edot/main-logs-otel-api.yaml | kubectl apply -f -
kubectl -n lab-main rollout status ds/edot-main-logs-api --timeout=300s

# ── Extra cluster (optional) ──────────────────────────────────────────────────
if extra_cluster_enabled; then
  echo "EXTRA_CLUSTER=true: deploying extra cluster (${EXTRA_CLUSTER_NAME}) in namespace ${EXTRA_CLUSTER_NAMESPACE}..."

  # Create the extra cluster namespace
  kubectl create namespace "${EXTRA_CLUSTER_NAMESPACE}" --dry-run=client -o yaml | kubectl apply -f -

  # Issue TLS cert for extra cluster HTTP endpoint (idempotent)
  sed -e "s/__EXTRA_CLUSTER_NAME__/${EXTRA_CLUSTER_NAME}/g" \
      -e "s/__EXTRA_CLUSTER_NAMESPACE__/${EXTRA_CLUSTER_NAMESPACE}/g" \
    manifests/cert-manager/cert-es-extra.yaml | kubectl apply -f - || true
  kubectl -n "${EXTRA_CLUSTER_NAMESPACE}" wait --for=condition=Ready \
    certificate/es-extra-cert --timeout=120s

  # Deploy ECK cluster only if it doesn't already exist (ECK forbids version downgrades)
  if kubectl -n "${EXTRA_CLUSTER_NAMESPACE}" get elasticsearch "${EXTRA_CLUSTER_NAME}" >/dev/null 2>&1; then
    echo "Extra cluster ${EXTRA_CLUSTER_NAME} already exists, skipping creation."
  else
    sed -e "s/__ES_VERSION__/${ES_VERSION}/g" \
        -e "s/__EXTRA_CLUSTER_NAME__/${EXTRA_CLUSTER_NAME}/g" \
        -e "s/__EXTRA_CLUSTER_NAMESPACE__/${EXTRA_CLUSTER_NAMESPACE}/g" \
      manifests/elastic/elasticsearch-extra.yaml | kubectl apply -f -
  fi

  # Wait for ECK to provision pods (takes several seconds after CRD apply)
  echo "Waiting for ECK to provision ${EXTRA_CLUSTER_NAME} pods..."
  for _ in $(seq 1 60); do
    if kubectl -n "${EXTRA_CLUSTER_NAMESPACE}" get pod \
        -l elasticsearch.k8s.elastic.co/cluster-name="${EXTRA_CLUSTER_NAME}" \
        --no-headers 2>/dev/null | grep -q .; then
      break
    fi
    sleep 3
  done
  kubectl -n "${EXTRA_CLUSTER_NAMESPACE}" wait --for=condition=Ready pod \
    -l elasticsearch.k8s.elastic.co/cluster-name="${EXTRA_CLUSTER_NAME}" --timeout=900s
  echo "Extra cluster ${EXTRA_CLUSTER_NAME} is ready."

  # Create monitoring API key on extra cluster
  EXTRA_ELASTIC_PASSWORD="$(kubectl -n "${EXTRA_CLUSTER_NAMESPACE}" get secret \
    "${EXTRA_CLUSTER_NAME}-es-elastic-user" -o jsonpath='{.data.elastic}' | base64 -d)"
  [[ -z "${EXTRA_ELASTIC_PASSWORD}" ]] && { echo "Cannot read extra ES password" >&2; exit 1; }

  kubectl -n "${EXTRA_CLUSTER_NAMESPACE}" port-forward \
    "service/${EXTRA_CLUSTER_NAME}-es-http" 19203:9200 \
    >/tmp/edot-apikey-extra-pf.log 2>&1 &
  EXTRA_PF_PID="$!"
  trap 'kill "${EXTRA_PF_PID}" >/dev/null 2>&1 || true' EXIT
  wait_port_forward 19203

  EXTRA_ES_URL="https://127.0.0.1:19203"

  create_or_update_json "${EXTRA_ES_URL}" "${EXTRA_ELASTIC_PASSWORD}" \
    "/_security/role/${APIKEY_ROLE_NAME}" \
    '{"cluster":["monitor","manage_ilm","manage_index_templates"],"indices":[{"names":["*"],"privileges":["monitor","read","view_index_metadata"]}]}'

  EXTRA_API_KEY="$(create_api_key "${EXTRA_ES_URL}" "${EXTRA_ELASTIC_PASSWORD}" \
    "edot-apikey-monitor-extra" \
    "{\"${APIKEY_ROLE_NAME}\":{\"cluster\":[\"monitor\",\"manage_ilm\",\"manage_index_templates\"],\"indices\":[{\"names\":[\"*\"],\"privileges\":[\"monitor\",\"read\",\"view_index_metadata\"]}]}}")"
  echo "Extra cluster API key created."

  # Store in lab-main namespace so the metrics scraper pod can reference it
  kubectl -n lab-main create secret generic es-creds-extra-cluster \
    --from-literal=api_key="${EXTRA_API_KEY}" \
    --dry-run=client -o yaml | kubectl apply -f -

  kill "${EXTRA_PF_PID}" >/dev/null 2>&1 || true
  trap - EXIT

  # Inject extra API key env var into the metrics scraper deployment
  kubectl -n lab-main patch deploy edot-main-metrics-api --type=strategic -p "$(cat <<'PATCH'
spec:
  template:
    spec:
      containers:
      - name: edot-main-metrics-api
        env:
        - name: ES_EXTRA_API_KEY
          valueFrom:
            secretKeyRef:
              name: es-creds-extra-cluster
              key: api_key
PATCH
)"

  # Apply extended metrics ConfigMap — two receivers, one per cluster
  kubectl apply -f - <<EOF
apiVersion: v1
kind: ConfigMap
metadata:
  name: edot-main-metrics-api-config
  namespace: lab-main
data:
  config.yaml: |
    receivers:
      elasticsearch/main:
        collection_interval: 10s
        initial_delay: 1s
        endpoint: https://elasticsearch-main-es-http.lab-main.svc.cluster.local:9200
        nodes: ["_all"]
        indices: ["_all"]
        tls:
          ca_file: /etc/otel/certs/ca.crt
        auth:
          authenticator: headers_setter/main
      elasticsearch/extra:
        collection_interval: 10s
        initial_delay: 1s
        endpoint: https://${EXTRA_CLUSTER_NAME}-es-http.${EXTRA_CLUSTER_NAMESPACE}.svc.cluster.local:9200
        nodes: ["_all"]
        indices: ["_all"]
        tls:
          ca_file: /etc/otel/certs/ca.crt
        auth:
          authenticator: headers_setter/extra

    extensions:
      health_check:
        endpoint: 0.0.0.0:13133
      headers_setter/main:
        headers:
          - action: insert
            key: Authorization
            value: ApiKey \${env:ES_SOURCE_API_KEY}
      headers_setter/extra:
        headers:
          - action: insert
            key: Authorization
            value: ApiKey \${env:ES_EXTRA_API_KEY}

    processors:
      memory_limiter:
        check_interval: 1s
        limit_mib: 256
      resource/main:
        attributes:
          - {key: data_stream.type, value: metrics, action: upsert}
          - {key: data_stream.dataset, value: elasticsearch.stack_monitoring, action: upsert}
          - {key: data_stream.namespace, value: main, action: upsert}
          - {key: elasticsearch.cluster.name, value: main, action: upsert}
          - {key: service.name, value: elasticsearch-main, action: upsert}
          - {key: service.namespace, value: lab-main, action: upsert}
          - {key: orchestrator.cluster.name, value: edot-lab, action: upsert}
      resource/extra:
        attributes:
          - {key: data_stream.type, value: metrics, action: upsert}
          - {key: data_stream.dataset, value: elasticsearch.stack_monitoring, action: upsert}
          - {key: data_stream.namespace, value: main, action: upsert}
          - {key: elasticsearch.cluster.name, value: extra, action: upsert}
          - {key: service.name, value: ${EXTRA_CLUSTER_NAME}, action: upsert}
          - {key: service.namespace, value: ${EXTRA_CLUSTER_NAMESPACE}, action: upsert}
          - {key: orchestrator.cluster.name, value: edot-lab, action: upsert}
      batch:
        send_batch_size: 1024
        send_batch_max_size: 2048
        timeout: 5s

    exporters:
      otlp_grpc/gateway:
        endpoint: edot-gateway.lab-monitoring.svc.cluster.local:4317
        tls:
          insecure: true

    service:
      extensions: [health_check, headers_setter/main, headers_setter/extra]
      pipelines:
        metrics/main:
          receivers: [elasticsearch/main]
          processors: [memory_limiter, resource/main, batch]
          exporters: [otlp_grpc/gateway]
        metrics/extra:
          receivers: [elasticsearch/extra]
          processors: [memory_limiter, resource/extra, batch]
          exporters: [otlp_grpc/gateway]
EOF

  # Apply extended logs ConfigMap — filelog per cluster namespace
  kubectl apply -f - <<EOF
apiVersion: v1
kind: ConfigMap
metadata:
  name: edot-main-logs-api-config
  namespace: lab-main
data:
  config.yaml: |
    receivers:
      filelog/main:
        include:
          - /var/log/containers/*_lab-main_elasticsearch-*.log
        start_at: beginning
        include_file_path: true
      filelog/extra:
        include:
          - /var/log/containers/*_${EXTRA_CLUSTER_NAMESPACE}_elasticsearch-*.log
        start_at: beginning
        include_file_path: true

    processors:
      memory_limiter:
        check_interval: 1s
        limit_mib: 256
      attributes/logs_main:
        actions:
          - {key: data_stream.dataset, action: upsert, value: elasticsearch.logs}
          - {key: data_stream.namespace, action: upsert, value: main}
      attributes/logs_extra:
        actions:
          - {key: data_stream.dataset, action: upsert, value: elasticsearch.logs}
          - {key: data_stream.namespace, action: upsert, value: main}
      k8sattributes:
        auth_type: serviceAccount
        passthrough: false
        filter:
          node_from_env_var: KUBE_NODE_NAME
      resource/main:
        attributes:
          - {key: elasticsearch.cluster.name, action: upsert, value: main}
          - {key: service.name, action: upsert, value: elasticsearch-main}
          - {key: service.namespace, action: upsert, value: lab-main}
          - {key: orchestrator.cluster.name, action: upsert, value: edot-lab}
      resource/extra:
        attributes:
          - {key: elasticsearch.cluster.name, action: upsert, value: extra}
          - {key: service.name, action: upsert, value: ${EXTRA_CLUSTER_NAME}}
          - {key: service.namespace, action: upsert, value: ${EXTRA_CLUSTER_NAMESPACE}}
          - {key: orchestrator.cluster.name, action: upsert, value: edot-lab}
      batch:
        send_batch_size: 1024
        timeout: 5s

    exporters:
      otlp_grpc/gateway:
        endpoint: edot-gateway.lab-monitoring.svc.cluster.local:4317
        tls:
          insecure: true

    extensions:
      health_check:
        endpoint: 0.0.0.0:13133

    service:
      extensions: [health_check]
      pipelines:
        logs/main:
          receivers: [filelog/main]
          processors: [memory_limiter, attributes/logs_main, k8sattributes, resource/main, batch]
          exporters: [otlp_grpc/gateway]
        logs/extra:
          receivers: [filelog/extra]
          processors: [memory_limiter, attributes/logs_extra, k8sattributes, resource/extra, batch]
          exporters: [otlp_grpc/gateway]
EOF

  # Restart collectors so they pick up the updated ConfigMaps and new env var
  kubectl -n lab-main rollout restart deploy/edot-main-metrics-api
  kubectl -n lab-main rollout restart ds/edot-main-logs-api
  kubectl -n lab-main wait --for=condition=Available deploy/edot-main-metrics-api --timeout=300s
  kubectl -n lab-main rollout status ds/edot-main-logs-api --timeout=300s
fi

bash "$(dirname "$0")/import_apikey_dashboard.sh"

echo "API key OTEL collector deployment is ready."
echo "Run ./scripts/test_agent_api.sh to validate end-to-end."
