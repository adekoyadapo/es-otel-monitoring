# es-otel-monitoring

This repository provisions a local `k3d` lab with two Elasticsearch clusters managed by ECK and connected through EDOT.

The resulting environment is:

- a main Elasticsearch and Kibana stack in `lab-main`
- a dedicated monitoring Elasticsearch and Kibana stack in `lab-monitoring`
- a monitoring Elasticsearch cluster sized to `2` nodes
- HTTPS ingress endpoints via `sslip.io`
- cert-manager managed TLS certificates
- EDOT collectors that ship main-cluster metrics and logs into the monitoring cluster
- a derived TSDS metrics stream for dashboards and time-series storage
- a synthetic search workload that writes and searches across five `logsdb` data streams in the main cluster

This repo is intentionally narrow in scope. It only contains the manifests, scripts, and docs needed for this local EDOT monitoring lab.

## Repository Layout

- `manifests/elastic`
  - ECK operator manifests and the main and monitoring Elasticsearch/Kibana resources
- `manifests/edot`
  - EDOT gateway, Elasticsearch metrics collector, Elasticsearch logs collector, derived TSDS CronJob, and synthetic search-load deployment
- `dashboards`
  - the generated OTEL monitoring dashboard NDJSON imported into the monitoring Kibana on supported stack versions
- `manifests/ingress`
  - Ingress resources for both Elasticsearch and Kibana endpoints
- `manifests/cert-manager`
  - Local issuers and certificates used by the ingresses
- `scripts`
  - Cluster lifecycle, deployment, readiness, verification, TSDS asset install, derivation, and synthetic workload scripts
- `Makefile`
  - Main entrypoint for spin-up, verification, inspection, and teardown

## Topology

- `lab-main`
  - `elasticsearch-main`
  - `kibana-main`
  - `edot-main-metrics`
  - `edot-main-logs`
  - `main-search-load`
- `lab-monitoring`
  - `elasticsearch-monitoring`
  - `kibana-monitoring`
  - `edot-gateway`

Data flow:

- the main cluster exposes HTTPS ingress and internal services
- the EDOT metrics collector polls Elasticsearch monitoring endpoints in `lab-main`
- the EDOT logs collector tails Elasticsearch pod logs from nodes in the local cluster
- the synthetic workload continuously indexes and searches data in five `logsdb` data streams on the main cluster
- both collectors send their output through the EDOT gateway in `lab-monitoring`
- the EDOT gateway writes the resulting documents into the monitoring Elasticsearch cluster
- the source monitoring metrics land in `logs-elasticsearch.metrics-main`
- a CronJob derives a curated metrics TSDS from that source into `metrics-elasticsearch.autoops-main`

## What EDOT Ships

- EDOT monitoring documents from the main cluster using the bundled EDOT Elasticsearch monitoring module
- Elasticsearch container logs from the main cluster via a DaemonSet file log collector

The monitoring cluster receives:

- `logs-elasticsearch.metrics-main`
- `logs-elasticsearch.logs.otel-main`
- `metrics-elasticsearch.autoops-main`

The important detail is that the bundled `metricbeatreceiver/elasticsearch` in the current EDOT image still emits this monitoring payload as log records. To keep the source path stable while still getting a metrics TSDS for dashboards, this repo derives a second stream from the stable source data stream.

The synthetic workload exists so the OTEL dashboard sees ongoing indexing and search activity shortly after `make up`, without waiting for manual traffic generation.

## Dashboard Assets

- `stack-mon.ndjson`
  - legacy baseline dashboard export kept intact for comparison and reuse
- `dashboards/elasticsearch-otel-monitoring-main.ndjson`
  - generated OTEL-focused dashboard export for this lab, built around the derived TSDS `metrics-elasticsearch.autoops-main`
  - imports three linked dashboards: overview, nodes, and indices
- `dashboards/elasticsearch-otel-monitoring-main.export.json`
  - structured JSON wrapper for the same dashboard objects, useful for review and source control, but not directly importable through the Kibana Saved Objects UI
- `presentation/otel-monitoring-presentation.html`
  - standalone HTML presentation that explains the OTEL architecture, metric flow, dashboards, and operational checks with animated slide-style navigation
