# API key-authenticated Elasticsearch monitoring with OTEL

This guide covers the API key authentication path for Elasticsearch monitoring using the OpenTelemetry `elasticsearchreceiver` with `headers_setter` extension. It explains how the authentication works end-to-end, what gets shipped, how to tune it, and how to extend it to multiple clusters.

## Architecture overview

The API key path monitors a source Elasticsearch cluster without storing a username or password in the collector configuration. Authentication uses an Elasticsearch API key injected at request time by the `headers_setter` extension. The API key is stored in a Kubernetes secret, mounted into the collector pod as an environment variable, and never written to any ConfigMap.

```
┌─────────────────────────────────────────────────────────────────────┐
│  edot-main-metrics-api pod (namespace: lab-main)                    │
│                                                                     │
│  [elastic-agent, EDOT runtime]                                      │
│       │  elasticsearchreceiver polls https://ES:9200                │
│       │  headers_setter injects:                                    │
│       │    Authorization: ApiKey <encoded>                          │
│       │                                                             │
│       ▼ OTLP/gRPC :4317                                             │
└───────────────────────────────────┼─────────────────────────────────┘
                                    │
                                    ▼
                  edot-gateway pod (namespace: lab-monitoring)
                       │  receives OTLP/gRPC from scrapers
                       │  elasticsearch exporter writes directly to
                       │  monitoring cluster via API key
                       │    Authorization: ApiKey <encoded>
                       ▼
           monitoring Elasticsearch cluster
           data stream: metrics-elasticsearch.stack_monitoring.otel-main
```

The `elasticsearchreceiver` talks directly to the source cluster over HTTPS. The `headers_setter` extension intercepts each outbound request and appends the `Authorization: ApiKey` header before the request leaves the pod. No proxy sidecar, no token minting, no refresh cycle.

## Pod containers

Each scraper deployment runs a single container.

### otel-collector-contrib (metrics scraper)

Runs `otel/opentelemetry-collector-contrib` for the metrics scraper. The `elasticsearchreceiver` and `headers_setter` extension are OTel Contrib components — they are not included in the EDOT distribution. Configuration:

- **Receiver**: `elasticsearchreceiver` pointing at the source cluster's Kubernetes service DNS over HTTPS. TLS is validated against the ECK root CA mounted at `/etc/otel/certs/ca.crt`.
- **Runtime**: `otel/opentelemetry-collector-contrib` — required because `elasticsearchreceiver` and `headers_setter` are OTel Contrib-only components not present in the EDOT distribution. The gateway and logs collector use `docker.elastic.co/elastic-agent/elastic-agent` with `ELASTIC_AGENT_OTEL=true`.
- **Auth**: `headers_setter` extension injects `Authorization: ApiKey ${env:ES_SOURCE_API_KEY}` into every request the receiver makes.
- **Processor**: `resource/main` sets `data_stream.*`, `service.name`, and `orchestrator.cluster.name` attributes for routing.
- **Exporter**: `otlp_grpc/gateway` forwards to the in-cluster EDOT gateway.

Receiver config:
```yaml
receivers:
  elasticsearch:
    collection_interval: 10s
    initial_delay: 1s
    endpoint: https://elasticsearch-main-es-http.lab-main.svc.cluster.local:9200
    nodes: ["_all"]
    indices: ["_all"]
    tls:
      ca_file: /etc/otel/certs/ca.crt
    auth:
      authenticator: headers_setter

extensions:
  headers_setter:
    headers:
      - action: insert
        key: Authorization
        value: ApiKey ${env:ES_SOURCE_API_KEY}
```

## How API key authentication works

### API key format

Elasticsearch API key authentication uses the `encoded` field returned by `POST /_security/api_key`. The encoded value is `base64(id:api_key)`. This value is stored verbatim in the Kubernetes secret and injected verbatim into the `Authorization` header:

```
Authorization: ApiKey <encoded>
```

