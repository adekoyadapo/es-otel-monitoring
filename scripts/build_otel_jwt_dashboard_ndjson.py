#!/usr/bin/env python3

import json
from pathlib import Path


DATA_VIEW_ID = "otel-elasticsearch-jwt-native-main"
DATA_VIEW_TITLE = "metrics-elasticsearch.stack_monitoring.otel-main"
DASHBOARD_ID = "otel-elasticsearch-monitoring-jwt"
NODES_DASHBOARD_ID = "otel-elasticsearch-monitoring-jwt-nodes"
INDICES_DASHBOARD_ID = "otel-elasticsearch-monitoring-jwt-indices"
LINKS_ID = "otel-elasticsearch-monitoring-jwt-links"

LENS_EXPORT_META = {
    "coreMigrationVersion": "8.8.0",
    "created_at": "2026-05-02T00:00:00.000Z",
    "created_by": "elastic",
    "managed": False,
    "typeMigrationVersion": "10.1.0",
    "updated_at": "2026-05-02T00:00:00.000Z",
    "updated_by": "elastic",
    "version": "WzEsMV0=",
}

# Dataset stored by the EDOT gateway (otel mapping appends .otel)
DATASET = "elasticsearch.stack_monitoring.otel"


def _f(field):
    """Prefix a metric name with the metrics.* path used by otel mapping mode."""
    return f"metrics.{field}"


def _a(attr):
    """Prefix an attribute name with attributes.* used by otel mapping mode."""
    return f"attributes.{attr}"


def _filter(extra=""):
    base = f'data_stream.dataset: "{DATASET}"'
    return f"{base} and {extra}" if extra else base


def metric_lens(lens_id, title, field, filter_query, operation="max", params=None, data_view_id=DATA_VIEW_ID):
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
                        "currentIndexPatternId": data_view_id,
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
                                "indexPatternId": data_view_id,
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
        "references": [{"id": data_view_id, "name": ref_name, "type": "index-pattern"}],
    }
    obj.update(LENS_EXPORT_META)
    return obj


def xy_lens(lens_id, title, field, filter_query, operation, color, data_view_id=DATA_VIEW_ID):
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
                        "currentIndexPatternId": data_view_id,
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
                                "indexPatternId": data_view_id,
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
        "references": [{"id": data_view_id, "name": ref_name, "type": "index-pattern"}],
    }
    obj.update(LENS_EXPORT_META)
    return obj


def datatable_lens(lens_id, title, row_field, row_label, row_size, metric_specs, row_filter=None, data_view_id=DATA_VIEW_ID):
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
                        "currentIndexPatternId": data_view_id,
                        "layers": {
                            layer_id: {
                                "columnOrder": column_order,
                                "columns": columns,
                                "incompleteColumns": {},
                                "indexPatternId": data_view_id,
                                "sampling": 1,
                            }
                        },
                    },
                    "indexpattern": {"layers": {}},
                    "textBased": {"layers": {}},
                },
                "filters": [],
                "internalReferences": [],
                "query": {
                    "language": "kuery",
                    "query": row_filter or _filter(),
                },
                "visualization": {"columns": vis_columns, "layerId": layer_id, "layerType": "data"},
            },
        },
        "references": [{"id": data_view_id, "name": f"indexpattern-datasource-layer-{layer_id}", "type": "index-pattern"}],
    }
    obj.update(LENS_EXPORT_META)
    return obj


def multi_terms_table_lens(lens_id, title, row_specs, row_size, row_filter=None, data_view_id=DATA_VIEW_ID):
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
                        "currentIndexPatternId": data_view_id,
                        "layers": {
                            layer_id: {
                                "columnOrder": column_order,
                                "columns": columns,
                                "incompleteColumns": {},
                                "indexPatternId": data_view_id,
                                "sampling": 1,
                            }
                        },
                    },
                    "indexpattern": {"layers": {}},
                    "textBased": {"layers": {}},
                },
                "filters": [],
                "internalReferences": [],
                "query": {"language": "kuery", "query": row_filter or _filter()},
                "visualization": {"columns": vis_columns, "layerId": layer_id, "layerType": "data"},
            },
        },
        "references": [{"id": data_view_id, "name": f"indexpattern-datasource-layer-{layer_id}", "type": "index-pattern"}],
    }
    obj.update(LENS_EXPORT_META)
    return obj


