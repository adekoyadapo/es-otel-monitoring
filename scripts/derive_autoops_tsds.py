#!/usr/bin/env python3

import base64
import json
import os
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone


SOURCE_DATASTREAM = os.getenv("SOURCE_DATASTREAM", "logs-elasticsearch.metrics-main")
DEST_DATASTREAM = os.getenv("DEST_DATASTREAM", "metrics-elasticsearch.autoops-main")
LOOKBACK_MINUTES = int(os.getenv("LOOKBACK_MINUTES", "15"))
QUERY_SIZE = int(os.getenv("QUERY_SIZE", "2000"))

CLUSTER_HEALTH_FIELDS = [
    "active_primary_shards",
    "active_shards_percent_as_number",
    "delayed_unassigned_shards",
    "initializing_shards",
    "number_of_data_nodes",
    "number_of_nodes",
    "number_of_pending_tasks",
    "relocating_shards",
    "status",
    "unassigned_shards",
]

NODE_STATS_FIELDS = [
    "search_rate_per_second",
    "index_rate_per_second",
    "search_latency_in_millis",
    "index_latency_in_millis",
    "index_failed_rate_per_second",
    "merge_rate_per_second",
    "merge_latency_in_millis",
    "jvm.mem.heap_used_in_bytes",
    "jvm.mem.heap_max_in_bytes",
    "jvm.mem.heap_used_percent",
    "jvm.gc.collectors.young.collection_time_in_millis",
    "jvm.gc.collectors.young.collection_count",
    "jvm.gc.collectors.old.collection_time_in_millis",
    "jvm.gc.collectors.old.collection_count",
    "http.current_open",
    "http.total_opened",
    "process.cpu.percent",
    "process.open_file_descriptors",
    "process.max_file_descriptors",
    "os.mem.used_in_bytes",
    "os.mem.total_in_bytes",
    "os.cpu.load_average.1m",
    "os.cpu.load_average.5m",
    "os.cpu.load_average.15m",
    "fs.total.available_in_bytes",
    "fs.total.free_in_bytes",
    "fs.total.total_in_bytes",
    "thread_pool.search.queue",
    "thread_pool.write.queue",
    "thread_pool.search.rejected",
    "thread_pool.write.rejected",
    "breakers.parent.tripped",
    "breakers.request.tripped",
    "indices.docs.count",
    "indices.store.size_in_bytes",
    "indices.store.total_data_set_size_in_bytes",
    "indices.segments.count",
    "indices.segments.memory_in_bytes",
    "indices.query_cache.hit_count",
    "indices.query_cache.miss_count",
    "indices.query_cache.evictions",
    "indices.request_cache.hit_count",
    "indices.request_cache.miss_count",
    "indices.request_cache.evictions",
]

CAT_SHARDS_FIELDS = [
    "shards_count",
    "primary_shards",
    "replica_shards",
    "initializing_shards",
    "relocating_shards",
]

NODE_INDEX_SHARDS_FIELDS = [
    "index",
    "index_type",
    "index_status",
    "total_size_in_bytes",
    "size_in_bytes",
    "max_shard_size_in_bytes",
    "min_shard_size_in_bytes",
    "docs_count",
    "segments_count",
    "primary_shards_count",
    "replica_shards_count",
    "unassigned_shards_count",
    "relocating_shards_count",
    "initializing_shards_count",
    "search_rate_per_second",
    "index_rate_per_second",
    "search_latency_in_millis",
    "index_latency_in_millis",
    "index_failed_rate_per_second",
]


def log(message):
    print(message, file=sys.stderr)


def make_ssl_context():
    ca_file = os.getenv("ES_CA_FILE")
    verify = os.getenv("ES_VERIFY", "true").lower() not in {"0", "false", "no"}
    if not verify:
        return ssl._create_unverified_context()
    if ca_file:
        return ssl.create_default_context(cafile=ca_file)
    return ssl.create_default_context()


SSL_CONTEXT = make_ssl_context()