The deploy script creates the API key, extracts the `encoded` field, and stores it in the `es-creds-source-cluster` secret. No manual encoding is required.

### headers_setter extension

The `headers_setter` extension is an OTEL component that intercepts HTTP requests made by components that declare `auth.authenticator: headers_setter`. The elasticsearchreceiver uses `confighttp.ClientConfig` which supports this pattern. On each poll cycle, the extension reads `ES_SOURCE_API_KEY` from the pod environment and appends the Authorization header before the receiver's HTTP request is dispatched.

### Elasticsearch security model

On the source cluster, the API key is scoped to a monitoring role:

```json
{
  "cluster": ["monitor", "manage_ilm", "manage_index_templates"],
  "indices": [{"names": ["*"], "privileges": ["monitor", "read", "view_index_metadata"]}]
}
```

The key never has write or manage access. It can only read cluster health, node stats, and index stats — exactly what the receiver needs.

On the monitoring cluster, a separate API key is created for the gateway exporter with ingest privileges:

```json
{
  "cluster": ["monitor"],
  "indices": [{"names": ["logs-*", "metrics-*"], "privileges": ["auto_configure", "create_doc", "view_index_metadata"]}]
}
```

Both keys are scoped to minimum required privileges.

## Kubernetes configuration

### Secrets

Two Kubernetes secrets carry the credentials:

| Secret name | Namespace | Key | Purpose |
|-------------|-----------|-----|---------|
| `es-creds-source-cluster` | `lab-main` | `api_key` | API key for the scraper to read from the source cluster |
| `es-creds-monitoring-cluster` | `lab-monitoring` | `api_key` | API key for the gateway to write to the monitoring cluster |

Both are created by `deploy_agent_api.sh` via `kubectl create secret generic --dry-run=client -o yaml | kubectl apply -f -`. Template YAML files for manual creation are in `manifests/secrets/`.

### Scraper deployment (manifests/edot/main-metrics-otel-api.yaml)

The `ES_SOURCE_API_KEY` env var is sourced from the secret:
```yaml
env:
  - name: ES_SOURCE_API_KEY
    valueFrom:
      secretKeyRef:
        name: es-creds-source-cluster
        key: api_key
```

The pod mounts the ECK root CA for TLS verification:
```yaml
volumes:
  - name: root-ca
    secret:
      secretName: edot-root-ca
```

### Gateway deployment (manifests/edot/gateway-apikey.yaml)

The gateway uses the `elasticsearch` exporter with API key auth. The endpoint is set as a plain env var; the key comes from the secret:
```yaml
env:
  - name: MONITORING_ES_ENDPOINT
    value: https://elasticsearch-monitoring-es-http.lab-monitoring.svc.cluster.local:9200
  - name: MONITORING_ES_API_KEY
    valueFrom:
      secretKeyRef:
        name: es-creds-monitoring-cluster
        key: api_key
```

Gateway exporter config:
```yaml
exporters:
  elasticsearch/monitoring:
    endpoints:
      - ${env:MONITORING_ES_ENDPOINT}
    headers:
      Authorization: ApiKey ${env:MONITORING_ES_API_KEY}
    mapping:
      mode: otel
    metrics_index: metrics-elasticsearch.stack_monitoring.otel-main
    logs_index: logs-elasticsearch.logs.otel-main
    tls:
      ca_file: /etc/edot/certs/ca.crt
```

## OTEL data model in the monitoring cluster

With `mapping.mode: otel` on the gateway, data lands as:

| Path | What it contains |
|------|-----------------|
| `metrics.<metric_name>` | The numeric gauge value |
| `resource.attributes.elasticsearch.cluster.name` | Source cluster name |
| `resource.attributes.elasticsearch.node.name` | Node name (node-level metrics) |
| `resource.attributes.elasticsearch.index.name` | Index name (index-level metrics) |
| `attributes.state` | Health state (`green`, `yellow`, `red`) |
| `data_stream.dataset` | `elasticsearch.stack_monitoring.otel` |
| `@timestamp` | Observation time |

