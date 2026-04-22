#!/usr/bin/env python3

import base64
import json
import os
import random
import socket
import ssl
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone


ES_URL = os.environ["ES_URL"].rstrip("/")
ES_USERNAME = os.environ["ES_USERNAME"]
ES_PASSWORD = os.environ["ES_PASSWORD"]
ES_CA_FILE = os.getenv("ES_CA_FILE")
STREAM_PREFIX = os.getenv("STREAM_PREFIX", "logs-sampleapp")
STREAM_NAMESPACE = os.getenv("STREAM_NAMESPACE", "default")
STREAM_COUNT = int(os.getenv("STREAM_COUNT", "5"))
WRITE_BATCH_SIZE = int(os.getenv("WRITE_BATCH_SIZE", "75"))
SEARCHES_PER_CYCLE = int(os.getenv("SEARCHES_PER_CYCLE", "6"))
SLEEP_SECONDS = float(os.getenv("SLEEP_SECONDS", "5"))
NUMBER_OF_SHARDS = int(os.getenv("NUMBER_OF_SHARDS", "1"))
NUMBER_OF_REPLICAS = int(os.getenv("NUMBER_OF_REPLICAS", "0"))
QUERY_SIZE = int(os.getenv("QUERY_SIZE", "5"))

STREAMS = [f"{STREAM_PREFIX}-{index:02d}-{STREAM_NAMESPACE}" for index in range(1, STREAM_COUNT + 1)]
SERVICE_NAMES = ["catalog", "checkout", "inventory", "billing", "search"]
LEVELS = ["INFO", "WARN", "ERROR"]
METHODS = ["GET", "POST", "PUT"]
WORDS = [
    "alpha",
    "bravo",
    "charlie",
    "delta",
    "echo",
    "foxtrot",
    "golf",
    "hotel",
    "india",
    "juliet",
    "kilo",
    "lima",
    "mike",
    "november",
]


def make_ssl_context():
    if ES_CA_FILE:
        return ssl.create_default_context(cafile=ES_CA_FILE)
    return ssl._create_unverified_context()


SSL_CONTEXT = make_ssl_context()


def request(method, path, body=None, content_type="application/json"):
    url = f"{ES_URL}{path}"
    headers = {"Content-Type": content_type}
    if body is not None and not isinstance(body, (bytes, bytearray)):
        body = json.dumps(body).encode("utf-8")

    req = urllib.request.Request(url, data=body, method=method, headers=headers)
    creds = f"{ES_USERNAME}:{ES_PASSWORD}".encode("utf-8")
    req.add_header("Authorization", f"Basic {base64.b64encode(creds).decode('ascii')}")

    try:
        with urllib.request.urlopen(req, context=SSL_CONTEXT, timeout=30) as response:
            payload = response.read().decode("utf-8")
            if not payload:
                return {}
            return json.loads(payload)
    except urllib.error.HTTPError as exc:
        payload = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {url} failed with HTTP {exc.code}: {payload}") from exc


def ensure_template():
    template = {
        "index_patterns": [f"{STREAM_PREFIX}-*-{STREAM_NAMESPACE}"],
        "data_stream": {},
        "priority": 250,
        "template": {
            "settings": {
                "index.mode": "logsdb",
                "index.number_of_shards": NUMBER_OF_SHARDS,
                "index.number_of_replicas": NUMBER_OF_REPLICAS,
            },
            "mappings": {
                "properties": {
                    "@timestamp": {"type": "date"},
                    "message": {"type": "text"},
                    "service": {"properties": {"name": {"type": "keyword"}}},
                    "event": {
                        "properties": {
                            "dataset": {"type": "keyword"},
                            "severity": {"type": "keyword"},
                        }
                    },
                    "http": {
                        "properties": {
                            "request": {"properties": {"method": {"type": "keyword"}}},
                            "response": {"properties": {"status_code": {"type": "integer"}}},
                        }
                    },
                    "user": {"properties": {"id": {"type": "keyword"}}},
                    "labels": {
                        "properties": {
                            "tenant": {"type": "keyword"},
                            "region": {"type": "keyword"},
                            "workflow": {"type": "keyword"},
                        }
                    },
                }
            },
        },
        "_meta": {
            "description": "Logsdb template for synthetic main-cluster search/write load",
            "managed": False,
        },
    }
    request("PUT", f"/_index_template/{STREAM_PREFIX}-logsdb", template)


def bulk_write():
    lines = []
    for index in range(WRITE_BATCH_SIZE):
        stream = STREAMS[index % len(STREAMS)]
        service = SERVICE_NAMES[index % len(SERVICE_NAMES)]
        term = random.choice(WORDS)
        level = random.choice(LEVELS)
        method = random.choice(METHODS)
        status = random.choice([200, 200, 201, 202, 404, 500])
        doc = {
            "@timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "message": f"{service} handled {term} request {index}",
            "service": {"name": service},
            "event": {"dataset": f"{service}.app", "severity": level},
            "http": {"request": {"method": method}, "response": {"status_code": status}},
            "user": {"id": f"user-{random.randint(1, 50):03d}"},
            "labels": {
                "tenant": f"tenant-{random.randint(1, 8)}",
                "region": random.choice(["us-west", "us-east", "eu-west"]),
                "workflow": random.choice(["browse", "checkout", "reindex", "report"]),
            },
            "host": {"name": socket.gethostname()},
        }
        lines.append(json.dumps({"create": {"_index": stream}}))
        lines.append(json.dumps(doc, separators=(",", ":")))

    payload = ("\n".join(lines) + "\n").encode("utf-8")
    response = request("POST", "/_bulk", payload, content_type="application/x-ndjson")
    failures = [item for item in response.get("items", []) if item.get("create", {}).get("status", 500) >= 300]
    if failures:
        raise RuntimeError(f"bulk write failed: {json.dumps(failures[:3])}")


def search_once():
    stream = random.choice(STREAMS)
    service = random.choice(SERVICE_NAMES)
    term = random.choice(WORDS)
    body = {
        "size": 5,
        "size": QUERY_SIZE,
        "track_total_hits": True,
        "query": {
            "bool": {
                "filter": [
                    {"term": {"service.name": service}},
                    {"range": {"@timestamp": {"gte": "now-15m"}}},
                ],
                "must": [
                    {"match": {"message": term}},
                ],
            }
        },
        "sort": [{"@timestamp": {"order": "desc"}}],
    }
    request("POST", f"/{stream}/_search", body)


def main():
    ensure_template()
    cycle = 0
    while True:
        cycle += 1
        bulk_write()
        for _ in range(SEARCHES_PER_CYCLE):
            search_once()
        print(
            json.dumps(
                {
                    "cycle": cycle,
                    "streams": STREAMS,
                    "writes": WRITE_BATCH_SIZE,
                    "searches": SEARCHES_PER_CYCLE,
                    "number_of_shards": NUMBER_OF_SHARDS,
                    "number_of_replicas": NUMBER_OF_REPLICAS,
                    "query_size": QUERY_SIZE,
                }
            ),
            flush=True,
        )
        time.sleep(SLEEP_SECONDS)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        raise
