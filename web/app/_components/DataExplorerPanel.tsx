"use client";

import { useState } from "react";
import { DatasetFull, TablePreview, DerivedTable } from "@/app/_lib/api";
import { DataView } from "@/app/_stores/workspace-store";

interface DataExplorerPanelProps {
  sessionDatasets: DatasetFull[];
  queryResult: { data: unknown[]; columns: string[] } | null;
  tablePreview: TablePreview | null;
  isPreviewLoading: boolean;
  selectedDatasetTable: { datasetId: string; tableName: string } | null;
  activeDataView: DataView;
  onSelectTable: (datasetId: string, tableName: string) => void;
  onSwitchDataView: (view: DataView) => void;
  derivedTables?: DerivedTable[];
  onPromoteDerivedTable?: (tableName: string, newName: string) => Promise<void>;
}

function DatasetList({
  datasets,
  selectedDatasetTable,
  onSelectTable,
}: {
  datasets: DatasetFull[];
  selectedDatasetTable: { datasetId: string; tableName: string } | null;
  onSelectTable: (datasetId: string, tableName: string) => void;
}) {
  if (datasets.length === 0) {
    return (
      <div className="p-4 text-center text-gray-500 text-sm">
        No datasets attached. Upload a CSV to get started.
      </div>
    );
  }

  return (
    <div className="divide-y">
      {datasets.map((ds) => (
        <div key={ds.id} className="p-3">
          <div className="flex items-center gap-2 text-sm font-medium text-gray-900">
            <svg
              className="w-4 h-4 text-gray-400 shrink-0"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"
              />
            </svg>
            {ds.name}
          </div>
          <div className="mt-1 space-y-0.5">
            {ds.tables.map((table) => {
              const isSelected =
                selectedDatasetTable?.datasetId === ds.id &&
                selectedDatasetTable?.tableName === table.name;
              return (
                <button
                  key={table.name}
                  onClick={() => onSelectTable(ds.id, table.name)}
                  className={`w-full flex items-center justify-between px-2 py-1.5 rounded text-xs transition-colors ${
                    isSelected
                      ? "bg-blue-50 text-blue-700"
                      : "text-gray-600 hover:bg-gray-50"
                  }`}
                >
                  <span className="ml-6 truncate">{table.name}</span>
                  <span className="text-gray-400 shrink-0 ml-2">
                    {table.row_count.toLocaleString()} rows, {table.columns.length} cols
                  </span>
                </button>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}

function DerivedTablesList({
  derivedTables,
  onPromote,
}: {
  derivedTables: DerivedTable[];
  onPromote: (tableName: string, newName: string) => Promise<void>;
}) {
  const [promotingTable, setPromotingTable] = useState<string | null>(null);

  if (derivedTables.length === 0) {
    return null;
  }

  const handlePromote = async (table: DerivedTable) => {
    const newName = window.prompt(
      `Enter a name for the new dataset:`,
      table.name.replace(/_/g, " ")
    );
    if (!newName) return;

    setPromotingTable(table.name);
    try {
      await onPromote(table.name, newName);
    } finally {
      setPromotingTable(null);
    }
  };

  return (
    <div className="p-3 border-t bg-amber-50">
      <div className="flex items-center gap-2 text-sm font-medium text-amber-800 mb-2">
        <svg
          className="w-4 h-4 shrink-0"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
          />
        </svg>
        Derived Tables
        <span className="text-xs font-normal text-amber-600">(temporary)</span>
      </div>
      <div className="space-y-1">
        {derivedTables.map((table) => (
          <div
            key={table.pg_table_name}
            className="flex items-center justify-between px-2 py-1.5 rounded bg-white border border-amber-200"
          >
            <div className="flex-1 min-w-0">
              <span className="text-xs text-gray-700 truncate block">{table.name}</span>
              <span className="text-xs text-gray-400">
                {table.row_count.toLocaleString()} rows, {table.columns.length} cols
              </span>
            </div>
            <button
              onClick={() => handlePromote(table)}
              disabled={promotingTable === table.name}
              className="ml-2 px-2 py-1 text-xs bg-blue-50 text-blue-600 rounded hover:bg-blue-100 disabled:opacity-50 disabled:cursor-not-allowed shrink-0"
              title="Save as permanent dataset"
            >
              {promotingTable === table.name ? (
                <span className="flex items-center gap-1">
                  <svg className="w-3 h-3 animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  Saving...
                </span>
              ) : (
                "Save as Dataset"
              )}
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}

function DataToggleBar({
  activeDataView,
  onSwitch,
  previewLabel,
  queryLabel,
}: {
  activeDataView: DataView;
  onSwitch: (view: DataView) => void;
  previewLabel: string | null;
  queryLabel: string | null;
}) {
  if (!previewLabel && !queryLabel) return null;

  return (
    <div className="flex border-b bg-gray-50 px-3 py-1.5 gap-2 text-xs">
      {previewLabel && (
        <button
          onClick={() => onSwitch("preview")}
          className={`px-2 py-1 rounded transition-colors ${
            activeDataView === "preview"
              ? "bg-white text-blue-700 shadow-sm"
              : "text-gray-500 hover:text-gray-700"
          }`}
        >
          {previewLabel}
        </button>
      )}
      {queryLabel && (
        <button
          onClick={() => onSwitch("query")}
          className={`px-2 py-1 rounded transition-colors ${
            activeDataView === "query"
              ? "bg-white text-blue-700 shadow-sm"
              : "text-gray-500 hover:text-gray-700"
          }`}
        >
          {queryLabel}
        </button>
      )}
    </div>
  );
}

function DataTable({
  data,
  columns,
}: {
  data: Record<string, unknown>[];
  columns: string[];
}) {
  if (!data || data.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center text-gray-500 text-sm">
        No data
      </div>
    );
  }

  return (
    <div className="overflow-auto flex-1">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50 sticky top-0">
          <tr>
            {columns.map((col) => (
              <th
                key={col}
                className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
              >
                {col}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {data.slice(0, 100).map((row, i) => (
            <tr key={i} className="hover:bg-gray-50">
              {columns.map((col) => (
                <td
                  key={col}
                  className="px-4 py-1.5 text-xs text-gray-900 whitespace-nowrap"
                >
                  {String(row[col] ?? "")}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {data.length > 100 && (
        <div className="p-2 text-center text-xs text-gray-500 bg-gray-50 border-t">
          Showing 100 of {data.length} rows
        </div>
      )}
    </div>
  );
}

export function DataExplorerPanel({
  sessionDatasets,
  queryResult,
  tablePreview,
  isPreviewLoading,
  selectedDatasetTable,
  activeDataView,
  onSelectTable,
  onSwitchDataView,
  derivedTables = [],
  onPromoteDerivedTable,
}: DataExplorerPanelProps) {
  const previewLabel = selectedDatasetTable
    ? `Table: ${selectedDatasetTable.tableName} (preview)`
    : null;
  const queryLabel = queryResult ? "Query result" : null;

  const renderDataContent = () => {
    if (activeDataView === "preview") {
      if (isPreviewLoading) {
        return (
          <div className="flex-1 flex items-center justify-center">
            <div className="w-5 h-5 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
          </div>
        );
      }
      if (tablePreview) {
        return (
          <DataTable
            data={tablePreview.data as Record<string, unknown>[]}
            columns={tablePreview.columns}
          />
        );
      }
      if (!selectedDatasetTable && sessionDatasets.length > 0) {
        return (
          <div className="flex-1 flex items-center justify-center text-gray-500 text-sm">
            Select a table to preview its data
          </div>
        );
      }
      return null;
    }

    // query view
    if (queryResult) {
      return (
        <DataTable
          data={queryResult.data as Record<string, unknown>[]}
          columns={queryResult.columns}
        />
      );
    }

    return (
      <div className="flex-1 flex items-center justify-center text-gray-500 text-sm">
        Query results will appear here
      </div>
    );
  };

  return (
    <div className="flex flex-col h-full">
      {/* Top: Dataset list + Derived tables */}
      <div className="border-b max-h-[50%] overflow-y-auto">
        <DatasetList
          datasets={sessionDatasets}
          selectedDatasetTable={selectedDatasetTable}
          onSelectTable={onSelectTable}
        />
        {derivedTables.length > 0 && onPromoteDerivedTable && (
          <DerivedTablesList
            derivedTables={derivedTables}
            onPromote={onPromoteDerivedTable}
          />
        )}
      </div>

      {/* Toggle bar */}
      <DataToggleBar
        activeDataView={activeDataView}
        onSwitch={onSwitchDataView}
        previewLabel={previewLabel}
        queryLabel={queryLabel}
      />

      {/* Bottom: Data display */}
      <div className="flex-1 overflow-hidden flex flex-col">
        {renderDataContent()}
      </div>
    </div>
  );
}
