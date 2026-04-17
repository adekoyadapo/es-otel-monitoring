# es-otel-monitoring

This repository provisions a local `k3d` lab with two Elasticsearch clusters managed by ECK and connected through EDOT.

The resulting environment is:

- a main Elasticsearch and Kibana stack in `lab-main`
- a dedicated monitoring Elasticsearch and Kibana stack in `lab-monitoring`
- a monitoring Elasticsearch cluster sized to `2` nodes
- HTTPS ingress endpoints via `sslip.io`
- cert-manager managed TLS certificates
- EDOT collectors that ship main-cluster metrics and logs into the monitoring cluster

This repo is intentionally narrow in scope. It only contains the manifests, scripts, and docs needed for this local EDOT monitoring lab.

## Repository Layout

- `manifests/elastic`
  - ECK operator manifests and the main and monitoring Elasticsearch/Kibana resources
- `manifests/edot`
  - EDOT gateway, Elasticsearch metrics collector, and Elasticsearch logs collector
- `dashboards`
  - the generated OTEL monitoring dashboard NDJSON imported into the monitoring Kibana on supported stack versions
- `manifests/ingress`
  - Ingress resources for both Elasticsearch and Kibana endpoints
- `manifests/cert-manager`
  - Local issuers and certificates used by the ingresses
- `scripts`
  - Cluster lifecycle, deployment, readiness, and verification scripts
- `Makefile`
  - Main entrypoint for spin-up, verification, inspection, and teardown

## Topology

- `lab-main`
  - `elasticsearch-main`
  - `kibana-main`
  - `edot-main-metrics`
  - `edot-main-logs`
- `lab-monitoring`
  - `elasticsearch-monitoring`
  - `kibana-monitoring`
  - `edot-gateway`

Data flow:

- the main cluster exposes HTTPS ingress and internal services
- the EDOT metrics collector polls Elasticsearch monitoring endpoints in `lab-main`
- the EDOT logs collector tails Elasticsearch pod logs from nodes in the local cluster
- both collectors send their output through the EDOT gateway in `lab-monitoring`
- the EDOT gateway writes the resulting documents into the monitoring Elasticsearch cluster

## What EDOT Ships

- EDOT monitoring documents from the main cluster using the bundled EDOT Elasticsearch monitoring module
- Elasticsearch container logs from the main cluster via a DaemonSet file log collector

The monitoring cluster receives:

- `logs-elasticsearch.metrics-main`
- `logs-elasticsearch.logs.otel-main`

## Dashboard Assets

- `stack-mon.ndjson`
  - legacy baseline dashboard export kept intact for comparison and reuse
- `dashboards/elasticsearch-otel-monitoring-main.ndjson`
  - generated OTEL-focused dashboard export for this lab, built around `logs-elasticsearch.metrics-main` and `autoops_es.*` fields
- `scripts/build_otel_dashboard_ndjson.py`
  - rebuilds the importable OTEL dashboard export
- `scripts/import_monitoring_dashboard.sh`
  - imports the OTEL dashboard into the monitoring Kibana when the selected stack version supports it

The OTEL dashboard import is enabled for stack versions `>= 9.3.0`. On lower versions, deployment skips the dashboard import cleanly and `make test` reports that skip instead of failing.

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

## Lifecycle Commands

- `make help`
  - shows the available targets and supported overrides
- `make up`
  - creates the local cluster, installs dependencies, deploys both Elasticsearch clusters, and deploys EDOT
- `make test`
  - verifies ingress reachability, authentication, and that metrics and logs are arriving in the monitoring cluster
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
7. create EDOT credentials and deploy the gateway, metrics collector, and logs collector
8. import the OTEL monitoring dashboard into the monitoring Kibana when `ES_VERSION >= 9.3.0`

## Verification Flow

`make test` validates the end-to-end setup by checking:

- the main and monitoring ingress endpoints answer over HTTPS
- the main cluster is reachable with the generated `elastic` credentials
- the monitoring cluster contains the expected EDOT data streams
- the monitoring cluster contains metrics documents in `logs-elasticsearch.metrics-main`
- the monitoring cluster contains log documents in `logs-elasticsearch.logs.otel-main`
- the OTEL monitoring dashboard exists in the monitoring Kibana on supported stack versions

## Verification

To inspect shipped data manually:

```bash
MON_PASS=$(kubectl -n lab-monitoring get secret elasticsearch-monitoring-es-elastic-user -o jsonpath='{.data.elastic}' | base64 -d)
curl -sk -u "elastic:${MON_PASS}" "https://es-monitoring.$(./scripts/detect_host_ip.sh).sslip.io/_cat/indices?h=index,docs.count" | sort
```

## Notes

- `ES_VERSION`, `ECK_VERSION`, and `CLUSTER_NAME` are designed to be easy to override from `make`
- the Elasticsearch node count, CPU, and memory for both clusters are configurable from `make` or the shell environment
- the EDOT metrics receiver still uses the built-in collector module name required by the runtime image, but the shipped data stream names are clean and EDOT-focused
