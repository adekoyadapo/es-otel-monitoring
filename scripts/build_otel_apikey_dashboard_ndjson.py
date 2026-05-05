#!/usr/bin/env python3
# Dashboard for API key-authenticated Elasticsearch monitoring via elasticsearchreceiver.
# Metric names and resource attribute paths match the upstream OTEL elasticsearchreceiver
# (same as the contrib monitoring mode).  The API key-specific part is only the auth path:
# the receiver talks to a local source cluster instead of directly to Elasticsearch.

import json
from pathlib import Path


DATA_VIEW_ID = "otel-elasticsearch-apikey-native-main"
DATA_VIEW_TITLE = "metrics-elasticsearch.stack_monitoring.otel-main"
DASHBOARD_ID = "otel-elasticsearch-monitoring-apikey"
NODES_DASHBOARD_ID = "otel-elasticsearch-monitoring-apikey-nodes"
INDICES_DASHBOARD_ID = "otel-elasticsearch-monitoring-apikey-indices"
LINKS_ID = "otel-elasticsearch-monitoring-apikey-links"

LENS_EXPORT_META = {
    "coreMigrationVersion": "8.8.0",
    "created_at": "2026-05-03T00:00:00.000Z",
    "created_by": "elastic",
    "managed": False,
    "typeMigrationVersion": "10.1.0",
    "updated_at": "2026-05-03T00:00:00.000Z",
    "updated_by": "elastic",
    "version": "WzEsMV0=",
}

# Resource attribute paths set by the elasticsearchreceiver
_CLUSTER = "resource.attributes.elasticsearch.cluster.name"
_NODE    = "resource.attributes.elasticsearch.node.name"
_INDEX   = "resource.attributes.elasticsearch.index.name"

# Metric field prefix in OTEL mapping mode
def _m(name): return f"metrics.{name}"


def metric_lens(lens_id, title, field, filter_query, operation="last_value", params=None, breakdown=False):
    layer_id = f"{lens_id}-layer"
    metric_id = f"{lens_id}-metric"
    breakdown_id = f"{lens_id}-breakdown"
    ref_name = f"indexpattern-datasource-layer-{layer_id}"

    default_params = {"emptyAsNull": True} if operation in ("unique_count", "count") else {"sortField": "@timestamp"}
    metric_col = {
        "customLabel": True,
        "dataType": "number",
        "filter": {"language": "kuery", "query": filter_query},
        "isBucketed": False,
        "label": title,
        "operationType": operation,
        "params": params if params is not None else default_params,
        "scale": "ratio",
        "sourceField": field,
    }

    if breakdown:
        column_order = [breakdown_id, metric_id]
        columns = {
            breakdown_id: {
                "customLabel": True,
                "dataType": "string",
                "isBucketed": True,
                "label": "Cluster",
                "operationType": "terms",
                "params": {
                    "exclude": [], "excludeIsRegex": False,
                    "include": [], "includeIsRegex": False,
                    "missingBucket": False,
                    "orderBy": {"type": "alphabetical"},
                    "orderDirection": "asc",
                    "otherBucket": False,
                    "parentFormat": {"id": "terms"},
                    "size": 10,
                },
                "scale": "ordinal",
                "sourceField": _CLUSTER,
            },
            metric_id: metric_col,
        }
    else:
        column_order = [metric_id]
        columns = {metric_id: metric_col}

    visualization = {
        "accessor": metric_id,
        "colorMode": "Labels",
        "layerId": layer_id,
        "layerType": "data",
        "size": "xl",
        "textAlign": "center",
        "titlePosition": "top",
    }
    if breakdown:
        visualization["breakdownAccessor"] = breakdown_id

    obj = {
        "type": "lens",
        "id": lens_id,
        "attributes": {
            "description": "",
            "title": title,
            "visualizationType": "lnsLegacyMetric",
            "state": {
                "adHocDataViews": {},
                "datasourceStates": {
                    "formBased": {
                        "currentIndexPatternId": DATA_VIEW_ID,
                        "layers": {
                            layer_id: {
                                "columnOrder": column_order,
                                "columns": columns,
                                "incompleteColumns": {},
                                "indexPatternId": DATA_VIEW_ID,
                                "sampling": 1,
                            }
                        },
                    },
                    "indexpattern": {"layers": {}},
                    "textBased": {"layers": {}},
                },
                "filters": [],
                "internalReferences": [],
                "query": {"language": "kuery", "query": ""},
                "visualization": visualization,
            },
        },
        "references": [{"id": DATA_VIEW_ID, "name": ref_name, "type": "index-pattern"}],
    }
    obj.update(LENS_EXPORT_META)
    return obj


