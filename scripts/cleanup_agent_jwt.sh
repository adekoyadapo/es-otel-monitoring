#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "$0")/common.sh"

# Remove JWT OTEL collector
kubectl -n lab-main delete deploy edot-main-metrics-jwt --ignore-not-found
kubectl -n lab-main delete configmap edot-main-metrics-jwt-config --ignore-not-found
kubectl -n lab-main delete ds edot-main-logs-jwt --ignore-not-found
kubectl -n lab-main delete configmap edot-main-logs-jwt-config --ignore-not-found
kubectl -n lab-main delete serviceaccount edot-main-logs-jwt --ignore-not-found
kubectl delete clusterrole edot-main-logs-jwt --ignore-not-found
kubectl delete clusterrolebinding edot-main-logs-jwt --ignore-not-found
kubectl -n lab-main delete secret agent-jwt-mint-credentials --ignore-not-found

bash "$(dirname "$0")/cleanup_jwt_test.sh"

echo "JWT OTEL agent workflow removed."
