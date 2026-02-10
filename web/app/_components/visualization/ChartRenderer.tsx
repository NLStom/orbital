"use client";

import { useMemo } from "react";
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  ScatterChart,
  Scatter,
  PieChart,
  Pie,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Cell,
  ReferenceLine,
} from "recharts";

interface ChartSpec {
  type: string;
  title?: string;
  data: Array<Record<string, unknown>>;
  x: string;
  y: string;
  color?: string;
  series?: string[];
  x_label?: string;
  y_label?: string;
  reference_lines?: Array<{ axis: string; value: string | number; label?: string; color?: string }>;
  dashed?: string[];
}

interface ChartRendererProps {
  spec: Record<string, unknown>;
}

const parseNumeric = (value: unknown): number | null => {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === "string") {
    const trimmed = value.trim();
    if (!trimmed) {
      return null;
    }
    const numericValue = Number(trimmed);
    if (!Number.isNaN(numericValue)) {
      return numericValue;
    }
  }
  return null;
};

const getSortableValue = (value: unknown): number | null => {
  const numeric = parseNumeric(value);
  if (numeric !== null) {
    return numeric;
  }

  if (typeof value === "string") {
    const timestamp = Date.parse(value);
    if (!Number.isNaN(timestamp)) {
      return timestamp;
    }
  }

  return null;
};

// Color palette for charts
const COLORS = [
  "#3b82f6", // blue
  "#10b981", // green
  "#f59e0b", // amber
  "#ef4444", // red
  "#8b5cf6", // purple
  "#06b6d4", // cyan
  "#f97316", // orange
  "#ec4899", // pink
];

/**
 * Renders chart visualizations using Recharts.
 */
