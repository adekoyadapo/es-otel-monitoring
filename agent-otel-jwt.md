# JWT-authenticated OTLP setup

This document describes the isolated JWT-authenticated Elastic Agent workflow in this repository.
It focuses on the Kubernetes configuration, how the JWT authentication works, how metrics and logs
move through the EDOT gateway, and which fields the native metrics exporter exposes.

## Overview

The JWT path keeps Elastic Agent runtime containers in the pod, but it does not use a
scrape-based collector model.

The flow is:

1. a JWT is minted into a shared volume
2. a local proxy injects the JWT and the required shared-secret header
3. a small exporter queries Elasticsearch through that proxy
4. the exporter emits native OTLP metrics to the local EDOT collector
5. the collector forwards those metrics to `edot-gateway`
6. the gateway writes the metrics to Elasticsearch as an OTLP-native metrics stream
7. logs follow a separate `filelog` path and are shipped through the same gateway

## Kubernetes Configuration

### JWT realm overlay

File:

- `manifests/jwt/elasticsearch-main-jwt.yaml`

Key sections:

- `xpack.security.authc.realms.jwt.jwt1`
- `client_authentication.type: shared_secret`
- `allowed_signature_algorithms: [HS256]`
- `allowed_issuer`
- `allowed_audiences`
- `allowed_subjects`
- `hmac_jwkset`

This realm validates the JWT signature and the shared-secret client authentication header
before allowing the source cluster request.

The repo now applies an ECK trial-license secret in `elastic-system` before the
clusters are created, so a fresh install can enable JWT realms without a manual
license step after the fact.

JWT realms require a trial or commercial license on the source cluster. A basic license
will reject the JWT-authenticated requests and the exporter will report 401 responses.

### JWT metrics exporter

File:

- `manifests/edot/main-metrics-otel-jwt.yaml`

Relevant sections:

- `jwt-metrics-exporter`
  - Python sidecar that polls Elasticsearch through the local proxy
  - reads `/jwt/token`
  - injects `Authorization: Bearer ...`
  - injects `ES-Client-Authentication: SharedSecret ...`
  - emits OTLP metric points to the local collector on `127.0.0.1:4318`
- `edot-main-metrics-jwt-config`
  - `receivers.otlp`
  - `data_stream.type: metrics`
  - `data_stream.dataset: elasticsearch.stack_monitoring`
  - `data_stream.namespace: main`
  - `exporters.otlp_grpc/gateway`

This is the piece that keeps the JWT path native OTLP instead of a scrape-to-log workaround.

### JWT logs collector

File:

- `manifests/edot/main-logs-otel-jwt.yaml`

Relevant sections:

- `filelog/elasticsearch`
  - tails the Elasticsearch container logs
- `attributes/edot_logs`
- `exporters.otlp_grpc/gateway`

Logs and metrics are shipped independently, but they share the same EDOT gateway target.

## Authentication Flow

1. The `mint-jwt` init container creates a signed JWT and stores it at `/jwt/token`.
2. The `jwt-source-proxy` sidecar reads that token and forwards requests to the source cluster.
3. The proxy injects:
   - `Authorization: Bearer <token>`
   - `ES-Client-Authentication: SharedSecret <secret>`
4. The source Elasticsearch JWT realm validates the request.
5. The exporter queries Elasticsearch through the proxy and turns the responses into OTLP metrics.
6. The Elastic Agent EDOT runtime receives those OTLP points on `127.0.0.1:4318`.
7. The EDOT gateway stores the metrics in the monitoring cluster as a metrics data stream.

## Data Shape

The exporter emits OTLP-native metrics, not logs documents.

The main metric families are:

- `elasticsearch_cluster_health_state`
- `elasticsearch_cluster_nodes_total`
- `elasticsearch_cluster_nodes_data`
- `elasticsearch_cluster_indices_total`
- `elasticsearch_cluster_shards_total`
- `elasticsearch_cluster_shards_primaries`
- `elasticsearch_cluster_docs_total`
- `elasticsearch_cluster_store_size_bytes`
- `elasticsearch_cluster_pending_tasks_total`
- `elasticsearch_node_heap_used_bytes`
- `elasticsearch_node_heap_max_bytes`
- `elasticsearch_node_heap_used_pct`
- `elasticsearch_node_cpu_pct`
- `elasticsearch_node_open_file_descriptors`
- `elasticsearch_node_search_queue`
- `elasticsearch_node_write_queue`
- `elasticsearch_node_search_rejected_total`
- `elasticsearch_node_write_rejected_total`
- `elasticsearch_node_young_gc_time_ms`
- `elasticsearch_node_old_gc_time_ms`
- `elasticsearch_node_search_total`
- `elasticsearch_node_indexing_total`
- `elasticsearch_node_store_size_bytes`
- `elasticsearch_node_segments_count`
- `elasticsearch_node_request_breakers_total`
- `elasticsearch_node_parent_breakers_total`
- `elasticsearch_node_ingest_failures_total`
- `elasticsearch_index_docs`
- `elasticsearch_index_store_size_bytes`
- `elasticsearch_index_segments_count`
- `elasticsearch_index_search_query_total`
- `elasticsearch_index_indexing_total`
- `elasticsearch_index_primary_shards`
- `elasticsearch_index_total_shards`

Common dimensions:

- `cluster_name`
- `node_name`
- `node_id`
- `index_name`
- `status`
- `state`

Those labels are what make the dashboards filterable and multi-cluster friendly.

## Sampling And Collection Rate

The main control is the exporter poll interval.

Current default:

- exporter poll interval: `10s`

Practical guidance:

- `10s` is a good default for lab-scale Elasticsearch clusters.
- `5s` gives faster visibility but increases source-cluster cost and monitoring churn.
- `30s` or `1m` reduces source load if you only need coarse trends.

If you need to adjust the sampling size, change the exporter `POLL_INTERVAL`
environment variable in `manifests/edot/main-metrics-otel-jwt.yaml`.

## What To Change For Other Endpoints

If you need to ship the same native metrics to a different OTLP endpoint:

- change the collector exporter endpoint in `manifests/edot/main-metrics-otel-jwt.yaml`
- keep the JWT realm overlay and local proxy unchanged
- keep the exporter metric names stable so the dashboard stays valid

If you change the metric names or dimensions, the JWT dashboard must be rebuilt to match the new field set.
