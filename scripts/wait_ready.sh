#!/usr/bin/env bash
set -euo pipefail

kubectl -n lab-main wait --for=condition=Ready certificate/es-main-cert --timeout=180s
kubectl -n lab-monitoring wait --for=condition=Ready certificate/es-monitoring-cert --timeout=180s

kubectl -n lab-main wait --for=condition=Ready pod -l elasticsearch.k8s.elastic.co/cluster-name=elasticsearch-main --timeout=900s
kubectl -n lab-main wait --for=condition=Ready pod -l kibana.k8s.elastic.co/name=kibana-main --timeout=420s
kubectl -n lab-monitoring wait --for=condition=Ready pod -l elasticsearch.k8s.elastic.co/cluster-name=elasticsearch-monitoring --timeout=900s
kubectl -n lab-monitoring wait --for=condition=Ready pod -l kibana.k8s.elastic.co/name=kibana-monitoring --timeout=420s
kubectl -n lab-main rollout status deploy/edot-main-metrics --timeout=300s
kubectl -n lab-main rollout status ds/edot-main-logs --timeout=300s
kubectl -n lab-monitoring rollout status deploy/edot-gateway --timeout=300s
