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
