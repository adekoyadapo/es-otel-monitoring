#!/usr/bin/env bash

# Shared defaults for the local EDOT lab. Callers can override these via env.
: "${CLUSTER_NAME:=edot-lab}"
: "${ES_VERSION:=9.3.2}"
: "${ECK_VERSION:=2.16.1}"
: "${MAIN_ES_NODES:=1}"
: "${MAIN_ES_CPU:=500m}"
: "${MAIN_ES_MEMORY:=1Gi}"
: "${MONITORING_ES_NODES:=2}"
: "${MONITORING_ES_CPU:=500m}"
: "${MONITORING_ES_MEMORY:=1Gi}"
: "${DASHBOARD_IMPORT_MIN_VERSION:=9.3.0}"

OTEL_MONITORING_DASHBOARD_ID="otel-elasticsearch-monitoring-main"
OTEL_MONITORING_DASHBOARD_PATH="dashboards/elasticsearch-otel-monitoring-main.ndjson"
AUTOOPS_DERIVED_TSDS="metrics-elasticsearch.autoops-main"
AUTOOPS_SOURCE_DATASTREAM="logs-elasticsearch.metrics-main"
: "${SEARCH_LOAD_STREAM_PREFIX:=logs-sampleapp}"
: "${SEARCH_LOAD_STREAM_NAMESPACE:=default}"
: "${SEARCH_LOAD_STREAM_COUNT:=5}"
: "${SEARCH_LOAD_WRITE_BATCH_SIZE:=75}"
: "${SEARCH_LOAD_SEARCHES_PER_CYCLE:=6}"
: "${SEARCH_LOAD_SLEEP_SECONDS:=5}"
: "${SEARCH_LOAD_NUMBER_OF_SHARDS:=1}"
: "${SEARCH_LOAD_NUMBER_OF_REPLICAS:=0}"
: "${SEARCH_LOAD_QUERY_SIZE:=5}"
: "${SEARCH_LOAD_DEPLOYMENT_REPLICAS:=1}"

version_to_int() {
  local version="${1%%[-+]*}"
  local major=0
  local minor=0
  local patch=0
  IFS='.' read -r major minor patch <<<"${version}"
  major="${major:-0}"
  minor="${minor:-0}"
  patch="${patch:-0}"
  printf '%d%03d%03d\n' "${major}" "${minor}" "${patch}"
}

version_gte() {
  local left="$1"
  local right="$2"
  [[ "$(version_to_int "${left}")" -ge "$(version_to_int "${right}")" ]]
}

dashboard_import_supported() {
  version_gte "${ES_VERSION}" "${DASHBOARD_IMPORT_MIN_VERSION}"
}

export CLUSTER_NAME
export ES_VERSION
export ECK_VERSION
export MAIN_ES_NODES
export MAIN_ES_CPU
export MAIN_ES_MEMORY
export MONITORING_ES_NODES
export MONITORING_ES_CPU
export MONITORING_ES_MEMORY
export DASHBOARD_IMPORT_MIN_VERSION
export OTEL_MONITORING_DASHBOARD_ID
export OTEL_MONITORING_DASHBOARD_PATH
export AUTOOPS_DERIVED_TSDS
export AUTOOPS_SOURCE_DATASTREAM
export SEARCH_LOAD_STREAM_PREFIX
export SEARCH_LOAD_STREAM_NAMESPACE
export SEARCH_LOAD_STREAM_COUNT
export SEARCH_LOAD_WRITE_BATCH_SIZE
export SEARCH_LOAD_SEARCHES_PER_CYCLE
export SEARCH_LOAD_SLEEP_SECONDS
export SEARCH_LOAD_NUMBER_OF_SHARDS
export SEARCH_LOAD_NUMBER_OF_REPLICAS
export SEARCH_LOAD_QUERY_SIZE
export SEARCH_LOAD_DEPLOYMENT_REPLICAS
