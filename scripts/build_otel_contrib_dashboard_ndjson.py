#!/usr/bin/env python3

import json
from pathlib import Path


DATA_VIEW_ID = "otel-elasticsearch-contrib-metrics-main"
DASHBOARD_ID = "otel-elasticsearch-monitoring-contrib"
NODES_DASHBOARD_ID = "otel-elasticsearch-monitoring-contrib-nodes"
INDICES_DASHBOARD_ID = "otel-elasticsearch-monitoring-contrib-indices"
LINKS_ID = "otel-elasticsearch-monitoring-contrib-links"
LENS_EXPORT_META = {
    "coreMigrationVersion": "8.8.0",
    "created_at": "2026-04-22T17:56:26.273Z",
    "created_by": "elastic",
    "managed": False,
    "typeMigrationVersion": "10.1.0",
    "updated_at": "2026-04-22T17:56:26.273Z",
    "updated_by": "elastic",
    "version": "WzEsMV0=",
}


def metric_lens(lens_id, title, field, filter_query, operation="last_value", params=None):
    layer_id = f"{lens_id}-layer"
    metric_id = f"{lens_id}-metric"
    ref_name = f"indexpattern-datasource-layer-{layer_id}"
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
                                "columnOrder": [metric_id],
                                "columns": {
                                    metric_id: {
                                        "customLabel": True,
                                        "dataType": "number",
                                        "filter": {"language": "kuery", "query": filter_query},
                                        "isBucketed": False,
                                        "label": title,
                                        "operationType": operation,
                                        "params": params or {"sortField": "@timestamp"},
                                        "scale": "ratio",
                                        "sourceField": field,
                                    }
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
                    "accessor": metric_id,
                    "colorMode": "Labels",
                    "layerId": layer_id,
                    "layerType": "data",
                    "size": "xl",
                    "textAlign": "center",
                    "titlePosition": "top",
                },
            },
        },
        "references": [{"id": DATA_VIEW_ID, "name": ref_name, "type": "index-pattern"}],
    }
    obj.update(LENS_EXPORT_META)
    return obj


def xy_lens(lens_id, title, field, filter_query, operation, color):
    layer_id = f"{lens_id}-layer"
    date_id = f"{lens_id}-date"
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
                                "columnOrder": [date_id, metric_id],
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
                            "xAccessor": date_id,
                            "yConfig": [{"axisMode": "left", "color": color, "forAccessor": metric_id}],
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


def datatable_lens(lens_id, title, row_field, row_label, row_size, metric_specs, row_exclude=None):
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
        vis_columns.append(
            {
                "columnId": metric_id,
                "isMetric": True,
                "isTransposed": False,
                "width": spec.get("width", 110),
            }
        )

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
                "query": {"language": "kuery", "query": ""},
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
        "gridData": {"i": panel_id, "x": x, "y": y, "w": w, "h": h},
        "embeddableConfig": {
            "enhancements": {"dynamicActions": {"events": []}},
            "filters": [],
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
        "gridData": {"i": panel_id, "x": x, "y": y, "w": w, "h": h},
        "embeddableConfig": {"enhancements": {}, "savedObjectId": links_id, "title": title},
    }


