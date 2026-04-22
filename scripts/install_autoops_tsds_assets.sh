#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "$0")/common.sh"

HOST_IP="${HOST_IP:-$(./scripts/detect_host_ip.sh)}"
MONITORING_ES_URL="https://es-monitoring.${HOST_IP}.sslip.io"
MONITORING_ELASTIC_PASSWORD="$(kubectl -n lab-monitoring get secret elasticsearch-monitoring-es-elastic-user -o jsonpath='{.data.elastic}' | base64 -d)"

if [[ -z "${MONITORING_ELASTIC_PASSWORD}" ]]; then
  echo "Unable to read monitoring Elasticsearch password for TSDS asset install" >&2
  exit 1
fi

read -r -d '' COMPONENT_TEMPLATE <<'JSON' || true
{
  "template": {
    "mappings": {
      "properties": {
        "@timestamp": { "type": "date" },
        "event": {
          "properties": {
            "dataset": { "type": "keyword", "time_series_dimension": true },
            "kind": { "type": "keyword" },
            "module": { "type": "keyword" }
          }
        },
        "metricset": {
          "properties": {
            "name": { "type": "keyword", "time_series_dimension": true }
          }
        },
        "host": {
          "properties": {
            "name": { "type": "keyword" }
          }
        },
        "service": {
          "properties": {
            "address": { "type": "keyword", "time_series_dimension": true },
            "type": { "type": "keyword" }
          }
        },
        "autoops_es": {
          "properties": {
            "cluster": {
              "properties": {
                "id": { "type": "keyword", "time_series_dimension": true },
                "name": { "type": "keyword" },
                "version": { "type": "keyword" }
              }
            },
            "cluster_health": {
              "properties": {
                "active_primary_shards": { "type": "long", "time_series_metric": "gauge" },
                "active_shards_percent_as_number": { "type": "long", "time_series_metric": "gauge" },
                "delayed_unassigned_shards": { "type": "long", "time_series_metric": "gauge" },
                "initializing_shards": { "type": "long", "time_series_metric": "gauge" },
                "number_of_data_nodes": { "type": "long", "time_series_metric": "gauge" },
                "number_of_nodes": { "type": "long", "time_series_metric": "gauge" },
                "number_of_pending_tasks": { "type": "long", "time_series_metric": "gauge" },
                "relocating_shards": { "type": "long", "time_series_metric": "gauge" },
                "status": { "type": "keyword" },
                "unassigned_shards": { "type": "long", "time_series_metric": "gauge" }
              }
            },
            "node_stats": {
              "properties": {
                "id": { "type": "keyword", "time_series_dimension": true },
                "name": { "type": "keyword", "time_series_dimension": true },
                "search_rate_per_second": { "type": "float", "time_series_metric": "gauge" },
                "index_rate_per_second": { "type": "float", "time_series_metric": "gauge" },
                "search_latency_in_millis": { "type": "float", "time_series_metric": "gauge" },
                "index_latency_in_millis": { "type": "float", "time_series_metric": "gauge" },
                "index_failed_rate_per_second": { "type": "float", "time_series_metric": "gauge" },
                "merge_rate_per_second": { "type": "float", "time_series_metric": "gauge" },
                "merge_latency_in_millis": { "type": "float", "time_series_metric": "gauge" },
                "http": {
                  "properties": {
                    "current_open": { "type": "long", "time_series_metric": "gauge" },
                    "total_opened": { "type": "long", "time_series_metric": "counter" }
                  }
                },
                "process": {
                  "properties": {
                    "cpu": {
                      "properties": {
                        "percent": { "type": "long", "time_series_metric": "gauge" }
                      }
                    },
                    "open_file_descriptors": { "type": "long", "time_series_metric": "gauge" },
                    "max_file_descriptors": { "type": "long", "time_series_metric": "gauge" }
                  }
                },
                "os": {
                  "properties": {
                    "mem": {
                      "properties": {
                        "used_in_bytes": { "type": "long", "time_series_metric": "gauge" },
                        "total_in_bytes": { "type": "long", "time_series_metric": "gauge" }
                      }
                    },
                    "cpu": {
                      "properties": {
                        "load_average": {
                          "properties": {
                            "1m": { "type": "float", "time_series_metric": "gauge" },
                            "5m": { "type": "float", "time_series_metric": "gauge" },
                            "15m": { "type": "float", "time_series_metric": "gauge" }
                          }
                        }
                      }
                    }
                  }
                },
                "fs": {
                  "properties": {
                    "total": {
                      "properties": {
                        "available_in_bytes": { "type": "long", "time_series_metric": "gauge" },
                        "free_in_bytes": { "type": "long", "time_series_metric": "gauge" },
                        "total_in_bytes": { "type": "long", "time_series_metric": "gauge" }
                      }
                    }
                  }
                },
                "jvm": {
                  "properties": {
                    "mem": {
                      "properties": {
                        "heap_used_in_bytes": { "type": "long", "time_series_metric": "gauge" },
                        "heap_max_in_bytes": { "type": "long", "time_series_metric": "gauge" },
                        "heap_used_percent": { "type": "long", "time_series_metric": "gauge" }
                      }
                    },
                    "gc": {
                      "properties": {
                        "collectors": {
                          "properties": {
                            "young": {
                              "properties": {
                                "collection_time_in_millis": { "type": "long", "time_series_metric": "counter" },
                                "collection_count": { "type": "long", "time_series_metric": "counter" }
                              }
                            },
                            "old": {
                              "properties": {
                                "collection_time_in_millis": { "type": "long", "time_series_metric": "counter" },
                                "collection_count": { "type": "long", "time_series_metric": "counter" }
                              }
                            }
                          }
                        }
                      }
                    }
                  }
                },
                "thread_pool": {
                  "properties": {
                    "search": {
                      "properties": {
                        "queue": { "type": "long", "time_series_metric": "gauge" },
                        "rejected": { "type": "long", "time_series_metric": "counter" }
                      }
                    },
                    "write": {
                      "properties": {
                        "queue": { "type": "long", "time_series_metric": "gauge" },
                        "rejected": { "type": "long", "time_series_metric": "counter" }
                      }
                    }
                  }
                },
                "breakers": {
                  "properties": {
                    "parent": {
                      "properties": {
                        "tripped": { "type": "long", "time_series_metric": "counter" }
                      }
                    },
                    "request": {
                      "properties": {
                        "tripped": { "type": "long", "time_series_metric": "counter" }
                      }
                    }
                  }
                },
                "indices": {
                  "properties": {
                    "docs": {
                      "properties": {
                        "count": { "type": "long", "time_series_metric": "gauge" }
                      }
                    },
                    "store": {
                      "properties": {
                        "size_in_bytes": { "type": "long", "time_series_metric": "gauge" },
                        "total_data_set_size_in_bytes": { "type": "long", "time_series_metric": "gauge" }
                      }
                    },
                    "segments": {
                      "properties": {
                        "count": { "type": "long", "time_series_metric": "gauge" },
                        "memory_in_bytes": { "type": "long", "time_series_metric": "gauge" }
                      }
                    },
                    "query_cache": {
                      "properties": {
                        "hit_count": { "type": "long", "time_series_metric": "counter" },
                        "miss_count": { "type": "long", "time_series_metric": "counter" },
                        "evictions": { "type": "long", "time_series_metric": "counter" }
                      }
                    },
                    "request_cache": {
                      "properties": {
                        "hit_count": { "type": "long", "time_series_metric": "counter" },
                        "miss_count": { "type": "long", "time_series_metric": "counter" },
                        "evictions": { "type": "long", "time_series_metric": "counter" }
                      }
                    }
                  }
                }
              }
            },
            "cat_shards": {
              "properties": {
                "node_shards_count": {
                  "properties": {
                    "node_id": { "type": "keyword", "time_series_dimension": true },
                    "node_name": { "type": "keyword", "time_series_dimension": true },
                    "shards_count": { "type": "float", "time_series_metric": "gauge" },
                    "primary_shards": { "type": "float", "time_series_metric": "gauge" },
                    "replica_shards": { "type": "float", "time_series_metric": "gauge" },
                    "initializing_shards": { "type": "float", "time_series_metric": "gauge" },
                    "relocating_shards": { "type": "float", "time_series_metric": "gauge" }
                  }
                },
                "node_index_shards": {
                  "properties": {
                    "node_id": { "type": "keyword", "time_series_dimension": true },
                    "node_name": { "type": "keyword", "time_series_dimension": true },
                    "index": { "type": "keyword", "time_series_dimension": true },
                    "index_type": { "type": "keyword" },
                    "index_status": { "type": "keyword" },
                    "total_size_in_bytes": { "type": "float", "time_series_metric": "gauge" },
                    "size_in_bytes": { "type": "float", "time_series_metric": "gauge" },
                    "max_shard_size_in_bytes": { "type": "float", "time_series_metric": "gauge" },
                    "min_shard_size_in_bytes": { "type": "float", "time_series_metric": "gauge" },
                    "docs_count": { "type": "float", "time_series_metric": "gauge" },
                    "segments_count": { "type": "float", "time_series_metric": "gauge" },
                    "primary_shards_count": { "type": "float", "time_series_metric": "gauge" },
                    "replica_shards_count": { "type": "float", "time_series_metric": "gauge" },
                    "unassigned_shards_count": { "type": "float", "time_series_metric": "gauge" },
                    "relocating_shards_count": { "type": "float", "time_series_metric": "gauge" },
                    "initializing_shards_count": { "type": "float", "time_series_metric": "gauge" },
                    "search_rate_per_second": { "type": "float", "time_series_metric": "gauge" },
                    "index_rate_per_second": { "type": "float", "time_series_metric": "gauge" },
                    "search_latency_in_millis": { "type": "float", "time_series_metric": "gauge" },
                    "index_latency_in_millis": { "type": "float", "time_series_metric": "gauge" },
                    "index_failed_rate_per_second": { "type": "float", "time_series_metric": "gauge" }
                  }
                }
              }
            }
          }
        }
      }
    }
  }
}
JSON