def request(method, path, body=None, headers=None):
    base = os.environ["ES_URL"].rstrip("/")
    url = f"{base}{path}"
    data = None
    req_headers = {"Content-Type": "application/json"}
    if headers:
        req_headers.update(headers)
    if body is not None:
        if isinstance(body, (dict, list)):
            data = json.dumps(body).encode("utf-8")
        elif isinstance(body, str):
            data = body.encode("utf-8")
        else:
            data = body

    request_obj = urllib.request.Request(url, data=data, method=method, headers=req_headers)
    username = os.environ["ES_USERNAME"]
    password = os.environ["ES_PASSWORD"]
    creds = f"{username}:{password}".encode("utf-8")
    request_obj.add_header("Authorization", f"Basic {base64.b64encode(creds).decode('ascii')}")

    try:
        with urllib.request.urlopen(request_obj, context=SSL_CONTEXT) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        payload = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {url} failed with HTTP {exc.code}: {payload}") from exc


def get_path(data, path):
    current = data
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def set_path(data, path, value):
    current = data
    parts = path.split(".")
    for part in parts[:-1]:
        current = current.setdefault(part, {})
    current[parts[-1]] = value


def copy_selected(source, destination, paths):
    copied = 0
    for path in paths:
        value = get_path(source, path)
        if value is None:
            continue
        set_path(destination, path, value)
        copied += 1
    return copied


def base_doc(source):
    autoops_cluster = get_path(source, "autoops_es.cluster") or {}
    return {
        "@timestamp": source["@timestamp"],
        "event": {
            "dataset": get_path(source, "event.dataset"),
            "kind": get_path(source, "event.kind"),
            "module": get_path(source, "event.module"),
        },
        "metricset": {
            "name": get_path(source, "metricset.name"),
        },
        "host": {
            "name": get_path(source, "host.name"),
        },
        "service": {
            "address": get_path(source, "service.address"),
            "type": get_path(source, "service.type"),
        },
        "autoops_es": {
            "cluster": {
                "id": autoops_cluster.get("id"),
                "name": autoops_cluster.get("name"),
                "version": autoops_cluster.get("version"),
            }
        },
    }


def cluster_health_doc(source):
    cluster_health = get_path(source, "autoops_es.cluster_health")
    if not isinstance(cluster_health, dict):
        return None
    doc = base_doc(source)
    copied = copy_selected({"autoops_es": {"cluster_health": cluster_health}}, doc, [f"autoops_es.cluster_health.{f}" for f in CLUSTER_HEALTH_FIELDS])
    return doc if copied else None


def node_stats_doc(source):
    node_stats = get_path(source, "autoops_es.node_stats")
    if not isinstance(node_stats, dict):
        return None
    doc = base_doc(source)
    copied = 0
    for path in ["name", "id"]:
        value = node_stats.get(path)
        if value is not None:
            set_path(doc, f"autoops_es.node_stats.{path}", value)
            copied += 1
    copied += copy_selected({"autoops_es": {"node_stats": node_stats}}, doc, [f"autoops_es.node_stats.{f}" for f in NODE_STATS_FIELDS])
    return doc if copied else None


def cat_shards_docs(source):
    docs = []

    node_counts = get_path(source, "autoops_es.cat_shards.node_shards_count")
    if isinstance(node_counts, list):
        for node_count in node_counts:
            if not isinstance(node_count, dict):
                continue
            doc = base_doc(source)
            copied = 0
            for path in ["node_id", "node_name"]:
                value = node_count.get(path)
                if value is not None:
                    set_path(doc, f"autoops_es.cat_shards.node_shards_count.{path}", value)
                    copied += 1
            copied += copy_selected(
                {"autoops_es": {"cat_shards": {"node_shards_count": node_count}}},
                doc,
                [f"autoops_es.cat_shards.node_shards_count.{f}" for f in CAT_SHARDS_FIELDS],
            )
            if copied:
                docs.append(doc)

    index_shards = get_path(source, "autoops_es.cat_shards.node_index_shards")
    if isinstance(index_shards, list):
        for shard_info in index_shards:
            if not isinstance(shard_info, dict):
                continue
            doc = base_doc(source)
            copied = 0
            for path in ["node_id", "node_name", "index", "index_type", "index_status"]:
                value = shard_info.get(path)
                if value is not None:
                    set_path(doc, f"autoops_es.cat_shards.node_index_shards.{path}", value)
                    copied += 1
            copied += copy_selected(
                {"autoops_es": {"cat_shards": {"node_index_shards": shard_info}}},
                doc,
                [f"autoops_es.cat_shards.node_index_shards.{f}" for f in NODE_INDEX_SHARDS_FIELDS],
            )
            if copied:
                docs.append(doc)
    return docs


