SHELL := /bin/bash

CLUSTER_NAME ?= edot-lab
HOST_IP ?= $(shell ./scripts/detect_host_ip.sh)
ES_VERSION ?= 9.3.2
ECK_VERSION ?= 2.16.1
MAIN_ES_NODES ?= 1
MAIN_ES_CPU ?= 500m
MAIN_ES_MEMORY ?= 1Gi
MONITORING_ES_NODES ?= 2
MONITORING_ES_CPU ?= 500m
MONITORING_ES_MEMORY ?= 1Gi
SEARCH_LOAD_STREAM_PREFIX ?= logs-sampleapp
SEARCH_LOAD_STREAM_NAMESPACE ?= default
SEARCH_LOAD_STREAM_COUNT ?= 5
SEARCH_LOAD_WRITE_BATCH_SIZE ?= 75
SEARCH_LOAD_SEARCHES_PER_CYCLE ?= 6
SEARCH_LOAD_SLEEP_SECONDS ?= 5
SEARCH_LOAD_NUMBER_OF_SHARDS ?= 1
SEARCH_LOAD_NUMBER_OF_REPLICAS ?= 0
SEARCH_LOAD_QUERY_SIZE ?= 5
SEARCH_LOAD_DEPLOYMENT_REPLICAS ?= 1
export CLUSTER_NAME
export HOST_IP
export ES_VERSION
export ECK_VERSION
export MAIN_ES_NODES
export MAIN_ES_CPU
export MAIN_ES_MEMORY
export MONITORING_ES_NODES
export MONITORING_ES_CPU
export MONITORING_ES_MEMORY
export SEARCH_LOAD_STREAM_PREFIX
export SEARCH_LOAD_STREAM_NAMESPACE
export SEARCH_LOAD_STREAM_COUNT
export SEARCH_LOAD_WRITE_BATCH_SIZE
export SEARCH_LOAD_SEARCHES_PER_CYCLE
export SEARCH_LOAD_SLEEP_SECONDS
export SEARCH_LOAD_NUMBER_OF_SHARDS
export SEARCH_LOAD_NUMBER_OF_REPLICAS
export SEARCH_LOAD_QUERY_SIZE
export SEARCH_LOAD_DEPLOYMENT_REPLICAS

.PHONY: help up down reset status logs test import-dashboard search-load-up search-load-down search-load-reset

help:
	@echo "Targets:"
	@echo "  make up      Create the local k3d lab and deploy the full EDOT topology"
	@echo "  make test    Verify ingress, auth, and EDOT metrics/log shipping"
	@echo "  make import-dashboard  Rebuild and import the OTEL monitoring dashboard"
	@echo "  make search-load-up    Deploy or update the synthetic search workload"
	@echo "  make search-load-down  Stop the synthetic search workload"
	@echo "  make search-load-reset Delete the synthetic workload data streams and template"
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
	@echo "  MAIN_ES_NODES=<count>     Main Elasticsearch node count"
	@echo "  MAIN_ES_CPU=<cpu>         Main Elasticsearch CPU request"
	@echo "  MAIN_ES_MEMORY=<memory>   Main Elasticsearch memory request and limit"
	@echo "  MONITORING_ES_NODES=<n>   Monitoring Elasticsearch node count"
	@echo "  MONITORING_ES_CPU=<cpu>   Monitoring Elasticsearch CPU request"
	@echo "  MONITORING_ES_MEMORY=<m>  Monitoring Elasticsearch memory request and limit"
	@echo "  SEARCH_LOAD_STREAM_COUNT=<n>         Number of synthetic data streams"
	@echo "  SEARCH_LOAD_WRITE_BATCH_SIZE=<n>     Bulk write size per cycle"
	@echo "  SEARCH_LOAD_SEARCHES_PER_CYCLE=<n>   Searches per workload cycle"
	@echo "  SEARCH_LOAD_SLEEP_SECONDS=<n>        Delay between workload cycles"
	@echo "  SEARCH_LOAD_NUMBER_OF_SHARDS=<n>     Shards per synthetic logsdb stream"
	@echo "  SEARCH_LOAD_NUMBER_OF_REPLICAS=<n>   Replicas per synthetic logsdb stream"
	@echo "  SEARCH_LOAD_QUERY_SIZE=<n>           Search hits requested per query"
	@echo "  SEARCH_LOAD_DEPLOYMENT_REPLICAS=<n>  Number of workload pods"

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
	@echo "Main ES sizing:     nodes=$${MAIN_ES_NODES} cpu=$${MAIN_ES_CPU} memory=$${MAIN_ES_MEMORY}"
	@echo "Monitoring sizing:  nodes=$${MONITORING_ES_NODES} cpu=$${MONITORING_ES_CPU} memory=$${MONITORING_ES_MEMORY}"
	@echo ""
	@echo "Main cluster username:  elastic"
	@printf "Main cluster password:  "; kubectl -n lab-main get secret elasticsearch-main-es-elastic-user -o jsonpath='{.data.elastic}' | base64 -d; echo
	@echo "Monitoring username:    elastic"
	@printf "Monitoring password:    "; kubectl -n lab-monitoring get secret elasticsearch-monitoring-es-elastic-user -o jsonpath='{.data.elastic}' | base64 -d; echo

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

import-dashboard:
	@bash ./scripts/import_monitoring_dashboard.sh

search-load-up:
	@bash ./scripts/deploy_search_load.sh

search-load-down:
	@bash ./scripts/stop_search_load.sh

search-load-reset:
	@bash ./scripts/reset_search_load_data.sh