def markdown_panel(panel_id, content, x, y, w, h):
    return {
        "type": "visualization",
        "panelIndex": panel_id,
        "gridData": {"i": panel_id, "x": x, "y": y, "w": w, "h": h},
        "embeddableConfig": {
            "description": "",
            "hidePanelTitles": True,
            "enhancements": {"dynamicActions": {"events": []}},
            "savedVis": {
                "title": "Contrib Header",
                "description": "",
                "type": "markdown",
                "params": {"fontSize": 12, "markdown": content, "openLinksInNewTab": False},
                "uiState": {},
                "data": {"aggs": [], "searchSource": {"query": {"language": "kuery", "query": ""}, "filter": []}},
            },
            "title": "",
        },
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
        link_id = f"otel-contrib-link-{label.lower()}"
        ref_name = f"link_{link_id}_dashboard"
        links.append(
            {
                "destinationRefName": ref_name,
                "id": link_id,
                "label": label,
                "options": {"openInNewTab": False, "useCurrentDateRange": True, "useCurrentFilters": True},
                "order": order,
                "type": "dashboardLink",
            }
        )
        references.append({"id": dash_id, "name": ref_name, "type": "dashboard"})
    return {
        "type": "links",
        "id": LINKS_ID,
        "attributes": {
            "description": "",
            "layout": "horizontal",
            "links": links,
            "title": "Elasticsearch OTEL contrib navigation",
        },
        "references": references,
        "managed": False,
    }


def dashboard_references(panels):
    refs = []
    for panel in panels:
        if "panelRefName" not in panel:
            continue
        refs.append(
            {
                "id": panel["embeddableConfig"]["savedObjectId"],
                "name": f"{panel['panelIndex']}:{panel['panelRefName']}",
                "type": panel["type"],
            }
        )
    return refs


def control_group_and_references():
    specs = [
        ("cluster", "resource.attributes.elasticsearch.cluster.name", "Cluster Name(s)", "medium", False),
        ("node", "resource.attributes.elasticsearch.node.name", "Node(s)", "medium", True),
        ("index", "resource.attributes.elasticsearch.index.name", "Index(s)", "large", True),
    ]
    control_panels = {}
    references = []
    for order, (suffix, field_name, title, width, grow) in enumerate(specs):
        control_id = f"otel-contrib-control-{suffix}"
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
        references.append(
            {
                "id": DATA_VIEW_ID,
                "name": f"controlGroup_{control_id}:optionsListDataView",
                "type": "index-pattern",
            }
        )
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
                "ignoreParentSettingsJSON": json.dumps(
                    {
                        "ignoreFilters": False,
                        "ignoreQuery": False,
                        "ignoreTimerange": False,
                        "ignoreValidations": False,
                    }
                ),
                "panelsJSON": json.dumps(control_panels),
                "showApplySelections": False,
            },
            "title": title,
            "description": description,
            "optionsJSON": json.dumps(
                {
                    "useMargins": True,
                    "syncColors": False,
                    "syncCursor": True,
                    "syncTooltips": False,
                    "hidePanelTitles": False,
                }
            ),
            "panelsJSON": json.dumps(panels),
            "timeRestore": False,
            "kibanaSavedObjectMeta": {"searchSourceJSON": json.dumps({"query": {"language": "kuery", "query": ""}, "filter": []})},
            "version": 1,
        },
        "references": references,
    }