### Metric families

**Cluster-level**: `elasticsearch.cluster.health`, `elasticsearch.cluster.nodes`, `elasticsearch.cluster.data_nodes`, `elasticsearch.cluster.shards`, `elasticsearch.cluster.pending_tasks`

**Node-level**: `jvm.memory.heap.used`, `jvm.memory.heap.max`, `jvm.memory.heap.utilization`, `jvm.gc.collections.elapsed`, `elasticsearch.node.cache.memory.usage`, `elasticsearch.node.open_files`, `elasticsearch.node.operations.completed`, `elasticsearch.node.thread_pool.tasks.queued`, `elasticsearch.node.documents`, `elasticsearch.node.fs.disk.available`, `elasticsearch.breaker.memory.estimated`

**Index-level**: `elasticsearch.index.documents`, `elasticsearch.index.operations.completed`, `elasticsearch.index.shards.size`, `elasticsearch.index.primary_shards`

## Sampling and performance tuning

The primary knob is `collection_interval` in the `elasticsearch` receiver config:

```yaml
receivers:
  elasticsearch:
    collection_interval: 10s
```

| Interval | Trade-off |
|----------|-----------|
| `5s` | Higher resolution, more ES query load, more ingest volume |
| `10s` | Good default for labs and low-traffic production |
| `30s` | Lower source load, coarser trends, suitable for large clusters |
| `60s` | Minimal footprint, long-lived monitoring without index bloat |

### Batch processor

```yaml
batch:
  send_batch_size: 1024
  send_batch_max_size: 2048
  timeout: 5s
```

Increase `send_batch_size` for large clusters with many indices. Decrease `timeout` for lower latency.

### Memory limits

The collector is capped at 256 MiB request / 512 MiB limit. For clusters with thousands of indices, the receiver holds per-index and per-node state in memory. Raise the memory limit or increase `collection_interval` if the pod OOMKills.

## Multiple clusters

### How cluster identity works

The `elasticsearchreceiver` reads the cluster name from `/_cluster/health` and sets `resource.attributes.elasticsearch.cluster.name` on every document. In this lab the `resource` processor immediately overrides that value with a short display name (`main` or `extra`) so the dashboard cluster control shows clean labels instead of the ECK resource names. All clusters write to the same data stream (`metrics-elasticsearch.stack_monitoring.otel-main`) and the dashboard cluster filter differentiates them by that attribute.

### Lab demo: second cluster with EXTRA_CLUSTER=true

```bash
EXTRA_CLUSTER=true make apikey-agent-up
```

This deploys a second ECK Elasticsearch cluster (`elasticsearch-extra` by default, overridable with `EXTRA_CLUSTER_NAME`) in its own `lab-extra` namespace (overridable with `EXTRA_CLUSTER_NAMESPACE`). It issues a cert-manager `Certificate` with the correct SAN for its in-cluster endpoint, creates a monitoring API key, and updates the metrics scraper and logs DaemonSet ConfigMaps to collect from both clusters. Both clusters appear in the dashboard.

### Pattern A — one collector pod per source cluster

This is the pattern used in this repo. Each source cluster gets its own collector Deployment. Advantages: independent failure domains, independent scaling, simpler per-cluster config.

```
cluster-a scraper ──┐
                    ├──► edot-gateway ──► monitoring ES
cluster-b scraper ──┘
```

**Step 1 — API key per cluster**

On each source cluster, create the monitoring role and API key (or use `deploy_agent_api.sh` which does this automatically):

