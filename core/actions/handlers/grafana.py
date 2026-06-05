import re
import asyncio
import logging
import os
from typing import Dict, Any
from core.actions.base import ActionHandler
from core.actions.registry import ActionRegistry
from core.context import IncidentContext
from core.settings import settings
from services.grafana import (
    capture_dashboard,
    fetch_grafana_metric,
    execute_grafana_query,
)

logger = logging.getLogger(__name__)


class CaptureDashboardHandler(ActionHandler):
    async def execute(
        self, action: Dict[str, Any], context: IncidentContext, alert: Dict[str, Any]
    ):
        target_url = action.get("url") or settings.GRAFANA_DASHBOARD_URL
        if target_url:
            logger.info(f"Capturing dashboard: {target_url}")
            safe_alert_name = re.sub(r"[^a-zA-Z0-9_]", "_", context.alert_name)
            unique_filename = f"snapshot_{safe_alert_name}_{context.incident_id}.png"
            screenshot_path = await asyncio.to_thread(
                capture_dashboard, target_url, unique_filename
            )
            if screenshot_path:
                context.add_step(
                    f"Visual Evidence: Dashboard captured from {target_url}"
                )
                context.add_screenshot(screenshot_path)
            else:
                context.add_step("Visual Evidence: Failed to capture dashboard.")


class FetchMetricsHandler(ActionHandler):
    async def execute(
        self, action: Dict[str, Any], context: IncidentContext, alert: Dict[str, Any]
    ):
        target = action.get("target", "unknown metric")
        prom_query = action.get("query")
        if not prom_query:
            if "cpu" in target.lower():
                prom_query = (
                    "100 - (avg(rate(node_cpu_seconds_total{mode='idle'}[5m])) * 100)"
                )
            elif "memory" in target.lower():
                prom_query = "100 * (1 - ((avg_over_time(node_memory_MemFree_bytes[5m]) + avg_over_time(node_memory_Cached_bytes[5m]) + avg_over_time(node_memory_Buffers_bytes[5m])) / avg_over_time(node_memory_MemTotal_bytes[5m])))"
            else:
                prom_query = target

        metric_val = await asyncio.to_thread(fetch_grafana_metric, target, prom_query)
        context.add_enrichment(f"- [Metric] {target}: {metric_val}")
        context.add_step(f"Enrichment: {target} metrics retrieved.")


class GrafanaQueryHandler(ActionHandler):
    async def execute(
        self, action: Dict[str, Any], context: IncidentContext, alert: Dict[str, Any]
    ):
        datasource_uid = action.get("datasource_uid", "")
        query = action.get("query", "")
        time_range = action.get("time_range", "now-15m")

        if datasource_uid.startswith("$"):
            datasource_uid = os.path.expandvars(datasource_uid)

        alert_vars = {**alert.get("labels", {}), **alert.get("annotations", {})}
        for k, v in alert_vars.items():
            query = query.replace(f"${{{k}}}", str(v))

        logger.info(f"Executing Grafana Query on DS: {datasource_uid}")
        query_result = await asyncio.to_thread(
            execute_grafana_query, datasource_uid, query, time_from=time_range
        )

        context.add_enrichment(f"- [Grafana Query Results]\n{query_result}\n")
        context.add_step("Enrichment: Grafana generic query executed.")


ActionRegistry.register("capture_dashboard_screenshot", CaptureDashboardHandler())
ActionRegistry.register("fetch_metrics", FetchMetricsHandler())
ActionRegistry.register("grafana_query", GrafanaQueryHandler())