def xy_lens(lens_id, title, field, filter_query, operation, color):
    layer_id = f"{lens_id}-layer"
    date_id = f"{lens_id}-date"
    cluster_id = f"{lens_id}-cluster"
    metric_id = f"{lens_id}-metric"
    ref_name = f"indexpattern-datasource-layer-{layer_id}"
    obj = {
        "type": "lens",
        "id": lens_id,
        "attributes": {
            "description": "",
            "title": title,
            "visualizationType": "lnsXY",
            "state": {
                "adHocDataViews": {},
                "datasourceStates": {
                    "formBased": {
                        "currentIndexPatternId": DATA_VIEW_ID,
                        "layers": {
                            layer_id: {
                                "columnOrder": [date_id, cluster_id, metric_id],
                                "columns": {
                                    date_id: {
                                        "dataType": "date",
                                        "isBucketed": True,
                                        "label": "@timestamp",
                                        "operationType": "date_histogram",
                                        "params": {
                                            "dropPartials": True,
                                            "includeEmptyRows": True,
                                            "interval": "auto",
                                        },
                                        "scale": "interval",
                                        "sourceField": "@timestamp",
                                    },
                                    cluster_id: {
                                        "customLabel": True,
                                        "dataType": "string",
                                        "isBucketed": True,
                                        "label": "Cluster",
                                        "operationType": "terms",
                                        "params": {
                                            "exclude": [],
                                            "excludeIsRegex": False,
                                            "include": [],
                                            "includeIsRegex": False,
                                            "missingBucket": False,
                                            "orderBy": {"type": "alphabetical"},
                                            "orderDirection": "asc",
                                            "otherBucket": False,
                                            "parentFormat": {"id": "terms"},
                                            "size": 10,
                                        },
                                        "scale": "ordinal",
                                        "sourceField": _CLUSTER,
                                    },
                                    metric_id: {
                                        "customLabel": True,
                                        "dataType": "number",
                                        "filter": {"language": "kuery", "query": filter_query},
                                        "isBucketed": False,
                                        "label": title,
                                        "operationType": operation,
                                        "params": {"emptyAsNull": True},
                                        "scale": "ratio",
                                        "sourceField": field,
                                    },
                                },
                                "incompleteColumns": {},
                                "indexPatternId": DATA_VIEW_ID,
                                "sampling": 1,
                            }
                        },
                    },
                    "indexpattern": {"layers": {}},
                    "textBased": {"layers": {}},
                },
                "filters": [],
                "internalReferences": [],
                "query": {"language": "kuery", "query": ""},
                "visualization": {
                    "axisTitlesVisibilitySettings": {"x": False, "yLeft": False, "yRight": True},
                    "fittingFunction": "None",
                    "gridlinesVisibilitySettings": {"x": False, "yLeft": True, "yRight": True},
                    "labelsOrientation": {"x": 0, "yLeft": 0, "yRight": 0},
                    "layers": [
                        {
                            "accessors": [metric_id],
                            "layerId": layer_id,
                            "layerType": "data",
                            "position": "top",
                            "seriesType": "line",
                            "showGridlines": False,
                            "splitAccessor": cluster_id,
                            "xAccessor": date_id,
                        }
                    ],
                    "legend": {"isVisible": True, "legendSize": "auto", "position": "right"},
                    "preferredSeriesType": "line",
                    "tickLabelsVisibilitySettings": {"x": True, "yLeft": True, "yRight": True},
                    "valueLabels": "hide",
                    "yLeftExtent": {"mode": "dataBounds"},
                    "yRightExtent": {"mode": "full"},
                },
            },
        },
        "references": [{"id": DATA_VIEW_ID, "name": ref_name, "type": "index-pattern"}],
    }
    obj.update(LENS_EXPORT_META)
    return obj


def datatable_lens(lens_id, title, row_field, row_label, row_size, metric_specs, row_exclude=None, row_filter=None):
    layer_id = f"{lens_id}-layer"
    row_id = f"{lens_id}-row"
    count_id = f"{lens_id}-count"
    columns = {
        row_id: {
            "customLabel": True,
            "dataType": "string",
            "isBucketed": True,
            "label": row_label,
            "operationType": "terms",
            "params": {
                "exclude": row_exclude or [],
                "excludeIsRegex": False,
                "include": [],
                "includeIsRegex": False,
                "missingBucket": False,
                "orderBy": {"columnId": count_id, "type": "column"},
                "orderDirection": "desc",
                "otherBucket": True,
                "parentFormat": {"id": "terms"},
                "size": row_size,
            },
            "scale": "ordinal",
            "sourceField": row_field,
        },
        count_id: {
            "dataType": "number",
            "isBucketed": False,
            "label": "Count of records",
            "operationType": "count",
            "params": {"emptyAsNull": True},
            "scale": "ratio",
            "sourceField": "___records___",
        },
    }
    column_order = [row_id, count_id]
    vis_columns = [
        {"alignment": "left", "columnId": row_id, "isTransposed": False, "oneClickFilter": True, "width": 240},
        {"columnId": count_id, "hidden": True, "isMetric": True, "isTransposed": False},
    ]
    for spec in metric_specs:
        metric_id = spec["id"]
        col = {
            "customLabel": True,
            "dataType": spec.get("data_type", "number"),
            "isBucketed": False,
            "label": spec["label"],
            "operationType": spec["operation"],
            "scale": spec.get("scale", "ratio"),
            "sourceField": spec["field"],
        }
        if "filter" in spec:
            col["filter"] = {"language": "kuery", "query": spec["filter"]}
        if "params" in spec:
            col["params"] = spec["params"]
        columns[metric_id] = col
        column_order.append(metric_id)
        vis_columns.append({"columnId": metric_id, "isMetric": True, "isTransposed": False, "width": spec.get("width", 110)})

    obj = {
        "type": "lens",
        "id": lens_id,
        "attributes": {
            "description": "",
            "title": title,
            "visualizationType": "lnsDatatable",
            "state": {
                "adHocDataViews": {},
                "datasourceStates": {
                    "formBased": {
                        "currentIndexPatternId": DATA_VIEW_ID,
                        "layers": {
                            layer_id: {
                                "columnOrder": column_order,
                                "columns": columns,
                                "incompleteColumns": {},
                                "indexPatternId": DATA_VIEW_ID,
                                "sampling": 1,
                            }
                        },
                    },
                    "indexpattern": {"layers": {}},
                    "textBased": {"layers": {}},
                },
                "filters": [],
                "internalReferences": [],
                "query": {"language": "kuery", "query": row_filter or ""},
                "visualization": {"columns": vis_columns, "layerId": layer_id, "layerType": "data"},
            },
        },
        "references": [{"id": DATA_VIEW_ID, "name": f"indexpattern-datasource-layer-{layer_id}", "type": "index-pattern"}],
    }
    obj.update(LENS_EXPORT_META)
    return obj


