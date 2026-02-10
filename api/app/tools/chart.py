"""ChartTool - Generate chart visualization specifications."""

from typing import Any

import pandas as pd
from pandas.api.types import is_numeric_dtype


class ChartTool:
    """Tool for generating chart specifications with sensible data caps."""

    name = "chart"
    description = "Generate a chart visualization from table data"

    SUPPORTED_TYPES = ["bar", "line", "scatter", "pie", "area"]
    SEQUENTIAL_TYPES = ("line", "area")
    DEFAULT_FETCH_LIMIT = 100
    DEFAULT_TOP_N = 10

    def __init__(self, data_loader: Any):
        self._loader = data_loader

    def execute(
        self,
        table: str,
        chart_type: str,
        x: str,
        y: str,
        title: str | None = None,
        color: str | None = None,
        limit: int = DEFAULT_FETCH_LIMIT,
        x_label: str | None = None,
        y_label: str | None = None,
        top_n: int = DEFAULT_TOP_N,
        group_other: bool = False,
        series: list[str] | None = None,
        reference_lines: list[dict] | None = None,
        dashed: list[str] | None = None,
    ) -> dict:
        """Generate a chart specification with enforced top-N capping."""
        if chart_type not in self.SUPPORTED_TYPES:
            return {
                "error": f"Unsupported chart type: {chart_type}. Supported: {self.SUPPORTED_TYPES}"
            }

        top_n = self._sanitize_top_n(top_n)
        fetch_limit = max(limit or self.DEFAULT_FETCH_LIMIT, top_n)

        df = self._loader.get_table(table, limit=fetch_limit)

        if x not in df.columns:
            return {"error": f"Column '{x}' not found in table '{table}'"}
        if y not in df.columns:
            return {"error": f"Column '{y}' not found in table '{table}'"}
        if color and color not in df.columns:
            return {"error": f"Color column '{color}' not found in table '{table}'"}

        # Wide-format series path (e.g. actual + predicted columns)
        if series:
            missing = [s for s in series if s not in df.columns]
            if missing:
                return {"error": f"Series column(s) not found in table '{table}': {', '.join(missing)}"}

            columns = list(dict.fromkeys([x] + series))
            working = df[columns].dropna(subset=[x]).copy()
            data = working.to_dict(orient="records")

            spec: dict = {
                "type": chart_type,
                "title": title or f"{chart_type.capitalize()} Chart: {y} by {x}",
                "data": data,
                "x": x,
                "y": y,
                "x_label": x_label or x.replace("_", " ").title(),
                "y_label": y_label or y.replace("_", " ").title(),
                "series": series,
                "meta": {
                    "top_n": top_n,
                    "rows_returned": len(data),
                    "truncated": False,
                    "grouped_other": False,
                    "tail_rows": 0,
                    "fetch_limit": fetch_limit,
                },
            }
            if dashed:
                spec["dashed"] = dashed
            if reference_lines:
                spec["reference_lines"] = reference_lines
            return {"spec": spec}

        columns = [x, y]
        if color:
            columns.append(color)
        working = df[columns].dropna(subset=[x, y]).copy()

        numeric_y = is_numeric_dtype(working[y])
        skip_truncation = chart_type in self.SEQUENTIAL_TYPES

        if not skip_truncation:
            if numeric_y:
                working.sort_values(by=y, ascending=False, inplace=True)
            else:
                working.sort_values(by=x, inplace=True)

        truncated = False
        tail_rows = 0
        grouped_other = False
        if not skip_truncation and len(working) > top_n:
            truncated = True
            tail = working.iloc[top_n:]
            working = working.iloc[:top_n].copy()
            tail_rows = len(tail)
            if group_other and numeric_y and tail_rows > 0:
                other_value = tail[y].sum()
                other_row = {x: "Other", y: other_value}
                if color:
                    other_row[color] = "Other"
                working = pd.concat([working, pd.DataFrame([other_row])], ignore_index=True)
                grouped_other = True

        # Pivot long-to-wide for multi-series line/area charts
        series_list = None
        if color and skip_truncation:
            pivot = working.pivot_table(index=x, columns=color, values=y, aggfunc="first")
            series_list = list(pivot.columns)
            pivot = pivot.reset_index()
            # Convert to records and replace NaN with None for JSON
            data = pivot.to_dict(orient="records")
            data = [
                {k: (None if pd.isna(v) else v) for k, v in row.items()}
                for row in data
            ]
        else:
            data_columns = [x, y]
            if color:
                data_columns.append(color)
            data = working[data_columns].to_dict(orient="records")

        spec = {
            "type": chart_type,
            "title": title or f"{chart_type.capitalize()} Chart: {y} by {x}",
            "data": data,
            "x": x,
            "y": y,
            "x_label": x_label or x.replace("_", " ").title(),
            "y_label": y_label or y.replace("_", " ").title(),
            "meta": {
                "top_n": top_n,
                "rows_returned": len(data),
                "truncated": truncated,
                "grouped_other": grouped_other,
                "tail_rows": tail_rows,
                "fetch_limit": fetch_limit,
            },
        }

        if series_list:
            spec["series"] = series_list
        elif color:
            spec["color"] = color

        if reference_lines:
            spec["reference_lines"] = reference_lines

        return {"spec": spec}

    def _sanitize_top_n(self, top_n: int | None) -> int:
        try:
            value = int(top_n) if top_n is not None else self.DEFAULT_TOP_N
        except (TypeError, ValueError):
            value = self.DEFAULT_TOP_N
        return max(1, min(value, 20))