- `scripts/build_otel_dashboard_ndjson.py`
  - rebuilds both the importable NDJSON and the structured JSON wrapper
- `scripts/convert_saved_objects_export_json.py`
  - converts the structured dashboard `export.json` wrapper back into importable NDJSON for Kibana
- `scripts/import_monitoring_dashboard.sh`
  - imports the OTEL dashboard into the monitoring Kibana when the selected stack version supports it
- `scripts/derive_autoops_tsds.py`
  - reads recent documents from `logs-elasticsearch.metrics-main`, emits a curated subset into `metrics-elasticsearch.autoops-main`, and relies on TSDS overwrite semantics for overlapping reruns
- `scripts/install_autoops_tsds_assets.sh`
  - installs the custom TSDS component template and index template for the derived stream
- `scripts/generate_search_load.py`
  - writes synthetic documents into `logs-sampleapp-01-default` through `logs-sampleapp-05-default` and searches them continuously
- `scripts/deploy_search_load.sh`
  - creates or updates the synthetic workload using the current `SEARCH_LOAD_*` overrides
- `scripts/stop_search_load.sh`
  - stops the synthetic workload without deleting the generated data streams
- `scripts/reset_search_load_data.sh`
  - deletes the synthetic workload data streams and logsdb template so a new shard layout can be applied cleanly
- `manifests/edot/autoops-tsds-deriver.yaml`
  - CronJob that keeps the derived TSDS current inside the monitoring cluster
- `manifests/edot/main-search-load.yaml`
  - Deployment that runs the synthetic `logsdb` search/write workload in `lab-main`

The OTEL dashboard import is enabled for stack versions `>= 9.3.0`. On lower versions, deployment skips the dashboard import cleanly and `make test` reports that skip instead of failing.

Kibana Saved Objects import accepts `ndjson` files. The structured `export.json` wrapper in this repo is for storage and inspection, and must be converted back to `ndjson` before importing through the Kibana UI or Saved Objects API.
The Kibana ingress manifests set `nginx.ingress.kubernetes.io/proxy-body-size: "50m"` so larger Saved Objects imports continue to work after `make up`.

The OTEL dashboard is intentionally split into focused views instead of one oversized page:
- `Elasticsearch OTEL monitoring for metrics-elasticsearch.autoops-main`
  - cluster overview and health
- `Elasticsearch OTEL monitoring - Nodes`
  - JVM, caches, file descriptors, and node-level pressure
- `Elasticsearch OTEL monitoring - Indices`
  - shard, docs, and storage inventory

Each dashboard keeps the same top control bar for cluster and node filtering, and a shared links panel for navigation between views. This keeps the saved objects importable on the target Kibana version without relying on undocumented collapsible-section saved object structure.

## Dashboard Views

Overview:

![Overview dashboard](images/dashboard-overview.png)

Nodes:

![Nodes dashboard](images/dashboard-nodes.png)

Indices:

![Indices dashboard](images/dashboard-indices.png)

The dashboard is split this way on purpose:

- the overview page stays usable at a glance instead of turning into one oversized scrolling canvas
- the nodes page groups JVM, cache, file descriptor, and pressure metrics together
- the indices page groups shard inventory, docs, storage, and per-index rate metrics together
- the same top controls are available on every page, so the operator can filter by cluster, cluster ID, or node without losing context

## OTEL Data Path

This lab uses two different representations of Elasticsearch monitoring data:

1. the raw EDOT source stream
   - `logs-elasticsearch.metrics-main`
   - produced directly by `metricbeatreceiver/elasticsearch`
2. the derived metrics stream used for dashboards
   - `metrics-elasticsearch.autoops-main`
   - produced by the TSDS derivation job in the monitoring cluster

This split exists because the current EDOT runtime for this lab does not emit the `autoops_es` payload as native OTel metrics. The runtime emits log records for this receiver, so the source stream lands under `logs-*` even though the payload contains metric values.

The repo keeps that source path stable and derives a second stream that is safe to use as metrics storage and dashboard backing:

