#!/usr/bin/env python3

import json
from pathlib import Path


DATA_VIEW_ID = "otel-elasticsearch-agent-metrics-main"
DATA_VIEW_TITLE = "metrics-elasticsearch.stack_monitoring.*-main,-metrics-elasticsearch.stack_monitoring.otel-main"
DASHBOARD_ID = "otel-elasticsearch-monitoring-agent"
NODES_DASHBOARD_ID = "otel-elasticsearch-monitoring-agent-nodes"
INDICES_DASHBOARD_ID = "otel-elasticsearch-monitoring-agent-indices"
LINKS_ID = "otel-elasticsearch-monitoring-agent-links"
LENS_EXPORT_META = {
    "coreMigrationVersion": "8.8.0",
    "created_at": "2026-04-30T16:00:00.000Z",
    "created_by": "elastic",
    "managed": False,
    "typeMigrationVersion": "10.1.0",
    "updated_at": "2026-04-30T16:00:00.000Z",
    "updated_by": "elastic",
    "version": "WzEsMV0=",
}


def metric_lens(lens_id, title, field, filter_query, operation="max", params=None):
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
                                        "params": params or {"emptyAsNull": True},
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
        {"alignment": "left", "columnId": row_id, "isTransposed": False, "oneClickFilter": True, "width": 220},
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
                "query": {"language": "kuery", "query": ""},
                "visualization": {"columns": vis_columns, "layerId": layer_id, "layerType": "data"},
            },
        },
        "references": [{"id": DATA_VIEW_ID, "name": f"indexpattern-datasource-layer-{layer_id}", "type": "index-pattern"}],
    }
    obj.update(LENS_EXPORT_META)
    return obj


def terms_table_lens(lens_id, title, row_specs, row_size):
    layer_id = f"{lens_id}-layer"
    count_id = f"{lens_id}-count"
    columns = {}
    column_order = []
    vis_columns = []

    for idx, spec in enumerate(row_specs):
        row_id = f"{lens_id}-row-{idx}"
        columns[row_id] = {
            "customLabel": True,
            "dataType": "string",
            "isBucketed": True,
            "label": spec["label"],
            "operationType": "terms",
            "params": {
                "exclude": spec.get("exclude", []),
                "excludeIsRegex": False,
                "include": [],
                "includeIsRegex": False,
                "missingBucket": False,
                "orderBy": {"columnId": count_id, "type": "column"},
                "orderDirection": "desc",
                "otherBucket": False,
                "parentFormat": {"id": "terms"},
                "size": row_size,
            },
            "scale": "ordinal",
            "sourceField": spec["field"],
        }
        column_order.append(row_id)
        vis_columns.append({"alignment": "left", "columnId": row_id, "isTransposed": False, "oneClickFilter": True, "width": spec.get("width", 180)})

    columns[count_id] = {
        "dataType": "number",
        "isBucketed": False,
        "label": "Count of records",
        "operationType": "count",
        "params": {"emptyAsNull": True},
        "scale": "ratio",
        "sourceField": "___records___",
    }
    column_order.append(count_id)
    vis_columns.append({"columnId": count_id, "hidden": True, "isMetric": True, "isTransposed": False})

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
                "query": {"language": "kuery", "query": 'data_stream.dataset: "elasticsearch.stack_monitoring.cluster_stats" and elasticsearch.cluster.stats.status:*'},
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
                "title": "Agent Header",
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
        link_id = f"otel-agent-link-{label.lower()}"
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
            "title": "Elasticsearch monitoring navigation",
        },
        "references": references,
        "managed": False,
    }


def dashboard_references(panels):
    refs = []
    for panel in panels:
        if "panelRefName" not in panel:
            continue
        refs.append({"id": panel["embeddableConfig"]["savedObjectId"], "name": f"{panel['panelIndex']}:{panel['panelRefName']}", "type": panel["type"]})
    return refs


