#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "$0")/common.sh"

HOST_IP="${HOST_IP:-$(./scripts/detect_host_ip.sh)}"
export HOST_IP

./scripts/cleanup_legacy_resources.sh

kubectl apply -f manifests/namespaces.yaml
sed "s/__ES_VERSION__/${ES_VERSION}/g" manifests/elastic/elasticsearch-main.yaml | kubectl apply -f -
sed "s/__ES_VERSION__/${ES_VERSION}/g" manifests/elastic/elasticsearch-monitoring.yaml | kubectl apply -f -

sed "s/__HOST_IP__/${HOST_IP}/g" manifests/ingress/ingress-es-main.yaml | kubectl apply -f -
sed "s/__HOST_IP__/${HOST_IP}/g" manifests/ingress/ingress-kibana-main.yaml | kubectl apply -f -
sed "s/__HOST_IP__/${HOST_IP}/g" manifests/ingress/ingress-es-monitoring.yaml | kubectl apply -f -
sed "s/__HOST_IP__/${HOST_IP}/g" manifests/ingress/ingress-kibana-monitoring.yaml | kubectl apply -f -

for _ in $(seq 1 60); do
  if kubectl -n lab-main get pods -l elasticsearch.k8s.elastic.co/cluster-name=elasticsearch-main -o name | grep -q .; then
    break
  fi
  sleep 2
done
for _ in $(seq 1 60); do
  if kubectl -n lab-monitoring get pods -l elasticsearch.k8s.elastic.co/cluster-name=elasticsearch-monitoring -o name | grep -q .; then
    break
  fi
  sleep 2
done
for _ in $(seq 1 60); do
  if kubectl -n lab-main get pods -l kibana.k8s.elastic.co/name=kibana-main -o name | grep -q .; then
    break
  fi
  sleep 2
done
for _ in $(seq 1 60); do
  if kubectl -n lab-monitoring get pods -l kibana.k8s.elastic.co/name=kibana-monitoring -o name | grep -q .; then
    break
  fi
  sleep 2
done

kubectl -n lab-main wait --for=condition=Ready pod -l elasticsearch.k8s.elastic.co/cluster-name=elasticsearch-main --timeout=900s
kubectl -n lab-main wait --for=condition=Ready pod -l kibana.k8s.elastic.co/name=kibana-main --timeout=420s
kubectl -n lab-monitoring wait --for=condition=Ready pod -l elasticsearch.k8s.elastic.co/cluster-name=elasticsearch-monitoring --timeout=900s
kubectl -n lab-monitoring wait --for=condition=Ready pod -l kibana.k8s.elastic.co/name=kibana-monitoring --timeout=420s

./scripts/deploy_edot.sh