def dashboard_panel_ref(panel_id, title, x, y, w, h, lens_id):
    return {
        "type": "lens",
        "panelRefName": f"panel_{panel_id}",
        "panelIndex": panel_id,
        "title": title,
        "gridData": {"i": panel_id, "x": x, "y": y, "w": w, "h": h},
        "embeddableConfig": {
            "enhancements": {"dynamicActions": {"events": []}},
            "filters": [],
            "hidePanelTitles": False,
            "query": {"language": "kuery", "query": ""},
            "savedObjectId": lens_id,
            "syncColors": False,
            "syncCursor": True,
            "syncTooltips": False,
            "title": title,
        },
    }


def links_panel_ref(panel_id, title, x, y, w, h, links_id):
    return {
        "type": "links",
        "panelRefName": f"panel_{panel_id}",
        "panelIndex": panel_id,
        "title": title,
        "gridData": {"i": panel_id, "x": x, "y": y, "w": w, "h": h},
        "embeddableConfig": {"enhancements": {}, "savedObjectId": links_id, "title": title},
    }


def links_saved_object():
    links = []
    references = []
    specs = [
        ("Overview", DASHBOARD_ID, 0),
        ("Nodes", NODES_DASHBOARD_ID, 1),
        ("Indices", INDICES_DASHBOARD_ID, 2),
    ]
    for label, dash_id, order in specs:
        link_id = f"otel-apikey-link-{label.lower()}"
        ref_name = f"link_{link_id}_dashboard"
        links.append({
            "destinationRefName": ref_name,
            "id": link_id,
            "label": label,
            "options": {"openInNewTab": False, "useCurrentDateRange": True, "useCurrentFilters": True},
            "order": order,
            "type": "dashboardLink",
        })
        references.append({"id": dash_id, "name": ref_name, "type": "dashboard"})
    return {
        "type": "links",
        "id": LINKS_ID,
        "attributes": {
            "description": "",
            "layout": "horizontal",
            "links": links,
            "title": "Elasticsearch API key monitoring navigation",
        },
        "references": references,
        "managed": False,
    }


def dashboard_references(panels):
    refs = []
    for panel in panels:
        if "panelRefName" not in panel:
            continue
        refs.append({
            "id": panel["embeddableConfig"]["savedObjectId"],
            "name": f"{panel['panelIndex']}:{panel['panelRefName']}",
            "type": panel["type"],
        })
    return refs


def control_group_and_references():
    specs = [
        ("cluster", _CLUSTER, "Cluster Name(s)", "medium", False),
        ("node",    _NODE,    "Node(s)",          "medium", True),
        ("index",   _INDEX,   "Index(s)",         "large",  True),
    ]
    control_panels = {}
    references = []
    for order, (suffix, field_name, title, width, grow) in enumerate(specs):
        control_id = f"otel-apikey-control-{suffix}"
        control_panels[control_id] = {
            "explicitInput": {
                "dataViewId": DATA_VIEW_ID,
                "exclude": False,
                "existsSelected": False,
                "fieldName": field_name,
                "runPastTimeout": True,
                "searchTechnique": "wildcard",
                "selectedOptions": [],
                "sort": {"by": "_count", "direction": "desc"},
                "title": title,
            },
            "grow": grow,
            "order": order,
            "type": "optionsListControl",
            "width": width,
        }
        references.append({"id": DATA_VIEW_ID, "name": f"controlGroup_{control_id}:optionsListDataView", "type": "index-pattern"})
    return control_panels, references