- the source stream preserves the full raw monitoring payload that EDOT produced
- the derived stream keeps the curated fields needed for dashboards and stores them in a TSDS-compatible `metrics-*` data stream
- the dashboard points at the derived TSDS rather than the raw source stream

## How Metrics Are Generated

The metrics pipeline in this lab is a two-stage process.

Stage 1 is collection from the main cluster:

- the `edot-main-metrics` collector in `lab-main` uses `metricbeatreceiver/elasticsearch`
- it runs the bundled `autoops_es` module against the main cluster over HTTPS
- the receiver polls these metricsets every `10s`:
  - `cat_shards`
  - `node_stats`
  - `tasks_management`
- it polls these metricsets every `1m`:
  - `cluster_health`
  - `cluster_settings`
- the collector tags the output with:
  - `data_stream.dataset=elasticsearch.metrics`
  - `data_stream.namespace=main`
  - `service.name=elasticsearch-main`
  - `service.namespace=lab-main`

Even though the payload contains metrics, this receiver emits them as log records in the current runtime, so the collector sends them through a `logs` pipeline and the monitoring cluster stores them in:

- `logs-elasticsearch.metrics-main`

Stage 2 is derivation into a metrics TSDS:

- the `edot-autoops-tsds-deriver` job reads recent documents from `logs-elasticsearch.metrics-main`
- it keeps a rolling lookback window and rewrites only the curated parts of the payload needed for dashboards
- it writes the resulting documents into:
  - `metrics-elasticsearch.autoops-main`

The derivation script builds different document shapes from the raw `autoops_es` payload:

- cluster health documents from `autoops_es.cluster_health`
- node statistics documents from `autoops_es.node_stats`
- shard summary and per-index documents from `autoops_es.cat_shards`

The main field families promoted into the derived TSDS are:

- cluster health:
  - node counts
  - shard state
  - pending task counts
  - health status
- node stats:
  - search and index rates
  - search and index latency
  - merge rate and latency
  - JVM heap and GC metrics
  - CPU, memory, disk, and HTTP counters
  - thread pool queues and rejections
  - breaker trips
  - docs, store, segments, and cache counters
  - file descriptor counters
- cat shards:
  - shard counts by node
  - per-index size, docs, segment, primary, replica, and rate details

This is why the dashboard can show time-series style metrics even though the raw EDOT monitoring source lands under a `logs-*` data stream.

## How The Setup Runs

`make up` brings up the environment in this order:

1. create the local `k3d` cluster and install ingress-nginx, cert-manager, and ECK
2. deploy the main and monitoring Elasticsearch and Kibana stacks
3. deploy the EDOT gateway in `lab-monitoring`
4. deploy the main metrics and logs collectors in `lab-main`
5. deploy the synthetic search workload in `lab-main`
6. install the TSDS templates for `metrics-elasticsearch.autoops-main`
7. run a bootstrap derivation job and then keep the TSDS current with a CronJob
8. import the OTEL dashboard into the monitoring Kibana when the selected stack version supports it

After the environment is up, the normal steady state is:

- Elasticsearch monitoring data is scraped from the main cluster
- raw monitoring events land in `logs-elasticsearch.metrics-main`
- the derivation job reads recent source documents and writes curated metric documents into `metrics-elasticsearch.autoops-main`
- the synthetic workload continuously writes and searches across five `logsdb` data streams so index and search charts have activity to show
- Kibana dashboards read from the derived TSDS

## Expected Working State

When the setup is healthy, the important moving parts look like this:

- the main cluster is reachable at `https://es-main.<HOST_IP>.sslip.io`
- the monitoring cluster is reachable at `https://es-monitoring.<HOST_IP>.sslip.io`
- the raw monitoring source stream exists:
  - `logs-elasticsearch.metrics-main`
- the log stream exists:
  - `logs-elasticsearch.logs.otel-main`
- the derived TSDS exists:
  - `metrics-elasticsearch.autoops-main`
- the synthetic workload deployment is running:
  - `main-search-load`
- the three OTEL dashboard views are present in monitoring Kibana:
  - overview
  - nodes
  - indices