```bash
# Run on each source cluster
curl -sk -u "elastic:${PASSWORD}" -X PUT "${ES_URL}/_security/role/edot-monitor" \
  -H 'Content-Type: application/json' \
  -d '{"cluster":["monitor","manage_ilm","manage_index_templates"],
       "indices":[{"names":["*"],"privileges":["monitor","read","view_index_metadata"]}]}'

curl -sk -u "elastic:${PASSWORD}" -X POST "${ES_URL}/_security/api_key" \
  -H 'Content-Type: application/json' \
  -d '{"name":"edot-monitor-cluster-b","role_descriptors":{"edot-monitor":{...}}}'
# Save the returned "encoded" value
```

**Step 2 — Kubernetes secret per cluster**

```bash
kubectl -n lab-main create secret generic es-creds-cluster-b \
  --from-literal=api_key="<encoded>" \
  --dry-run=client -o yaml | kubectl apply -f -
```

**Step 3 — Collector Deployment for cluster-b**

Copy `manifests/edot/main-metrics-otel-api.yaml`, adjust the endpoint, secret reference, and `service.name` resource attribute:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: edot-cluster-b-metrics-config
  namespace: lab-main
data:
  config.yaml: |
    receivers:
      elasticsearch:
        collection_interval: 10s
        initial_delay: 1s
        endpoint: https://elasticsearch-cluster-b-es-http.lab-main.svc.cluster.local:9200
        nodes: ["_all"]
        indices: ["_all"]
        tls:
          ca_file: /etc/otel/certs/ca.crt
        auth:
          authenticator: headers_setter

    extensions:
      health_check:
        endpoint: 0.0.0.0:13133
      headers_setter:
        headers:
          - action: insert
            key: Authorization
            value: ApiKey ${env:ES_SOURCE_API_KEY}

    processors:
      memory_limiter:
        check_interval: 1s
        limit_mib: 256
      resource/cluster-b:
        attributes:
          - key: data_stream.type
            value: metrics
            action: upsert
          - key: data_stream.dataset
            value: elasticsearch.stack_monitoring
            action: upsert
          - key: data_stream.namespace
            value: main
            action: upsert
          - key: service.name
            value: elasticsearch-cluster-b   # identifies this cluster in dashboards
            action: upsert
          - key: service.namespace
            value: lab-main
            action: upsert
          - key: orchestrator.cluster.name
            value: edot-lab
            action: upsert
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
      extensions: [health_check, headers_setter]
      pipelines:
        metrics:
          receivers: [elasticsearch]
          processors: [memory_limiter, resource/cluster-b, batch]
          exporters: [otlp_grpc/gateway]
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: edot-cluster-b-metrics
  namespace: lab-main
spec:
  replicas: 1
  selector:
    matchLabels:
      app.kubernetes.io/name: edot-cluster-b-metrics
  template:
    metadata:
      labels:
        app.kubernetes.io/name: edot-cluster-b-metrics
    spec:
      containers:
        - name: edot-cluster-b-metrics
          image: otel/opentelemetry-collector-contrib:0.148.0
          args: ["--config=/etc/otel/config.yaml"]
          env:
            - name: ES_SOURCE_API_KEY
              valueFrom:
                secretKeyRef:
                  name: es-creds-cluster-b   # per-cluster secret
                  key: api_key
          volumeMounts:
            - name: config
              mountPath: /etc/otel/config.yaml
              subPath: config.yaml
            - name: root-ca
              mountPath: /etc/otel/certs
              readOnly: true
          resources:
            requests:
              cpu: 100m
              memory: 256Mi
            limits:
              memory: 512Mi
      volumes:
        - name: config
          configMap:
            name: edot-cluster-b-metrics-config
        - name: root-ca
          secret:
            secretName: edot-root-ca
