#!/usr/bin/env bash
set -euo pipefail

kubectl -n elastic-system logs statefulset/elastic-operator --tail=200 || true
kubectl -n lab-main logs -l elasticsearch.k8s.elastic.co/cluster-name=elasticsearch-main --tail=200 || true
kubectl -n lab-main logs -l kibana.k8s.elastic.co/name=kibana-main --tail=200 || true
kubectl -n lab-monitoring logs -l elasticsearch.k8s.elastic.co/cluster-name=elasticsearch-monitoring --tail=200 || true
kubectl -n lab-monitoring logs -l kibana.k8s.elastic.co/name=kibana-monitoring --tail=200 || true
kubectl -n lab-main logs deploy/edot-main-metrics --tail=200 || true
kubectl -n lab-main logs deploy/main-search-load --tail=200 || true
kubectl -n lab-monitoring logs deploy/edot-gateway --tail=200 || true
