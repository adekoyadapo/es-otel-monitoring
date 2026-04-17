#!/usr/bin/env python3

import json
from pathlib import Path


DATA_VIEW_ID = "otel-elasticsearch-metrics-main"
DASHBOARD_ID = "otel-elasticsearch-monitoring-main"
LENS_EXPORT_META = {
    "coreMigrationVersion": "8.8.0",
    "created_at": "2025-10-20T17:56:26.273Z",
    "created_by": "u_3963321524_cloud",
    "managed": False,
    "typeMigrationVersion": "10.1.0",
    "updated_at": "2025-10-20T17:56:26.273Z",
    "updated_by": "u_3963321524_cloud",
    "version": "WzM1NTUsMTNd",
}


def metric_lens(lens_id, title, field, filter_query):
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
                                        "operationType": "last_value",
                                        "params": {"sortField": "@timestamp"},
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


def xy_lens(lens_id, title, field, operation_type, filter_query, color, metric_params=None):
    layer_id = f"{lens_id}-layer"
    date_id = f"{lens_id}-date"
    metric_id = f"{lens_id}-metric"
    ref_name = f"indexpattern-datasource-layer-{layer_id}"
    params = {"emptyAsNull": True}
    if metric_params:
        params.update(metric_params)

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
                                        "operationType": operation_type,
                                        "params": params,
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
                            "yConfig": [
                                {
                                    "axisMode": "left",
                                    "color": color,
                                    "forAccessor": metric_id,
                                }
                            ],
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


def datatable_lens(lens_id, title, row_field, row_label, row_size, metric_specs):
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
                "exclude": [],
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
        {
            "alignment": "left",
            "columnId": row_id,
            "isTransposed": False,
            "oneClickFilter": True,
            "width": 220,
        },
        {
            "columnId": count_id,
            "hidden": True,
            "isMetric": True,
            "isTransposed": False,
        },
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
                "visualization": {
                    "columns": vis_columns,
                    "layerId": layer_id,
                    "layerType": "data",
                },
            },
        },
        "references": [
            {"id": DATA_VIEW_ID, "name": f"indexpattern-datasource-layer-{layer_id}", "type": "index-pattern"}
        ],
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
                "title": "OTEL Header",
                "description": "",
                "type": "markdown",
                "params": {"fontSize": 12, "markdown": content, "openLinksInNewTab": False},
                "uiState": {},
                "data": {
                    "aggs": [],
                    "searchSource": {"query": {"language": "kuery", "query": ""}, "filter": []},
                },
            },
            "title": "",
        },
    }