def control_group_and_references():
    specs = [
        ("cluster", "elasticsearch.cluster.name", "Cluster Name(s)", "medium", False),
        ("node", "elasticsearch.node.name", "Node(s)", "medium", True),
        ("index", "elasticsearch.index.name", "Index(s)", "large", True),
    ]
    control_panels = {}
    references = []
    for order, (suffix, field_name, title, width, grow) in enumerate(specs):
        control_id = f"otel-agent-control-{suffix}"
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
                "showApplySelections": False,
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
    }


def build_objects():
    field_format_map = {
        "elasticsearch.node.stats.jvm.mem.heap.used.bytes": {"id": "bytes"},
        "elasticsearch.node.stats.jvm.mem.heap.max.bytes": {"id": "bytes"},
        "elasticsearch.node.stats.indices.store.size.bytes": {"id": "bytes"},
        "elasticsearch.node.stats.indices.store.total_data_set_size.bytes": {"id": "bytes"},
        "elasticsearch.cluster.stats.indices.store.size.bytes": {"id": "bytes"},
        "elasticsearch.cluster.stats.indices.store.total_data_set_size.bytes": {"id": "bytes"},
        "elasticsearch.index.total.store.size_in_bytes": {"id": "bytes"},
        "elasticsearch.index.total.store.total_data_set_size_in_bytes": {"id": "bytes"},
        "elasticsearch.index.primaries.store.size_in_bytes": {"id": "bytes"},
        "elasticsearch.index.primaries.store.total_data_set_size_in_bytes": {"id": "bytes"},
    }
    objects = [
        {
            "type": "index-pattern",
            "id": DATA_VIEW_ID,
            "attributes": {
                "title": DATA_VIEW_TITLE,
                "name": "otel-elasticsearch-agent-metrics-main",
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
        terms_table_lens(
            "otel-agent-lens-health-status",
            "Cluster Health",
            [
                {"field": "elasticsearch.cluster.name", "label": "Cluster", "width": 220},
                {"field": "elasticsearch.cluster.stats.status", "label": "Status", "width": 140},
            ],
            20,
        ),
        metric_lens("otel-agent-lens-nodes", "Nodes", "elasticsearch.cluster.stats.nodes.count", 'data_stream.dataset: "elasticsearch.stack_monitoring.cluster_stats" and elasticsearch.cluster.stats.nodes.count:*'),
        metric_lens("otel-agent-lens-data-nodes", "Data Nodes", "elasticsearch.cluster.stats.nodes.data", 'data_stream.dataset: "elasticsearch.stack_monitoring.cluster_stats" and elasticsearch.cluster.stats.nodes.data:*'),
        metric_lens("otel-agent-lens-indices-count", "Indices", "elasticsearch.cluster.stats.indices.total", 'data_stream.dataset: "elasticsearch.stack_monitoring.cluster_stats" and elasticsearch.cluster.stats.indices.total:*'),
        metric_lens("otel-agent-lens-shards-count", "Shards", "elasticsearch.cluster.stats.indices.shards.count", 'data_stream.dataset: "elasticsearch.stack_monitoring.cluster_stats" and elasticsearch.cluster.stats.indices.shards.count:*'),
        metric_lens("otel-agent-lens-docs-total", "Docs", "elasticsearch.cluster.stats.indices.docs.total", 'data_stream.dataset: "elasticsearch.stack_monitoring.cluster_stats" and elasticsearch.cluster.stats.indices.docs.total:*'),
        metric_lens("otel-agent-lens-primary-shards", "Primary Shards", "elasticsearch.cluster.stats.indices.shards.primaries", 'data_stream.dataset: "elasticsearch.stack_monitoring.cluster_stats" and elasticsearch.cluster.stats.indices.shards.primaries:*'),
        metric_lens("otel-agent-lens-cluster-store-size", "Store Size", "elasticsearch.cluster.stats.indices.store.size.bytes", 'data_stream.dataset: "elasticsearch.stack_monitoring.cluster_stats" and elasticsearch.cluster.stats.indices.store.size.bytes:*'),
        xy_lens("otel-agent-lens-query-total", "Query Total", "elasticsearch.node.stats.indices.search.query_total.count", 'data_stream.dataset: "elasticsearch.stack_monitoring.node_stats" and elasticsearch.node.stats.indices.search.query_total.count:*', "max", "#348888"),
        xy_lens("otel-agent-lens-index-total", "Index Total", "elasticsearch.node.stats.indices.indexing.index_total.count", 'data_stream.dataset: "elasticsearch.stack_monitoring.node_stats" and elasticsearch.node.stats.indices.indexing.index_total.count:*', "max", "#d17c2d"),
        xy_lens("otel-agent-lens-heap-pct", "Heap Used %", "elasticsearch.node.stats.jvm.mem.heap.used.pct", 'data_stream.dataset: "elasticsearch.stack_monitoring.node_stats" and elasticsearch.node.stats.jvm.mem.heap.used.pct:*', "average", "#2f9c95"),
        xy_lens("otel-agent-lens-store-size", "Node Store Size", "elasticsearch.node.stats.indices.store.size.bytes", 'data_stream.dataset: "elasticsearch.stack_monitoring.node_stats" and elasticsearch.node.stats.indices.store.size.bytes:*', "sum", "#7aa95c"),
        xy_lens("otel-agent-lens-open-files", "Open Files", "elasticsearch.node.stats.process.open_file_descriptors", 'data_stream.dataset: "elasticsearch.stack_monitoring.node_stats" and elasticsearch.node.stats.process.open_file_descriptors:*', "max", "#6a8caf"),
        xy_lens("otel-agent-lens-cpu-pct", "CPU %", "elasticsearch.node.stats.process.cpu.pct", 'data_stream.dataset: "elasticsearch.stack_monitoring.node_stats" and elasticsearch.node.stats.process.cpu.pct:*', "average", "#7b6fd0"),
        xy_lens("otel-agent-lens-search-queue", "Search Queue", "elasticsearch.node.stats.thread_pool.search.queue.count", 'data_stream.dataset: "elasticsearch.stack_monitoring.node_stats" and elasticsearch.node.stats.thread_pool.search.queue.count:*', "average", "#7b6fd0"),
        xy_lens("otel-agent-lens-write-queue", "Write Queue", "elasticsearch.node.stats.thread_pool.write.queue.count", 'data_stream.dataset: "elasticsearch.stack_monitoring.node_stats" and elasticsearch.node.stats.thread_pool.write.queue.count:*', "average", "#d17c2d"),
        xy_lens("otel-agent-lens-search-rejected", "Search Rejected", "elasticsearch.node.stats.thread_pool.search.rejected.count", 'data_stream.dataset: "elasticsearch.stack_monitoring.node_stats" and elasticsearch.node.stats.thread_pool.search.rejected.count:*', "max", "#c2574c"),
        xy_lens("otel-agent-lens-write-rejected", "Write Rejected", "elasticsearch.node.stats.thread_pool.write.rejected.count", 'data_stream.dataset: "elasticsearch.stack_monitoring.node_stats" and elasticsearch.node.stats.thread_pool.write.rejected.count:*', "max", "#8c3a3a"),
        xy_lens("otel-agent-lens-young-gc", "Young GC Total", "elasticsearch.node.stats.jvm.gc.collectors.young.collection.ms", 'data_stream.dataset: "elasticsearch.stack_monitoring.node_stats" and elasticsearch.node.stats.jvm.gc.collectors.young.collection.ms:*', "max", "#b0922e"),
        xy_lens("otel-agent-lens-old-gc", "Old GC Total", "elasticsearch.node.stats.jvm.gc.collectors.old.collection.ms", 'data_stream.dataset: "elasticsearch.stack_monitoring.node_stats" and elasticsearch.node.stats.jvm.gc.collectors.old.collection.ms:*', "max", "#7b4f9e"),
        xy_lens("otel-agent-lens-index-docs", "Index Docs", "elasticsearch.index.total.docs.count", 'data_stream.dataset: "elasticsearch.stack_monitoring.index" and elasticsearch.index.total.docs.count:*', "max", "#4f86c6"),
        xy_lens("otel-agent-lens-index-size", "Index Size", "elasticsearch.index.total.store.size_in_bytes", 'data_stream.dataset: "elasticsearch.stack_monitoring.index" and elasticsearch.index.total.store.size_in_bytes:*', "max", "#7aa95c"),
        xy_lens("otel-agent-lens-index-segments", "Segments", "elasticsearch.index.total.segments.count", 'data_stream.dataset: "elasticsearch.stack_monitoring.index" and elasticsearch.index.total.segments.count:*', "max", "#7b6fd0"),
        xy_lens("otel-agent-lens-index-query-total", "Index Query Total", "elasticsearch.index.total.search.query_total", 'data_stream.dataset: "elasticsearch.stack_monitoring.index" and elasticsearch.index.total.search.query_total:*', "max", "#348888"),
        xy_lens("otel-agent-lens-index-write-total", "Index Write Total", "elasticsearch.index.total.indexing.index_total", 'data_stream.dataset: "elasticsearch.stack_monitoring.index" and elasticsearch.index.total.indexing.index_total:*', "max", "#d17c2d"),
        datatable_lens(
            "otel-agent-lens-cluster-info",
            "Cluster Info",
            "elasticsearch.cluster.name",
            "Cluster",
            10,
            [
                {"id": "otel-agent-cluster-nodes", "label": "Nodes", "operation": "max", "field": "elasticsearch.cluster.stats.nodes.count", "filter": 'data_stream.dataset: "elasticsearch.stack_monitoring.cluster_stats" and elasticsearch.cluster.stats.nodes.count:*'},
                {"id": "otel-agent-cluster-data", "label": "Data Nodes", "operation": "max", "field": "elasticsearch.cluster.stats.nodes.data", "filter": 'data_stream.dataset: "elasticsearch.stack_monitoring.cluster_stats" and elasticsearch.cluster.stats.nodes.data:*', "width": 120},
                {"id": "otel-agent-cluster-shards", "label": "Shards", "operation": "max", "field": "elasticsearch.cluster.stats.indices.shards.count", "filter": 'data_stream.dataset: "elasticsearch.stack_monitoring.cluster_stats" and elasticsearch.cluster.stats.indices.shards.count:*'},
                {"id": "otel-agent-cluster-docs", "label": "Docs", "operation": "max", "field": "elasticsearch.cluster.stats.indices.docs.total", "filter": 'data_stream.dataset: "elasticsearch.stack_monitoring.cluster_stats" and elasticsearch.cluster.stats.indices.docs.total:*', "width": 120},
            ],
        ),
        datatable_lens(
            "otel-agent-lens-node-summary",
            "Node Summary",
            "elasticsearch.node.name",
            "Node",
            20,
            [
                {"id": "otel-agent-node-heap-used", "label": "Heap Used", "operation": "max", "field": "elasticsearch.node.stats.jvm.mem.heap.used.bytes", "filter": 'data_stream.dataset: "elasticsearch.stack_monitoring.node_stats" and elasticsearch.node.stats.jvm.mem.heap.used.bytes:*', "width": 130},
                {"id": "otel-agent-node-heap-max", "label": "Heap Max", "operation": "max", "field": "elasticsearch.node.stats.jvm.mem.heap.max.bytes", "filter": 'data_stream.dataset: "elasticsearch.stack_monitoring.node_stats" and elasticsearch.node.stats.jvm.mem.heap.max.bytes:*', "width": 130},
                {"id": "otel-agent-node-heap-pct", "label": "Heap %", "operation": "average", "field": "elasticsearch.node.stats.jvm.mem.heap.used.pct", "filter": 'data_stream.dataset: "elasticsearch.stack_monitoring.node_stats" and elasticsearch.node.stats.jvm.mem.heap.used.pct:*'},
                {"id": "otel-agent-node-cpu", "label": "CPU %", "operation": "average", "field": "elasticsearch.node.stats.process.cpu.pct", "filter": 'data_stream.dataset: "elasticsearch.stack_monitoring.node_stats" and elasticsearch.node.stats.process.cpu.pct:*'},
                {"id": "otel-agent-node-open-files", "label": "Open Files", "operation": "max", "field": "elasticsearch.node.stats.process.open_file_descriptors", "filter": 'data_stream.dataset: "elasticsearch.stack_monitoring.node_stats" and elasticsearch.node.stats.process.open_file_descriptors:*', "width": 120},
                {"id": "otel-agent-node-search-total", "label": "Query Total", "operation": "max", "field": "elasticsearch.node.stats.indices.search.query_total.count", "filter": 'data_stream.dataset: "elasticsearch.stack_monitoring.node_stats" and elasticsearch.node.stats.indices.search.query_total.count:*', "width": 120},
                {"id": "otel-agent-node-index-total", "label": "Index Total", "operation": "max", "field": "elasticsearch.node.stats.indices.indexing.index_total.count", "filter": 'data_stream.dataset: "elasticsearch.stack_monitoring.node_stats" and elasticsearch.node.stats.indices.indexing.index_total.count:*', "width": 120},
            ],
        ),
        datatable_lens(
            "otel-agent-lens-index-summary",
            "Index Activity",
            "elasticsearch.index.name",
            "Index",
            20,
            [
                {"id": "otel-agent-index-docs-table", "label": "Docs", "operation": "max", "field": "elasticsearch.index.total.docs.count", "filter": 'data_stream.dataset: "elasticsearch.stack_monitoring.index" and elasticsearch.index.total.docs.count:*', "width": 120},
                {"id": "otel-agent-index-size-table", "label": "Size", "operation": "max", "field": "elasticsearch.index.total.store.size_in_bytes", "filter": 'data_stream.dataset: "elasticsearch.stack_monitoring.index" and elasticsearch.index.total.store.size_in_bytes:*', "width": 130},
                {"id": "otel-agent-index-primaries-table", "label": "Primary Shards", "operation": "max", "field": "elasticsearch.index.shards.primaries", "filter": 'data_stream.dataset: "elasticsearch.stack_monitoring.index" and elasticsearch.index.shards.primaries:*', "width": 120},
                {"id": "otel-agent-index-total-shards-table", "label": "Total Shards", "operation": "max", "field": "elasticsearch.index.shards.total", "filter": 'data_stream.dataset: "elasticsearch.stack_monitoring.index" and elasticsearch.index.shards.total:*', "width": 120},
                {"id": "otel-agent-index-segments-table", "label": "Segments", "operation": "max", "field": "elasticsearch.index.total.segments.count", "filter": 'data_stream.dataset: "elasticsearch.stack_monitoring.index" and elasticsearch.index.total.segments.count:*'},
                {"id": "otel-agent-index-query-total-table", "label": "Query Total", "operation": "max", "field": "elasticsearch.index.total.search.query_total", "filter": 'data_stream.dataset: "elasticsearch.stack_monitoring.index" and elasticsearch.index.total.search.query_total:*', "width": 120},
                {"id": "otel-agent-index-write-total-table", "label": "Write Total", "operation": "max", "field": "elasticsearch.index.total.indexing.index_total", "filter": 'data_stream.dataset: "elasticsearch.stack_monitoring.index" and elasticsearch.index.total.indexing.index_total:*', "width": 120},
            ],
        ),
        datatable_lens(
            "otel-agent-lens-shard-summary",
            "Shard Layout",
            "elasticsearch.index.name",
            "Index",
            20,
            [
                {"id": "otel-agent-shard-node", "label": "Records", "operation": "count", "field": "___records___", "filter": 'data_stream.dataset: "elasticsearch.stack_monitoring.shard" and elasticsearch.shard.state:*', "width": 100},
                {"id": "otel-agent-shard-primary", "label": "Primary Count", "operation": "count", "field": "___records___", "filter": 'data_stream.dataset: "elasticsearch.stack_monitoring.shard" and elasticsearch.shard.primary: true', "width": 120},
            ],
        ),
    ]
    objects.extend(lens_objects)
    objects.append(links_saved_object())

    overview_panels = [
        links_panel_ref("otel-agent-panel-links-overview", "Navigation", 0, 0, 48, 3, LINKS_ID),
        markdown_panel("otel-agent-markdown-overview", "## Elasticsearch monitoring overview\nElastic Agent with EDOT runtime using Beat receivers and ECS-compatible routing.", 0, 3, 48, 3),
        dashboard_panel_ref("otel-agent-panel-cluster-info", "Cluster Info", 0, 6, 34, 8, "otel-agent-lens-cluster-info"),
        dashboard_panel_ref("otel-agent-panel-health", "Cluster Health", 34, 6, 14, 8, "otel-agent-lens-health-status"),
        dashboard_panel_ref("otel-agent-panel-nodes", "Nodes", 0, 14, 6, 5, "otel-agent-lens-nodes"),
        dashboard_panel_ref("otel-agent-panel-data-nodes", "Data Nodes", 6, 14, 6, 5, "otel-agent-lens-data-nodes"),
        dashboard_panel_ref("otel-agent-panel-indices", "Indices", 12, 14, 6, 5, "otel-agent-lens-indices-count"),
        dashboard_panel_ref("otel-agent-panel-shards", "Shards", 18, 14, 6, 5, "otel-agent-lens-shards-count"),
        dashboard_panel_ref("otel-agent-panel-docs", "Docs", 24, 14, 6, 5, "otel-agent-lens-docs-total"),
        dashboard_panel_ref("otel-agent-panel-primary-shards", "Primary Shards", 30, 14, 6, 5, "otel-agent-lens-primary-shards"),
        dashboard_panel_ref("otel-agent-panel-cluster-store-size", "Store Size", 36, 14, 6, 5, "otel-agent-lens-cluster-store-size"),
        dashboard_panel_ref("otel-agent-panel-heap-pct", "Heap Used %", 0, 19, 12, 7, "otel-agent-lens-heap-pct"),
        dashboard_panel_ref("otel-agent-panel-query-total", "Query Total", 12, 19, 12, 7, "otel-agent-lens-query-total"),
        dashboard_panel_ref("otel-agent-panel-index-total", "Index Total", 24, 19, 12, 7, "otel-agent-lens-index-total"),
        dashboard_panel_ref("otel-agent-panel-store-size", "Node Store Size", 36, 19, 12, 7, "otel-agent-lens-store-size"),
    ]

    nodes_panels = [
        links_panel_ref("otel-agent-panel-links-nodes", "Navigation", 0, 0, 48, 3, LINKS_ID),
        markdown_panel("otel-agent-markdown-nodes", "## Elasticsearch monitoring nodes\nJVM, CPU, open files, queues, rejections, and node summaries from the Elasticsearch integration.", 0, 3, 48, 3),
        dashboard_panel_ref("otel-agent-panel-open-files", "Open Files", 0, 6, 12, 7, "otel-agent-lens-open-files"),
        dashboard_panel_ref("otel-agent-panel-cpu-pct", "CPU %", 12, 6, 12, 7, "otel-agent-lens-cpu-pct"),
        dashboard_panel_ref("otel-agent-panel-search-queue", "Search Queue", 24, 6, 12, 7, "otel-agent-lens-search-queue"),
        dashboard_panel_ref("otel-agent-panel-write-queue", "Write Queue", 36, 6, 12, 7, "otel-agent-lens-write-queue"),
        dashboard_panel_ref("otel-agent-panel-search-rejected", "Search Rejected", 0, 13, 12, 7, "otel-agent-lens-search-rejected"),
        dashboard_panel_ref("otel-agent-panel-write-rejected", "Write Rejected", 12, 13, 12, 7, "otel-agent-lens-write-rejected"),
        dashboard_panel_ref("otel-agent-panel-young-gc", "Young GC Total", 24, 13, 12, 7, "otel-agent-lens-young-gc"),
        dashboard_panel_ref("otel-agent-panel-old-gc", "Old GC Total", 36, 13, 12, 7, "otel-agent-lens-old-gc"),
        dashboard_panel_ref("otel-agent-panel-node-summary", "Node Summary", 0, 20, 48, 14, "otel-agent-lens-node-summary"),
    ]

    indices_panels = [
        links_panel_ref("otel-agent-panel-links-indices", "Navigation", 0, 0, 48, 3, LINKS_ID),
        markdown_panel("otel-agent-markdown-indices", "## Elasticsearch monitoring indices\nPer-index docs, size, segments, query totals, write totals, and shard layout.", 0, 3, 48, 3),
        dashboard_panel_ref("otel-agent-panel-index-docs", "Index Docs", 0, 6, 12, 7, "otel-agent-lens-index-docs"),
        dashboard_panel_ref("otel-agent-panel-index-size", "Index Size", 12, 6, 12, 7, "otel-agent-lens-index-size"),
        dashboard_panel_ref("otel-agent-panel-index-segments", "Segments", 24, 6, 12, 7, "otel-agent-lens-index-segments"),
        dashboard_panel_ref("otel-agent-panel-index-query-total", "Index Query Total", 0, 13, 12, 7, "otel-agent-lens-index-query-total"),
        dashboard_panel_ref("otel-agent-panel-index-write-total", "Index Write Total", 12, 13, 12, 7, "otel-agent-lens-index-write-total"),
        dashboard_panel_ref("otel-agent-panel-index-summary", "Index Activity", 0, 20, 48, 12, "otel-agent-lens-index-summary"),
        dashboard_panel_ref("otel-agent-panel-shard-summary", "Shard Layout", 0, 32, 48, 10, "otel-agent-lens-shard-summary"),
    ]

    objects.extend(
        [
            dashboard_object(
                DASHBOARD_ID,
                "Elasticsearch monitoring - Elastic Agent overview",
                "Overview dashboard for Elasticsearch stack monitoring metrics collected by Elastic Agent with EDOT runtime.",
                overview_panels,
            ),
            dashboard_object(
                NODES_DASHBOARD_ID,
                "Elasticsearch monitoring - Elastic Agent nodes",
                "Node dashboard for Elasticsearch stack monitoring metrics collected by Elastic Agent with EDOT runtime.",
                nodes_panels,
            ),
            dashboard_object(
                INDICES_DASHBOARD_ID,
                "Elasticsearch monitoring - Elastic Agent indices",
                "Index dashboard for Elasticsearch stack monitoring metrics collected by Elastic Agent with EDOT runtime.",
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

    ndjson_path = out_dir / "elasticsearch-otel-monitoring-agent.ndjson"
    export_json_path = out_dir / "elasticsearch-otel-monitoring-agent.export.json"

    with ndjson_path.open("w", encoding="utf-8") as fh:
        for obj in objects:
            fh.write(json.dumps(obj, separators=(",", ":")) + "\n")

    with export_json_path.open("w", encoding="utf-8") as fh:
        json.dump(
            {
                "description": "Structured export wrapper for the Elastic Agent EDOT Elasticsearch monitoring dashboards. Convert to NDJSON for Kibana UI import.",
                "objects": objects,
            },
            fh,
            indent=2,
        )
        fh.write("\n")


if __name__ == "__main__":
    main()
