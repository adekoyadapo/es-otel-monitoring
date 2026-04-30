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

## 1. `autoops`

Deploy:

```bash
make up EDOT_MONITORING_MODE=autoops
```

Flow:

1. `metricbeatreceiver/elasticsearch` collects `autoops_es`.
2. The raw monitoring payload is shipped into `logs-elasticsearch.metrics-main`.
3. The OTEL logs stream is shipped into `logs-elasticsearch.logs.otel-main`.
4. The deriver reads the raw monitoring stream.
5. The deriver writes curated documents into `metrics-elasticsearch.autoops-main`.
6. Kibana dashboards read the derived TSDS.

Key characteristics:

- Preserves the raw `autoops_es` source payload.
- Uses a derived TSDS for dashboard-friendly fields.
- Best when field discovery and raw payload inspection matter.
- Requires the extra deriver component.

Benefits:

- Full raw source retained for debugging and validation.
- Curated dashboard stream tuned for the existing OTEL dashboards.
- Works around the fact that `autoops_es` lands as logs first.

Tradeoffs:

- More moving parts.
- Metrics are not direct Elastic Agent stack-monitoring streams.
- Requires maintaining source and derived flows together.

## 2. `agent`

Deploy:

```bash
make up EDOT_MONITORING_MODE=agent
```

Flow:

1. Standalone Elastic Agent starts with local `agent.yml`.
2. The Agent runs the Elasticsearch integration metrics input.
3. The Agent runs the filestream logs input for Elasticsearch server logs.
4. Metrics are written directly into stack-monitoring metrics data streams.
5. Logs are written into `logs-elasticsearch.server-main`.
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

Key characteristics:

- Preferred Elastic-supported path in this repo.
- Uses Elastic Agent with embedded EDOT runtime.
- No custom deriver is required.
- Produces Beat/ECS-shaped stack-monitoring documents.

Benefits:

- Closest to the supported Elastic Agent operating model.
- Direct stack-monitoring data streams.
- Simpler deployment and fewer custom components.
- Clearer operational model for metrics and logs shipping.

Tradeoffs:

- Does not preserve the raw `autoops_es` payload.
- Field shape follows Elastic Agent / integration output, not the old derived TSDS schema.
- Historical `contrib` data streams may still exist on reused labs until cleaned up manually.

## 3. `contrib`

Deploy:

```bash
make up EDOT_MONITORING_MODE=contrib
```

What it does now:

- This no longer deploys the old upstream `elasticsearchreceiver` path.
- It resolves to the same runtime behavior as `EDOT_MONITORING_MODE=agent`.
- It exists only so existing automation or shell history does not break.

Benefits:

- Safe compatibility switch for older commands.
- Lets existing callers migrate without immediate script changes.

Tradeoffs:

- Not a distinct implementation anymore.
- Should be treated as transitional, not primary.

## What Differentiates Them

### Source model

- `autoops` collects raw `autoops_es` payloads first.
- `agent` collects supported Elasticsearch integration metrics directly.
- `contrib` is only an alias to `agent`.

### Storage model

- `autoops` writes raw logs-shaped monitoring events, then derives a TSDS.
- `agent` writes metrics directly into stack-monitoring metrics data streams.
- `contrib` uses the same storage model as `agent`.

### Operational complexity

- `autoops` is more flexible but has an extra derivation layer.
- `agent` is simpler and more support-aligned.
- `contrib` adds no extra runtime behavior.

### Best fit

- Use `autoops` when you need the raw payload and the derived OTEL dashboards.
- Use `agent` when you want the supported Elastic Agent monitoring path.
- Use `contrib` only when preserving backward compatibility for existing commands.

## Verification Commands

Validate the selected mode after deployment:

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