read -r -d '' INDEX_TEMPLATE <<'JSON' || true
{
  "index_patterns": ["metrics-elasticsearch.autoops-*"],
  "data_stream": {},
  "priority": 250,
  "composed_of": [
    "metrics@mappings",
    "data-streams@mappings",
    "metrics@tsdb-settings",
    "metrics-elasticsearch.autoops@custom"
  ],
  "template": {
    "settings": {
      "index.mode": "time_series",
      "index.routing_path": [
        "metricset.name",
        "event.dataset",
        "service.address",
        "autoops_es.cluster.id"
      ]
    }
  },
  "_meta": {
    "description": "TSDS template for derived EDOT autoops metrics",
    "managed": false
  }
}
JSON

curl -sk -u "elastic:${MONITORING_ELASTIC_PASSWORD}" \
  -H 'Content-Type: application/json' \
  -X PUT "${MONITORING_ES_URL}/_component_template/metrics-elasticsearch.autoops@custom" \
  -d "${COMPONENT_TEMPLATE}" >/dev/null

curl -sk -u "elastic:${MONITORING_ELASTIC_PASSWORD}" \
  -H 'Content-Type: application/json' \
  -X PUT "${MONITORING_ES_URL}/_index_template/metrics-elasticsearch.autoops" \
  -d "${INDEX_TEMPLATE}" >/dev/null

if [[ "${RESET_AUTOOPS_TSDS:-false}" == "true" ]]; then
  curl -sk -u "elastic:${MONITORING_ELASTIC_PASSWORD}" \
    -X DELETE "${MONITORING_ES_URL}/_data_stream/metrics-elasticsearch.autoops-main" >/dev/null || true
fi

echo "Installed TSDS template assets for metrics-elasticsearch.autoops-*"