If those pieces are present and document counts are increasing, the OTEL monitoring path is functioning end to end.

## Synthetic Workload

The synthetic workload exists so the dashboard shows real search and indexing activity shortly after deployment instead of sitting flat until somebody generates traffic manually.

By default it:

- writes to five `logsdb` data streams named `logs-sampleapp-01-default` through `logs-sampleapp-05-default`
- runs periodic search activity against those streams
- can be tuned with `SEARCH_LOAD_*` overrides from `make`
- installs a `logsdb` index template with:
  - `index.mode: logsdb`
  - configurable shard count
  - configurable replica count

Tuning knobs:

- `SEARCH_LOAD_STREAM_PREFIX`
  - data stream prefix, default `logs-sampleapp`
- `SEARCH_LOAD_STREAM_NAMESPACE`
  - data stream namespace suffix, default `default`
- `SEARCH_LOAD_STREAM_COUNT`
  - number of data streams, default `5`
- `SEARCH_LOAD_WRITE_BATCH_SIZE`
  - bulk write size per cycle, default `75`
- `SEARCH_LOAD_SEARCHES_PER_CYCLE`
  - searches per workload cycle, default `6`
- `SEARCH_LOAD_SLEEP_SECONDS`
  - delay between cycles, default `5`
- `SEARCH_LOAD_NUMBER_OF_SHARDS`
  - shards per synthetic stream, default `1`
- `SEARCH_LOAD_NUMBER_OF_REPLICAS`
  - replicas per synthetic stream, default `0`
- `SEARCH_LOAD_QUERY_SIZE`
  - requested search hits per query, default `5`
- `SEARCH_LOAD_DEPLOYMENT_REPLICAS`
  - workload pod count, default `1`

Common operations:

- start or update the workload:
  - `make search-load-up`
- stop the workload without deleting its data:
  - `make search-load-down`
- reset the workload data streams so a new shard and replica layout takes effect:
  - `make search-load-reset`

## Gotchas

- The EDOT Elasticsearch monitoring receiver in this lab emits the `autoops_es` payload as logs, not native metrics.
  - forcing that receiver into a direct `metrics-*` path was not supportable in this runtime
- The raw monitoring stream uses a `logs-*` template by signal type.
  - TSDS behavior is only achieved through the derived `metrics-elasticsearch.autoops-main` stream
- The derived TSDS is curated.
  - it intentionally does not mirror every field from the raw `autoops_es` payload
- The derivation job can encounter duplicate writes on overlapping runs.
  - those `409` conflicts are expected steady-state behavior and are treated as duplicates, not failures
- Kibana Saved Objects UI imports `ndjson`, not the structured `export.json` wrapper.
  - the JSON wrapper is for source control and review
- Large dashboard imports can fail through ingress unless the body size is raised.
  - this repo sets `nginx.ingress.kubernetes.io/proxy-body-size: "50m"` on the Kibana ingresses
- Shard and replica changes for the synthetic workload only apply to new backing indices.
  - use `make search-load-reset` before `make search-load-up` when you want a new layout to apply immediately

## Metrics Coverage

The derived TSDS and dashboards include data from these main areas when present in `autoops_es`:

- cluster health and shard state
- node throughput and latency
- JVM heap and GC time
- thread pool queues and rejections
- breaker trips
- CPU, disk, store size, docs count, and segments
- query cache and request cache counters
- file descriptors and HTTP connection counters
- shard inventory and per-index rate details from `cat_shards`

This is intentionally based on what actually exists in the monitoring cluster for this lab, not on classic `.monitoring-*` Stack Monitoring documents. Some classic Stack Monitoring saved objects expect datasets or indices that do not exist in this OTEL setup.

## Prerequisites

- Docker
- kubectl
- k3d
- curl

The deployment assumes those tools are already installed on the host and that Docker can start local containers.

## Quick Start

```bash
make help
make up
make test
make down
```

The defaults are centralized in [scripts/common.sh](/Users/ade/Documents/github/es-otel-monitoring/scripts/common.sh:1).

- Change the stack version:
  - `make up ES_VERSION=9.3.0`