def dashboard_object(dashboard_id, title, description, panels):
    control_panels, control_refs = control_group_and_references()
    references = dashboard_references(panels)
    references.extend(control_refs)
    return {
        "type": "dashboard",
        "id": dashboard_id,
        "attributes": {
            "controlGroupInput": {
                "chainingSystem": "HIERARCHICAL",
                "controlStyle": "oneLine",
                "ignoreParentSettingsJSON": json.dumps({"ignoreFilters": False, "ignoreQuery": False, "ignoreTimerange": False, "ignoreValidations": False}),
                "panelsJSON": json.dumps(control_panels),
                "showApplySelections": True,
            },
            "title": title,
            "description": description,
            "optionsJSON": json.dumps({"useMargins": True, "syncColors": False, "syncCursor": True, "syncTooltips": False, "hidePanelTitles": False}),
            "panelsJSON": json.dumps(panels),
            "timeRestore": False,
            "kibanaSavedObjectMeta": {"searchSourceJSON": json.dumps({"query": {"language": "kuery", "query": ""}, "filter": []})},
            "version": 1,
        },
        "references": references,
        "managed": False,
    }


def build_objects():
    # Field format map: byte and duration fields auto-format in Kibana tables
    field_format_map = {
        _m("jvm.memory.heap.used"): {"id": "bytes"},
        _m("jvm.memory.heap.max"):  {"id": "bytes"},
        _m("jvm.gc.collections.elapsed"): {
            "id": "duration",
            "params": {"inputFormat": "milliseconds", "outputFormat": "humanize", "outputPrecision": 2},
        },
        _m("elasticsearch.node.fs.disk.available"):    {"id": "bytes"},
        _m("elasticsearch.index.shards.size"):         {"id": "bytes"},
        _m("elasticsearch.node.shards.size"):          {"id": "bytes"},
        _m("elasticsearch.node.cache.memory.usage"):   {"id": "bytes"},
    }

    objects = [
        {
            "type": "index-pattern",
            "id": DATA_VIEW_ID,
            "attributes": {
                "title": DATA_VIEW_TITLE,
                "name": "otel-elasticsearch-apikey-native-main",
                "timeFieldName": "@timestamp",
                "fields": "[]",
                "fieldAttrs": "{}",
                "fieldFormatMap": json.dumps(field_format_map),
                "runtimeFieldMap": "{}",
                "sourceFilters": "[]",
                "allowHidden": False,
            },
        }
    ]

    lens_objects = [
        # ── Overview scalar tiles ─────────────────────────────────────────────
        # "Green" counts distinct clusters reporting green status
        metric_lens("otel-apikey-lens-green-health",   "Green",
            _CLUSTER,
            'attributes.status: "green" and metrics.elasticsearch.cluster.health:*',
            operation="unique_count"),
        # Per-cluster tiles for all count/gauge stats
        metric_lens("otel-apikey-lens-nodes",           "Nodes",
            _m("elasticsearch.cluster.nodes"),
            f"{_m('elasticsearch.cluster.nodes')}:*",
            breakdown=True),
        metric_lens("otel-apikey-lens-data-nodes",      "Data Nodes",
            _m("elasticsearch.cluster.data_nodes"),
            f"{_m('elasticsearch.cluster.data_nodes')}:*",
            breakdown=True),
        metric_lens("otel-apikey-lens-active-shards",   "Active Shards",
            _m("elasticsearch.cluster.shards"),
            'attributes.state: "active" and metrics.elasticsearch.cluster.shards:*',
            breakdown=True),
        metric_lens("otel-apikey-lens-primary-shards",  "Primary Shards",
            _m("elasticsearch.cluster.shards"),
            'attributes.state: "active_primary" and metrics.elasticsearch.cluster.shards:*',
            breakdown=True),
        metric_lens("otel-apikey-lens-unassigned",      "Unassigned",
            _m("elasticsearch.cluster.shards"),
            'attributes.state: "unassigned" and metrics.elasticsearch.cluster.shards:*',
            breakdown=True),
        metric_lens("otel-apikey-lens-pending-tasks",   "Pending Tasks",
            _m("elasticsearch.cluster.pending_tasks"),
            f"{_m('elasticsearch.cluster.pending_tasks')}:*",
            breakdown=True),
        metric_lens("otel-apikey-lens-req-breakers",    "Request Breakers",
            _m("elasticsearch.breaker.tripped"),
            'attributes.name: "request" and metrics.elasticsearch.breaker.tripped:*',
            operation="max", breakdown=True),
        metric_lens("otel-apikey-lens-parent-breakers", "Parent Breakers",
            _m("elasticsearch.breaker.tripped"),
            'attributes.name: "parent" and metrics.elasticsearch.breaker.tripped:*',
            operation="max", breakdown=True),
        metric_lens("otel-apikey-lens-ingest-failures", "Ingest Failures",
            _m("elasticsearch.node.ingest.operations.failed"),
            f"{_m('elasticsearch.node.ingest.operations.failed')}:*",
            operation="max", breakdown=True),
        # ── Overview time-series ──────────────────────────────────────────────
        xy_lens("otel-apikey-lens-query-rate",   "Query Ops Total",
            _m("elasticsearch.node.operations.completed"),
            'attributes.operation: "query" and metrics.elasticsearch.node.operations.completed:*',
            "max", "#348888"),
        xy_lens("otel-apikey-lens-fetch-rate",   "Fetch Ops Total",
            _m("elasticsearch.node.operations.completed"),
            'attributes.operation: "fetch" and metrics.elasticsearch.node.operations.completed:*',
            "max", "#4f86c6"),
        xy_lens("otel-apikey-lens-index-rate",   "Index Ops Total",
            _m("elasticsearch.node.operations.completed"),
            'attributes.operation: "index" and metrics.elasticsearch.node.operations.completed:*',
            "max", "#d17c2d"),
        xy_lens("otel-apikey-lens-refresh-rate", "Refresh Ops Total",
            _m("elasticsearch.node.operations.completed"),
            'attributes.operation: "refresh" and metrics.elasticsearch.node.operations.completed:*',
            "max", "#8e6db0"),
        # ── Node time-series ─────────────────────────────────────────────────
        xy_lens("otel-apikey-lens-heap-used",    "Heap Used",
            _m("jvm.memory.heap.used"),
            f"{_m('jvm.memory.heap.used')}:*",
            "average", "#2f9c95"),
        xy_lens("otel-apikey-lens-heap-max",     "Heap Max",
            _m("jvm.memory.heap.max"),
            f"{_m('jvm.memory.heap.max')}:*",
            "average", "#5f9ea0"),
        xy_lens("otel-apikey-lens-open-files",   "Open Files",
            _m("elasticsearch.node.open_files"),
            f"{_m('elasticsearch.node.open_files')}:*",
            "max", "#6a8caf"),
        xy_lens("otel-apikey-lens-disk-avail",   "Disk Available",
            _m("elasticsearch.node.fs.disk.available"),
            f"{_m('elasticsearch.node.fs.disk.available')}:*",
            "sum", "#7aa95c"),
        xy_lens("otel-apikey-lens-search-queue", "Search Queue",
            _m("elasticsearch.node.thread_pool.tasks.queued"),
            'attributes.thread_pool_name: "search" and metrics.elasticsearch.node.thread_pool.tasks.queued:*',
            "average", "#7b6fd0"),
        xy_lens("otel-apikey-lens-write-queue",  "Write Queue",
            _m("elasticsearch.node.thread_pool.tasks.queued"),
            'attributes.thread_pool_name: "write" and metrics.elasticsearch.node.thread_pool.tasks.queued:*',
            "average", "#d17c2d"),
        xy_lens("otel-apikey-lens-query-cache",  "Query Cache Memory",
            _m("elasticsearch.node.cache.memory.usage"),
            'attributes.cache_name: "query" and metrics.elasticsearch.node.cache.memory.usage:*',
            "average", "#2d7a78"),
        xy_lens("otel-apikey-lens-fielddata-cache", "Fielddata Cache Memory",
            _m("elasticsearch.node.cache.memory.usage"),
            'attributes.cache_name: "fielddata" and metrics.elasticsearch.node.cache.memory.usage:*',
            "average", "#9c6b2f"),
        xy_lens("otel-apikey-lens-young-gc",     "Young GC Elapsed",
            _m("jvm.gc.collections.elapsed"),
            'attributes.name: "young" and metrics.jvm.gc.collections.elapsed:*',
            "max", "#b0922e"),
        xy_lens("otel-apikey-lens-old-gc",       "Old GC Elapsed",
            _m("jvm.gc.collections.elapsed"),
            'attributes.name: "old" and metrics.jvm.gc.collections.elapsed:*',
            "max", "#7b4f9e"),
        xy_lens("otel-apikey-lens-req-breakers-ts", "Request Breakers",
            _m("elasticsearch.breaker.tripped"),
            'attributes.name: "request" and metrics.elasticsearch.breaker.tripped:*',
            "max", "#c2574c"),
        xy_lens("otel-apikey-lens-parent-breakers-ts", "Parent Breakers",
            _m("elasticsearch.breaker.tripped"),
            'attributes.name: "parent" and metrics.elasticsearch.breaker.tripped:*',
            "max", "#8c3a3a"),
        xy_lens("otel-apikey-lens-jvm-threads",  "JVM Threads",
            _m("jvm.threads.count"),
            f"{_m('jvm.threads.count')}:*",
            "max", "#6d8b74"),
        xy_lens("otel-apikey-lens-translog",     "Translog Size",
            _m("elasticsearch.node.translog.size"),
            f"{_m('elasticsearch.node.translog.size')}:*",
            "max", "#9a6d38"),
        xy_lens("otel-apikey-lens-ingest-fail-ts", "Ingest Failures",
            _m("elasticsearch.node.ingest.operations.failed"),
            f"{_m('elasticsearch.node.ingest.operations.failed')}:*",
            "max", "#b14d4d"),
        # ── Index time-series ─────────────────────────────────────────────────
        xy_lens("otel-apikey-lens-index-docs",   "Docs",
            _m("elasticsearch.index.documents"),
            f'{_m("elasticsearch.index.documents")}:* and not {_INDEX}: "_all"',
            "max", "#4f86c6"),
        xy_lens("otel-apikey-lens-index-size",   "Shard Size",
            _m("elasticsearch.index.shards.size"),
            f'{_m("elasticsearch.index.shards.size")}:* and not {_INDEX}: "_all"',
            "max", "#7aa95c"),
        xy_lens("otel-apikey-lens-index-segments", "Segments",
            _m("elasticsearch.index.segments.count"),
            f'{_m("elasticsearch.index.segments.count")}:* and not {_INDEX}: "_all"',
            "max", "#7b6fd0"),
        xy_lens("otel-apikey-lens-index-read",   "Read Ops Total",
            _m("elasticsearch.index.operations.completed"),
            f'attributes.operation: "fetch" and {_m("elasticsearch.index.operations.completed")}:* and not {_INDEX}: "_all"',
            "max", "#4f86c6"),
        xy_lens("otel-apikey-lens-index-write",  "Write Ops Total",
            _m("elasticsearch.index.operations.completed"),
            f'attributes.operation: "index" and {_m("elasticsearch.index.operations.completed")}:* and not {_INDEX}: "_all"',
            "max", "#d17c2d"),
        xy_lens("otel-apikey-lens-index-merge",  "Merge Current",
            _m("elasticsearch.index.operations.merge.current"),
            f'{_m("elasticsearch.index.operations.merge.current")}:* and not {_INDEX}: "_all"',
            "average", "#8a8f43"),
        # ── Tables ───────────────────────────────────────────────────────────
        datatable_lens(
            "otel-apikey-lens-health-status", "Cluster Health",
            "attributes.status", "Status", 3,
            [{"id": "otel-apikey-health-current", "label": "Current", "operation": "last_value",
              "field": _m("elasticsearch.cluster.health"),
              "filter": f"{_m('elasticsearch.cluster.health')}:*",
              "params": {"sortField": "@timestamp"}, "width": 90}],
        ),
        datatable_lens(
            "otel-apikey-lens-cluster-info", "Cluster Info",
            _CLUSTER, "Cluster", 10,
            [
                {"id": "otel-apikey-cluster-nodes",      "label": "Nodes",           "operation": "max", "field": _m("elasticsearch.cluster.nodes"),        "filter": f"{_m('elasticsearch.cluster.nodes')}:*"},
                {"id": "otel-apikey-cluster-data",       "label": "Data Nodes",      "operation": "max", "field": _m("elasticsearch.cluster.data_nodes"),   "filter": f"{_m('elasticsearch.cluster.data_nodes')}:*"},
                {"id": "otel-apikey-cluster-active",     "label": "Active Shards",   "operation": "max", "field": _m("elasticsearch.cluster.shards"),       "filter": 'attributes.state: "active" and metrics.elasticsearch.cluster.shards:*', "width": 130},
                {"id": "otel-apikey-cluster-unassigned", "label": "Unassigned",      "operation": "max", "field": _m("elasticsearch.cluster.shards"),       "filter": 'attributes.state: "unassigned" and metrics.elasticsearch.cluster.shards:*'},
                {"id": "otel-apikey-cluster-pending",    "label": "Pending Tasks",   "operation": "max", "field": _m("elasticsearch.cluster.pending_tasks"), "filter": f"{_m('elasticsearch.cluster.pending_tasks')}:*"},
            ],
        ),
        datatable_lens(
            "otel-apikey-lens-node-summary", "Node Summary",
            _NODE, "Node", 20,
            [
                {"id": "otel-apikey-node-heap-used",  "label": "Heap Used",   "operation": "max", "field": _m("jvm.memory.heap.used"),  "filter": f"{_m('jvm.memory.heap.used')}:*",  "width": 130, "params": {"format": {"id": "bytes", "params": {"decimals": 2}}}},
                {"id": "otel-apikey-node-heap-max",   "label": "Heap Max",    "operation": "max", "field": _m("jvm.memory.heap.max"),   "filter": f"{_m('jvm.memory.heap.max')}:*",   "width": 130, "params": {"format": {"id": "bytes", "params": {"decimals": 2}}}},
                {"id": "otel-apikey-node-open-files", "label": "Open Files",  "operation": "max", "field": _m("elasticsearch.node.open_files"),  "filter": f"{_m('elasticsearch.node.open_files')}:*"},
                {"id": "otel-apikey-node-query",      "label": "Query Total", "operation": "max", "field": _m("elasticsearch.node.operations.completed"), "filter": 'attributes.operation: "query" and metrics.elasticsearch.node.operations.completed:*'},
                {"id": "otel-apikey-node-index",      "label": "Index Total", "operation": "max", "field": _m("elasticsearch.node.operations.completed"), "filter": 'attributes.operation: "index" and metrics.elasticsearch.node.operations.completed:*'},
                {"id": "otel-apikey-node-disk",       "label": "Disk Avail",  "operation": "max", "field": _m("elasticsearch.node.fs.disk.available"), "filter": f"{_m('elasticsearch.node.fs.disk.available')}:*", "width": 130, "params": {"format": {"id": "bytes", "params": {"decimals": 2}}}},
            ],
        ),
        datatable_lens(
            "otel-apikey-lens-index-summary", "Index Activity",
            _INDEX, "Index", 20,
            [
                {"id": "otel-apikey-index-docs",     "label": "Docs",       "operation": "max", "field": _m("elasticsearch.index.documents"),           "filter": f'{_m("elasticsearch.index.documents")}:* and not {_INDEX}: "_all"'},
                {"id": "otel-apikey-index-size",     "label": "Shard Size", "operation": "max", "field": _m("elasticsearch.index.shards.size"),         "filter": f'{_m("elasticsearch.index.shards.size")}:* and not {_INDEX}: "_all"', "width": 130, "params": {"format": {"id": "bytes", "params": {"decimals": 2}}}},
                {"id": "otel-apikey-index-segments", "label": "Segments",   "operation": "max", "field": _m("elasticsearch.index.segments.count"),      "filter": f'{_m("elasticsearch.index.segments.count")}:* and not {_INDEX}: "_all"'},
                {"id": "otel-apikey-index-read",     "label": "Read Total", "operation": "max", "field": _m("elasticsearch.index.operations.completed"), "filter": f'attributes.operation: "fetch" and {_m("elasticsearch.index.operations.completed")}:* and not {_INDEX}: "_all"'},
                {"id": "otel-apikey-index-write",    "label": "Write Total", "operation": "max", "field": _m("elasticsearch.index.operations.completed"), "filter": f'attributes.operation: "index" and {_m("elasticsearch.index.operations.completed")}:* and not {_INDEX}: "_all"'},
            ],
            row_exclude=["_all"],
        ),
    ]

    objects.extend(lens_objects)
    objects.append(links_saved_object())

    overview_panels = [
        links_panel_ref("otel-apikey-panel-links-overview", "Navigation", 0, 0, 48, 3, LINKS_ID),
        dashboard_panel_ref("otel-apikey-panel-cluster-info",     "Cluster Info",     0,  3, 34, 8, "otel-apikey-lens-cluster-info"),
        dashboard_panel_ref("otel-apikey-panel-health-status",    "Cluster Health",   34, 3, 14, 8, "otel-apikey-lens-health-status"),
        dashboard_panel_ref("otel-apikey-panel-nodes",            "Nodes",            0,  11, 6, 5, "otel-apikey-lens-nodes"),
        dashboard_panel_ref("otel-apikey-panel-data-nodes",       "Data Nodes",       6,  11, 6, 5, "otel-apikey-lens-data-nodes"),
        dashboard_panel_ref("otel-apikey-panel-active",           "Active Shards",    12, 11, 6, 5, "otel-apikey-lens-active-shards"),
        dashboard_panel_ref("otel-apikey-panel-primary",          "Primary Shards",   18, 11, 6, 5, "otel-apikey-lens-primary-shards"),
        dashboard_panel_ref("otel-apikey-panel-unassigned",       "Unassigned",       24, 11, 6, 5, "otel-apikey-lens-unassigned"),
        dashboard_panel_ref("otel-apikey-panel-pending",          "Pending Tasks",    30, 11, 6, 5, "otel-apikey-lens-pending-tasks"),
        dashboard_panel_ref("otel-apikey-panel-green",            "Green",            36, 11, 6, 5, "otel-apikey-lens-green-health"),
        dashboard_panel_ref("otel-apikey-panel-req-breakers",     "Request Breakers", 0,  16, 8, 7, "otel-apikey-lens-req-breakers"),
        dashboard_panel_ref("otel-apikey-panel-parent-breakers",  "Parent Breakers",  8,  16, 8, 7, "otel-apikey-lens-parent-breakers"),
        dashboard_panel_ref("otel-apikey-panel-ingest-failures",  "Ingest Failures",  16, 16, 8, 7, "otel-apikey-lens-ingest-failures"),
        dashboard_panel_ref("otel-apikey-panel-query-rate",       "Query Ops Total",  0,  23, 12, 7, "otel-apikey-lens-query-rate"),
        dashboard_panel_ref("otel-apikey-panel-fetch-rate",       "Fetch Ops Total",  12, 23, 12, 7, "otel-apikey-lens-fetch-rate"),
        dashboard_panel_ref("otel-apikey-panel-index-rate",       "Index Ops Total",  24, 23, 12, 7, "otel-apikey-lens-index-rate"),
        dashboard_panel_ref("otel-apikey-panel-refresh-rate",     "Refresh Ops Total",36, 23, 12, 7, "otel-apikey-lens-refresh-rate"),
    ]

    nodes_panels = [
        links_panel_ref("otel-apikey-panel-links-nodes", "Navigation", 0, 0, 48, 3, LINKS_ID),
        dashboard_panel_ref("otel-apikey-panel-heap-used",          "Heap Used",             0,  3,  8, 7, "otel-apikey-lens-heap-used"),
        dashboard_panel_ref("otel-apikey-panel-heap-max",           "Heap Max",              8,  3,  8, 7, "otel-apikey-lens-heap-max"),
        dashboard_panel_ref("otel-apikey-panel-open-files",         "Open Files",            16, 3,  8, 7, "otel-apikey-lens-open-files"),
        dashboard_panel_ref("otel-apikey-panel-disk-avail",         "Disk Available",        24, 3,  8, 7, "otel-apikey-lens-disk-avail"),
        dashboard_panel_ref("otel-apikey-panel-search-queue",       "Search Queue",          32, 3,  8, 7, "otel-apikey-lens-search-queue"),
        dashboard_panel_ref("otel-apikey-panel-write-queue",        "Write Queue",           40, 3,  8, 7, "otel-apikey-lens-write-queue"),
        dashboard_panel_ref("otel-apikey-panel-query-cache",        "Query Cache Memory",    0,  10, 8, 7, "otel-apikey-lens-query-cache"),
        dashboard_panel_ref("otel-apikey-panel-fielddata-cache",    "Fielddata Cache",       8,  10, 8, 7, "otel-apikey-lens-fielddata-cache"),
        dashboard_panel_ref("otel-apikey-panel-young-gc",           "Young GC Elapsed",      16, 10, 8, 7, "otel-apikey-lens-young-gc"),
        dashboard_panel_ref("otel-apikey-panel-old-gc",             "Old GC Elapsed",        24, 10, 8, 7, "otel-apikey-lens-old-gc"),
        dashboard_panel_ref("otel-apikey-panel-req-breakers-ts",    "Request Breakers",      32, 10, 8, 7, "otel-apikey-lens-req-breakers-ts"),
        dashboard_panel_ref("otel-apikey-panel-parent-breakers-ts", "Parent Breakers",       40, 10, 8, 7, "otel-apikey-lens-parent-breakers-ts"),
        dashboard_panel_ref("otel-apikey-panel-jvm-threads",        "JVM Threads",           0,  17, 12, 7, "otel-apikey-lens-jvm-threads"),
        dashboard_panel_ref("otel-apikey-panel-translog",           "Translog Size",         12, 17, 12, 7, "otel-apikey-lens-translog"),
        dashboard_panel_ref("otel-apikey-panel-ingest-fail-ts",     "Ingest Failures",       24, 17, 12, 7, "otel-apikey-lens-ingest-fail-ts"),
        dashboard_panel_ref("otel-apikey-panel-node-summary",       "Node Summary",          0,  24, 48, 12, "otel-apikey-lens-node-summary"),
    ]

    indices_panels = [
        links_panel_ref("otel-apikey-panel-links-indices", "Navigation", 0, 0, 48, 3, LINKS_ID),
        dashboard_panel_ref("otel-apikey-panel-index-docs",     "Docs",          0,  3,  12, 7, "otel-apikey-lens-index-docs"),
        dashboard_panel_ref("otel-apikey-panel-index-size",     "Shard Size",    12, 3,  12, 7, "otel-apikey-lens-index-size"),
        dashboard_panel_ref("otel-apikey-panel-index-segments", "Segments",      24, 3,  12, 7, "otel-apikey-lens-index-segments"),
        dashboard_panel_ref("otel-apikey-panel-index-merge",    "Merge Current", 36, 3,  12, 7, "otel-apikey-lens-index-merge"),
        dashboard_panel_ref("otel-apikey-panel-index-read",     "Read Ops",      0,  10, 12, 7, "otel-apikey-lens-index-read"),
        dashboard_panel_ref("otel-apikey-panel-index-write",    "Write Ops",     12, 10, 12, 7, "otel-apikey-lens-index-write"),
        dashboard_panel_ref("otel-apikey-panel-index-summary",  "Index Activity",0,  17, 48, 14, "otel-apikey-lens-index-summary"),
    ]

    objects.extend([
        dashboard_object(
            DASHBOARD_ID,
            "Elasticsearch API key monitoring — Overview",
            "API key-authenticated OTEL metrics via elasticsearchreceiver → edot-gateway.",
            overview_panels,
        ),
        dashboard_object(
            NODES_DASHBOARD_ID,
            "Elasticsearch API key monitoring — Nodes",
            "Node metrics: heap, GC, queues, caches, breakers, disk.",
            nodes_panels,
        ),
        dashboard_object(
            INDICES_DASHBOARD_ID,
            "Elasticsearch API key monitoring — Indices",
            "Index metrics: docs, shard size, segments, read/write ops.",
            indices_panels,
        ),
    ])
    return objects


def main():
    repo_root = Path(__file__).resolve().parent.parent
    out_dir = repo_root / "dashboards"
    out_dir.mkdir(parents=True, exist_ok=True)
    objects = build_objects()

    ndjson_path = out_dir / "elasticsearch-otel-monitoring-apikey.ndjson"
    export_json_path = out_dir / "elasticsearch-otel-monitoring-apikey.export.json"

    with ndjson_path.open("w", encoding="utf-8") as fh:
        for obj in objects:
            fh.write(json.dumps(obj, separators=(",", ":")) + "\n")

    with export_json_path.open("w", encoding="utf-8") as fh:
        json.dump(
            {
                "description": "API key-authenticated Elasticsearch OTEL monitoring dashboards using elasticsearchreceiver.",
                "objects": objects,
            },
            fh,
            indent=2,
        )
        fh.write("\n")


if __name__ == "__main__":
    main()
