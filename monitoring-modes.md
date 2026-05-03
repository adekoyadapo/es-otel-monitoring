# Monitoring Modes

This repository exposes three deployment commands through `EDOT_MONITORING_MODE`:

```bash
make up EDOT_MONITORING_MODE=autoops
make up EDOT_MONITORING_MODE=agent
make up EDOT_MONITORING_MODE=agent-jwt
make up EDOT_MONITORING_MODE=contrib
```

All four modes are supported and deploy different collection paths.

## At A Glance

| Mode | Runtime shape | Metrics landing point | Logs landing point | Extra transform | Best fit |
|---|---|---|---|---|---|
| `autoops` | EDOT Collector + gateway + deriver | `metrics-elasticsearch.autoops-main` | `logs-elasticsearch.metrics-main` and `logs-elasticsearch.logs.otel-main` | Yes | Preserve raw `autoops_es` and derive a curated TSDS |
| `agent` | Elastic Agent with EDOT runtime | `metrics-elasticsearch.stack_monitoring.*-main` | `logs-elasticsearch.server-main` | No | Direct Elastic-supported stack-monitoring path |
| `agent-jwt` | JWT-authenticated Elastic Agent EDOT runtime + gateway | `metrics-elasticsearch.stack_monitoring.otel-main` | `logs-elasticsearch.logs.otel-main` | No | Validate JWT auth and ship native OTLP metrics/logs through EDOT gateway without clashing with the standard Agent path |
| `contrib` | Collector Contrib receiver + gateway | `metrics-elasticsearch.stack_monitoring.otel-main` | `logs-elasticsearch.logs.otel-main` | No | Upstream Elasticsearch receiver path for comparison and direct stack-monitoring-style output |

## Deploy Commands

```bash
make up EDOT_MONITORING_MODE=autoops
make up EDOT_MONITORING_MODE=agent
make up EDOT_MONITORING_MODE=agent-jwt
make up EDOT_MONITORING_MODE=contrib
```

Validate the selected mode:

```bash
make test EDOT_MONITORING_MODE=autoops
make test EDOT_MONITORING_MODE=agent
make test EDOT_MONITORING_MODE=agent-jwt
make test EDOT_MONITORING_MODE=contrib
```

## 1. `autoops`

Primary manifests:

- [manifests/edot/main-metrics.yaml](manifests/edot/main-metrics.yaml)
- [manifests/edot/main-logs.yaml](manifests/edot/main-logs.yaml)
- [manifests/edot/gateway.yaml](manifests/edot/gateway.yaml)
- [manifests/edot/autoops-tsds-deriver.yaml](manifests/edot/autoops-tsds-deriver.yaml)

### Runtime flow

1. `metricbeatreceiver/elasticsearch` collects `autoops_es`.
2. The runtime emits that payload as logs, not native metrics.
3. The source payload lands in `logs-elasticsearch.metrics-main`.
4. The deriver reads the raw source stream.
5. The deriver writes curated documents into `metrics-elasticsearch.autoops-main`.
6. Dashboards read the derived TSDS.

### Key Kubernetes config

The mode is defined by the receiver type and by the fact that it intentionally runs a `logs` pipeline:

```yaml
receivers:
  metricbeatreceiver/elasticsearch:
    metricbeat:
      modules:
        - module: autoops_es
          period: 10s
          metricsets:
            - cat_shards
            - node_stats
            - tasks_management
    telemetry_types: ["logs"]

service:
  pipelines:
    logs:
      receivers: [metricbeatreceiver/elasticsearch]
      exporters: [otlp_grpc/gateway]
```

That handoff is why the monitoring path also needs the gateway:

```yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317

exporters:
  elasticsearch/monitoring:
    endpoints:
      - ${env:MONITORING_ELASTICSEARCH_URL}
    mapping:
      mode: otel

service:
  pipelines:
    logs:
      receivers: [otlp]
      exporters: [elasticsearch/monitoring]
    metrics:
      receivers: [otlp]
      exporters: [elasticsearch/monitoring]
```

The last distinguishing component is the deriver:

```yaml
# autoops deriver conceptually:
# source stream -> curated TSDS
logs-elasticsearch.metrics-main
  -> transform selected fields
  -> metrics-elasticsearch.autoops-main
```

