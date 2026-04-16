SHELL := /bin/bash

CLUSTER_NAME ?= edot-lab
HOST_IP ?= $(shell ./scripts/detect_host_ip.sh)
ES_VERSION ?= 9.2.5
ECK_VERSION ?= 2.16.1
export CLUSTER_NAME
export HOST_IP
export ES_VERSION
export ECK_VERSION

.PHONY: help up down reset status logs test

help:
	@echo "Targets:"
	@echo "  make up      Create the local k3d lab and deploy the full EDOT topology"
	@echo "  make test    Verify ingress, auth, and EDOT metrics/log shipping"
	@echo "  make status  Show cluster nodes, pods, ingresses, and certificates"
	@echo "  make logs    Show useful workload logs for the lab"
	@echo "  make down    Delete the local k3d lab"
	@echo "  make reset   Recreate the lab from scratch and run verification"
	@echo ""
	@echo "Overrides:"
	@echo "  ES_VERSION=<version>      Elastic Stack version to deploy"
	@echo "  ECK_VERSION=<version>     ECK operator version to install"
	@echo "  CLUSTER_NAME=<name>       k3d cluster name"
	@echo "  HOST_IP=<ip>              Host IP used for sslip.io ingress URLs"

up:
	@./scripts/validate_version.sh
	@./scripts/create_cluster.sh
	@./scripts/install_ingress.sh
	@./scripts/install_cert_manager.sh
	@./scripts/install_eck.sh
	@./scripts/deploy_elastic.sh
	@./scripts/wait_ready.sh
	@echo ""
	@echo "Environment ready"
	@echo "Main Kibana:        https://kibana-main.$${HOST_IP}.sslip.io"
	@echo "Main Elasticsearch: https://es-main.$${HOST_IP}.sslip.io"
	@echo "Monitoring Kibana:  https://kibana-monitoring.$${HOST_IP}.sslip.io"
	@echo "Monitoring ES:      https://es-monitoring.$${HOST_IP}.sslip.io"
	@echo "k3d cluster name:   $${CLUSTER_NAME}"
	@echo "Elastic Stack version: $${ES_VERSION}"
	@echo "Main cluster elastic password: kubectl -n lab-main get secret elasticsearch-main-es-elastic-user -o jsonpath='{.data.elastic}' | base64 -d; echo"
	@echo "Monitoring cluster elastic password: kubectl -n lab-monitoring get secret elasticsearch-monitoring-es-elastic-user -o jsonpath='{.data.elastic}' | base64 -d; echo"

down:
	@./scripts/destroy_cluster.sh

reset: down up test

status:
	@echo "== Nodes =="
	@kubectl get nodes
	@echo "\n== Pods (all namespaces) =="
	@kubectl get pods -A
	@echo "\n== Ingresses =="
	@kubectl get ingress -A
	@echo "\n== Certificates =="
	@kubectl get certificate -A

logs:
	@./scripts/logs.sh

test:
	@./scripts/test_auth.sh
