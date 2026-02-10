"use client";

import { ChartSpec, DatasetFull, TablePreview, DerivedTable } from "@/app/_lib/api";
import { ChartTab, DataView } from "@/app/_stores/workspace-store";
import { getRenderer } from "@/app/_lib/viz-registry";
import { ChartTabBar } from "./ChartTabBar";
import { DataExplorerPanel } from "./DataExplorerPanel";

export type NavTab = "viz" | "data";

interface VizPanelProps {
  activeTab: NavTab;
  onTabChange: (tab: NavTab) => void;
  currentVisualization?: ChartSpec | null;
  queryResult?: { data: unknown[]; columns: string[] } | null;
  visualizationTabs?: ChartTab[];
  activeVizTabIndex?: number | null;
  onVizTabClick?: (index: number) => void;
  // Data Explorer props
  sessionDatasets?: DatasetFull[];
  tablePreview?: TablePreview | null;
  isPreviewLoading?: boolean;
  selectedDatasetTable?: { datasetId: string; tableName: string } | null;
  activeDataView?: DataView;
  onSelectTable?: (datasetId: string, tableName: string) => void;
  onSwitchDataView?: (view: DataView) => void;
  // Derived tables
  derivedTables?: DerivedTable[];
  onPromoteDerivedTable?: (tableName: string, newName: string) => Promise<void>;
}

function TabBar({
  activeTab,
  onTabChange,
}: {
  activeTab: NavTab;
  onTabChange: (tab: NavTab) => void;
}) {
  const tabs: { id: NavTab; label: string }[] = [
    { id: "viz", label: "Visualization" },
    { id: "data", label: "Data" },
  ];

  return (
    <div className="flex border-b bg-gray-50">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          onClick={() => onTabChange(tab.id)}
          className={`px-4 py-2 text-sm font-medium transition-colors ${
            activeTab === tab.id
              ? "text-blue-600 border-b-2 border-blue-600 bg-white"
              : "text-gray-500 hover:text-gray-700"
          }`}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}

function EmptyVizState() {
  return (
    <div className="h-full flex items-center justify-center text-gray-500">
      <div className="text-center">
        <svg
          className="w-16 h-16 mx-auto text-gray-300 mb-4"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.5}
            d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
          />
        </svg>
        <p className="text-lg mb-1">No visualization yet</p>
        <p className="text-sm">
          Ask a question to generate charts
        </p>
      </div>
    </div>
  );
}

export function VizPanel({
  activeTab,
  onTabChange,
  currentVisualization,
  queryResult,
  visualizationTabs = [],
  activeVizTabIndex = null,
  onVizTabClick,
  sessionDatasets = [],
  tablePreview,
  isPreviewLoading = false,
  selectedDatasetTable,
  activeDataView = "preview",
  onSelectTable,
  onSwitchDataView,
  derivedTables = [],
  onPromoteDerivedTable,
}: VizPanelProps) {
  const renderContent = () => {
    switch (activeTab) {
      case "viz": {
        if (!currentVisualization) {
          return <EmptyVizState />;
        }
        const spec = currentVisualization as unknown as Record<string, unknown>;
        const Renderer = getRenderer(spec);
        if (!Renderer) return <EmptyVizState />;
        return (
          <div className="h-full p-4">
            <Renderer spec={spec} />
          </div>
        );
      }

      case "data":
        return (
          <DataExplorerPanel
            sessionDatasets={sessionDatasets}
            queryResult={queryResult ?? null}
            tablePreview={tablePreview ?? null}
            isPreviewLoading={isPreviewLoading}
            selectedDatasetTable={selectedDatasetTable ?? null}
            activeDataView={activeDataView}
            onSelectTable={onSelectTable ?? (() => {})}
            onSwitchDataView={onSwitchDataView ?? (() => {})}
            derivedTables={derivedTables}
            onPromoteDerivedTable={onPromoteDerivedTable}
          />
        );

      default:
        return null;
    }
  };

  return (
    <div className="flex flex-col h-full bg-white">
      <TabBar activeTab={activeTab} onTabChange={onTabChange} />
      {activeTab === "viz" && visualizationTabs.length > 0 && onVizTabClick && (
        <ChartTabBar
          tabs={visualizationTabs}
          activeIndex={activeVizTabIndex}
          onTabClick={onVizTabClick}
        />
      )}
      <div className="flex-1 overflow-hidden">{renderContent()}</div>
    </div>
  );
}