### Why use it

- Preserves the raw `autoops_es` payload.
- Keeps a source stream available for debugging and field discovery.
- Lets the dashboard read a curated TSDS instead of the raw logs-shaped payload.

### To ship to another OTEL endpoint

This mode is already OTLP-shaped internally, so it is the easier one to redirect toward another OTEL collector or gateway.

The main changes are:

1. change the exporter in [manifests/edot/main-metrics.yaml](manifests/edot/main-metrics.yaml)
2. optionally replace or remove the monitoring-side [manifests/edot/gateway.yaml](manifests/edot/gateway.yaml)
3. decide whether the deriver still runs against Elasticsearch or whether derivation moves downstream

Typical change:

```yaml
exporters:
  otlp_grpc/external:
    endpoint: other-otel-gateway.example:4317
    tls:
      insecure: false

service:
  pipelines:
    logs:
      exporters: [otlp_grpc/external]
```

Notable impact:

- if Elasticsearch is no longer the first landing point, the current deriver path will need to be redesigned
- the current dashboards will not work until a replacement metrics store or Elasticsearch landing path exists

## 2. `agent`

Primary manifests:

- [manifests/edot/main-metrics-agent.yaml](manifests/edot/main-metrics-agent.yaml)
- [manifests/edot/main-logs-agent.yaml](manifests/edot/main-logs-agent.yaml)

### Runtime flow

1. Standalone Elastic Agent starts with local `agent.yml`.
2. The Agent runs the Elasticsearch integration metrics input.
3. The Agent runs the filestream logs input for Elasticsearch server logs.
4. Metrics are written directly into stack-monitoring metrics data streams.
5. Logs are written into `logs-elasticsearch.server-main`.
6. Dashboards read the stack-monitoring metrics streams directly.

### Key Kubernetes config

The most important distinction is that this mode is integration-driven, not raw collector-pipeline driven.

Metrics config:

```yaml
outputs:
  default:
    type: elasticsearch
    hosts:
      - ${MONITORING_ELASTICSEARCH_URL}

inputs:
  - id: elasticsearch-stack-monitoring
    type: elasticsearch/metrics
    use_output: default
    data_stream.namespace: main
    streams:
      - metricsets: ["cluster_stats"]
        data_stream.dataset: elasticsearch.stack_monitoring.cluster_stats
      - metricsets: ["index"]
        data_stream.dataset: elasticsearch.stack_monitoring.index
      - metricsets: ["node_stats"]
        data_stream.dataset: elasticsearch.stack_monitoring.node_stats
      - metricsets: ["shard"]
        data_stream.dataset: elasticsearch.stack_monitoring.shard
```

Logs config:

```yaml
outputs:
  default:
    type: elasticsearch
    hosts:
      - ${MONITORING_ELASTICSEARCH_URL}

inputs:
  - id: elasticsearch-server-logs
    type: filestream
    use_output: default
    data_stream.namespace: main
    streams:
      - id: elasticsearch-server-stream
        data_stream.dataset: elasticsearch.server
        paths:
          - /var/log/containers/*_lab-main_elasticsearch-*.log
        parsers:
          - container: ~
```

This path writes directly to Elasticsearch. There is no monitoring-side OTLP gateway and no deriver stage in the steady-state path.

### Why use it

- Closest to the supported Elastic operating model.
- Direct stack-monitoring metrics streams.
- Fewer moving parts than `autoops`.
- Simpler dashboard data source design.

### To ship to another OTEL endpoint

This mode is less natural to redirect to a generic OTEL endpoint because it is currently defined around Elastic Agent integration outputs that write straight to Elasticsearch.

To push elsewhere, the main changes are:

1. replace the `outputs.default` block in the Agent config
2. choose whether Elastic Agent should still own collection or whether collection should move back to a collector/gateway path
3. redesign dashboards if Elasticsearch is no longer the first landing point

The desired shape would be conceptually:

```yaml
outputs:
  default:
    type: otlp
    hosts:
      - other-otel-gateway.example:4317
```

## 3. `agent-jwt`

Primary manifests:

