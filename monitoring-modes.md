# Monitoring Modes

This repository currently supports three deployment commands through `EDOT_MONITORING_MODE`:

```bash
make up EDOT_MONITORING_MODE=autoops
make up EDOT_MONITORING_MODE=agent
make up EDOT_MONITORING_MODE=contrib
```

`contrib` is kept only as a backward-compatible alias. It now resolves to the same Elastic Agent path as `agent`.

## At A Glance

| Mode | Collector path | Metrics destination | Logs destination | Deriver | Recommended use |
|---|---|---|---|---|---|
| `autoops` | EDOT Collector with `autoops_es` | `metrics-elasticsearch.autoops-main` | `logs-elasticsearch.metrics-main` and `logs-elasticsearch.logs.otel-main` | Yes | When you need the raw `autoops_es` payload and curated TSDS dashboards |
| `agent` | Elastic Agent with EDOT runtime and Elasticsearch integration | `metrics-elasticsearch.stack_monitoring.*-main` | `logs-elasticsearch.server-main` | No | Preferred supported path for Elasticsearch monitoring with Elastic Agent |
| `contrib` | Compatibility alias to `agent` | Same as `agent` | Same as `agent` | No | For older scripts or automation that still call `contrib` |

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

Flow:

1. `metricbeatreceiver/elasticsearch` collects `autoops_es`.
2. The raw monitoring payload is emitted as logs.
3. Raw monitoring documents are written to `logs-elasticsearch.metrics-main`.
4. OTEL infrastructure logs are written to `logs-elasticsearch.logs.otel-main`.
5. The deriver reads the raw source stream.
6. The deriver writes curated documents to `metrics-elasticsearch.autoops-main`.
7. Kibana dashboards read the derived TSDS.

Benefits:

- preserves the full raw `autoops_es` payload
- gives a debuggable source stream
- supports richer custom dashboards after derivation

Tradeoffs:

- metrics land as logs first
- requires a second derivation stage
- more custom moving parts to operate

## 2. `agent`

Primary manifests:

- [manifests/edot/main-metrics-agent.yaml](manifests/edot/main-metrics-agent.yaml)
- [manifests/edot/main-logs-agent.yaml](manifests/edot/main-logs-agent.yaml)

Flow:

1. Standalone Elastic Agent starts with local `agent.yml`.
2. The Agent runs the Elasticsearch integration metrics input.
3. The Agent runs the filestream logs input for Elasticsearch server logs.
4. Metrics are written directly to stack-monitoring metrics data streams.
5. Logs are written to `logs-elasticsearch.server-main`.
6. Kibana dashboards read the stack-monitoring metrics streams directly.

Current metrics streams:

- `metrics-elasticsearch.stack_monitoring.cluster_stats-main`
- `metrics-elasticsearch.stack_monitoring.index-main`
- `metrics-elasticsearch.stack_monitoring.index_recovery-main`
- `metrics-elasticsearch.stack_monitoring.index_summary-main`
- `metrics-elasticsearch.stack_monitoring.node-main`
- `metrics-elasticsearch.stack_monitoring.node_stats-main`
- `metrics-elasticsearch.stack_monitoring.shard-main`

Current log stream:

- `logs-elasticsearch.server-main`

Benefits:

- closest to the supported Elastic operating model
- no custom deriver required
- direct stack-monitoring data streams
- simpler runtime and easier lifecycle management

Tradeoffs:

- does not preserve the raw `autoops_es` payload
- uses integration-shaped ECS/Beat fields instead of the custom derived schema

## 3. `contrib`

Deploy:

```bash
make up EDOT_MONITORING_MODE=contrib
```

Current behavior:

- this no longer deploys the old upstream `elasticsearchreceiver` path
- it resolves to the same runtime behavior as `EDOT_MONITORING_MODE=agent`
- it exists only so older automation and shell history do not break

Benefits:

- safe compatibility switch for older commands
- lets existing callers migrate incrementally

Tradeoffs:

- not a distinct implementation anymore
- should be treated as transitional, not primary

## Kubernetes Manifest Distinctions

### `autoops` manifest characteristics

The `autoops` path is collector-centric and split across metrics, logs, gateway, and derivation manifests.

Key configuration distinctions:

- [manifests/edot/main-metrics.yaml](manifests/edot/main-metrics.yaml)
  - uses `metricbeatreceiver/elasticsearch`
  - collects `autoops_es`
  - does not write directly to final dashboard metrics streams
- [manifests/edot/gateway.yaml](manifests/edot/gateway.yaml)
  - central export point to the monitoring cluster
  - keeps the OTEL/collector routing layer
- [manifests/edot/autoops-tsds-deriver.yaml](manifests/edot/autoops-tsds-deriver.yaml)
  - adds a second processing stage
  - reads `logs-elasticsearch.metrics-main`
  - writes `metrics-elasticsearch.autoops-main`

Operationally, `autoops` is a source-preserving design with explicit transformation after ingest.

### `agent` manifest characteristics

The `agent` path is integration-centric and uses standalone Elastic Agent manifests.

Key configuration distinctions:

- [manifests/edot/main-metrics-agent.yaml](manifests/edot/main-metrics-agent.yaml)
  - container image: Elastic Agent
  - config source: embedded `agent.yml` in a ConfigMap
  - input type: `elasticsearch/metrics`
  - output: monitoring Elasticsearch directly
  - readiness/liveness: Agent HTTP monitoring endpoint
- [manifests/edot/main-logs-agent.yaml](manifests/edot/main-logs-agent.yaml)
  - input type: `filestream`
  - tails Elasticsearch server logs from Kubernetes nodes
  - outputs directly to monitoring Elasticsearch
- no deriver manifest is used
- no monitoring-side gateway deployment is required for the final stack-monitoring path

Operationally, `agent` is a direct-write design with fewer runtime layers.

### Configuration summary

| Area | `autoops` | `agent` |
|---|---|---|
| Runtime shape | EDOT Collector + gateway + deriver | Elastic Agent + EDOT runtime |
| Metrics source | `autoops_es` | Elasticsearch integration |
| Metrics first land in | `logs-*` | `metrics-*` |
| Extra transformation | required | not required |
| Logs path | OTEL collector logs flow | filestream integration flow |
| Dashboard source | derived TSDS | direct stack-monitoring metrics streams |

## Verification Commands

```bash
make test EDOT_MONITORING_MODE=autoops
make test EDOT_MONITORING_MODE=agent
make test EDOT_MONITORING_MODE=contrib
```

Synthetic workload control:

```bash
make search-load-up
make search-load-down
```

## Credentials And Permissions

The deployment uses Kubernetes Secrets. Credentials are not hardcoded into the manifests.

Important permissions:

- source-cluster collector user:
  - `remote_monitoring_collector`
- monitoring-cluster ingest user:
  - write privileges for the destination monitoring data streams

## Migration Guidance

If you are moving from older usage:

- old `contrib` command:
  - now maps to `agent`
- old `autoops` usage:
  - still works and remains useful when the raw `autoops_es` source stream is required
- preferred new command:
  - `make up EDOT_MONITORING_MODE=agent`
