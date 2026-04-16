#!/usr/bin/env bash
set -euo pipefail

kubectl delete namespace lab --ignore-not-found=true >/dev/null 2>&1 || true

kubectl -n lab-main delete deploy ldap phpldapadmin --ignore-not-found >/dev/null 2>&1 || true
kubectl -n lab-main delete svc ldap phpldapadmin --ignore-not-found >/dev/null 2>&1 || true
kubectl -n lab-main delete ingress ldap-ui --ignore-not-found >/dev/null 2>&1 || true
kubectl -n lab-main delete configmap ldap-bootstrap --ignore-not-found >/dev/null 2>&1 || true
kubectl -n lab-main delete pod ldap-posix-seed ldap-verify --ignore-not-found >/dev/null 2>&1 || true
kubectl -n lab-main delete certificate ldap-ldaps-cert --ignore-not-found >/dev/null 2>&1 || true
kubectl -n lab-main delete secret ldap-admin-credentials ldap-ldaps-tls es-ldap-bind-secret es-ldap-role-mapping --ignore-not-found >/dev/null 2>&1 || true

kubectl -n lab-main delete elasticsearch elasticsearch --ignore-not-found >/dev/null 2>&1 || true
kubectl -n lab-main delete kibana kibana --ignore-not-found >/dev/null 2>&1 || true
