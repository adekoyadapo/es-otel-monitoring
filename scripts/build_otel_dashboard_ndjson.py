#!/usr/bin/env python3

import json
from pathlib import Path


DATA_VIEW_ID = "otel-elasticsearch-metrics-main"
DASHBOARD_ID = "otel-elasticsearch-monitoring-main"
NODES_DASHBOARD_ID = "otel-elasticsearch-monitoring-nodes"
INDICES_DASHBOARD_ID = "otel-elasticsearch-monitoring-indices"
LINKS_ID = "otel-elasticsearch-monitoring-links"
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


def links_panel_ref(panel_id, title, x, y, w, h, links_id):
    return {
        "type": "links",
        "panelRefName": f"panel_{panel_id}",
        "panelIndex": panel_id,
        "gridData": {"i": panel_id, "x": x, "y": y, "w": w, "h": h},
        "embeddableConfig": {
            "enhancements": {},
            "savedObjectId": links_id,
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


def links_saved_object():
    link_specs = [
        ("Overview", DASHBOARD_ID, 0),
        ("Nodes", NODES_DASHBOARD_ID, 1),
        ("Indices", INDICES_DASHBOARD_ID, 2),
    ]
    links = []
    references = []
    for label, dashboard_id, order in link_specs:
        link_id = f"otel-link-{label.lower()}"
        ref_name = f"link_{link_id}_dashboard"
        links.append(
            {
                "destinationRefName": ref_name,
                "id": link_id,
                "label": label,
                "options": {
                    "openInNewTab": False,
                    "useCurrentDateRange": True,
                    "useCurrentFilters": True,
                },
                "order": order,
                "type": "dashboardLink",
            }
        )
        references.append({"id": dashboard_id, "name": ref_name, "type": "dashboard"})

    return {
        "type": "links",
        "id": LINKS_ID,
        "attributes": {
            "description": "",
            "layout": "horizontal",
            "links": links,
            "title": "Elasticsearch OTEL Navigation",
        },
        "references": references,
        "managed": False,
    }


def dashboard_references(panels):
    references = []
    for panel in panels:
        if "panelRefName" not in panel:
            continue
        references.append(
            {
                "id": panel["embeddableConfig"]["savedObjectId"],
                "name": f"{panel['panelIndex']}:{panel['panelRefName']}",
                "type": panel["type"],
            }
        )
    return references


def control_group_and_references():
    cluster_name_control_id = "otel-control-cluster-name"
    cluster_id_control_id = "otel-control-cluster-id"
    node_name_control_id = "otel-control-node-name"
    control_panels = {
        cluster_name_control_id: {
            "explicitInput": {
                "dataViewId": DATA_VIEW_ID,
                "exclude": False,
                "existsSelected": False,
                "fieldName": "autoops_es.cluster.name",
                "runPastTimeout": True,
                "searchTechnique": "wildcard",
                "selectedOptions": [],
                "sort": {"by": "_count", "direction": "desc"},
                "title": "Cluster Name(s)",
            },
            "grow": False,
            "order": 0,
            "type": "optionsListControl",
            "width": "medium",
        },
        cluster_id_control_id: {
            "explicitInput": {
                "dataViewId": DATA_VIEW_ID,
                "exclude": False,
                "existsSelected": False,
                "fieldName": "autoops_es.cluster.id",
                "runPastTimeout": True,
                "searchTechnique": "wildcard",
                "selectedOptions": [],
                "sort": {"by": "_count", "direction": "desc"},
                "title": "Cluster ID(s)",
            },
            "grow": True,
            "order": 1,
            "type": "optionsListControl",
            "width": "medium",
        },
        node_name_control_id: {
            "explicitInput": {
                "dataViewId": DATA_VIEW_ID,
                "exclude": False,
                "existsSelected": False,
                "fieldName": "autoops_es.node_stats.name",
                "runPastTimeout": True,
                "searchTechnique": "wildcard",
                "selectedOptions": [],
                "sort": {"by": "_count", "direction": "desc"},
                "title": "Node(s)",
            },
            "grow": True,
            "order": 2,
            "type": "optionsListControl",
            "width": "small",
        },
    }
    references = [
        {
            "id": DATA_VIEW_ID,
            "name": f"controlGroup_{cluster_name_control_id}:optionsListDataView",
            "type": "index-pattern",
        },
        {
            "id": DATA_VIEW_ID,
            "name": f"controlGroup_{cluster_id_control_id}:optionsListDataView",
            "type": "index-pattern",
        },
        {
            "id": DATA_VIEW_ID,
            "name": f"controlGroup_{node_name_control_id}:optionsListDataView",
            "type": "index-pattern",
        },
    ]
    return control_panels, references


def dashboard_object(dashboard_id, title, description, panels):
    control_panels, control_references = control_group_and_references()
    references = dashboard_references(panels)
    references.extend(control_references)
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


def build_objects():
    objects = [
        {
            "type": "index-pattern",
            "id": DATA_VIEW_ID,
            "attributes": {
                "title": "metrics-elasticsearch.autoops-main",
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
            "otel-lens-cpu-percent",
            "CPU %",
            "autoops_es.node_stats.process.cpu.percent",
            "max",
            'metricset.name: "node_stats" and autoops_es.node_stats.process.cpu.percent: * and autoops_es.node_stats.name: *',
            "#E7664C",
        ),
        xy_lens(
            "otel-lens-disk-available",
            "Disk Available (GB)",
            "autoops_es.node_stats.fs.total.available_in_bytes",
            "max",
            'metricset.name: "node_stats" and autoops_es.node_stats.fs.total.available_in_bytes: * and autoops_es.node_stats.name: *',
            "#54B399",
            {"format": {"id": "bytes", "params": {"decimals": 1}}},
        ),
        xy_lens(
            "otel-lens-store-size",
            "Store Size (GB)",
            "autoops_es.node_stats.indices.store.size_in_bytes",
            "max",
            'metricset.name: "node_stats" and autoops_es.node_stats.indices.store.size_in_bytes: * and autoops_es.node_stats.name: *',
            "#6092C0",
            {"format": {"id": "bytes", "params": {"decimals": 1}}},
        ),
        xy_lens(
            "otel-lens-segments-count",
            "Segments Count",
            "autoops_es.node_stats.indices.segments.count",
            "max",
            'metricset.name: "node_stats" and autoops_es.node_stats.indices.segments.count: * and autoops_es.node_stats.name: *',
            "#9170B8",
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
            "otel-lens-merge-rate",
            "Merge Rate /s",
            "autoops_es.node_stats.merge_rate_per_second",
            "average",
            'metricset.name: "node_stats" and autoops_es.node_stats.merge_rate_per_second: * and autoops_es.node_stats.name: *',
            "#DA8B45",
        ),
        xy_lens(
            "otel-lens-merge-latency",
            "Merge Latency (ms)",
            "autoops_es.node_stats.merge_latency_in_millis",
            "average",
            'metricset.name: "node_stats" and autoops_es.node_stats.merge_latency_in_millis: * and autoops_es.node_stats.name: *',
            "#B95F0B",
        ),
        xy_lens(
            "otel-lens-open-file-descriptors",
            "Open File Descriptors",
            "autoops_es.node_stats.process.open_file_descriptors",
            "max",
            'metricset.name: "node_stats" and autoops_es.node_stats.process.open_file_descriptors: * and autoops_es.node_stats.name: *',
            "#E7664C",
        ),
        xy_lens(
            "otel-lens-max-file-descriptors",
            "Max File Descriptors",
            "autoops_es.node_stats.process.max_file_descriptors",
            "max",
            'metricset.name: "node_stats" and autoops_es.node_stats.process.max_file_descriptors: * and autoops_es.node_stats.name: *',
            "#CA8EAE",
        ),
        xy_lens(
            "otel-lens-http-total-opened",
            "HTTP Opened Total",
            "autoops_es.node_stats.http.total_opened",
            "max",
            'metricset.name: "node_stats" and autoops_es.node_stats.http.total_opened: * and autoops_es.node_stats.name: *',
            "#54B399",
        ),
        xy_lens(
            "otel-lens-query-cache-hits",
            "Query Cache Hits",
            "autoops_es.node_stats.indices.query_cache.hit_count",
            "max",
            'metricset.name: "node_stats" and autoops_es.node_stats.indices.query_cache.hit_count: * and autoops_es.node_stats.name: *',
            "#6092C0",
        ),
        xy_lens(
            "otel-lens-query-cache-misses",
            "Query Cache Misses",
            "autoops_es.node_stats.indices.query_cache.miss_count",
            "max",
            'metricset.name: "node_stats" and autoops_es.node_stats.indices.query_cache.miss_count: * and autoops_es.node_stats.name: *',
            "#9170B8",
        ),
        xy_lens(
            "otel-lens-query-cache-evictions",
            "Query Cache Evictions",
            "autoops_es.node_stats.indices.query_cache.evictions",
            "max",
            'metricset.name: "node_stats" and autoops_es.node_stats.indices.query_cache.evictions: * and autoops_es.node_stats.name: *',
            "#BD271E",
        ),
        xy_lens(
            "otel-lens-request-cache-hits",
            "Request Cache Hits",
            "autoops_es.node_stats.indices.request_cache.hit_count",
            "max",
            'metricset.name: "node_stats" and autoops_es.node_stats.indices.request_cache.hit_count: * and autoops_es.node_stats.name: *',
            "#1EA593",
        ),
        xy_lens(
            "otel-lens-request-cache-misses",
            "Request Cache Misses",
            "autoops_es.node_stats.indices.request_cache.miss_count",
            "max",
            'metricset.name: "node_stats" and autoops_es.node_stats.indices.request_cache.miss_count: * and autoops_es.node_stats.name: *',
            "#D6BF57",
        ),
        xy_lens(
            "otel-lens-request-cache-evictions",
            "Request Cache Evictions",
            "autoops_es.node_stats.indices.request_cache.evictions",
            "max",
            'metricset.name: "node_stats" and autoops_es.node_stats.indices.request_cache.evictions: * and autoops_es.node_stats.name: *',
            "#F04E98",
        ),
        xy_lens(
            "otel-lens-docs-count",
            "Docs Count",
            "autoops_es.node_stats.indices.docs.count",
            "max",
            'metricset.name: "node_stats" and autoops_es.node_stats.indices.docs.count: * and autoops_es.node_stats.name: *',
            "#54B399",
        ),
        xy_lens(
            "otel-lens-total-data-set-size",
            "Total Data Set Size (GB)",
            "autoops_es.node_stats.indices.store.total_data_set_size_in_bytes",
            "max",
            'metricset.name: "node_stats" and autoops_es.node_stats.indices.store.total_data_set_size_in_bytes: * and autoops_es.node_stats.name: *',
            "#6092C0",
            {"format": {"id": "bytes", "params": {"decimals": 1}}},
        ),
        xy_lens(
            "otel-lens-segments-memory",
            "Segments Memory (GB)",
            "autoops_es.node_stats.indices.segments.memory_in_bytes",
            "max",
            'metricset.name: "node_stats" and autoops_es.node_stats.indices.segments.memory_in_bytes: * and autoops_es.node_stats.name: *',
            "#9170B8",
            {"format": {"id": "bytes", "params": {"decimals": 1}}},
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
                    "id": "node-cpu",
                    "label": "CPU %",
                    "operation": "last_value",
                    "field": "autoops_es.node_stats.process.cpu.percent",
                    "filter": 'metricset.name: "node_stats" and autoops_es.node_stats.process.cpu.percent: *',
                    "params": {"sortField": "@timestamp"},
                    "width": 75,
                },
                {
                    "id": "node-disk-available",
                    "label": "Disk Avail",
                    "operation": "last_value",
                    "field": "autoops_es.node_stats.fs.total.available_in_bytes",
                    "filter": 'metricset.name: "node_stats" and autoops_es.node_stats.fs.total.available_in_bytes: *',
                    "params": {"sortField": "@timestamp", "format": {"id": "bytes", "params": {"decimals": 1}}},
                    "width": 105,
                },
                {
                    "id": "node-store-size",
                    "label": "Store Size",
                    "operation": "last_value",
                    "field": "autoops_es.node_stats.indices.store.size_in_bytes",
                    "filter": 'metricset.name: "node_stats" and autoops_es.node_stats.indices.store.size_in_bytes: *',
                    "params": {"sortField": "@timestamp", "format": {"id": "bytes", "params": {"decimals": 1}}},
                    "width": 105,
                },
                {
                    "id": "node-data-set-size",
                    "label": "Data Set",
                    "operation": "last_value",
                    "field": "autoops_es.node_stats.indices.store.total_data_set_size_in_bytes",
                    "filter": 'metricset.name: "node_stats" and autoops_es.node_stats.indices.store.total_data_set_size_in_bytes: *',
                    "params": {"sortField": "@timestamp", "format": {"id": "bytes", "params": {"decimals": 1}}},
                    "width": 105,
                },
                {
                    "id": "node-docs-count",
                    "label": "Docs",
                    "operation": "last_value",
                    "field": "autoops_es.node_stats.indices.docs.count",
                    "filter": 'metricset.name: "node_stats" and autoops_es.node_stats.indices.docs.count: *',
                    "params": {"sortField": "@timestamp"},
                    "width": 95,
                },
                {
                    "id": "node-segments",
                    "label": "Segments",
                    "operation": "last_value",
                    "field": "autoops_es.node_stats.indices.segments.count",
                    "filter": 'metricset.name: "node_stats" and autoops_es.node_stats.indices.segments.count: *',
                    "params": {"sortField": "@timestamp"},
                    "width": 85,
                },
                {
                    "id": "node-open-fds",
                    "label": "Open FDs",
                    "operation": "last_value",
                    "field": "autoops_es.node_stats.process.open_file_descriptors",
                    "filter": 'metricset.name: "node_stats" and autoops_es.node_stats.process.open_file_descriptors: *',
                    "params": {"sortField": "@timestamp"},
                    "width": 85,
                },
                {
                    "id": "node-max-fds",
                    "label": "Max FDs",
                    "operation": "last_value",
                    "field": "autoops_es.node_stats.process.max_file_descriptors",
                    "filter": 'metricset.name: "node_stats" and autoops_es.node_stats.process.max_file_descriptors: *',
                    "params": {"sortField": "@timestamp"},
                    "width": 85,
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
        datatable_lens(
            "otel-lens-index-inventory",
            "Index Inventory",
            "autoops_es.cat_shards.node_index_shards.index",
            "Index",
            50,
            [
                {
                    "id": "index-status",
                    "label": "Status",
                    "operation": "last_value",
                    "field": "autoops_es.cat_shards.node_index_shards.index_status",
                    "data_type": "string",
                    "scale": "ordinal",
                    "filter": 'metricset.name: "cat_shards" and autoops_es.cat_shards.node_index_shards.index_status: *',
                    "params": {"sortField": "@timestamp"},
                    "width": 80,
                },
                {
                    "id": "index-size",
                    "label": "Total Size",
                    "operation": "max",
                    "field": "autoops_es.cat_shards.node_index_shards.total_size_in_bytes",
                    "filter": 'metricset.name: "cat_shards" and autoops_es.cat_shards.node_index_shards.total_size_in_bytes: *',
                    "params": {"emptyAsNull": True, "format": {"id": "bytes", "params": {"decimals": 1}}},
                    "width": 105,
                },
                {
                    "id": "index-max-shard",
                    "label": "Max Shard",
                    "operation": "max",
                    "field": "autoops_es.cat_shards.node_index_shards.max_shard_size_in_bytes",
                    "filter": 'metricset.name: "cat_shards" and autoops_es.cat_shards.node_index_shards.max_shard_size_in_bytes: *',
                    "params": {"emptyAsNull": True, "format": {"id": "bytes", "params": {"decimals": 1}}},
                    "width": 105,
                },
                {
                    "id": "index-docs",
                    "label": "Docs",
                    "operation": "max",
                    "field": "autoops_es.cat_shards.node_index_shards.docs_count",
                    "filter": 'metricset.name: "cat_shards" and autoops_es.cat_shards.node_index_shards.docs_count: *',
                    "params": {"emptyAsNull": True},
                    "width": 90,
                },
                {
                    "id": "index-segments",
                    "label": "Segments",
                    "operation": "max",
                    "field": "autoops_es.cat_shards.node_index_shards.segments_count",
                    "filter": 'metricset.name: "cat_shards" and autoops_es.cat_shards.node_index_shards.segments_count: *',
                    "params": {"emptyAsNull": True},
                    "width": 90,
                },
                {
                    "id": "index-search-rate",
                    "label": "Search /s",
                    "operation": "max",
                    "field": "autoops_es.cat_shards.node_index_shards.search_rate_per_second",
                    "filter": 'metricset.name: "cat_shards" and autoops_es.cat_shards.node_index_shards.search_rate_per_second: *',
                    "params": {"emptyAsNull": True},
                    "width": 90,
                },
                {
                    "id": "index-rate",
                    "label": "Index /s",
                    "operation": "max",
                    "field": "autoops_es.cat_shards.node_index_shards.index_rate_per_second",
                    "filter": 'metricset.name: "cat_shards" and autoops_es.cat_shards.node_index_shards.index_rate_per_second: *',
                    "params": {"emptyAsNull": True},
                    "width": 85,
                },
                {
                    "id": "index-failed-rate",
                    "label": "Failed /s",
                    "operation": "max",
                    "field": "autoops_es.cat_shards.node_index_shards.index_failed_rate_per_second",
                    "filter": 'metricset.name: "cat_shards" and autoops_es.cat_shards.node_index_shards.index_failed_rate_per_second: *',
                    "params": {"emptyAsNull": True},
                    "width": 90,
                },
                {
                    "id": "index-primary-count",
                    "label": "Primary",
                    "operation": "max",
                    "field": "autoops_es.cat_shards.node_index_shards.primary_shards_count",
                    "filter": 'metricset.name: "cat_shards" and autoops_es.cat_shards.node_index_shards.primary_shards_count: *',
                    "params": {"emptyAsNull": True},
                    "width": 80,
                },
                {
                    "id": "index-replica-count",
                    "label": "Replica",
                    "operation": "max",
                    "field": "autoops_es.cat_shards.node_index_shards.replica_shards_count",
                    "filter": 'metricset.name: "cat_shards" and autoops_es.cat_shards.node_index_shards.replica_shards_count: *',
                    "params": {"emptyAsNull": True},
                    "width": 80,
                },
            ],
        ),
        datatable_lens(
            "otel-lens-cluster-signals",
            "Cluster Signals",
            "autoops_es.cluster.name",
            "Cluster",
            10,
            [
                {
                    "id": "signal-status",
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
                    "id": "signal-active-pct",
                    "label": "Active %",
                    "operation": "last_value",
                    "field": "autoops_es.cluster_health.active_shards_percent_as_number",
                    "filter": 'metricset.name: "cluster_health" and autoops_es.cluster_health.active_shards_percent_as_number: *',
                    "params": {"sortField": "@timestamp"},
                    "width": 85,
                },
                {
                    "id": "signal-unassigned",
                    "label": "Unassigned",
                    "operation": "last_value",
                    "field": "autoops_es.cluster_health.unassigned_shards",
                    "filter": 'metricset.name: "cluster_health" and autoops_es.cluster_health.unassigned_shards: *',
                    "params": {"sortField": "@timestamp"},
                    "width": 95,
                },
                {
                    "id": "signal-pending",
                    "label": "Pending",
                    "operation": "last_value",
                    "field": "autoops_es.cluster_health.number_of_pending_tasks",
                    "filter": 'metricset.name: "cluster_health" and autoops_es.cluster_health.number_of_pending_tasks: *',
                    "params": {"sortField": "@timestamp"},
                    "width": 80,
                },
                {
                    "id": "signal-heap-pct",
                    "label": "Heap %",
                    "operation": "max",
                    "field": "autoops_es.node_stats.jvm.mem.heap_used_percent",
                    "filter": 'metricset.name: "node_stats" and autoops_es.node_stats.jvm.mem.heap_used_percent: *',
                    "params": {"emptyAsNull": True},
                    "width": 80,
                },
                {
                    "id": "signal-search-rej",
                    "label": "Search Rej",
                    "operation": "max",
                    "field": "autoops_es.node_stats.thread_pool.search.rejected",
                    "filter": 'metricset.name: "node_stats" and autoops_es.node_stats.thread_pool.search.rejected: *',
                    "params": {"emptyAsNull": True},
                    "width": 95,
                },
                {
                    "id": "signal-write-rej",
                    "label": "Write Rej",
                    "operation": "max",
                    "field": "autoops_es.node_stats.thread_pool.write.rejected",
                    "filter": 'metricset.name: "node_stats" and autoops_es.node_stats.thread_pool.write.rejected: *',
                    "params": {"emptyAsNull": True},
                    "width": 90,
                },
                {
                    "id": "signal-parent-trips",
                    "label": "Parent Trips",
                    "operation": "max",
                    "field": "autoops_es.node_stats.breakers.parent.tripped",
                    "filter": 'metricset.name: "node_stats" and autoops_es.node_stats.breakers.parent.tripped: *',
                    "params": {"emptyAsNull": True},
                    "width": 95,
                },
                {
                    "id": "signal-request-trips",
                    "label": "Request Trips",
                    "operation": "max",
                    "field": "autoops_es.node_stats.breakers.request.tripped",
                    "filter": 'metricset.name: "node_stats" and autoops_es.node_stats.breakers.request.tripped: *',
                    "params": {"emptyAsNull": True},
                    "width": 100,
                },
            ],
        ),
        datatable_lens(
            "otel-lens-shard-signals",
            "Shard Signals",
            "autoops_es.cat_shards.node_shards_count.node_name",
            "Node",
            20,
            [
                {
                    "id": "shard-total",
                    "label": "Shard Count",
                    "operation": "max",
                    "field": "autoops_es.cat_shards.node_shards_count.shards_count",
                    "filter": 'metricset.name: "cat_shards" and autoops_es.cat_shards.node_shards_count.shards_count: *',
                    "params": {"emptyAsNull": True},
                    "width": 95,
                },
                {
                    "id": "shard-primary",
                    "label": "Primary",
                    "operation": "max",
                    "field": "autoops_es.cat_shards.node_shards_count.primary_shards",
                    "filter": 'metricset.name: "cat_shards" and autoops_es.cat_shards.node_shards_count.primary_shards: *',
                    "params": {"emptyAsNull": True},
                    "width": 80,
                },
                {
                    "id": "shard-replica",
                    "label": "Replica",
                    "operation": "max",
                    "field": "autoops_es.cat_shards.node_shards_count.replica_shards",
                    "filter": 'metricset.name: "cat_shards" and autoops_es.cat_shards.node_shards_count.replica_shards: *',
                    "params": {"emptyAsNull": True},
                    "width": 80,
                },
                {
                    "id": "shard-initializing",
                    "label": "Initializing",
                    "operation": "max",
                    "field": "autoops_es.cat_shards.node_shards_count.initializing_shards",
                    "filter": 'metricset.name: "cat_shards" and autoops_es.cat_shards.node_shards_count.initializing_shards: *',
                    "params": {"emptyAsNull": True},
                    "width": 95,
                },
                {
                    "id": "shard-relocating",
                    "label": "Relocating",
                    "operation": "max",
                    "field": "autoops_es.cat_shards.node_shards_count.relocating_shards",
                    "filter": 'metricset.name: "cat_shards" and autoops_es.cat_shards.node_shards_count.relocating_shards: *',
                    "params": {"emptyAsNull": True},
                    "width": 90,
                },
            ],
        ),
    ]
    objects.extend(lens_objects)
    objects.append(links_saved_object())

    overview_panels = [
        links_panel_ref("otel-panel-links-overview", "Navigation", 0, 0, 48, 3, LINKS_ID),
        markdown_panel(
            "otel-markdown-header-overview",
            "## Elasticsearch OTEL monitoring overview\nDerived TSDS for the EDOT autoops_es metrics stream",
            0,
            3,
            48,
            3,
        ),
        dashboard_panel_ref("otel-panel-cluster-info", "Cluster Info", 0, 6, 48, 8, "otel-lens-cluster-info"),
        dashboard_panel_ref("otel-panel-nodes", "Nodes", 0, 14, 6, 5, "otel-lens-nodes"),
        dashboard_panel_ref("otel-panel-data-nodes", "Data Nodes", 6, 14, 6, 5, "otel-lens-data-nodes"),
        dashboard_panel_ref("otel-panel-unassigned", "Unassigned Shards", 12, 14, 6, 5, "otel-lens-unassigned-shards"),
        dashboard_panel_ref("otel-panel-pending", "Pending Tasks", 18, 14, 6, 5, "otel-lens-pending-tasks"),
        dashboard_panel_ref("otel-panel-active-primary", "Active Primary Shards", 24, 14, 6, 5, "otel-lens-active-primary-shards"),
        dashboard_panel_ref("otel-panel-active-pct", "Active Shards %", 30, 14, 6, 5, "otel-lens-active-shards-pct"),
        dashboard_panel_ref("otel-panel-initializing", "Initializing Shards", 36, 14, 6, 5, "otel-lens-initializing-shards"),
        dashboard_panel_ref("otel-panel-delayed", "Delayed Unassigned", 42, 14, 6, 5, "otel-lens-delayed-unassigned"),
        markdown_panel("otel-markdown-throughput", "Throughput, latency, and pressure", 0, 19, 48, 2),
        dashboard_panel_ref("otel-panel-search-rate", "Search Rate /s", 0, 21, 12, 7, "otel-lens-search-rate"),
        dashboard_panel_ref("otel-panel-index-rate", "Index Rate /s", 12, 21, 12, 7, "otel-lens-index-rate"),
        dashboard_panel_ref("otel-panel-search-latency", "Search Latency (ms)", 24, 21, 12, 7, "otel-lens-search-latency"),
        dashboard_panel_ref("otel-panel-index-failed", "Index Failed Rate /s", 36, 21, 12, 7, "otel-lens-index-failed-rate"),
        dashboard_panel_ref("otel-panel-search-queue", "Search Queue Max", 0, 28, 12, 7, "otel-lens-search-queue"),
        dashboard_panel_ref("otel-panel-write-queue", "Write Queue Max", 12, 28, 12, 7, "otel-lens-write-queue"),
        dashboard_panel_ref("otel-panel-search-rejected", "Search Rejected", 24, 28, 12, 7, "otel-lens-search-rejected"),
        dashboard_panel_ref("otel-panel-write-rejected", "Write Rejected", 36, 28, 12, 7, "otel-lens-write-rejected"),
        dashboard_panel_ref("otel-panel-cluster-signals", "Cluster Signals", 0, 35, 48, 8, "otel-lens-cluster-signals"),
    ]

    nodes_panels = [
        links_panel_ref("otel-panel-links-nodes", "Navigation", 0, 0, 48, 3, LINKS_ID),
        markdown_panel(
            "otel-markdown-header-nodes",
            "## Elasticsearch OTEL monitoring nodes\nJVM, caches, file descriptors, and node resource pressure",
            0,
            3,
            48,
            3,
        ),
        dashboard_panel_ref("otel-panel-heap-used", "Heap Used (GB)", 0, 6, 8, 7, "otel-lens-heap-used"),
        dashboard_panel_ref("otel-panel-heap-max", "Heap Max (GB)", 8, 6, 8, 7, "otel-lens-heap-max"),
        dashboard_panel_ref("otel-panel-heap-pct", "Heap Used %", 16, 6, 8, 7, "otel-lens-heap-used-pct"),
        dashboard_panel_ref("otel-panel-open-http", "Open HTTP Connections", 24, 6, 8, 7, "otel-lens-open-http"),
        dashboard_panel_ref("otel-panel-cpu-percent", "CPU %", 32, 6, 8, 7, "otel-lens-cpu-percent"),
        dashboard_panel_ref("otel-panel-disk-available", "Disk Available (GB)", 40, 6, 8, 7, "otel-lens-disk-available"),
        dashboard_panel_ref("otel-panel-gc-young", "GC Young Time (ms)", 0, 13, 8, 7, "otel-lens-gc-young-time"),
        dashboard_panel_ref("otel-panel-gc-old", "GC Old Time (ms)", 8, 13, 8, 7, "otel-lens-gc-old-time"),
        dashboard_panel_ref("otel-panel-parent-breaker", "Parent Breaker Trips", 16, 13, 8, 7, "otel-lens-parent-breaker-tripped"),
        dashboard_panel_ref("otel-panel-request-breaker", "Request Breaker Trips", 24, 13, 8, 7, "otel-lens-request-breaker-tripped"),
        dashboard_panel_ref("otel-panel-store-size", "Store Size (GB)", 32, 13, 8, 7, "otel-lens-store-size"),
        dashboard_panel_ref("otel-panel-segments-count", "Segments Count", 40, 13, 8, 7, "otel-lens-segments-count"),
        dashboard_panel_ref("otel-panel-merge-rate", "Merge Rate /s", 0, 20, 12, 7, "otel-lens-merge-rate"),
        dashboard_panel_ref("otel-panel-merge-latency", "Merge Latency (ms)", 12, 20, 12, 7, "otel-lens-merge-latency"),
        dashboard_panel_ref("otel-panel-open-fds", "Open File Descriptors", 24, 20, 12, 7, "otel-lens-open-file-descriptors"),
        dashboard_panel_ref("otel-panel-max-fds", "Max File Descriptors", 36, 20, 12, 7, "otel-lens-max-file-descriptors"),
        dashboard_panel_ref("otel-panel-query-cache-hits", "Query Cache Hits", 0, 27, 12, 7, "otel-lens-query-cache-hits"),
        dashboard_panel_ref("otel-panel-query-cache-misses", "Query Cache Misses", 12, 27, 12, 7, "otel-lens-query-cache-misses"),
        dashboard_panel_ref("otel-panel-request-cache-hits", "Request Cache Hits", 24, 27, 12, 7, "otel-lens-request-cache-hits"),
        dashboard_panel_ref("otel-panel-request-cache-misses", "Request Cache Misses", 36, 27, 12, 7, "otel-lens-request-cache-misses"),
        dashboard_panel_ref("otel-panel-query-cache-evictions", "Query Cache Evictions", 0, 34, 12, 7, "otel-lens-query-cache-evictions"),
        dashboard_panel_ref("otel-panel-request-cache-evictions", "Request Cache Evictions", 12, 34, 12, 7, "otel-lens-request-cache-evictions"),
        dashboard_panel_ref("otel-panel-http-total-opened", "HTTP Opened Total", 24, 34, 12, 7, "otel-lens-http-total-opened"),
        dashboard_panel_ref("otel-panel-node-summary", "Node Summary", 0, 41, 48, 12, "otel-lens-node-summary"),
    ]

    indices_panels = [
        links_panel_ref("otel-panel-links-indices", "Navigation", 0, 0, 48, 3, LINKS_ID),
        markdown_panel(
            "otel-markdown-header-indices",
            "## Elasticsearch OTEL monitoring indices\nIndex, shard, docs, and storage detail derived from node stats and cat shards",
            0,
            3,
            48,
            3,
        ),
        dashboard_panel_ref("otel-panel-node-shards", "Shard Count by Node", 0, 6, 12, 7, "otel-lens-node-shards"),
        dashboard_panel_ref("otel-panel-primary-shards", "Primary Shards by Node", 12, 6, 12, 7, "otel-lens-primary-shards"),
        dashboard_panel_ref("otel-panel-docs-count", "Docs Count", 24, 6, 12, 7, "otel-lens-docs-count"),
        dashboard_panel_ref("otel-panel-total-data-set", "Total Data Set Size (GB)", 36, 6, 12, 7, "otel-lens-total-data-set-size"),
        dashboard_panel_ref("otel-panel-store-size-index", "Store Size (GB)", 0, 13, 12, 7, "otel-lens-store-size"),
        dashboard_panel_ref("otel-panel-segments-memory", "Segments Memory (GB)", 12, 13, 12, 7, "otel-lens-segments-memory"),
        dashboard_panel_ref("otel-panel-segments-count-index", "Segments Count", 24, 13, 12, 7, "otel-lens-segments-count"),
        dashboard_panel_ref("otel-panel-index-rate-index", "Index Rate /s", 36, 13, 12, 7, "otel-lens-index-rate"),
        dashboard_panel_ref("otel-panel-search-rate-index", "Search Rate /s", 0, 20, 12, 7, "otel-lens-search-rate"),
        dashboard_panel_ref("otel-panel-index-failed-index", "Index Failed Rate /s", 12, 20, 12, 7, "otel-lens-index-failed-rate"),
        dashboard_panel_ref("otel-panel-shard-signals", "Shard Signals", 24, 20, 24, 7, "otel-lens-shard-signals"),
        dashboard_panel_ref("otel-panel-index-inventory", "Index Inventory", 0, 27, 48, 14, "otel-lens-index-inventory"),
    ]

    objects.extend(
        [
            dashboard_object(
                DASHBOARD_ID,
                "Elasticsearch OTEL monitoring for metrics-elasticsearch.autoops-main",
                "Overview dashboard derived from the EDOT autoops_es metrics stream.",
                overview_panels,
            ),
            dashboard_object(
                NODES_DASHBOARD_ID,
                "Elasticsearch OTEL monitoring - Nodes",
                "Node and JVM dashboard derived from the EDOT autoops_es metrics stream.",
                nodes_panels,
            ),
            dashboard_object(
                INDICES_DASHBOARD_ID,
                "Elasticsearch OTEL monitoring - Indices",
                "Index and shard dashboard derived from the EDOT autoops_es metrics stream.",
                indices_panels,
            ),
        ]
    )

    return objects


def main():
    repo_root = Path(__file__).resolve().parents[1]
    out_dir = repo_root / "dashboards"
    ndjson_path = out_dir / "elasticsearch-otel-monitoring-main.ndjson"
    export_json_path = out_dir / "elasticsearch-otel-monitoring-main.export.json"
    out_dir.mkdir(parents=True, exist_ok=True)

    objects = build_objects()

    with ndjson_path.open("w", encoding="utf-8") as fh:
        for obj in objects:
            fh.write(json.dumps(obj, separators=(",", ":")))
            fh.write("\n")

    with export_json_path.open("w", encoding="utf-8") as fh:
        json.dump(
            {
                "description": "Structured export wrapper for the Elasticsearch OTEL monitoring dashboard. Convert to NDJSON for Kibana UI import.",
                "objects": objects,
            },
            fh,
            indent=2,
        )
        fh.write("\n")

    print(ndjson_path)
    print(export_json_path)


if __name__ == "__main__":
    main()
