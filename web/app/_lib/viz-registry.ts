/**
 * Visualization Registry — centralized dispatch for all viz types.
 *
 * Both the catalog page and VizPanel use this registry for rendering.
 */
import { ComponentType } from "react";
import { ChartRenderer } from "@/app/_components/visualization/ChartRenderer";

export interface VizType {
  id: string;
  category: "chart";
  label: string;
  description: string;
  renderer: ComponentType<{ spec: Record<string, unknown> }>;
  sampleSpec: Record<string, unknown>;
}

const vizTypes: VizType[] = [
  // --- Charts (all use ChartRenderer) ---
  {
    id: "bar",
    category: "chart",
    label: "Bar Chart",
    description: "Compare values across categories",
    renderer: ChartRenderer,
    sampleSpec: {
      type: "bar",
      title: "Sample Bar Chart",
      data: [
        { category: "A", count: 25 },
        { category: "B", count: 18 },
        { category: "C", count: 32 },
      ],
      x: "category",
      y: "count",
    },
  },
  {
    id: "line",
    category: "chart",
    label: "Line Chart",
    description: "Show trends over time or ordered sequences",
    renderer: ChartRenderer,
    sampleSpec: {
      type: "line",
      title: "Trends Over Time",
      data: [
        { year: "2018", value: 45 },
        { year: "2019", value: 52 },
        { year: "2020", value: 48 },
        { year: "2021", value: 65 },
      ],
      x: "year",
      y: "value",
    },
  },
  {
    id: "scatter",
    category: "chart",
    label: "Scatter Plot",
    description: "Show correlation between two numeric variables",
    renderer: ChartRenderer,
    sampleSpec: {
      type: "scatter",
      title: "Correlation",
      data: [
        { x: 7.2, y: 1200 },
        { x: 8.5, y: 3400 },
        { x: 6.8, y: 800 },
      ],
      x: "x",
      y: "y",
    },
  },
  {
    id: "pie",
    category: "chart",
    label: "Pie Chart",
    description: "Show parts of a whole",
    renderer: ChartRenderer,
    sampleSpec: {
      type: "pie",
      title: "Distribution",
      data: [
        { category: "A", count: 35 },
        { category: "B", count: 45 },
        { category: "C", count: 20 },
      ],
      x: "category",
      y: "count",
    },
  },
  {
    id: "area",
    category: "chart",
    label: "Area Chart",
    description: "Show cumulative values over time",
    renderer: ChartRenderer,
    sampleSpec: {
      type: "area",
      title: "Cumulative Values",
      data: [
        { month: "Jan", value: 1000 },
        { month: "Feb", value: 2500 },
        { month: "Mar", value: 4200 },
      ],
      x: "month",
      y: "value",
    },
  },
];

// --- Lookup maps (built once) ---

const typeById = new Map(vizTypes.map((vt) => [vt.id, vt]));

// --- Public API ---

export function getAllVizTypes(): VizType[] {
  return vizTypes;
}

export function getVizTypesByCategory(category: string): VizType[] {
  return vizTypes.filter((vt) => vt.category === category);
}

export function getVizCategory(spec: Record<string, unknown>): string | null {
  const type = spec.type as string | undefined;
  if (!type) return null;
  const vt = typeById.get(type);
  return vt?.category ?? null;
}

export function getRenderer(
  spec: Record<string, unknown>
): ComponentType<{ spec: Record<string, unknown> }> | null {
  const type = spec.type as string | undefined;
  if (!type) return null;
  const vt = typeById.get(type);
  return vt?.renderer ?? null;
}