def dashboard_panel_ref(panel_id, title, x, y, w, h, lens_id, panel_type="lens"):
    return {
        "type": panel_type,
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


def text_panel(panel_id, content, x, y, w, h):
    """Inline markdown text panel using the 'text' embeddable (Kibana 8.5+/9.x)."""
    return {
        "type": "text",
        "panelIndex": panel_id,
        "gridData": {"i": panel_id, "x": x, "y": y, "w": w, "h": h},
        "embeddableConfig": {
            "hidePanelTitles": True,
            "enhancements": {},
            "attributes": {
                "openLinksInNewTab": False,
                "text": content,
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
        link_id = f"otel-jwt-link-{label.lower()}"
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


def control_group_and_references(data_view_id=DATA_VIEW_ID):
    # Fields are stored under attributes.* in otel mapping mode
    specs = [
        ("cluster", _a("cluster_name"), "Cluster Name(s)", "medium", False),
        ("node", _a("node_name"), "Node(s)", "medium", True),
        ("index", _a("index_name"), "Index(s)", "large", True),
    ]
    control_panels = {}
    references = []
    for order, (suffix, field_name, title, width, grow) in enumerate(specs):
        control_id = f"otel-jwt-control-{suffix}"
        control_panels[control_id] = {
            "explicitInput": {
                "dataViewId": data_view_id,
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
        references.append({"id": data_view_id, "name": f"controlGroup_{control_id}:optionsListDataView", "type": "index-pattern"})
    return control_panels, references


def dashboard_object(dashboard_id, title, description, panels, data_view_id=DATA_VIEW_ID):
    control_panels, control_refs = control_group_and_references(data_view_id)
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
        },
        "references": references,
        "managed": False,
    }


def build_objects():
    objects = [
        {
            "type": "index-pattern",
            "id": DATA_VIEW_ID,
            "attributes": {
                "title": DATA_VIEW_TITLE,
                "name": "otel-elasticsearch-jwt-native-main",
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

    # Convenience shorthands for filter fragments
    CF = _filter  # cluster-level filter with optional extra clause
    NF = lambda extra="": _filter(extra)  # noqa: E731

    lens_objects = [
        # ── Cluster health status table ──────────────────────────────────────
        multi_terms_table_lens(
            "otel-jwt-lens-health-status",
            "Cluster Health",
            [
                {"field": _a("cluster_name"), "label": "Cluster", "width": 220},
                {"field": _a("state"), "label": "Status", "width": 140},
            ],
            20,
            row_filter=_filter(f"{_a('state')}:* and {_f('elasticsearch_cluster_health_state')}: 1"),
        ),
        # ── Health state metric tiles ─────────────────────────────────────────
        metric_lens(
            "otel-jwt-lens-health-green", "GREEN",
            _f("elasticsearch_cluster_health_state"),
            _filter(f'{_a("state")}: "green"'),
            params={"emptyAsNull": True},
        ),
        metric_lens(
            "otel-jwt-lens-health-yellow", "YELLOW",
            _f("elasticsearch_cluster_health_state"),
            _filter(f'{_a("state")}: "yellow"'),
            params={"emptyAsNull": True},
        ),
        metric_lens(
            "otel-jwt-lens-health-red", "RED",
            _f("elasticsearch_cluster_health_state"),
            _filter(f'{_a("state")}: "red"'),
            params={"emptyAsNull": True},
        ),
        # ── Cluster scalar tiles ─────────────────────────────────────────────
        metric_lens(
            "otel-jwt-lens-nodes", "Nodes",
            _f("elasticsearch_cluster_nodes_total"),
            _filter(f"{_f('elasticsearch_cluster_nodes_total')}:*"),
        ),
        metric_lens(
            "otel-jwt-lens-data-nodes", "Data Nodes",
            _f("elasticsearch_cluster_nodes_data"),
            _filter(f"{_f('elasticsearch_cluster_nodes_data')}:*"),
        ),
        metric_lens(
            "otel-jwt-lens-indices-count", "Indices",
            _f("elasticsearch_cluster_indices_total"),
            _filter(f"{_f('elasticsearch_cluster_indices_total')}:*"),
        ),
        metric_lens(
            "otel-jwt-lens-shards-count", "Shards",
            _f("elasticsearch_cluster_shards_total"),
            _filter(f"{_f('elasticsearch_cluster_shards_total')}:*"),
        ),
        metric_lens(
            "otel-jwt-lens-docs-total", "Docs",
            _f("elasticsearch_cluster_docs_total"),
            _filter(f"{_f('elasticsearch_cluster_docs_total')}:*"),
        ),
        metric_lens(
            "otel-jwt-lens-primary-shards", "Primary Shards",
            _f("elasticsearch_cluster_shards_primaries"),
            _filter(f"{_f('elasticsearch_cluster_shards_primaries')}:*"),
        ),
        metric_lens(
            "otel-jwt-lens-cluster-store-size", "Store Size",
            _f("elasticsearch_cluster_store_size_bytes"),
            _filter(f"{_f('elasticsearch_cluster_store_size_bytes')}:*"),
        ),
        metric_lens(
            "otel-jwt-lens-pending-tasks", "Pending Tasks",
            _f("elasticsearch_cluster_pending_tasks_total"),
            _filter(f"{_f('elasticsearch_cluster_pending_tasks_total')}:*"),
        ),
        # ── Node time-series charts ──────────────────────────────────────────
        xy_lens(
            "otel-jwt-lens-heap-pct", "Heap Used %",
            _f("elasticsearch_node_heap_used_pct"),
            _filter(f"{_f('elasticsearch_node_heap_used_pct')}:*"),
            "average", "#2f9c95",
        ),
        xy_lens(
            "otel-jwt-lens-query-total", "Query Total",
            _f("elasticsearch_node_search_total"),
            _filter(f"{_f('elasticsearch_node_search_total')}:*"),
            "max", "#348888",
        ),
        xy_lens(
            "otel-jwt-lens-index-total", "Index Total",
            _f("elasticsearch_node_indexing_total"),
            _filter(f"{_f('elasticsearch_node_indexing_total')}:*"),
            "max", "#d17c2d",
        ),
        xy_lens(
            "otel-jwt-lens-store-size", "Node Store Size",
            _f("elasticsearch_node_store_size_bytes"),
            _filter(f"{_f('elasticsearch_node_store_size_bytes')}:*"),
            "sum", "#7aa95c",
        ),
        xy_lens(
            "otel-jwt-lens-open-files", "Open Files",
            _f("elasticsearch_node_open_file_descriptors"),
            _filter(f"{_f('elasticsearch_node_open_file_descriptors')}:*"),
            "max", "#6a8caf",
        ),
        xy_lens(
            "otel-jwt-lens-cpu-pct", "CPU %",
            _f("elasticsearch_node_cpu_pct"),
            _filter(f"{_f('elasticsearch_node_cpu_pct')}:*"),
            "average", "#7b6fd0",
        ),
        xy_lens(
            "otel-jwt-lens-search-queue", "Search Queue",
            _f("elasticsearch_node_search_queue"),
            _filter(f"{_f('elasticsearch_node_search_queue')}:*"),
            "average", "#7b6fd0",
        ),
        xy_lens(
            "otel-jwt-lens-write-queue", "Write Queue",
            _f("elasticsearch_node_write_queue"),
            _filter(f"{_f('elasticsearch_node_write_queue')}:*"),
            "average", "#d17c2d",
        ),
        xy_lens(
            "otel-jwt-lens-search-rejected", "Search Rejected",
            _f("elasticsearch_node_search_rejected_total"),
            _filter(f"{_f('elasticsearch_node_search_rejected_total')}:*"),
            "max", "#c2574c",
        ),
        xy_lens(
            "otel-jwt-lens-write-rejected", "Write Rejected",
            _f("elasticsearch_node_write_rejected_total"),
            _filter(f"{_f('elasticsearch_node_write_rejected_total')}:*"),
            "max", "#8c3a3a",
        ),
        xy_lens(
            "otel-jwt-lens-young-gc", "Young GC Total",
            _f("elasticsearch_node_young_gc_time_ms"),
            _filter(f"{_f('elasticsearch_node_young_gc_time_ms')}:*"),
            "max", "#b0922e",
        ),
        xy_lens(
            "otel-jwt-lens-old-gc", "Old GC Total",
            _f("elasticsearch_node_old_gc_time_ms"),
            _filter(f"{_f('elasticsearch_node_old_gc_time_ms')}:*"),
            "max", "#7b4f9e",
        ),
        # ── Cluster info table ───────────────────────────────────────────────
        multi_terms_table_lens(
            "otel-jwt-lens-cluster-info",
            "Cluster Info",
            [
                {"field": _a("cluster_name"), "label": "Cluster", "width": 220},
                {"field": _a("state"), "label": "Status", "width": 140},
            ],
            10,
            row_filter=_filter(f"{_a('state')}:* and {_f('elasticsearch_cluster_health_state')}: 1"),
        ),
        # ── Node summary table ───────────────────────────────────────────────
        datatable_lens(
            "otel-jwt-lens-node-summary",
            "Node Summary",
            _a("node_name"),
            "Node",
            20,
            [
                {"id": "otel-jwt-node-heap-used", "label": "Heap Used (GB)", "operation": "max", "field": _f("elasticsearch_node_heap_used_bytes"), "filter": _filter(f"{_f('elasticsearch_node_heap_used_bytes')}:*"), "width": 140, "params": {"format": {"id": "bytes", "params": {"decimals": 4}}}},
                {"id": "otel-jwt-node-heap-max", "label": "Heap Max (GB)", "operation": "max", "field": _f("elasticsearch_node_heap_max_bytes"), "filter": _filter(f"{_f('elasticsearch_node_heap_max_bytes')}:*"), "width": 140, "params": {"format": {"id": "bytes", "params": {"decimals": 4}}}},
                {"id": "otel-jwt-node-heap-pct", "label": "Heap %", "operation": "average", "field": _f("elasticsearch_node_heap_used_pct"), "filter": _filter(f"{_f('elasticsearch_node_heap_used_pct')}:*")},
                {"id": "otel-jwt-node-cpu", "label": "CPU %", "operation": "average", "field": _f("elasticsearch_node_cpu_pct"), "filter": _filter(f"{_f('elasticsearch_node_cpu_pct')}:*")},
                {"id": "otel-jwt-node-open-files", "label": "Open Files", "operation": "max", "field": _f("elasticsearch_node_open_file_descriptors"), "filter": _filter(f"{_f('elasticsearch_node_open_file_descriptors')}:*"), "width": 120},
                {"id": "otel-jwt-node-search-total", "label": "Query Total", "operation": "max", "field": _f("elasticsearch_node_search_total"), "filter": _filter(f"{_f('elasticsearch_node_search_total')}:*"), "width": 120},
                {"id": "otel-jwt-node-index-total", "label": "Index Total", "operation": "max", "field": _f("elasticsearch_node_indexing_total"), "filter": _filter(f"{_f('elasticsearch_node_indexing_total')}:*"), "width": 120},
            ],
            row_filter=_filter(f"{_a('node_name')}:*"),
        ),
        # ── Index activity table ─────────────────────────────────────────────
        datatable_lens(
            "otel-jwt-lens-index-summary",
            "Index Activity",
            _a("index_name"),
            "Index",
            20,
            [
                {"id": "otel-jwt-index-docs-table", "label": "Docs", "operation": "max", "field": _f("elasticsearch_index_docs"), "filter": _filter(f"{_f('elasticsearch_index_docs')}:*"), "width": 120},
                {"id": "otel-jwt-index-size-table", "label": "Size", "operation": "max", "field": _f("elasticsearch_index_store_size_bytes"), "filter": _filter(f"{_f('elasticsearch_index_store_size_bytes')}:*"), "width": 130},
                {"id": "otel-jwt-index-primaries-table", "label": "Primary Shards", "operation": "max", "field": _f("elasticsearch_index_primary_shards"), "filter": _filter(f"{_f('elasticsearch_index_primary_shards')}:*"), "width": 120},
                {"id": "otel-jwt-index-total-shards-table", "label": "Total Shards", "operation": "max", "field": _f("elasticsearch_index_total_shards"), "filter": _filter(f"{_f('elasticsearch_index_total_shards')}:*"), "width": 120},
                {"id": "otel-jwt-index-segments-table", "label": "Segments", "operation": "max", "field": _f("elasticsearch_index_segments_count"), "filter": _filter(f"{_f('elasticsearch_index_segments_count')}:*")},
                {"id": "otel-jwt-index-query-total-table", "label": "Query Total", "operation": "max", "field": _f("elasticsearch_index_search_query_total"), "filter": _filter(f"{_f('elasticsearch_index_search_query_total')}:*"), "width": 120},
                {"id": "otel-jwt-index-write-total-table", "label": "Write Total", "operation": "max", "field": _f("elasticsearch_index_indexing_total"), "filter": _filter(f"{_f('elasticsearch_index_indexing_total')}:*"), "width": 120},
            ],
            row_filter=_filter(f"{_a('index_name')}:*"),
        ),
        # ── Shard layout table ───────────────────────────────────────────────
        datatable_lens(
            "otel-jwt-lens-shard-summary",
            "Shard Layout",
            _a("index_name"),
            "Index",
            20,
            [
                {"id": "otel-jwt-shard-primaries", "label": "Primary Shards", "operation": "max", "field": _f("elasticsearch_index_primary_shards"), "filter": _filter(f"{_f('elasticsearch_index_primary_shards')}:*"), "width": 130},
                {"id": "otel-jwt-shard-total", "label": "Total Shards", "operation": "max", "field": _f("elasticsearch_index_total_shards"), "filter": _filter(f"{_f('elasticsearch_index_total_shards')}:*"), "width": 130},
            ],
            row_filter=_filter(f"{_a('index_name')}:*"),
        ),
        # ── Index time-series charts ─────────────────────────────────────────
        xy_lens(
            "otel-jwt-lens-index-docs", "Index Docs",
            _f("elasticsearch_index_docs"),
            _filter(f"{_f('elasticsearch_index_docs')}:*"),
            "max", "#4f86c6",
        ),
        xy_lens(
            "otel-jwt-lens-index-size", "Index Size",
            _f("elasticsearch_index_store_size_bytes"),
            _filter(f"{_f('elasticsearch_index_store_size_bytes')}:*"),
            "max", "#7aa95c",
        ),
        xy_lens(
            "otel-jwt-lens-index-segments", "Segments",
            _f("elasticsearch_index_segments_count"),
            _filter(f"{_f('elasticsearch_index_segments_count')}:*"),
            "max", "#7b6fd0",
        ),
        xy_lens(
            "otel-jwt-lens-index-query-total", "Index Query Total",
            _f("elasticsearch_index_search_query_total"),
            _filter(f"{_f('elasticsearch_index_search_query_total')}:*"),
            "max", "#348888",
        ),
        xy_lens(
            "otel-jwt-lens-index-write-total", "Index Write Total",
            _f("elasticsearch_index_indexing_total"),
            _filter(f"{_f('elasticsearch_index_indexing_total')}:*"),
            "max", "#d17c2d",
        ),
    ]

    objects.extend(lens_objects)
    objects.append(links_saved_object())

    overview_panels = [
        links_panel_ref("otel-jwt-panel-links-overview", "Navigation", 0, 0, 48, 3, LINKS_ID),
        text_panel("otel-jwt-markdown-overview", "## JWT-authenticated OTLP monitoring\nElastic Agent runtime containers scrape a local exporter and ship native metrics to the EDOT gateway.", 0, 3, 48, 3),
        dashboard_panel_ref("otel-jwt-panel-cluster-info", "Cluster Info", 0, 6, 24, 8, "otel-jwt-lens-cluster-info"),
        dashboard_panel_ref("otel-jwt-panel-health", "Cluster Health", 24, 6, 24, 8, "otel-jwt-lens-health-status"),
        dashboard_panel_ref("otel-jwt-panel-health-green", "GREEN", 0, 14, 16, 6, "otel-jwt-lens-health-green"),
        dashboard_panel_ref("otel-jwt-panel-health-yellow", "YELLOW", 16, 14, 16, 6, "otel-jwt-lens-health-yellow"),
        dashboard_panel_ref("otel-jwt-panel-health-red", "RED", 32, 14, 16, 6, "otel-jwt-lens-health-red"),
        dashboard_panel_ref("otel-jwt-panel-nodes", "Nodes", 0, 20, 8, 5, "otel-jwt-lens-nodes"),
        dashboard_panel_ref("otel-jwt-panel-data-nodes", "Data Nodes", 8, 20, 8, 5, "otel-jwt-lens-data-nodes"),
        dashboard_panel_ref("otel-jwt-panel-indices", "Indices", 16, 20, 8, 5, "otel-jwt-lens-indices-count"),
        dashboard_panel_ref("otel-jwt-panel-shards", "Shards", 24, 20, 8, 5, "otel-jwt-lens-shards-count"),
        dashboard_panel_ref("otel-jwt-panel-docs", "Docs", 32, 20, 8, 5, "otel-jwt-lens-docs-total"),
        dashboard_panel_ref("otel-jwt-panel-primary-shards", "Primary Shards", 40, 20, 8, 5, "otel-jwt-lens-primary-shards"),
        dashboard_panel_ref("otel-jwt-panel-cluster-store-size", "Store Size", 0, 25, 12, 5, "otel-jwt-lens-cluster-store-size"),
        dashboard_panel_ref("otel-jwt-panel-pending-tasks", "Pending Tasks", 12, 25, 12, 5, "otel-jwt-lens-pending-tasks"),
        dashboard_panel_ref("otel-jwt-panel-heap-pct", "Heap Used %", 24, 25, 12, 7, "otel-jwt-lens-heap-pct"),
        dashboard_panel_ref("otel-jwt-panel-query-total", "Query Total", 36, 25, 12, 7, "otel-jwt-lens-query-total"),
    ]

    nodes_panels = [
        links_panel_ref("otel-jwt-panel-links-nodes", "Navigation", 0, 0, 48, 3, LINKS_ID),
        text_panel("otel-jwt-markdown-nodes", "## Elasticsearch node pressure\nHeap, CPU, open files, queues, rejections, GC, and node totals from the local exporter.", 0, 3, 48, 3),
        dashboard_panel_ref("otel-jwt-panel-open-files", "Open Files", 0, 6, 12, 7, "otel-jwt-lens-open-files"),
        dashboard_panel_ref("otel-jwt-panel-cpu-pct", "CPU %", 12, 6, 12, 7, "otel-jwt-lens-cpu-pct"),
        dashboard_panel_ref("otel-jwt-panel-search-queue", "Search Queue", 24, 6, 12, 7, "otel-jwt-lens-search-queue"),
        dashboard_panel_ref("otel-jwt-panel-write-queue", "Write Queue", 36, 6, 12, 7, "otel-jwt-lens-write-queue"),
        dashboard_panel_ref("otel-jwt-panel-search-rejected", "Search Rejected", 0, 13, 12, 7, "otel-jwt-lens-search-rejected"),
        dashboard_panel_ref("otel-jwt-panel-write-rejected", "Write Rejected", 12, 13, 12, 7, "otel-jwt-lens-write-rejected"),
        dashboard_panel_ref("otel-jwt-panel-young-gc", "Young GC Total", 24, 13, 12, 7, "otel-jwt-lens-young-gc"),
        dashboard_panel_ref("otel-jwt-panel-old-gc", "Old GC Total", 36, 13, 12, 7, "otel-jwt-lens-old-gc"),
        dashboard_panel_ref("otel-jwt-panel-node-summary", "Node Summary", 0, 20, 48, 14, "otel-jwt-lens-node-summary"),
    ]

    indices_panels = [
        links_panel_ref("otel-jwt-panel-links-indices", "Navigation", 0, 0, 48, 3, LINKS_ID),
        text_panel("otel-jwt-markdown-indices", "## Elasticsearch index activity\nDocs, size, segments, query totals, write totals, and shard layout per index.", 0, 3, 48, 3),
        dashboard_panel_ref("otel-jwt-panel-index-docs", "Index Docs", 0, 6, 12, 7, "otel-jwt-lens-index-docs"),
        dashboard_panel_ref("otel-jwt-panel-index-size", "Index Size", 12, 6, 12, 7, "otel-jwt-lens-index-size"),
        dashboard_panel_ref("otel-jwt-panel-index-segments", "Segments", 24, 6, 12, 7, "otel-jwt-lens-index-segments"),
        dashboard_panel_ref("otel-jwt-panel-index-query-total", "Index Query Total", 36, 6, 12, 7, "otel-jwt-lens-index-query-total"),
        dashboard_panel_ref("otel-jwt-panel-index-write-total", "Index Write Total", 0, 13, 12, 7, "otel-jwt-lens-index-write-total"),
        dashboard_panel_ref("otel-jwt-panel-index-summary", "Index Activity", 0, 20, 48, 12, "otel-jwt-lens-index-summary"),
        dashboard_panel_ref("otel-jwt-panel-shard-summary", "Shard Layout", 0, 32, 48, 10, "otel-jwt-lens-shard-summary"),
    ]

    objects.extend(
        [
            dashboard_object(
                DASHBOARD_ID,
                "Elasticsearch OTLP monitoring for JWT-authenticated Agent metrics",
                "Overview dashboard for native OTLP metrics collected through JWT-authenticated Elastic Agent runtime containers.",
                overview_panels,
            ),
            dashboard_object(
                NODES_DASHBOARD_ID,
                "Elasticsearch OTLP monitoring - Nodes",
                "Node dashboard for native OTLP metrics collected through JWT-authenticated Elastic Agent runtime containers.",
                nodes_panels,
            ),
            dashboard_object(
                INDICES_DASHBOARD_ID,
                "Elasticsearch OTLP monitoring - Indices",
                "Index dashboard for native OTLP metrics collected through JWT-authenticated Elastic Agent runtime containers.",
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

    ndjson_path = out_dir / "elasticsearch-otel-monitoring-jwt.ndjson"
    export_json_path = out_dir / "elasticsearch-otel-monitoring-jwt.export.json"

    with ndjson_path.open("w", encoding="utf-8") as fh:
        for obj in objects:
            fh.write(json.dumps(obj, separators=(",", ":")) + "\n")

    with export_json_path.open("w", encoding="utf-8") as fh:
        json.dump(
            {
                "description": "Structured export wrapper for the JWT Elasticsearch OTLP monitoring dashboards. Convert to NDJSON for Kibana UI import.",
                "objects": objects,
            },
            fh,
            indent=2,
        )
        fh.write("\n")


if __name__ == "__main__":
    main()
