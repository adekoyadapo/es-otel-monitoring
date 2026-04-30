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
: "${EDOT_MONITORING_MODE:=autoops}"
: "${ELASTIC_AGENT_VERSION:=${ES_VERSION}}"

AUTOOPS_DASHBOARD_ID="otel-elasticsearch-monitoring-main"
AUTOOPS_DASHBOARD_PATH="dashboards/elasticsearch-otel-monitoring-main.ndjson"
AGENT_DASHBOARD_ID="otel-elasticsearch-monitoring-agent"
AGENT_DASHBOARD_PATH="dashboards/elasticsearch-otel-monitoring-agent.ndjson"
AUTOOPS_DERIVED_TSDS="metrics-elasticsearch.autoops-main"
AUTOOPS_SOURCE_DATASTREAM="logs-elasticsearch.metrics-main"
AGENT_METRICS_DATASTREAM_PATTERN="metrics-elasticsearch.stack_monitoring.*-main"
AGENT_METRICS_DATASTREAM_TARGET="metrics-elasticsearch.stack_monitoring.*-main,-metrics-elasticsearch.stack_monitoring.otel-main"
AGENT_LOGS_DATASTREAM_PATTERN="logs-elasticsearch.server-main"
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

monitoring_mode_autoops() {
  [[ "${EDOT_MONITORING_MODE}" == "autoops" ]]
}

monitoring_mode_agent() {
  [[ "${EDOT_MONITORING_MODE}" == "agent" || "${EDOT_MONITORING_MODE}" == "contrib" ]]
}

validate_monitoring_mode() {
  case "${EDOT_MONITORING_MODE}" in
    autoops|agent|contrib) ;;
    *)
      echo "Unsupported EDOT_MONITORING_MODE: ${EDOT_MONITORING_MODE}. Use autoops, agent, or contrib." >&2
      return 1
      ;;
  esac
}

current_dashboard_id() {
  if monitoring_mode_agent; then
    printf '%s\n' "${AGENT_DASHBOARD_ID}"
  else
    printf '%s\n' "${AUTOOPS_DASHBOARD_ID}"
  fi
}

current_dashboard_path() {
  if monitoring_mode_agent; then
    printf '%s\n' "${AGENT_DASHBOARD_PATH}"
  else
    printf '%s\n' "${AUTOOPS_DASHBOARD_PATH}"
  fi
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
export EDOT_MONITORING_MODE
export ELASTIC_AGENT_VERSION
export AUTOOPS_DASHBOARD_ID
export AUTOOPS_DASHBOARD_PATH
export AGENT_DASHBOARD_ID
export AGENT_DASHBOARD_PATH
export AUTOOPS_DERIVED_TSDS
export AUTOOPS_SOURCE_DATASTREAM
export AGENT_METRICS_DATASTREAM_PATTERN
export AGENT_METRICS_DATASTREAM_TARGET
export AGENT_LOGS_DATASTREAM_PATTERN
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
