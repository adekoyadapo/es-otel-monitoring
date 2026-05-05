#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "$0")/common.sh"
validate_monitoring_mode

kubectl -n lab-main wait --for=condition=Ready certificate/es-main-cert --timeout=180s
kubectl -n lab-monitoring wait --for=condition=Ready certificate/es-monitoring-cert --timeout=180s

kubectl -n lab-main wait --for=condition=Ready pod -l elasticsearch.k8s.elastic.co/cluster-name=elasticsearch-main --timeout=900s
kubectl -n lab-main wait --for=condition=Ready pod -l kibana.k8s.elastic.co/name=kibana-main --timeout=420s
kubectl -n lab-monitoring wait --for=condition=Ready pod -l elasticsearch.k8s.elastic.co/cluster-name=elasticsearch-monitoring --timeout=900s
kubectl -n lab-monitoring wait --for=condition=Ready pod -l kibana.k8s.elastic.co/name=kibana-monitoring --timeout=420s

if monitoring_mode_agent_api; then
  kubectl -n lab-main wait --for=condition=Available deploy/edot-main-metrics-api --timeout=600s
  kubectl -n lab-main rollout status ds/edot-main-logs-api --timeout=600s
else
  kubectl -n lab-main rollout status deploy/edot-main-metrics --timeout=300s
  kubectl -n lab-main rollout status ds/edot-main-logs --timeout=300s
fi

if monitoring_mode_autoops || monitoring_mode_contrib || monitoring_mode_agent_api; then
  kubectl -n lab-monitoring rollout status deploy/edot-gateway --timeout=300s
fi
