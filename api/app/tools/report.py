"""CreateReportTool - Generate shareable multi-section reports."""

from datetime import UTC, datetime
from typing import Any

from app.tools.chart import ChartTool


class CreateReportTool:
    """Tool for creating report artifacts with text and chart sections."""

    name = "report"
    description = "Create a shareable report summarizing analysis findings"

    def __init__(self, data_loader: Any, storage: Any):
        self._chart_tool = ChartTool(data_loader)
        self._storage = storage

    def execute(
        self,
        session_id: str,
        title: str,
        sections: list[dict],
    ) -> dict:
        """Create a report artifact with text and chart sections."""
        if not sections:
            return {"error": "Report must have at least one section."}

        built_sections: list[dict] = []
        all_data: list[Any] = []
        all_columns: set[str] = set()

        for section in sections:
            section_type = section.get("type")

            if section_type == "text":
                built_sections.append({
                    "type": "text",
                    "content": section.get("content", ""),
                })

            elif section_type == "chart":
                chart_result = self._chart_tool.execute(
                    table=section["table"],
                    chart_type=section["chart_type"],
                    x=section["x"],
                    y=section["y"],
                    title=section.get("title"),
                    color=section.get("color"),
                )

                if "error" in chart_result:
                    return {"error": f"Chart section '{section.get('title', 'untitled')}': {chart_result['error']}"}

                chart_spec = chart_result["spec"]
                built_sections.append({
                    "type": "chart",
                    "title": section.get("title", chart_spec.get("title", "")),
                    "chartSpec": chart_spec,
                })

                # Accumulate data for snapshot
                chart_data = chart_spec.get("data", [])
                all_data.extend(chart_data)
                if chart_data and isinstance(chart_data[0], dict):
                    all_columns.update(chart_data[0].keys())

            else:
                return {"error": f"Unknown section type: {section_type}"}

        visualization = {
            "type": "report",
            "sections": built_sections,
        }

        data_snapshot = {
            "data": all_data,
            "columns": sorted(all_columns),
            "rowCount": len(all_data),
            "capturedAt": datetime.now(UTC).isoformat(),
        }

        artifact = self._storage.create_report_artifact(
            session_id=session_id,
            title=title,
            description="",
            visualization=visualization,
            data_snapshot=data_snapshot,
        )

        if artifact is None:
            return {"error": "Session not found."}

        return {
            "artifact_id": artifact["id"],
            "url": f"/artifact/{artifact['id']}",
        }
