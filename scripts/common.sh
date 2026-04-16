#!/usr/bin/env bash

# Shared defaults for the local EDOT lab. Callers can override these via env.
: "${CLUSTER_NAME:=edot-lab}"
: "${ES_VERSION:=9.2.5}"
: "${ECK_VERSION:=2.16.1}"
: "${MAIN_ES_NODES:=1}"
: "${MAIN_ES_CPU:=500m}"
: "${MAIN_ES_MEMORY:=1Gi}"
: "${MONITORING_ES_NODES:=2}"
: "${MONITORING_ES_CPU:=500m}"
: "${MONITORING_ES_MEMORY:=1Gi}"

export CLUSTER_NAME
export ES_VERSION
export ECK_VERSION
export MAIN_ES_NODES
export MAIN_ES_CPU
export MAIN_ES_MEMORY
export MONITORING_ES_NODES
export MONITORING_ES_CPU
export MONITORING_ES_MEMORY