def build_objects():
    objects = [
        {
            "type": "index-pattern",
            "id": DATA_VIEW_ID,
            "attributes": {
                "title": "logs-elasticsearch.metrics-main",
                "name": "otel-elasticsearch-metrics-main",
                "timeFieldName": "@timestamp",
                "fields": "[]",
                "fieldAttrs": "{}",
                "fieldFormatMap": "{}",
                "runtimeFieldMap": "{}",
                "sourceFilters": "[]",
                "allowHidden": False,
            },
        }
    ]

    lens_objects = [
        metric_lens(
            "otel-lens-nodes",
            "Nodes",
            "autoops_es.cluster_health.number_of_nodes",
            'metricset.name: "cluster_health" and autoops_es.cluster_health.number_of_nodes: *',
        ),
        metric_lens(
            "otel-lens-data-nodes",
            "Data Nodes",
            "autoops_es.cluster_health.number_of_data_nodes",
            'metricset.name: "cluster_health" and autoops_es.cluster_health.number_of_data_nodes: *',
        ),
        metric_lens(
            "otel-lens-unassigned-shards",
            "Unassigned Shards",
            "autoops_es.cluster_health.unassigned_shards",
            'metricset.name: "cluster_health" and autoops_es.cluster_health.unassigned_shards: *',
        ),
        metric_lens(
            "otel-lens-pending-tasks",
            "Pending Tasks",
            "autoops_es.cluster_health.number_of_pending_tasks",
            'metricset.name: "cluster_health" and autoops_es.cluster_health.number_of_pending_tasks: *',
        ),
        metric_lens(
            "otel-lens-active-primary-shards",
            "Active Primary Shards",
            "autoops_es.cluster_health.active_primary_shards",
            'metricset.name: "cluster_health" and autoops_es.cluster_health.active_primary_shards: *',
        ),
        metric_lens(
            "otel-lens-active-shards-pct",
            "Active Shards %",
            "autoops_es.cluster_health.active_shards_percent_as_number",
            'metricset.name: "cluster_health" and autoops_es.cluster_health.active_shards_percent_as_number: *',
        ),
        metric_lens(
            "otel-lens-initializing-shards",
            "Initializing Shards",
            "autoops_es.cluster_health.initializing_shards",
            'metricset.name: "cluster_health" and autoops_es.cluster_health.initializing_shards: *',
        ),
        metric_lens(
            "otel-lens-delayed-unassigned",
            "Delayed Unassigned",
            "autoops_es.cluster_health.delayed_unassigned_shards",
            'metricset.name: "cluster_health" and autoops_es.cluster_health.delayed_unassigned_shards: *',
        ),
        xy_lens(
            "otel-lens-search-rate",
            "Search Rate /s",
            "autoops_es.node_stats.search_rate_per_second",
            "average",
            'metricset.name: "node_stats" and autoops_es.node_stats.search_rate_per_second: * and autoops_es.node_stats.name: *',
            "#1EA593",
        ),
        xy_lens(
            "otel-lens-index-rate",
            "Index Rate /s",
            "autoops_es.node_stats.index_rate_per_second",
            "average",
            'metricset.name: "node_stats" and autoops_es.node_stats.index_rate_per_second: * and autoops_es.node_stats.name: *',
            "#9170B8",
        ),
        xy_lens(
            "otel-lens-heap-used",
            "Heap Used (GB)",
            "autoops_es.node_stats.jvm.mem.heap_used_in_bytes",
            "average",
            'metricset.name: "node_stats" and autoops_es.node_stats.jvm.mem.heap_used_in_bytes: * and autoops_es.node_stats.name: *',
            "#6092C0",
            {"format": {"id": "bytes", "params": {"decimals": 1}}},
        ),
        xy_lens(
            "otel-lens-heap-max",
            "Heap Max (GB)",
            "autoops_es.node_stats.jvm.mem.heap_max_in_bytes",
            "average",
            'metricset.name: "node_stats" and autoops_es.node_stats.jvm.mem.heap_max_in_bytes: * and autoops_es.node_stats.name: *',
            "#2E6DCC",
            {"format": {"id": "bytes", "params": {"decimals": 1}}},
        ),
        xy_lens(
            "otel-lens-heap-used-pct",
            "Heap Used %",
            "autoops_es.node_stats.jvm.mem.heap_used_percent",
            "average",
            'metricset.name: "node_stats" and autoops_es.node_stats.jvm.mem.heap_used_percent: * and autoops_es.node_stats.name: *',
            "#4CB140",
        ),
        xy_lens(
            "otel-lens-open-http",
            "Open HTTP Connections",
            "autoops_es.node_stats.http.current_open",
            "max",
            'metricset.name: "node_stats" and autoops_es.node_stats.http.current_open: * and autoops_es.node_stats.name: *',
            "#CA8EAE",
        ),
        xy_lens(
            "otel-lens-search-queue",
            "Search Queue Max",
            "autoops_es.node_stats.thread_pool.search.queue",
            "max",
            'metricset.name: "node_stats" and autoops_es.node_stats.thread_pool.search.queue: * and autoops_es.node_stats.name: *',
            "#D6BF57",
        ),
        xy_lens(
            "otel-lens-write-queue",
            "Write Queue Max",
            "autoops_es.node_stats.thread_pool.write.queue",
            "max",
            'metricset.name: "node_stats" and autoops_es.node_stats.thread_pool.write.queue: * and autoops_es.node_stats.name: *',
            "#E7664C",
        ),
        xy_lens(
            "otel-lens-search-rejected",
            "Search Rejected",
            "autoops_es.node_stats.thread_pool.search.rejected",
            "max",
            'metricset.name: "node_stats" and autoops_es.node_stats.thread_pool.search.rejected: * and autoops_es.node_stats.name: *',
            "#BD271E",
        ),
        xy_lens(
            "otel-lens-write-rejected",
            "Write Rejected",
            "autoops_es.node_stats.thread_pool.write.rejected",
            "max",
            'metricset.name: "node_stats" and autoops_es.node_stats.thread_pool.write.rejected: * and autoops_es.node_stats.name: *',
            "#F04E98",
        ),
        xy_lens(
            "otel-lens-search-latency",
            "Search Latency (ms)",
            "autoops_es.node_stats.search_latency_in_millis",
            "average",
            'metricset.name: "node_stats" and autoops_es.node_stats.search_latency_in_millis: * and autoops_es.node_stats.name: *',
            "#6092C0",
        ),
        xy_lens(
            "otel-lens-index-failed-rate",
            "Index Failed Rate /s",
            "autoops_es.node_stats.index_failed_rate_per_second",
            "average",
            'metricset.name: "node_stats" and autoops_es.node_stats.index_failed_rate_per_second: * and autoops_es.node_stats.name: *',
            "#CC5642",
        ),
        xy_lens(
            "otel-lens-gc-young-time",
            "GC Young Time (ms)",
            "autoops_es.node_stats.jvm.gc.collectors.young.collection_time_in_millis",
            "max",
            'metricset.name: "node_stats" and autoops_es.node_stats.jvm.gc.collectors.young.collection_time_in_millis: * and autoops_es.node_stats.name: *',
            "#DA8B45",
        ),
        xy_lens(
            "otel-lens-gc-old-time",
            "GC Old Time (ms)",
            "autoops_es.node_stats.jvm.gc.collectors.old.collection_time_in_millis",
            "max",
            'metricset.name: "node_stats" and autoops_es.node_stats.jvm.gc.collectors.old.collection_time_in_millis: * and autoops_es.node_stats.name: *',
            "#B95F0B",
        ),
        xy_lens(
            "otel-lens-parent-breaker-tripped",
            "Parent Breaker Trips",
            "autoops_es.node_stats.breakers.parent.tripped",
            "max",
            'metricset.name: "node_stats" and autoops_es.node_stats.breakers.parent.tripped: * and autoops_es.node_stats.name: *',
            "#BD271E",
        ),
        xy_lens(
            "otel-lens-request-breaker-tripped",
            "Request Breaker Trips",
            "autoops_es.node_stats.breakers.request.tripped",
            "max",
            'metricset.name: "node_stats" and autoops_es.node_stats.breakers.request.tripped: * and autoops_es.node_stats.name: *',
            "#D36086",
        ),
        xy_lens(
            "otel-lens-node-shards",
            "Shard Count by Node",
            "autoops_es.cat_shards.node_shards_count.shards_count",
            "max",
            'metricset.name: "cat_shards" and autoops_es.cat_shards.node_shards_count.shards_count: * and autoops_es.cat_shards.node_shards_count.node_name: *',
            "#9170B8",
        ),
        xy_lens(
            "otel-lens-primary-shards",
            "Primary Shards by Node",
            "autoops_es.cat_shards.node_shards_count.primary_shards",
            "max",
            'metricset.name: "cat_shards" and autoops_es.cat_shards.node_shards_count.primary_shards: * and autoops_es.cat_shards.node_shards_count.node_name: *',
            "#54B399",
        ),
        datatable_lens(
            "otel-lens-cluster-info",
            "Cluster Info",
            "autoops_es.cluster.name",
            "Cluster",
            10,
            [
                {
                    "id": "cluster-id",
                    "label": "Cluster ID",
                    "operation": "last_value",
                    "field": "autoops_es.cluster.id",
                    "data_type": "string",
                    "scale": "ordinal",
                    "filter": 'metricset.name: "cluster_health" and autoops_es.cluster.id: *',
                    "params": {"sortField": "@timestamp"},
                    "width": 170,
                },
                {
                    "id": "cluster-version",
                    "label": "Version",
                    "operation": "last_value",
                    "field": "autoops_es.cluster.version",
                    "data_type": "string",
                    "scale": "ordinal",
                    "filter": 'metricset.name: "cluster_health" and autoops_es.cluster.version: *',
                    "params": {"sortField": "@timestamp"},
                    "width": 90,
                },
                {
                    "id": "cluster-status",
                    "label": "Status",
                    "operation": "last_value",
                    "field": "autoops_es.cluster_health.status",
                    "data_type": "string",
                    "scale": "ordinal",
                    "filter": 'metricset.name: "cluster_health" and autoops_es.cluster_health.status: *',
                    "params": {"sortField": "@timestamp"},
                    "width": 90,
                },
                {
                    "id": "cluster-nodes",
                    "label": "Nodes",
                    "operation": "last_value",
                    "field": "autoops_es.cluster_health.number_of_nodes",
                    "filter": 'metricset.name: "cluster_health" and autoops_es.cluster_health.number_of_nodes: *',
                    "params": {"sortField": "@timestamp"},
                    "width": 70,
                },
                {
                    "id": "cluster-data-nodes",
                    "label": "Data Nodes",
                    "operation": "last_value",
                    "field": "autoops_es.cluster_health.number_of_data_nodes",
                    "filter": 'metricset.name: "cluster_health" and autoops_es.cluster_health.number_of_data_nodes: *',
                    "params": {"sortField": "@timestamp"},
                    "width": 90,
                },
                {
                    "id": "cluster-primary",
                    "label": "Active Primary",
                    "operation": "last_value",
                    "field": "autoops_es.cluster_health.active_primary_shards",
                    "filter": 'metricset.name: "cluster_health" and autoops_es.cluster_health.active_primary_shards: *',
                    "params": {"sortField": "@timestamp"},
                    "width": 110,
                },
                {
                    "id": "cluster-active-pct",
                    "label": "Active %",
                    "operation": "last_value",
                    "field": "autoops_es.cluster_health.active_shards_percent_as_number",
                    "filter": 'metricset.name: "cluster_health" and autoops_es.cluster_health.active_shards_percent_as_number: *',
                    "params": {"sortField": "@timestamp"},
                    "width": 80,
                },
                {
                    "id": "cluster-unassigned",
                    "label": "Unassigned",
                    "operation": "last_value",
                    "field": "autoops_es.cluster_health.unassigned_shards",
                    "filter": 'metricset.name: "cluster_health" and autoops_es.cluster_health.unassigned_shards: *',
                    "params": {"sortField": "@timestamp"},
                    "width": 90,
                },
                {
                    "id": "cluster-pending",
                    "label": "Pending",
                    "operation": "last_value",
                    "field": "autoops_es.cluster_health.number_of_pending_tasks",
                    "filter": 'metricset.name: "cluster_health" and autoops_es.cluster_health.number_of_pending_tasks: *',
                    "params": {"sortField": "@timestamp"},
                    "width": 80,
                },
            ],
        ),
        datatable_lens(
            "otel-lens-node-summary",
            "Node Summary",
            "autoops_es.node_stats.name",
            "Node",
            20,
            [
                {
                    "id": "node-heap",
                    "label": "Heap Used (GB)",
                    "operation": "last_value",
                    "field": "autoops_es.node_stats.jvm.mem.heap_used_in_bytes",
                    "filter": 'metricset.name: "node_stats" and autoops_es.node_stats.jvm.mem.heap_used_in_bytes: *',
                    "params": {"sortField": "@timestamp", "format": {"id": "bytes", "params": {"decimals": 1}}},
                    "width": 100,
                },
                {
                    "id": "node-heap-max",
                    "label": "Heap Max (GB)",
                    "operation": "last_value",
                    "field": "autoops_es.node_stats.jvm.mem.heap_max_in_bytes",
                    "filter": 'metricset.name: "node_stats" and autoops_es.node_stats.jvm.mem.heap_max_in_bytes: *',
                    "params": {"sortField": "@timestamp", "format": {"id": "bytes", "params": {"decimals": 1}}},
                    "width": 100,
                },
                {
                    "id": "node-heap-pct",
                    "label": "Heap %",
                    "operation": "last_value",
                    "field": "autoops_es.node_stats.jvm.mem.heap_used_percent",
                    "filter": 'metricset.name: "node_stats" and autoops_es.node_stats.jvm.mem.heap_used_percent: *',
                    "params": {"sortField": "@timestamp"},
                    "width": 75,
                },
                {
                    "id": "node-open-http",
                    "label": "Open HTTP",
                    "operation": "last_value",
                    "field": "autoops_es.node_stats.http.current_open",
                    "filter": 'metricset.name: "node_stats" and autoops_es.node_stats.http.current_open: *',
                    "params": {"sortField": "@timestamp"},
                    "width": 90,
                },
                {
                    "id": "node-search-rate",
                    "label": "Search /s",
                    "operation": "average",
                    "field": "autoops_es.node_stats.search_rate_per_second",
                    "filter": 'metricset.name: "node_stats" and autoops_es.node_stats.search_rate_per_second: *',
                    "params": {"emptyAsNull": True},
                    "width": 85,
                },
                {
                    "id": "node-index-rate",
                    "label": "Index /s",
                    "operation": "average",
                    "field": "autoops_es.node_stats.index_rate_per_second",
                    "filter": 'metricset.name: "node_stats" and autoops_es.node_stats.index_rate_per_second: *',
                    "params": {"emptyAsNull": True},
                    "width": 80,
                },
                {
                    "id": "node-search-queue",
                    "label": "Search Q",
                    "operation": "max",
                    "field": "autoops_es.node_stats.thread_pool.search.queue",
                    "filter": 'metricset.name: "node_stats" and autoops_es.node_stats.thread_pool.search.queue: *',
                    "params": {"emptyAsNull": True},
                    "width": 80,
                },
                {
                    "id": "node-write-queue",
                    "label": "Write Q",
                    "operation": "max",
                    "field": "autoops_es.node_stats.thread_pool.write.queue",
                    "filter": 'metricset.name: "node_stats" and autoops_es.node_stats.thread_pool.write.queue: *',
                    "params": {"emptyAsNull": True},
                    "width": 75,
                },
                {
                    "id": "node-search-rej",
                    "label": "Search Rej",
                    "operation": "max",
                    "field": "autoops_es.node_stats.thread_pool.search.rejected",
                    "filter": 'metricset.name: "node_stats" and autoops_es.node_stats.thread_pool.search.rejected: *',
                    "params": {"emptyAsNull": True},
                    "width": 85,
                },
                {
                    "id": "node-write-rej",
                    "label": "Write Rej",
                    "operation": "max",
                    "field": "autoops_es.node_stats.thread_pool.write.rejected",
                    "filter": 'metricset.name: "node_stats" and autoops_es.node_stats.thread_pool.write.rejected: *',
                    "params": {"emptyAsNull": True},
                    "width": 80,
                },
                {
                    "id": "node-parent-breaker",
                    "label": "Parent Trips",
                    "operation": "max",
                    "field": "autoops_es.node_stats.breakers.parent.tripped",
                    "filter": 'metricset.name: "node_stats" and autoops_es.node_stats.breakers.parent.tripped: *',
                    "params": {"emptyAsNull": True},
                    "width": 95,
                },
                {
                    "id": "node-request-breaker",
                    "label": "Request Trips",
                    "operation": "max",
                    "field": "autoops_es.node_stats.breakers.request.tripped",
                    "filter": 'metricset.name: "node_stats" and autoops_es.node_stats.breakers.request.tripped: *',
                    "params": {"emptyAsNull": True},
                    "width": 100,
                },
            ],
        ),
    ]
    objects.extend(lens_objects)

    panels = [
        markdown_panel(
            "otel-markdown-header",
            "Elasticsearch OTEL monitoring for logs-elasticsearch.metrics-main\n\nBuilt for the EDOT autoops_es metrics stream",
            0,
            0,
            48,
            3,
        ),
        dashboard_panel_ref("otel-panel-cluster-info", "Cluster Info", 0, 3, 48, 8, "otel-lens-cluster-info"),
        dashboard_panel_ref("otel-panel-nodes", "Nodes", 0, 11, 6, 5, "otel-lens-nodes"),
        dashboard_panel_ref("otel-panel-data-nodes", "Data Nodes", 6, 11, 6, 5, "otel-lens-data-nodes"),
        dashboard_panel_ref("otel-panel-unassigned", "Unassigned Shards", 12, 11, 6, 5, "otel-lens-unassigned-shards"),
        dashboard_panel_ref("otel-panel-pending", "Pending Tasks", 18, 11, 6, 5, "otel-lens-pending-tasks"),
        dashboard_panel_ref("otel-panel-active-primary", "Active Primary Shards", 24, 11, 6, 5, "otel-lens-active-primary-shards"),
        dashboard_panel_ref("otel-panel-active-pct", "Active Shards %", 30, 11, 6, 5, "otel-lens-active-shards-pct"),
        dashboard_panel_ref("otel-panel-initializing", "Initializing Shards", 36, 11, 6, 5, "otel-lens-initializing-shards"),
        dashboard_panel_ref("otel-panel-delayed", "Delayed Unassigned", 42, 11, 6, 5, "otel-lens-delayed-unassigned"),
        markdown_panel(
            "otel-markdown-throughput",
            "Throughput and latency",
            0,
            16,
            48,
            2,
        ),
        dashboard_panel_ref("otel-panel-search-rate", "Search Rate /s", 0, 18, 12, 7, "otel-lens-search-rate"),
        dashboard_panel_ref("otel-panel-index-rate", "Index Rate /s", 12, 18, 12, 7, "otel-lens-index-rate"),
        dashboard_panel_ref("otel-panel-search-latency", "Search Latency (ms)", 24, 18, 12, 7, "otel-lens-search-latency"),
        dashboard_panel_ref("otel-panel-index-failed", "Index Failed Rate /s", 36, 18, 12, 7, "otel-lens-index-failed-rate"),
        markdown_panel(
            "otel-markdown-pressure",
            "Thread pools and resource pressure",
            0,
            25,
            48,
            2,
        ),
        dashboard_panel_ref("otel-panel-search-queue", "Search Queue Max", 0, 27, 12, 7, "otel-lens-search-queue"),
        dashboard_panel_ref("otel-panel-write-queue", "Write Queue Max", 12, 27, 12, 7, "otel-lens-write-queue"),
        dashboard_panel_ref("otel-panel-search-rejected", "Search Rejected", 24, 27, 12, 7, "otel-lens-search-rejected"),
        dashboard_panel_ref("otel-panel-write-rejected", "Write Rejected", 36, 27, 12, 7, "otel-lens-write-rejected"),
        markdown_panel(
            "otel-markdown-resources",
            "Resources and shard distribution",
            0,
            34,
            48,
            2,
        ),
        dashboard_panel_ref("otel-panel-heap-used", "Heap Used (GB)", 0, 36, 12, 7, "otel-lens-heap-used"),
        dashboard_panel_ref("otel-panel-heap-max", "Heap Max (GB)", 12, 36, 12, 7, "otel-lens-heap-max"),
        dashboard_panel_ref("otel-panel-heap-pct", "Heap Used %", 24, 36, 12, 7, "otel-lens-heap-used-pct"),
        dashboard_panel_ref("otel-panel-open-http", "Open HTTP Connections", 36, 36, 12, 7, "otel-lens-open-http"),
        markdown_panel(
            "otel-markdown-jvm",
            "JVM, breakers, and shard distribution",
            0,
            43,
            48,
            2,
        ),
        dashboard_panel_ref("otel-panel-gc-young", "GC Young Time (ms)", 0, 45, 8, 7, "otel-lens-gc-young-time"),
        dashboard_panel_ref("otel-panel-gc-old", "GC Old Time (ms)", 8, 45, 8, 7, "otel-lens-gc-old-time"),
        dashboard_panel_ref("otel-panel-parent-breaker", "Parent Breaker Trips", 16, 45, 8, 7, "otel-lens-parent-breaker-tripped"),
        dashboard_panel_ref("otel-panel-request-breaker", "Request Breaker Trips", 24, 45, 8, 7, "otel-lens-request-breaker-tripped"),
        dashboard_panel_ref("otel-panel-node-shards", "Shard Count by Node", 32, 45, 8, 7, "otel-lens-node-shards"),
        dashboard_panel_ref("otel-panel-primary-shards", "Primary Shards by Node", 40, 45, 8, 7, "otel-lens-primary-shards"),
        dashboard_panel_ref("otel-panel-node-summary", "Node Summary", 0, 52, 48, 10, "otel-lens-node-summary"),
    ]

    references = []
    for panel in panels:
        if "panelRefName" in panel:
            references.append(
                {
                    "id": panel["embeddableConfig"]["savedObjectId"],
                    "name": f"{panel['panelIndex']}:{panel['panelRefName']}",
                    "type": "lens",
                }
            )

    objects.append(
        {
            "type": "dashboard",
            "id": DASHBOARD_ID,
            "attributes": {
                "title": "Elasticsearch OTEL monitoring for logs-elasticsearch.metrics-main",
                "description": "Built for the EDOT autoops_es metrics stream.",
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
                "kibanaSavedObjectMeta": {
                    "searchSourceJSON": json.dumps(
                        {
                            "query": {"language": "kuery", "query": ""},
                            "filter": [],
                        }
                    )
                },
                "version": 1,
            },
            "references": references,
        }
    )

    return objects


def main():
    repo_root = Path(__file__).resolve().parents[1]
    out_path = repo_root / "dashboards" / "elasticsearch-otel-monitoring-main.ndjson"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as fh:
        for obj in build_objects():
            fh.write(json.dumps(obj, separators=(",", ":")))
            fh.write("\n")
    print(out_path)


if __name__ == "__main__":
    main()
