#!/usr/bin/env python3
"""Kibana NDJSON for the 'Elastic Agent' Elasticsearch monitoring dashboards.

On Elastic Observability Serverless with Managed OTLP, projects often have only
`metrics-elasticsearch.stack_monitoring.otel-main` (elasticsearchreceiver). The legacy
Agent bundle targeted Integration `cluster_stats` / `node_stats` streams and excluded
otel-main, so every panel was empty.

This script **reuses** `build_otel_contrib_dashboard_ndjson.build_objects()` and remaps
saved object IDs to the `otel-agent-*` / `otel-elasticsearch-monitoring-agent*` namespace.
Lens definitions, data view title (`otel-main`), and Serverless-safe field paths match Contrib.

Constants below are the post-remap ids (for docs and greps).
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent

DATA_VIEW_ID = "otel-elasticsearch-agent-metrics-main"
DASHBOARD_ID = "otel-elasticsearch-monitoring-agent"
NODES_DASHBOARD_ID = "otel-elasticsearch-monitoring-agent-nodes"
INDICES_DASHBOARD_ID = "otel-elasticsearch-monitoring-agent-indices"
LINKS_ID = "otel-elasticsearch-monitoring-agent-links"

# Longest id prefixes first.
_REPLACEMENTS: list[tuple[str, str]] = [
    ("otel-elasticsearch-monitoring-contrib-indices", INDICES_DASHBOARD_ID),
    ("otel-elasticsearch-monitoring-contrib-nodes", NODES_DASHBOARD_ID),
    ("otel-elasticsearch-monitoring-contrib-links", LINKS_ID),
    ("otel-elasticsearch-contrib-metrics-main", DATA_VIEW_ID),
    ("otel-elasticsearch-monitoring-contrib", DASHBOARD_ID),
    ("otel-contrib-", "otel-agent-"),
]


def _load_contrib_builder():
    path = Path(__file__).resolve().parent / "build_otel_contrib_dashboard_ndjson.py"
    spec = importlib.util.spec_from_file_location("_contrib_dashboard_builder", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def _patch_dashboard_markdown(dashboard: dict) -> None:
    """Rewrite markdown inside panelsJSON (nested JSON, literal newlines)."""
    attr = dashboard.get("attributes") or {}
    raw = attr.get("panelsJSON")
    if not raw:
        return
    panels = json.loads(raw)
    if isinstance(panels, dict):
        panel_iter = panels.values()
    elif isinstance(panels, list):
        panel_iter = panels
    else:
        return
    md_replacements = (
        ("## Elasticsearch OTEL contrib overview\n", "## Elasticsearch monitoring overview\n"),
        ("## Elasticsearch OTEL contrib nodes\n", "## Elasticsearch monitoring nodes\n"),
        ("## Elasticsearch OTEL contrib indices\n", "## Elasticsearch monitoring indices\n"),
    )
    for panel in panel_iter:
        params = (panel.get("embeddableConfig") or {}).get("savedVis", {}).get("params")
        if not isinstance(params, dict):
            continue
        md = params.get("markdown")
        if not isinstance(md, str):
            continue
        for old, new in md_replacements:
            md = md.replace(old, new)
        params["markdown"] = md
    attr["panelsJSON"] = json.dumps(panels)


def _remap_object(obj: dict) -> dict:
    s = json.dumps(obj, separators=(",", ":"))
    for old, new in _REPLACEMENTS:
        s = s.replace(old, new)
    s = s.replace("Elasticsearch OTEL contrib navigation", "Elasticsearch monitoring navigation")
    s = s.replace("Contrib Header", "Monitoring header")
    s = s.replace(
        "Elasticsearch OTEL monitoring for metrics-elasticsearch.stack_monitoring.otel-main",
        "Elasticsearch monitoring - Elastic Agent overview",
    )
    s = s.replace(
        "Elasticsearch OTEL monitoring - Contrib Nodes",
        "Elasticsearch monitoring - Elastic Agent nodes",
    )
    s = s.replace(
        "Elasticsearch OTEL monitoring - Contrib Indices",
        "Elasticsearch monitoring - Elastic Agent indices",
    )
    s = s.replace(
        "Overview dashboard for the OTEL contrib elasticsearchreceiver metrics stream.",
        "OTLP elasticsearchreceiver metrics (otel-main). Same Lens definitions as Contrib dashboards; different saved object IDs.",
    )
    s = s.replace(
        "Node dashboard for the OTEL contrib elasticsearchreceiver metrics stream.",
        "OTLP node metrics for elasticsearchreceiver (otel-main).",
    )
    s = s.replace(
        "Index dashboard for the OTEL contrib elasticsearchreceiver metrics stream.",
        "OTLP index metrics for elasticsearchreceiver (otel-main).",
    )
    out = json.loads(s)
    if out.get("type") == "dashboard":
        _patch_dashboard_markdown(out)
    return out


def build_objects() -> list[dict]:
    contrib = _load_contrib_builder()
    return [_remap_object(dict(o)) for o in contrib.build_objects()]


def main():
    out_dir = _REPO_ROOT / "dashboards"
    out_dir.mkdir(parents=True, exist_ok=True)
    objects = build_objects()

    ndjson_path = out_dir / "elasticsearch-otel-monitoring-agent.ndjson"
    export_json_path = out_dir / "elasticsearch-otel-monitoring-agent.export.json"

    with ndjson_path.open("w", encoding="utf-8") as fh:
        for obj in objects:
            fh.write(json.dumps(obj, separators=(",", ":")) + "\n")

    with export_json_path.open("w", encoding="utf-8") as fh:
        json.dump(
            {
                "description": (
                    "Elastic Agent–branded Elasticsearch monitoring dashboards. For Serverless OTLP "
                    "(otel-main), this bundle mirrors Contrib Lens panels under different saved object IDs. "
                    "Convert to NDJSON for Kibana import."
                ),
                "objects": objects,
            },
            fh,
            indent=2,
        )
        fh.write("\n")


if __name__ == "__main__":
    main()