def transform_source_doc(source):
    metricset = get_path(source, "metricset.name")
    if metricset == "cluster_health":
        doc = cluster_health_doc(source)
        return [doc] if doc else []
    if metricset == "node_stats":
        doc = node_stats_doc(source)
        return [doc] if doc else []
    if metricset == "cat_shards":
        return cat_shards_docs(source)
    return []


def search_source_docs():
    start = datetime.now(timezone.utc) - timedelta(minutes=LOOKBACK_MINUTES)
    start_iso = start.isoformat(timespec="seconds").replace("+00:00", "Z")
    body = {
        "size": QUERY_SIZE,
        "sort": [{"@timestamp": {"order": "asc"}}],
        "_source": True,
        "query": {
            "bool": {
                "filter": [
                    {"range": {"@timestamp": {"gte": start_iso}}},
                    {"terms": {"metricset.name": ["cluster_health", "node_stats", "cat_shards"]}},
                ]
            }
        },
    }
    response = request("POST", f"/{urllib.parse.quote(SOURCE_DATASTREAM, safe='')}/_search", body=body)
    return [hit["_source"] for hit in response.get("hits", {}).get("hits", []) if "_source" in hit]


def bulk_index(docs):
    if not docs:
        return {"indexed": 0, "duplicates": 0, "errors": []}

    lines = []
    for doc in docs:
        lines.append(json.dumps({"create": {}}))
        lines.append(json.dumps(doc, separators=(",", ":")))
    body = "\n".join(lines) + "\n"
    response = request(
        "POST",
        f"/{urllib.parse.quote(DEST_DATASTREAM, safe='')}/_bulk",
        body=body.encode("utf-8"),
        headers={"Content-Type": "application/x-ndjson"},
    )

    errors = []
    indexed = 0
    duplicates = 0
    for item in response.get("items", []):
        create = item.get("create", {})
        status = create.get("status", 500)
        if 200 <= status < 300:
            indexed += 1
            continue
        if status == 409 and create.get("error", {}).get("type") == "version_conflict_engine_exception":
            # TSDS derives the backing _id from dimensions and timestamp, so overlapping
            # CronJob runs naturally retry some points that are already present.
            duplicates += 1
            continue
        errors.append(
            {
                "status": status,
                "type": create.get("error", {}).get("type"),
                "reason": create.get("error", {}).get("reason"),
            }
        )
    return {"indexed": indexed, "duplicates": duplicates, "errors": errors}


def main():
    source_docs = search_source_docs()
    derived_docs = []
    metricset_counts = {}
    for source_doc in source_docs:
        docs = transform_source_doc(source_doc)
        derived_docs.extend(docs)
        metricset = get_path(source_doc, "metricset.name") or "unknown"
        metricset_counts[metricset] = metricset_counts.get(metricset, 0) + len(docs)

    result = bulk_index(derived_docs)

    summary = {
        "source_docs": len(source_docs),
        "derived_docs": len(derived_docs),
        "indexed_docs": result["indexed"],
        "duplicate_docs": result["duplicates"],
        "metricsets": metricset_counts,
    }
    print(json.dumps(summary, sort_keys=True))

    if result["errors"]:
        for error in result["errors"][:5]:
            log(json.dumps(error, sort_keys=True))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