- Change the local cluster name:
  - `make up CLUSTER_NAME=edot-dev`
- Change the main cluster sizing:
  - `make up MAIN_ES_NODES=2 MAIN_ES_CPU=1 MAIN_ES_MEMORY=2Gi`
- Change the monitoring cluster sizing:
  - `make up MONITORING_ES_NODES=3 MONITORING_ES_CPU=1 MONITORING_ES_MEMORY=2Gi`
- Change the synthetic workload layout:
  - `make search-load-up SEARCH_LOAD_STREAM_COUNT=5 SEARCH_LOAD_NUMBER_OF_SHARDS=2 SEARCH_LOAD_NUMBER_OF_REPLICAS=1`
- Increase the synthetic workload search pressure:
  - `make search-load-up SEARCH_LOAD_WRITE_BATCH_SIZE=150 SEARCH_LOAD_SEARCHES_PER_CYCLE=20 SEARCH_LOAD_QUERY_SIZE=10`
- Recreate the synthetic data streams with a new shard layout:
  - `make search-load-down && make search-load-reset && make search-load-up SEARCH_LOAD_NUMBER_OF_SHARDS=2 SEARCH_LOAD_NUMBER_OF_REPLICAS=1`

## Lifecycle Commands

- `make help`
  - shows the available targets and supported overrides
- `make up`
  - creates the local cluster, installs dependencies, deploys both Elasticsearch clusters, and deploys EDOT
- `make test`
  - verifies ingress reachability, authentication, source metrics/log shipping, and derived TSDS ingestion
- `make search-load-up`
  - creates or updates the synthetic workload using the current `SEARCH_LOAD_*` overrides
- `make search-load-down`
  - stops the synthetic workload while leaving previously written data in Elasticsearch
- `make search-load-reset`
  - deletes the synthetic data streams and template so new shard and replica settings take effect on recreated streams
- `make status`
  - prints a useful snapshot of nodes, pods, ingresses, and certificates
- `make logs`
  - prints workload logs useful for troubleshooting the lab
- `make down`
  - deletes the local `k3d` cluster
- `make reset`
  - recreates the entire environment and runs verification

Sizing defaults:

- main cluster: `MAIN_ES_NODES=1`, `MAIN_ES_CPU=500m`, `MAIN_ES_MEMORY=1Gi`
- monitoring cluster: `MONITORING_ES_NODES=2`, `MONITORING_ES_CPU=500m`, `MONITORING_ES_MEMORY=1Gi`

## Endpoints

`HOST_IP` is resolved automatically by `scripts/detect_host_ip.sh`.
The default local cluster name is `edot-lab`.

- Main Kibana: `https://kibana-main.<HOST_IP>.sslip.io`
- Main Elasticsearch: `https://es-main.<HOST_IP>.sslip.io`
- Monitoring Kibana: `https://kibana-monitoring.<HOST_IP>.sslip.io`
- Monitoring Elasticsearch: `https://es-monitoring.<HOST_IP>.sslip.io`

## Credentials

Main cluster:

```bash
echo elastic
kubectl -n lab-main get secret elasticsearch-main-es-elastic-user -o jsonpath='{.data.elastic}' | base64 -d; echo
```

Monitoring cluster:

```bash
echo elastic
kubectl -n lab-monitoring get secret elasticsearch-monitoring-es-elastic-user -o jsonpath='{.data.elastic}' | base64 -d; echo
```

`make up` prints the `elastic` username and the resolved password value for both clusters at the end of deployment.

## Monitoring Cluster Sizing

The Elasticsearch sizing is environment-driven so the lab can be scaled without editing manifests.

Defaults:

- stack version: `9.3.2`
- main cluster: `1` node, `500m` CPU request, `1Gi` memory request and limit
- monitoring cluster: `2` nodes, `500m` CPU request, `1Gi` memory request and limit

Example:

```bash
make up \
  MAIN_ES_NODES=2 \
  MAIN_ES_CPU=1 \
  MAIN_ES_MEMORY=2Gi \
  MONITORING_ES_NODES=3 \
  MONITORING_ES_CPU=1 \
  MONITORING_ES_MEMORY=2Gi
```

