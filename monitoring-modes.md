# Monitoring Modes

This repository exposes three deployment commands through `EDOT_MONITORING_MODE`:

```bash
make up EDOT_MONITORING_MODE=autoops
make up EDOT_MONITORING_MODE=agent
make up EDOT_MONITORING_MODE=contrib
```

`contrib` is still accepted, but it now resolves to the same runtime behavior as `agent`.

## At A Glance

| Mode | Runtime shape | Metrics landing point | Logs landing point | Extra transform | Best fit |
|---|---|---|---|---|---|
| `autoops` | EDOT Collector + gateway + deriver | `metrics-elasticsearch.autoops-main` | `logs-elasticsearch.metrics-main` and `logs-elasticsearch.logs.otel-main` | Yes | Preserve raw `autoops_es` and derive a curated TSDS |
| `agent` | Elastic Agent with EDOT runtime | `metrics-elasticsearch.stack_monitoring.*-main` | `logs-elasticsearch.server-main` | No | Direct Elastic-supported stack-monitoring path |
| `contrib` | Compatibility alias to `agent` | same as `agent` | same as `agent` | No | Older automation still using `contrib` |

## Deploy Commands

```bash
make up EDOT_MONITORING_MODE=autoops
make up EDOT_MONITORING_MODE=agent
make up EDOT_MONITORING_MODE=contrib
```

Validate the selected mode:

```bash
make test EDOT_MONITORING_MODE=autoops
make test EDOT_MONITORING_MODE=agent
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

Notable impact:

- this is a bigger design change than in `autoops`
- the current stack-monitoring data stream names will disappear unless another downstream system reproduces them
- the Kibana dashboards in this repo assume Elasticsearch remains the destination system

## 3. `contrib`

Deploy:

```bash
make up EDOT_MONITORING_MODE=contrib
```

### Current behavior

- This no longer deploys the old upstream `elasticsearchreceiver` path.
- It resolves to the same runtime behavior as `EDOT_MONITORING_MODE=agent`.
- It exists only so older automation and shell history do not break.

### Practical distinction

There is no manifest distinction anymore.

`contrib` now means:

```text
contrib -> agent
```

### To ship to another OTEL endpoint

Use the same considerations as `agent`, because the runtime path is the same.

## Configuration Summary

| Area | `autoops` | `agent` |
|---|---|---|
| Runtime shape | EDOT Collector + gateway + deriver | Elastic Agent + EDOT runtime |
| Primary config object | collector `config.yaml` | Agent `agent.yml` |
| Metrics source | `autoops_es` | Elasticsearch integration |
| First landing format | logs-shaped source docs | stack-monitoring metrics streams |
| Gateway required | yes | no |
| Deriver required | yes | no |
| External OTEL forwarding effort | lower | higher |

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
  - same changes as `agent`