```

Repeat for each additional cluster. The gateway `ConfigMap` does not change — it only has one exporter writing to the monitoring cluster.

### Pattern B — one collector pod, multiple clusters

Use multiple named receiver and extension instances in a single collector when you want fewer pods and are comfortable with a shared failure domain. This is appropriate for many small clusters or when your orchestration platform discourages many Deployments.

```
┌─────────────────────────────────────────────────────┐
│  edot-multi-metrics pod (namespace: lab-main)       │
│                                                     │
│  elasticsearch/cluster-a ──► headers_setter/a       │
│  elasticsearch/cluster-b ──► headers_setter/b       │
│  elasticsearch/cluster-c ──► headers_setter/c       │
│         │                                           │
│         ▼ OTLP/gRPC :4317                           │
└─────────────────────────────┼───────────────────────┘
                              │
                              ▼
            edot-gateway (namespace: lab-monitoring)
```

OTel Collector supports multiple named instances of the same component type using the `component/name` syntax. Each `headers_setter/<name>` is a separate extension with its own headers list. Each `elasticsearch/<name>` receiver declares `auth.authenticator: headers_setter/<name>` to bind to its own key.

```yaml
# ConfigMap config.yaml for a single pod monitoring three clusters
receivers:
  elasticsearch/cluster-a:
    collection_interval: 10s
    initial_delay: 1s
    endpoint: https://elasticsearch-a-es-http.lab-main.svc.cluster.local:9200
    nodes: ["_all"]
    indices: ["_all"]
    tls:
      ca_file: /etc/otel/certs/ca.crt
    auth:
      authenticator: headers_setter/cluster-a

  elasticsearch/cluster-b:
    collection_interval: 10s
    initial_delay: 1s
    endpoint: https://elasticsearch-b-es-http.lab-main.svc.cluster.local:9200
    nodes: ["_all"]
    indices: ["_all"]
    tls:
      ca_file: /etc/otel/certs/ca.crt
    auth:
      authenticator: headers_setter/cluster-b

  elasticsearch/cluster-c:
    collection_interval: 10s
    initial_delay: 1s
    endpoint: https://elasticsearch-c-es-http.lab-main.svc.cluster.local:9200
    nodes: ["_all"]
    indices: ["_all"]
    tls:
      ca_file: /etc/otel/certs/ca.crt
    auth:
      authenticator: headers_setter/cluster-c

extensions:
  health_check:
    endpoint: 0.0.0.0:13133
  headers_setter/cluster-a:
    headers:
      - action: insert
        key: Authorization
        value: ApiKey ${env:ES_API_KEY_CLUSTER_A}
  headers_setter/cluster-b:
    headers:
      - action: insert
        key: Authorization
        value: ApiKey ${env:ES_API_KEY_CLUSTER_B}
  headers_setter/cluster-c:
    headers:
      - action: insert
        key: Authorization
        value: ApiKey ${env:ES_API_KEY_CLUSTER_C}

processors:
  memory_limiter:
    check_interval: 1s
    limit_mib: 512    # raise proportionally to cluster count
  resource/cluster-a:
    attributes:
      - {key: data_stream.type,      value: metrics,                         action: upsert}
      - {key: data_stream.dataset,   value: elasticsearch.stack_monitoring,  action: upsert}
      - {key: data_stream.namespace, value: main,                            action: upsert}
      - {key: service.name,          value: elasticsearch-cluster-a,         action: upsert}
  resource/cluster-b:
    attributes:
      - {key: data_stream.type,      value: metrics,                         action: upsert}
      - {key: data_stream.dataset,   value: elasticsearch.stack_monitoring,  action: upsert}
      - {key: data_stream.namespace, value: main,                            action: upsert}
      - {key: service.name,          value: elasticsearch-cluster-b,         action: upsert}
  resource/cluster-c:
    attributes:
      - {key: data_stream.type,      value: metrics,                         action: upsert}
      - {key: data_stream.dataset,   value: elasticsearch.stack_monitoring,  action: upsert}
      - {key: data_stream.namespace, value: main,                            action: upsert}
      - {key: service.name,          value: elasticsearch-cluster-c,         action: upsert}
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
  extensions: [health_check, headers_setter/cluster-a, headers_setter/cluster-b, headers_setter/cluster-c]
  pipelines:
    metrics/cluster-a:
      receivers: [elasticsearch/cluster-a]
      processors: [memory_limiter, resource/cluster-a, batch]
      exporters: [otlp_grpc/gateway]
    metrics/cluster-b:
      receivers: [elasticsearch/cluster-b]
      processors: [memory_limiter, resource/cluster-b, batch]
      exporters: [otlp_grpc/gateway]
    metrics/cluster-c:
      receivers: [elasticsearch/cluster-c]
      processors: [memory_limiter, resource/cluster-c, batch]
      exporters: [otlp_grpc/gateway]
