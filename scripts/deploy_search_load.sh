#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "$0")/common.sh"

kubectl -n lab-main create configmap main-search-load-script \
  --from-file=generate_search_load.py=./scripts/generate_search_load.py \
  --dry-run=client -o yaml | kubectl apply -f -

sed \
  -e "s|__SEARCH_LOAD_DEPLOYMENT_REPLICAS__|${SEARCH_LOAD_DEPLOYMENT_REPLICAS}|g" \
  -e "s|__SEARCH_LOAD_STREAM_PREFIX__|${SEARCH_LOAD_STREAM_PREFIX}|g" \
  -e "s|__SEARCH_LOAD_STREAM_NAMESPACE__|${SEARCH_LOAD_STREAM_NAMESPACE}|g" \
  -e "s|__SEARCH_LOAD_STREAM_COUNT__|${SEARCH_LOAD_STREAM_COUNT}|g" \
  -e "s|__SEARCH_LOAD_WRITE_BATCH_SIZE__|${SEARCH_LOAD_WRITE_BATCH_SIZE}|g" \
  -e "s|__SEARCH_LOAD_SEARCHES_PER_CYCLE__|${SEARCH_LOAD_SEARCHES_PER_CYCLE}|g" \
  -e "s|__SEARCH_LOAD_SLEEP_SECONDS__|${SEARCH_LOAD_SLEEP_SECONDS}|g" \
  -e "s|__SEARCH_LOAD_NUMBER_OF_SHARDS__|${SEARCH_LOAD_NUMBER_OF_SHARDS}|g" \
  -e "s|__SEARCH_LOAD_NUMBER_OF_REPLICAS__|${SEARCH_LOAD_NUMBER_OF_REPLICAS}|g" \
  -e "s|__SEARCH_LOAD_QUERY_SIZE__|${SEARCH_LOAD_QUERY_SIZE}|g" \
  manifests/edot/main-search-load.yaml | kubectl apply -f -

kubectl -n lab-main rollout status deploy/main-search-load --timeout=300s