## Deployment Flow

`make up` performs:

1. create the local `k3d` cluster
2. install ingress-nginx
3. install cert-manager and issue TLS certs
4. install ECK
5. clean up resources from older revisions of this lab if they exist
6. deploy the main and monitoring Elasticsearch/Kibana stacks
7. create EDOT and synthetic workload credentials
8. deploy the gateway, metrics collector, logs collector, and synthetic search-load app
9. install the derived TSDS template and deploy the TSDS derivation CronJob
10. run a bootstrap derivation job to seed `metrics-elasticsearch.autoops-main`
11. import the OTEL monitoring dashboard into the monitoring Kibana when `ES_VERSION >= 9.3.0`

## Verification Flow

`make test` validates the end-to-end setup by checking:

- the main and monitoring ingress endpoints answer over HTTPS
- the main cluster is reachable with the generated `elastic` credentials
- the monitoring cluster contains the expected EDOT data streams
- the monitoring cluster contains source metrics documents in `logs-elasticsearch.metrics-main`
- the monitoring cluster contains derived TSDS metrics documents in `metrics-elasticsearch.autoops-main`
- the monitoring cluster contains log documents in `logs-elasticsearch.logs.otel-main`
- the main cluster contains five synthetic `logsdb` data streams with documents
- the synthetic workload deployment is running in `lab-main`
- the OTEL monitoring dashboard exists in the monitoring Kibana on supported stack versions

The verification script also checks that the synthetic `logsdb` data streams exist and contain documents, which matters because many of the index and search charts will otherwise remain flat even when the OTEL pipeline itself is healthy.

## Verification

To inspect shipped data manually:

```bash
MON_PASS=$(kubectl -n lab-monitoring get secret elasticsearch-monitoring-es-elastic-user -o jsonpath='{.data.elastic}' | base64 -d)
curl -sk -u "elastic:${MON_PASS}" "https://es-monitoring.$(./scripts/detect_host_ip.sh).sslip.io/_cat/indices?h=index,docs.count" | sort
```

To inspect the derived TSDS directly:

```bash
MON_PASS=$(kubectl -n lab-monitoring get secret elasticsearch-monitoring-es-elastic-user -o jsonpath='{.data.elastic}' | base64 -d)
curl -sk -u "elastic:${MON_PASS}" "https://es-monitoring.$(./scripts/detect_host_ip.sh).sslip.io/_data_stream/metrics-elasticsearch.autoops-main?pretty"
```

To inspect the synthetic workload data streams directly:

```bash
MAIN_PASS=$(kubectl -n lab-main get secret elasticsearch-main-es-elastic-user -o jsonpath='{.data.elastic}' | base64 -d)
curl -sk -u "elastic:${MAIN_PASS}" "https://es-main.$(./scripts/detect_host_ip.sh).sslip.io/_data_stream/logs-sampleapp-*-default?pretty"
```

## Notes

- `ES_VERSION`, `ECK_VERSION`, and `CLUSTER_NAME` are designed to be easy to override from `make`
- the Elasticsearch node count, CPU, and memory for both clusters are configurable from `make` or the shell environment
- the EDOT source metrics stream remains `logs-elasticsearch.metrics-main` because the current runtime emits the `autoops_es` payload as log records
- the repo derives `metrics-elasticsearch.autoops-main` as a supportable TSDS for dashboards and metrics storage
- the derived TSDS is intentionally curated; it keeps the fields used by the OTEL dashboard instead of mirroring the full raw source payload
- the dashboard is expected to read from `metrics-elasticsearch.autoops-main`, not directly from `logs-elasticsearch.metrics-main`
- the top dashboard controls are important in multi-cluster cases because the monitoring cluster can hold data for more than one Elasticsearch cluster
- the synthetic workload is controlled by `SEARCH_LOAD_*` overrides for stream count, write batch size, searches per cycle, sleep interval, shard count, replica count, query size, and workload pod replicas
- shard and replica changes for the synthetic workload only apply to newly created backing indices, so use `make search-load-reset` before `make search-load-up` when you want a new layout to take effect immediately