```

The Deployment loads one env var per cluster from separate secrets (or a single multi-key secret):

```yaml
env:
  - name: ES_API_KEY_CLUSTER_A
    valueFrom:
      secretKeyRef:
        name: es-creds-cluster-a
        key: api_key
  - name: ES_API_KEY_CLUSTER_B
    valueFrom:
      secretKeyRef:
        name: es-creds-cluster-b
        key: api_key
  - name: ES_API_KEY_CLUSTER_C
    valueFrom:
      secretKeyRef:
        name: es-creds-cluster-c
        key: api_key
```

### Choosing between Pattern A and Pattern B

| Concern | Pattern A (one pod per cluster) | Pattern B (one pod, N clusters) |
|---------|--------------------------------|--------------------------------|
| Failure isolation | One cluster failure doesn't affect others | A crash or OOM stops all scrapers |
| Pod count | One per cluster | One total |
| Memory scaling | Fixed per-cluster limit | Must raise `limit_mib` proportionally |
| Config changes | Edit one file per cluster | Edit one shared file |
| API key rotation | Restart one pod | Restart the shared pod (brief gap for all) |
| Recommended up to | Any scale | ~10 clusters before memory becomes a concern |

### Gateway configuration for multiple clusters

The gateway does not need to change when adding source clusters. It receives OTLP from any number of scrapers and writes everything to the single monitoring cluster. If you need per-cluster routing to different monitoring clusters, use separate gateway instances or a fanout exporter.

### N-cluster checklist

For each additional source cluster:
1. Create the monitoring role on the new cluster.
2. Create an API key scoped to that role and extract the `encoded` field.
3. Store the encoded key in a Kubernetes secret.
4. Deploy a collector (Pattern A: new Deployment; Pattern B: add receiver/extension/pipeline to existing config).
5. No gateway changes needed.

The `resource.attributes.elasticsearch.cluster.name` dimension separates the streams automatically in dashboards.

## Production configuration checklist

**License**

API key authentication is available on all license tiers including basic. No trial license is required.

**TLS**

The receiver and gateway both validate TLS against the ECK root CA (`edot-root-ca` secret). In production, replace with your actual CA bundle. The gateway uses `ca_file` for the monitoring cluster. Do not set `insecure_skip_verify: true` outside dev/test.

**API key rotation**

To rotate either key:
1. Create a new API key on the target cluster.
2. Extract the `encoded` field.
3. Update the Kubernetes secret: `kubectl -n <ns> create secret generic <name> --from-literal=api_key=<encoded> --dry-run=client -o yaml | kubectl apply -f -`
4. Restart the deployment: `kubectl -n <ns> rollout restart deploy/<name>`

There is a brief window between updating the secret and restarting the pod where the old key is still in use. Invalidate the old key only after confirming the pod has restarted with the new one.

**Minimum required privileges**

Source cluster monitoring role:
```json
{"cluster": ["monitor", "manage_ilm", "manage_index_templates"],
 "indices": [{"names": ["*"], "privileges": ["monitor", "read", "view_index_metadata"]}]}
```

Monitoring cluster ingest role:
```json
{"cluster": ["monitor"],
 "indices": [{"names": ["logs-*", "metrics-*"], "privileges": ["auto_configure", "create_doc", "view_index_metadata"]}]}