- [manifests/elastic/eck-trial-license.yaml](manifests/elastic/eck-trial-license.yaml)
- [manifests/jwt/elasticsearch-main-jwt.yaml](manifests/jwt/elasticsearch-main-jwt.yaml)
- [manifests/edot/main-metrics-otel-jwt.yaml](manifests/edot/main-metrics-otel-jwt.yaml)
- [manifests/edot/main-logs-otel-jwt.yaml](manifests/edot/main-logs-otel-jwt.yaml)
- [manifests/edot/gateway.yaml](manifests/edot/gateway.yaml)

### Runtime flow

1. The ECK trial-license secret is applied before the clusters are created, so fresh installs can enable JWT realms.
2. The JWT realm overlay is applied to the source Elasticsearch cluster.
3. The JWT metrics pod runs a local auth proxy sidecar that injects the JWT bearer token and `ES-Client-Authentication` header.
4. A local exporter sidecar queries Elasticsearch through that proxy and emits native OTLP metrics to the local EDOT collector on `127.0.0.1:4318`.
5. The Elastic Agent EDOT runtime receives those OTLP points and forwards them to `edot-gateway`.
6. The JWT logs collector tails Elasticsearch server logs.
7. Both collectors ship through `edot-gateway`.
8. Dashboards read the OTLP metrics stream and the logs stream directly.

### Key Kubernetes config

The JWT workflow is intentionally isolated from the standard Agent workflow.
It uses the ECK trial-license secret, the JWT realm overlay, collectors, a local
auth proxy, and dedicated data streams.
JWT auth itself still requires a trial or commercial license on the source
cluster; otherwise the exporter will see 401s even if the overlay is present.

JWT realm overlay:

```yaml
secureSettings:
  - secretName: elasticsearch-main-jwt-secure-settings

nodeSets:
  - name: default
    config:
      xpack.security.authc.realms.jwt.jwt1.order: 3
      xpack.security.authc.realms.jwt.jwt1.client_authentication.type: shared_secret
      xpack.security.authc.realms.jwt.jwt1.allowed_issuer: edot-jwt-test
      xpack.security.authc.realms.jwt.jwt1.allowed_audiences: [ "edot-jwt-test" ]
      xpack.security.authc.realms.jwt.jwt1.allowed_signature_algorithms: [HS256]
```

JWT metrics exporter and collector:

```yaml
containers:
  - name: jwt-metrics-exporter
    command:
      - /bin/sh
      - -ec
      - |
        python3 -m pip install --no-cache-dir opentelemetry-sdk opentelemetry-exporter-otlp-proto-http
        exec python3 /opt/jwt-exporter/exporter.py

receivers:
  otlp:
    protocols:
      http:
        endpoint: 127.0.0.1:4318

service:
  pipelines:
    metrics:
      receivers: [otlp]
      exporters: [otlp_grpc/gateway]
```

The exporter sidecar is responsible for the JWT-authenticated requests and for
translating the source Elasticsearch responses into native OTLP metric points.
The collector only receives those points and forwards them through OTLP.

JWT logs collector:

```yaml
receivers:
  filelog/elasticsearch:
    include:
      - /var/log/containers/*_lab-main_elasticsearch-*.log

service:
  pipelines:
    logs:
      receivers: [filelog/elasticsearch]
      exporters: [otlp_grpc/gateway]
```

### Why use it

- Validates JWT realm auth end to end.
- Keeps the JWT path isolated from the normal Agent collectors.
- Produces native OTLP metrics instead of logs-shaped monitoring records.
- Ships to the EDOT gateway first, so the monitoring cluster stays the final landing point.

### To ship to another OTEL endpoint

This mode is already gateway-shaped, so the main changes are:

1. change the OTLP exporter endpoint in the JWT collector manifests
2. keep the JWT realm, token-minting, and exporter sidecar pieces unchanged
3. if the downstream endpoint is not Elasticsearch, replace the dashboard data streams and any field filters

The recommended change is straightforward:

```yaml
exporters:
  otlp_grpc/external:
    endpoint: other-gateway.example:4317
```

Notable impact:

- this is a bigger design change than in `autoops`
- the current stack-monitoring data stream names will disappear unless another downstream system reproduces them
- the Kibana dashboards in this repo assume Elasticsearch remains the destination system

## 3. `contrib`

Primary manifests:

- [manifests/edot/main-metrics-contrib.yaml](manifests/edot/main-metrics-contrib.yaml)
- [manifests/edot/main-logs.yaml](manifests/edot/main-logs.yaml)
- [manifests/edot/gateway.yaml](manifests/edot/gateway.yaml)

### Runtime flow

1. The upstream OpenTelemetry Collector Contrib receiver scrapes Elasticsearch directly.
2. Metrics are emitted through the EDOT collector pipeline.
3. The monitoring gateway receives OTLP and writes to the monitoring cluster.
4. Metrics land in `metrics-elasticsearch.stack_monitoring.otel-main`.
5. Logs still land in `logs-elasticsearch.logs.otel-main`.
6. Dashboards read the contrib-specific metrics stream directly.

### Key Kubernetes config

The manifest distinction is the receiver and output shape:

```yaml
receivers:
  elasticsearch:
    collection_interval: 10s
    endpoint: ${env:MAIN_ELASTICSEARCH_URL}
    username: ${env:MAIN_ELASTICSEARCH_USERNAME}
    password: ${env:MAIN_ELASTICSEARCH_PASSWORD}
    nodes: ["_all"]
    indices: ["_all"]

service:
  pipelines:
    metrics:
      receivers: [elasticsearch]
      processors: [memory_limiter, resource/route, batch]
      exporters: [otlp_grpc/gateway]
```

The contrib path still uses the shared monitoring gateway:

```yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317

exporters:
  elasticsearch/monitoring:
    endpoints:
      - ${env:MONITORING_ELASTICSEARCH_URL}
    mapping:
      mode: otel

service:
  pipelines:
    logs:
      receivers: [otlp]
      exporters: [elasticsearch/monitoring]
    metrics:
      receivers: [otlp]
      exporters: [elasticsearch/monitoring]
```

### Why use it

- Restores the historical contrib-based collection path.
- Keeps an alternative collector implementation in the lab for comparison.
- Produces a direct stack-monitoring-style metrics stream without the `autoops` derivation layer.

### To ship to another OTEL endpoint

This mode is OTLP-forwarding already, so the main change is the gateway exporter:

1. change the exporter in [manifests/edot/main-metrics-contrib.yaml](manifests/edot/main-metrics-contrib.yaml)
2. optionally replace or remove the monitoring-side [manifests/edot/gateway.yaml](manifests/edot/gateway.yaml)
3. keep the dashboard and stream naming in sync with the downstream endpoint

Typical change:

```yaml
exporters:
  otlp_grpc/external:
    endpoint: other-otel-gateway.example:4317
    tls:
      insecure: false

service:
  pipelines:
    metrics:
      exporters: [otlp_grpc/external]
```

## Configuration Summary

| Area | `autoops` | `agent` | `contrib` |
|---|---|---|---|
| Runtime shape | EDOT Collector + gateway + deriver | Elastic Agent + EDOT runtime | Collector Contrib receiver + gateway |
| Primary config object | collector `config.yaml` | Agent `agent.yml` | collector `config.yaml` |
| Metrics source | `autoops_es` | Elasticsearch integration | upstream Elasticsearch receiver |
| First landing format | logs-shaped source docs | stack-monitoring metrics streams | native OTLP metrics via local exporter and gateway |
| Gateway required | yes | no | yes |
| Deriver required | yes | no | no |
| External OTEL forwarding effort | lower | higher | lower |

## Notable Changes When Switching Destination

If the target is no longer the monitoring Elasticsearch cluster:

- `autoops`
  - easiest place to change is the collector exporter
  - gateway can be replaced with another OTLP destination
  - deriver must be reconsidered if Elasticsearch is no longer first landing point
- `agent`
  - output block must be redesigned
  - current stack-monitoring stream contract will not hold automatically
  - dashboards will need a replacement storage/query path
- `contrib`
  - gateway exporter is the first change point
  - the collector receiver remains the upstream Elasticsearch receiver path
  - dashboards will need the contrib metrics stream or a replacement sink