def build_objects():
    field_format_map = {
        "metrics.jvm.memory.heap.used": {"id": "bytes"},
        "metrics.jvm.memory.heap.max": {"id": "bytes"},
        "metrics.jvm.gc.collections.elapsed": {"id": "duration", "params": {"inputFormat": "milliseconds", "outputFormat": "humanize", "outputPrecision": 2}},
        "metrics.elasticsearch.node.fs.disk.available": {"id": "bytes"},
        "metrics.elasticsearch.index.shards.size": {"id": "bytes"},
        "metrics.elasticsearch.node.shards.size": {"id": "bytes"},
        "metrics.elasticsearch.node.cache.memory.usage": {"id": "bytes"},
    }
    objects = [
        {
            "type": "index-pattern",
            "id": DATA_VIEW_ID,
            "attributes": {
                "title": "metrics-elasticsearch.stack_monitoring.otel-main",
                "name": "otel-elasticsearch-contrib-metrics-main",
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
        metric_lens("otel-contrib-lens-green-health", "Green", "metrics.elasticsearch.cluster.health", 'attributes.status: "green" and metrics.elasticsearch.cluster.health:*'),
        metric_lens("otel-contrib-lens-nodes", "Nodes", "metrics.elasticsearch.cluster.nodes", "metrics.elasticsearch.cluster.nodes:*"),
        metric_lens("otel-contrib-lens-data-nodes", "Data Nodes", "metrics.elasticsearch.cluster.data_nodes", "metrics.elasticsearch.cluster.data_nodes:*"),
        metric_lens("otel-contrib-lens-active-shards", "Active Shards", "metrics.elasticsearch.cluster.shards", 'attributes.state: "active" and metrics.elasticsearch.cluster.shards:*'),
        metric_lens("otel-contrib-lens-primary-shards", "Primary Shards", "metrics.elasticsearch.cluster.shards", 'attributes.state: "active_primary" and metrics.elasticsearch.cluster.shards:*'),
        metric_lens("otel-contrib-lens-unassigned-shards", "Unassigned", "metrics.elasticsearch.cluster.shards", 'attributes.state: "unassigned" and metrics.elasticsearch.cluster.shards:*'),
        metric_lens("otel-contrib-lens-pending-tasks", "Pending Tasks", "metrics.elasticsearch.cluster.pending_tasks", "metrics.elasticsearch.cluster.pending_tasks:*"),
        metric_lens("otel-contrib-lens-overview-request-breakers", "Request Breakers Total", "metrics.elasticsearch.breaker.tripped", 'attributes.name: "request" and metrics.elasticsearch.breaker.tripped:*', "max"),
        metric_lens("otel-contrib-lens-overview-parent-breakers", "Parent Breakers Total", "metrics.elasticsearch.breaker.tripped", 'attributes.name: "parent" and metrics.elasticsearch.breaker.tripped:*', "max"),
        metric_lens("otel-contrib-lens-overview-ingest-failures", "Ingest Failures Total", "metrics.elasticsearch.node.ingest.operations.failed", "metrics.elasticsearch.node.ingest.operations.failed:*", "max"),
        xy_lens("otel-contrib-lens-query-rate", "Query Ops Total", "metrics.elasticsearch.node.operations.completed", 'attributes.operation: "query" and metrics.elasticsearch.node.operations.completed:*', "max", "#348888"),
        xy_lens("otel-contrib-lens-fetch-rate", "Fetch Ops Total", "metrics.elasticsearch.node.operations.completed", 'attributes.operation: "fetch" and metrics.elasticsearch.node.operations.completed:*', "max", "#4f86c6"),
        xy_lens("otel-contrib-lens-index-rate", "Index Ops Total", "metrics.elasticsearch.node.operations.completed", 'attributes.operation: "index" and metrics.elasticsearch.node.operations.completed:*', "max", "#d17c2d"),
        xy_lens("otel-contrib-lens-refresh-rate", "Refresh Ops Total", "metrics.elasticsearch.node.operations.completed", 'attributes.operation: "refresh" and metrics.elasticsearch.node.operations.completed:*', "max", "#8e6db0"),
        xy_lens("otel-contrib-lens-heap-used", "Heap Used", "metrics.jvm.memory.heap.used", "metrics.jvm.memory.heap.used:*", "average", "#2f9c95"),
        xy_lens("otel-contrib-lens-heap-max", "Heap Max", "metrics.jvm.memory.heap.max", "metrics.jvm.memory.heap.max:*", "average", "#5f9ea0"),
        xy_lens("otel-contrib-lens-open-files", "Open Files", "metrics.elasticsearch.node.open_files", "metrics.elasticsearch.node.open_files:*", "max", "#6a8caf"),
        xy_lens("otel-contrib-lens-disk-available", "Disk Available", "metrics.elasticsearch.node.fs.disk.available", "metrics.elasticsearch.node.fs.disk.available:*", "sum", "#7aa95c"),
        xy_lens("otel-contrib-lens-search-queue", "Search Queue", "metrics.elasticsearch.node.thread_pool.tasks.queued", 'attributes.thread_pool_name: "search" and metrics.elasticsearch.node.thread_pool.tasks.queued:*', "average", "#7b6fd0"),
        xy_lens("otel-contrib-lens-write-queue", "Write Queue", "metrics.elasticsearch.node.thread_pool.tasks.queued", 'attributes.thread_pool_name: "write" and metrics.elasticsearch.node.thread_pool.tasks.queued:*', "average", "#d17c2d"),
        xy_lens("otel-contrib-lens-query-cache-memory", "Query Cache Memory", "metrics.elasticsearch.node.cache.memory.usage", 'attributes.cache_name: "query" and metrics.elasticsearch.node.cache.memory.usage:*', "average", "#2d7a78"),
        xy_lens("otel-contrib-lens-fielddata-cache-memory", "Fielddata Cache Memory", "metrics.elasticsearch.node.cache.memory.usage", 'attributes.cache_name: "fielddata" and metrics.elasticsearch.node.cache.memory.usage:*', "average", "#9c6b2f"),
        xy_lens("otel-contrib-lens-query-cache-evictions", "Query Cache Evictions Total", "metrics.elasticsearch.node.cache.evictions", 'attributes.cache_name: "query" and metrics.elasticsearch.node.cache.evictions:*', "max", "#b85450"),
        xy_lens("otel-contrib-lens-young-gc", "Young GC Elapsed", "metrics.jvm.gc.collections.elapsed", 'attributes.name: "young" and metrics.jvm.gc.collections.elapsed:*', "max", "#b0922e"),
        xy_lens("otel-contrib-lens-old-gc", "Old GC Elapsed", "metrics.jvm.gc.collections.elapsed", 'attributes.name: "old" and metrics.jvm.gc.collections.elapsed:*', "max", "#7b4f9e"),
        xy_lens("otel-contrib-lens-request-breakers", "Request Breakers", "metrics.elasticsearch.breaker.tripped", 'attributes.name: "request" and metrics.elasticsearch.breaker.tripped:*', "max", "#c2574c"),
        xy_lens("otel-contrib-lens-parent-breakers", "Parent Breakers", "metrics.elasticsearch.breaker.tripped", 'attributes.name: "parent" and metrics.elasticsearch.breaker.tripped:*', "max", "#8c3a3a"),
        xy_lens("otel-contrib-lens-index-docs", "Docs", "metrics.elasticsearch.index.documents", 'metrics.elasticsearch.index.documents:* and not resource.attributes.elasticsearch.index.name: "_all"', "max", "#4f86c6"),
        xy_lens("otel-contrib-lens-index-size", "Shard Size", "metrics.elasticsearch.index.shards.size", 'metrics.elasticsearch.index.shards.size:* and not resource.attributes.elasticsearch.index.name: "_all"', "max", "#7aa95c"),
        xy_lens("otel-contrib-lens-index-segments", "Segments", "metrics.elasticsearch.index.segments.count", 'metrics.elasticsearch.index.segments.count:* and not resource.attributes.elasticsearch.index.name: "_all"', "max", "#7b6fd0"),
        xy_lens("otel-contrib-lens-index-read-rate", "Read Ops Total", "metrics.elasticsearch.index.operations.completed", 'attributes.operation: "fetch" and metrics.elasticsearch.index.operations.completed:* and not resource.attributes.elasticsearch.index.name: "_all"', "max", "#4f86c6"),
        xy_lens("otel-contrib-lens-index-write-rate", "Write Ops Total", "metrics.elasticsearch.index.operations.completed", 'attributes.operation: "index" and metrics.elasticsearch.index.operations.completed:* and not resource.attributes.elasticsearch.index.name: "_all"', "max", "#d17c2d"),
        xy_lens("otel-contrib-lens-state-queue", "State Queue", "metrics.elasticsearch.cluster.state_queue", "metrics.elasticsearch.cluster.state_queue:*", "max", "#7f8c8d"),
        xy_lens("otel-contrib-lens-in-flight-fetch", "In-Flight Fetch", "metrics.elasticsearch.cluster.in_flight_fetch", "metrics.elasticsearch.cluster.in_flight_fetch:*", "max", "#5e81ac"),
        xy_lens("otel-contrib-lens-jvm-threads", "JVM Threads", "metrics.jvm.threads.count", "metrics.jvm.threads.count:*", "max", "#6d8b74"),
        xy_lens("otel-contrib-lens-translog-size", "Translog Size", "metrics.elasticsearch.node.translog.size", "metrics.elasticsearch.node.translog.size:*", "max", "#9a6d38"),
        xy_lens("otel-contrib-lens-ingest-failures", "Ingest Failures Total", "metrics.elasticsearch.node.ingest.operations.failed", "metrics.elasticsearch.node.ingest.operations.failed:*", "max", "#b14d4d"),
        xy_lens("otel-contrib-lens-index-merge-current", "Merge Current", "metrics.elasticsearch.index.operations.merge.current", 'metrics.elasticsearch.index.operations.merge.current:* and not resource.attributes.elasticsearch.index.name: "_all"', "average", "#8a8f43"),
        datatable_lens(
            "otel-contrib-lens-health-status",
            "Cluster Health",
            "attributes.status",
            "Status",
            3,
            [
                {"id": "otel-contrib-health-current", "label": "Current", "operation": "last_value", "field": "metrics.elasticsearch.cluster.health", "filter": "metrics.elasticsearch.cluster.health:*", "params": {"sortField": "@timestamp"}, "width": 90},
            ],
        ),
        datatable_lens(
            "otel-contrib-lens-cluster-info",
            "Cluster Info",
            "resource.attributes.elasticsearch.cluster.name",
            "Cluster",
            10,
            [
                {"id": "otel-contrib-cluster-nodes", "label": "Nodes", "operation": "max", "field": "metrics.elasticsearch.cluster.nodes", "filter": "metrics.elasticsearch.cluster.nodes:*"},
                {"id": "otel-contrib-cluster-data", "label": "Data Nodes", "operation": "max", "field": "metrics.elasticsearch.cluster.data_nodes", "filter": "metrics.elasticsearch.cluster.data_nodes:*"},
                {"id": "otel-contrib-cluster-active", "label": "Active Shards", "operation": "max", "field": "metrics.elasticsearch.cluster.shards", "filter": 'attributes.state: "active" and metrics.elasticsearch.cluster.shards:*', "width": 130},
                {"id": "otel-contrib-cluster-unassigned", "label": "Unassigned", "operation": "max", "field": "metrics.elasticsearch.cluster.shards", "filter": 'attributes.state: "unassigned" and metrics.elasticsearch.cluster.shards:*'},
                {"id": "otel-contrib-cluster-pending", "label": "Pending", "operation": "max", "field": "metrics.elasticsearch.cluster.pending_tasks", "filter": "metrics.elasticsearch.cluster.pending_tasks:*"},
            ],
        ),
        datatable_lens(
            "otel-contrib-lens-node-summary",
            "Node Summary",
            "resource.attributes.elasticsearch.node.name",
            "Node",
            20,
            [
                {"id": "otel-contrib-node-heap-used", "label": "Heap Used", "operation": "max", "field": "metrics.jvm.memory.heap.used", "filter": "metrics.jvm.memory.heap.used:*", "width": 130},
                {"id": "otel-contrib-node-heap-max", "label": "Heap Max", "operation": "max", "field": "metrics.jvm.memory.heap.max", "filter": "metrics.jvm.memory.heap.max:*", "width": 130},
                {"id": "otel-contrib-node-open-files", "label": "Open Files", "operation": "max", "field": "metrics.elasticsearch.node.open_files", "filter": "metrics.elasticsearch.node.open_files:*"},
                {"id": "otel-contrib-node-http", "label": "HTTP Conns", "operation": "max", "field": "metrics.elasticsearch.node.http.connections", "filter": "metrics.elasticsearch.node.http.connections:*"},
                {"id": "otel-contrib-node-query-rate", "label": "Query Total", "operation": "max", "field": "metrics.elasticsearch.node.operations.completed", "filter": 'attributes.operation: "query" and metrics.elasticsearch.node.operations.completed:*'},
                {"id": "otel-contrib-node-index-rate", "label": "Index Total", "operation": "max", "field": "metrics.elasticsearch.node.operations.completed", "filter": 'attributes.operation: "index" and metrics.elasticsearch.node.operations.completed:*'},
                {"id": "otel-contrib-node-disk", "label": "Disk Avail", "operation": "max", "field": "metrics.elasticsearch.node.fs.disk.available", "filter": "metrics.elasticsearch.node.fs.disk.available:*", "width": 130},
            ],
        ),
        datatable_lens(
            "otel-contrib-lens-index-summary",
            "Index Activity",
            "resource.attributes.elasticsearch.index.name",
            "Index",
            20,
            [
                {"id": "otel-contrib-index-docs-table", "label": "Docs", "operation": "max", "field": "metrics.elasticsearch.index.documents", "filter": 'metrics.elasticsearch.index.documents:* and not resource.attributes.elasticsearch.index.name: "_all"'},
                {"id": "otel-contrib-index-size-table", "label": "Shard Size", "operation": "max", "field": "metrics.elasticsearch.index.shards.size", "filter": 'metrics.elasticsearch.index.shards.size:* and not resource.attributes.elasticsearch.index.name: "_all"', "width": 130},
                {"id": "otel-contrib-index-segments-table", "label": "Segments", "operation": "max", "field": "metrics.elasticsearch.index.segments.count", "filter": 'metrics.elasticsearch.index.segments.count:* and not resource.attributes.elasticsearch.index.name: "_all"'},
                {"id": "otel-contrib-index-read-rate-table", "label": "Read Total", "operation": "max", "field": "metrics.elasticsearch.index.operations.completed", "filter": 'attributes.operation: "fetch" and metrics.elasticsearch.index.operations.completed:* and not resource.attributes.elasticsearch.index.name: "_all"'},
                {"id": "otel-contrib-index-write-rate-table", "label": "Write Total", "operation": "max", "field": "metrics.elasticsearch.index.operations.completed", "filter": 'attributes.operation: "index" and metrics.elasticsearch.index.operations.completed:* and not resource.attributes.elasticsearch.index.name: "_all"'},
            ],
            row_exclude=["_all"],
        ),
    ]
    objects.extend(lens_objects)
    objects.append(links_saved_object())

    overview_panels = [
        links_panel_ref("otel-contrib-panel-links-overview", "Navigation", 0, 0, 48, 3, LINKS_ID),
        markdown_panel(
            "otel-contrib-markdown-overview",
            "## Elasticsearch OTEL contrib overview\nNative OTEL metrics from `elasticsearchreceiver` stored in `metrics-elasticsearch.stack_monitoring.otel-main`.",
            0,
            3,
            48,
            3,
        ),
        dashboard_panel_ref("otel-contrib-panel-cluster-info", "Cluster Info", 0, 6, 34, 8, "otel-contrib-lens-cluster-info"),
        dashboard_panel_ref("otel-contrib-panel-health-status", "Cluster Health", 34, 6, 14, 8, "otel-contrib-lens-health-status"),
        dashboard_panel_ref("otel-contrib-panel-nodes", "Nodes", 0, 14, 6, 5, "otel-contrib-lens-nodes"),
        dashboard_panel_ref("otel-contrib-panel-data-nodes", "Data Nodes", 6, 14, 6, 5, "otel-contrib-lens-data-nodes"),
        dashboard_panel_ref("otel-contrib-panel-active", "Active Shards", 12, 14, 6, 5, "otel-contrib-lens-active-shards"),
        dashboard_panel_ref("otel-contrib-panel-primary", "Primary Shards", 18, 14, 6, 5, "otel-contrib-lens-primary-shards"),
        dashboard_panel_ref("otel-contrib-panel-unassigned", "Unassigned", 24, 14, 6, 5, "otel-contrib-lens-unassigned-shards"),
        dashboard_panel_ref("otel-contrib-panel-pending", "Pending Tasks", 30, 14, 6, 5, "otel-contrib-lens-pending-tasks"),
        dashboard_panel_ref("otel-contrib-panel-green", "Green", 36, 14, 6, 5, "otel-contrib-lens-green-health"),
        dashboard_panel_ref("otel-contrib-panel-state-queue", "State Queue", 0, 19, 12, 7, "otel-contrib-lens-state-queue"),
        dashboard_panel_ref("otel-contrib-panel-in-flight-fetch", "In-Flight Fetch", 12, 19, 12, 7, "otel-contrib-lens-in-flight-fetch"),
        dashboard_panel_ref("otel-contrib-panel-overview-request-breakers", "Request Breakers Total", 24, 19, 8, 7, "otel-contrib-lens-overview-request-breakers"),
        dashboard_panel_ref("otel-contrib-panel-overview-parent-breakers", "Parent Breakers Total", 32, 19, 8, 7, "otel-contrib-lens-overview-parent-breakers"),
        dashboard_panel_ref("otel-contrib-panel-overview-ingest-failures", "Ingest Failures Total", 40, 19, 8, 7, "otel-contrib-lens-overview-ingest-failures"),
        dashboard_panel_ref("otel-contrib-panel-query-rate", "Query Ops Total", 0, 26, 12, 7, "otel-contrib-lens-query-rate"),
        dashboard_panel_ref("otel-contrib-panel-fetch-rate", "Fetch Ops Total", 12, 26, 12, 7, "otel-contrib-lens-fetch-rate"),
        dashboard_panel_ref("otel-contrib-panel-index-rate", "Index Ops Total", 24, 26, 12, 7, "otel-contrib-lens-index-rate"),
        dashboard_panel_ref("otel-contrib-panel-refresh-rate", "Refresh Ops Total", 36, 26, 12, 7, "otel-contrib-lens-refresh-rate"),
    ]

    nodes_panels = [
        links_panel_ref("otel-contrib-panel-links-nodes", "Navigation", 0, 0, 48, 3, LINKS_ID),
        markdown_panel(
            "otel-contrib-markdown-nodes",
            "## Elasticsearch OTEL contrib nodes\nHeap, file handles, queues, caches, GC, and breaker pressure.",
            0,
            3,
            48,
            3,
        ),
        dashboard_panel_ref("otel-contrib-panel-heap-used-nodes", "Heap Used", 0, 6, 8, 7, "otel-contrib-lens-heap-used"),
        dashboard_panel_ref("otel-contrib-panel-heap-max-nodes", "Heap Max", 8, 6, 8, 7, "otel-contrib-lens-heap-max"),
        dashboard_panel_ref("otel-contrib-panel-open-files-nodes", "Open Files", 16, 6, 8, 7, "otel-contrib-lens-open-files"),
        dashboard_panel_ref("otel-contrib-panel-disk-nodes", "Disk Available", 24, 6, 8, 7, "otel-contrib-lens-disk-available"),
        dashboard_panel_ref("otel-contrib-panel-search-queue-nodes", "Search Queue", 32, 6, 8, 7, "otel-contrib-lens-search-queue"),
        dashboard_panel_ref("otel-contrib-panel-write-queue-nodes", "Write Queue", 40, 6, 8, 7, "otel-contrib-lens-write-queue"),
        dashboard_panel_ref("otel-contrib-panel-query-cache-memory", "Query Cache Memory", 0, 13, 8, 7, "otel-contrib-lens-query-cache-memory"),
        dashboard_panel_ref("otel-contrib-panel-fielddata-cache-memory", "Fielddata Cache Memory", 8, 13, 8, 7, "otel-contrib-lens-fielddata-cache-memory"),
        dashboard_panel_ref("otel-contrib-panel-query-cache-evictions", "Query Cache Evictions Total", 16, 13, 8, 7, "otel-contrib-lens-query-cache-evictions"),
        dashboard_panel_ref("otel-contrib-panel-young-gc", "Young GC Elapsed", 24, 13, 8, 7, "otel-contrib-lens-young-gc"),
        dashboard_panel_ref("otel-contrib-panel-old-gc", "Old GC Elapsed", 32, 13, 8, 7, "otel-contrib-lens-old-gc"),
        dashboard_panel_ref("otel-contrib-panel-request-breakers", "Request Breakers", 40, 13, 8, 7, "otel-contrib-lens-request-breakers"),
        dashboard_panel_ref("otel-contrib-panel-parent-breakers", "Parent Breakers", 0, 20, 12, 7, "otel-contrib-lens-parent-breakers"),
        dashboard_panel_ref("otel-contrib-panel-jvm-threads", "JVM Threads", 12, 20, 12, 7, "otel-contrib-lens-jvm-threads"),
        dashboard_panel_ref("otel-contrib-panel-translog-size", "Translog Size", 24, 20, 12, 7, "otel-contrib-lens-translog-size"),
        dashboard_panel_ref("otel-contrib-panel-ingest-failures", "Ingest Failures Total", 36, 20, 12, 7, "otel-contrib-lens-ingest-failures"),
        dashboard_panel_ref("otel-contrib-panel-node-summary", "Node Summary", 0, 27, 48, 12, "otel-contrib-lens-node-summary"),
    ]

    indices_panels = [
        links_panel_ref("otel-contrib-panel-links-indices", "Navigation", 0, 0, 48, 3, LINKS_ID),
        markdown_panel(
            "otel-contrib-markdown-indices",
            "## Elasticsearch OTEL contrib indices\nDocs, shard size, segments, and per-index read/write activity.",
            0,
            3,
            48,
            3,
        ),
        dashboard_panel_ref("otel-contrib-panel-index-docs", "Docs", 0, 6, 12, 7, "otel-contrib-lens-index-docs"),
        dashboard_panel_ref("otel-contrib-panel-index-size", "Shard Size", 12, 6, 12, 7, "otel-contrib-lens-index-size"),
        dashboard_panel_ref("otel-contrib-panel-index-segments", "Segments", 24, 6, 12, 7, "otel-contrib-lens-index-segments"),
        dashboard_panel_ref("otel-contrib-panel-index-merge-current", "Merge Current", 36, 6, 12, 7, "otel-contrib-lens-index-merge-current"),
        dashboard_panel_ref("otel-contrib-panel-index-read-rate", "Read Ops Total", 0, 13, 12, 7, "otel-contrib-lens-index-read-rate"),
        dashboard_panel_ref("otel-contrib-panel-index-write-rate", "Write Ops Total", 12, 13, 12, 7, "otel-contrib-lens-index-write-rate"),
        dashboard_panel_ref("otel-contrib-panel-index-summary", "Index Activity", 0, 20, 48, 14, "otel-contrib-lens-index-summary"),
    ]

    objects.extend(
        [
            dashboard_object(
                DASHBOARD_ID,
                "Elasticsearch OTEL monitoring for metrics-elasticsearch.stack_monitoring.otel-main",
                "Overview dashboard for the OTEL contrib elasticsearchreceiver metrics stream.",
                overview_panels,
            ),
            dashboard_object(
                NODES_DASHBOARD_ID,
                "Elasticsearch OTEL monitoring - Contrib Nodes",
                "Node dashboard for the OTEL contrib elasticsearchreceiver metrics stream.",
                nodes_panels,
            ),
            dashboard_object(
                INDICES_DASHBOARD_ID,
                "Elasticsearch OTEL monitoring - Contrib Indices",
                "Index dashboard for the OTEL contrib elasticsearchreceiver metrics stream.",
                indices_panels,
            ),
        ]
    )
    return objects


def main():
    repo_root = Path(__file__).resolve().parent.parent
    out_dir = repo_root / "dashboards"
    out_dir.mkdir(parents=True, exist_ok=True)
    objects = build_objects()

    ndjson_path = out_dir / "elasticsearch-otel-monitoring-contrib.ndjson"
    export_json_path = out_dir / "elasticsearch-otel-monitoring-contrib.export.json"

    with ndjson_path.open("w", encoding="utf-8") as fh:
        for obj in objects:
            fh.write(json.dumps(obj, separators=(",", ":")) + "\n")

    with export_json_path.open("w", encoding="utf-8") as fh:
        json.dump(
            {
                "description": "Structured export wrapper for the Elasticsearch OTEL contrib monitoring dashboards. Convert to NDJSON for Kibana UI import.",
                "objects": objects,
            },
            fh,
            indent=2,
        )
        fh.write("\n")


if __name__ == "__main__":
    main()