```

## Switching the Gateway to an OTLP Endpoint

Use an OTLP exporter instead of the `elasticsearch` exporter when the destination is not an Elasticsearch cluster — for example, Grafana Cloud, Datadog, a managed OTLP endpoint, or another OpenTelemetry Collector.

### Replacement exporter block

Replace the `elasticsearch/monitoring` exporter in `manifests/edot/gateway-apikey.yaml` with:

```yaml
exporters:
  otlphttp:
    endpoint: "https://YOUR_OTLP_ENDPOINT:4318"
    headers:
      Authorization: "${env:OTLP_AUTH_HEADER}"
    retry_on_failure:
      enabled: true
      initial_interval: 5s
      max_interval: 60s
      max_elapsed_time: 300s
    sending_queue:
      enabled: true
      num_consumers: 4
      queue_size: 200
```

For gRPC-based OTLP endpoints, use the `otlp` exporter instead of `otlphttp` and change the port to `4317`.

> **Note**: `mapping.mode: otel` is only meaningful on the `elasticsearch` exporter. Remove it when switching to `otlphttp` or `otlp`.

### Required credential changes

Create a new secret with the destination's auth header value (e.g. `ApiKey ...` or `Bearer ...`):
```bash
kubectl -n lab-monitoring create secret generic otlp-credentials \
  --from-literal=auth_header="Bearer YOUR_BEARER_TOKEN" \
  --dry-run=client -o yaml | kubectl apply -f -
```

Update the gateway Deployment env — replace `MONITORING_ES_API_KEY` and `MONITORING_ES_ENDPOINT` with:
```yaml
env:
  - name: OTLP_AUTH_HEADER
    valueFrom:
      secretKeyRef:
        name: otlp-credentials
        key: auth_header
```

### Files to change

- [ ] `manifests/edot/gateway-apikey.yaml` ConfigMap — replace `elasticsearch/monitoring` exporter block with `otlphttp` block; remove `mapping.mode: otel`; update pipeline `exporters` list from `[elasticsearch/monitoring]` to `[otlphttp]`
- [ ] `manifests/edot/gateway-apikey.yaml` Deployment — replace `MONITORING_ES_ENDPOINT` and `MONITORING_ES_API_KEY` env vars with `OTLP_AUTH_HEADER`
- [ ] `manifests/secrets/es-creds-monitoring-cluster.yaml` — replace with `otlp-credentials` secret containing `auth_header`

## Things to watch out for

**headers_setter requires the receiver to support auth.authenticator**

The `elasticsearchreceiver` uses `confighttp.ClientConfig`, which supports `auth.authenticator`. Not all OTEL receivers do. If you switch to a different receiver, verify it supports `confighttp.ClientConfig` before using this pattern.

**API key encoded value vs. id:secret format**

The `encoded` field from `POST /_security/api_key` is `base64(id:api_key)` and is what Elasticsearch expects in the `Authorization: ApiKey` header. The deploy script uses the `encoded` field directly. Do not manually base64-encode — the value from the API is already correct.

**API key expiry**

API keys have no time-based expiry built into the header — expiry is managed server-side in Elasticsearch and only takes effect when the key is explicitly invalidated or its configured expiration is reached.

**Index-level metrics grow with cluster size**

With 10,000 indices, each scrape cycle emits tens of thousands of data points. Increase `collection_interval` to 30–60 seconds and raise the memory limit at large scale.

**dashboard_dataset filter**

Dashboard queries use `data_stream.dataset: "elasticsearch.stack_monitoring*"` (prefix match) to handle the `.otel` suffix appended by the gateway. If you change the `data_stream.dataset` attribute in the `resource/main` processor, rebuild the NDJSON:

```bash
python3 scripts/build_otel_apikey_dashboard_ndjson.py
make import-dashboard EDOT_MONITORING_MODE=agent-api
```
