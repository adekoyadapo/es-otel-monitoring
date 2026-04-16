#!/usr/bin/env bash

# Shared defaults for the local EDOT lab. Callers can override these via env.
: "${CLUSTER_NAME:=edot-lab}"
: "${ES_VERSION:=9.2.5}"
: "${ECK_VERSION:=2.16.1}"

export CLUSTER_NAME
export ES_VERSION
export ECK_VERSION