export function ChartRenderer({ spec }: ChartRendererProps) {
  const chartSpec = spec as unknown as ChartSpec;
  const {
    type,
    title,
    data,
    x,
    y,
    series,
    x_label: xLabel,
    y_label: yLabel,
    reference_lines: referenceLines,
    dashed,
  } = chartSpec;

  const normalizedData = useMemo(() => {
    if (!data || data.length === 0) {
      return [] as Array<Record<string, unknown>>;
    }

    const numericKeys = series ?? [y];
    return data.map((row) => {
      const normalizedRow = { ...row } as Record<string, unknown>;
      for (const key of numericKeys) {
        const numericVal = parseNumeric(row[key]);
        if (numericVal !== null) {
          normalizedRow[key] = numericVal;
        }
      }
      return normalizedRow;
    });
  }, [data, y, series]);

  const sortedData = useMemo(() => {
    if (normalizedData.length === 0) {
      return normalizedData;
    }

    const sortReady = normalizedData.every((row) => getSortableValue(row[x]) !== null);
    if (!sortReady) {
      return normalizedData;
    }

    return [...normalizedData].sort((a, b) => {
      const aValue = getSortableValue(a[x]);
      const bValue = getSortableValue(b[x]);
      if (aValue === null || bValue === null) {
        return 0;
      }
      return aValue - bValue;
    });
  }, [normalizedData, x]);

  if (sortedData.length === 0) {
    return (
      <div className="p-4 bg-gray-100 text-gray-600 rounded-lg">
        No data to display
      </div>
    );
  }

  const axisLabelProps = yLabel
    ? { value: yLabel, angle: -90, position: "left" as const, offset: 55 }
    : undefined;
  const sharedMargins = { top: 20, right: 30, left: 80, bottom: 70 };

  const renderChart = () => {
    switch (type) {
      case "bar":
        return (
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={sortedData} margin={sharedMargins}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis
                dataKey={x}
                tick={{ fontSize: 12 }}
                angle={-45}
                textAnchor="end"
                height={70}
                label={xLabel ? { value: xLabel, position: "insideBottom", offset: -5 } : undefined}
              />
              <YAxis tick={{ fontSize: 12 }} width={80} label={axisLabelProps} />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#fff",
                  border: "1px solid #e5e7eb",
                  borderRadius: "8px",
                }}
              />
              <Bar dataKey={y} fill="#3b82f6" radius={[4, 4, 0, 0]} />
              {referenceLines?.map((rl, i) => (
                <ReferenceLine
                  key={i}
                  x={rl.axis === "x" ? rl.value : undefined}
                  y={rl.axis === "y" ? rl.value : undefined}
                  stroke={rl.color || "#888"}
                  strokeDasharray="4 4"
                  label={rl.label ? { value: rl.label, position: "top" as const } : undefined}
                />
              ))}
            </BarChart>
          </ResponsiveContainer>
        );

      case "line":
        return (
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={sortedData} margin={sharedMargins}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis
                dataKey={x}
                tick={{ fontSize: 12 }}
                angle={-45}
                textAnchor="end"
                height={70}
                label={xLabel ? { value: xLabel, position: "insideBottom", offset: -5 } : undefined}
              />
              <YAxis tick={{ fontSize: 12 }} width={80} label={axisLabelProps} />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#fff",
                  border: "1px solid #e5e7eb",
                  borderRadius: "8px",
                }}
              />
              {series ? (
                series.map((s, i) => (
                  <Line
                    key={s}
                    type="monotone"
                    dataKey={s}
                    stroke={COLORS[i % COLORS.length]}
                    strokeWidth={2}
                    dot={{ fill: COLORS[i % COLORS.length], strokeWidth: 2, r: 4 }}
                    activeDot={{ r: 6 }}
                    connectNulls
                    strokeDasharray={dashed?.includes(s) ? "8 4" : undefined}
                  />
                ))
              ) : (
                <Line
                  type="monotone"
                  dataKey={y}
                  stroke="#3b82f6"
                  strokeWidth={2}
                  dot={{ fill: "#3b82f6", strokeWidth: 2, r: 4 }}
                  activeDot={{ r: 6 }}
                />
              )}
              {referenceLines?.map((rl, i) => (
                <ReferenceLine
                  key={i}
                  x={rl.axis === "x" ? rl.value : undefined}
                  y={rl.axis === "y" ? rl.value : undefined}
                  stroke={rl.color || "#888"}
                  strokeDasharray="4 4"
                  label={rl.label ? { value: rl.label, position: "top" as const } : undefined}
                />
              ))}
              {series && <Legend />}
            </LineChart>
          </ResponsiveContainer>
        );

      case "scatter":
        return (
          <ResponsiveContainer width="100%" height={300}>
            <ScatterChart margin={{ top: 20, right: 30, left: 80, bottom: 40 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis
                dataKey={x}
                type="number"
                name={x}
                tick={{ fontSize: 12 }}
                label={xLabel ? { value: xLabel, position: "insideBottom", offset: -5 } : undefined}
              />
              <YAxis
                dataKey={y}
                type="number"
                name={y}
                tick={{ fontSize: 12 }}
                width={80}
                label={axisLabelProps}
              />
              <Tooltip
                cursor={{ strokeDasharray: "3 3" }}
                contentStyle={{
                  backgroundColor: "#fff",
                  border: "1px solid #e5e7eb",
                  borderRadius: "8px",
                }}
              />
              <Scatter data={sortedData} fill="#3b82f6">
                {sortedData.map((_, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Scatter>
            </ScatterChart>
          </ResponsiveContainer>
        );

      case "pie":
        return (
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={sortedData}
                dataKey={y}
                nameKey={x}
                cx="50%"
                cy="50%"
                outerRadius={100}
                label={({ name, percent }) =>
                  `${name ?? ""}: ${((percent ?? 0) * 100).toFixed(0)}%`
                }
                labelLine={{ stroke: "#9ca3af" }}
              >
                {sortedData.map((_, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{
                  backgroundColor: "#fff",
                  border: "1px solid #e5e7eb",
                  borderRadius: "8px",
                }}
              />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        );

      case "area":
        return (
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={sortedData} margin={sharedMargins}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis
                dataKey={x}
                tick={{ fontSize: 12 }}
                angle={-45}
                textAnchor="end"
                height={70}
                label={xLabel ? { value: xLabel, position: "insideBottom", offset: -5 } : undefined}
              />
              <YAxis tick={{ fontSize: 12 }} width={80} label={axisLabelProps} />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#fff",
                  border: "1px solid #e5e7eb",
                  borderRadius: "8px",
                }}
              />
              {series ? (
                series.map((s, i) => (
                  <Area
                    key={s}
                    type="monotone"
                    dataKey={s}
                    stroke={COLORS[i % COLORS.length]}
                    fill={COLORS[i % COLORS.length]}
                    fillOpacity={0.3}
                    connectNulls
                    strokeDasharray={dashed?.includes(s) ? "8 4" : undefined}
                  />
                ))
              ) : (
                <Area
                  type="monotone"
                  dataKey={y}
                  stroke="#3b82f6"
                  fill="#3b82f6"
                  fillOpacity={0.3}
                />
              )}
              {referenceLines?.map((rl, i) => (
                <ReferenceLine
                  key={i}
                  x={rl.axis === "x" ? rl.value : undefined}
                  y={rl.axis === "y" ? rl.value : undefined}
                  stroke={rl.color || "#888"}
                  strokeDasharray="4 4"
                  label={rl.label ? { value: rl.label, position: "top" as const } : undefined}
                />
              ))}
              {series && <Legend />}
            </AreaChart>
          </ResponsiveContainer>
        );

      default:
        return (
          <div className="p-4">
            <p className="text-gray-500 mb-2">
              Unsupported chart type: {type}
            </p>
            <pre className="bg-gray-100 p-2 rounded text-sm overflow-auto">
              {JSON.stringify(spec, null, 2)}
            </pre>
          </div>
        );
    }
  };

  return (
    <div className="p-4">
      {title && <h3 className="text-lg font-semibold mb-4">{title}</h3>}
      {renderChart()}
    </div>
  );
}
