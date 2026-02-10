"use client";

import { useState } from "react";
import { DataSourceType, DatasetSummary } from "@/app/_lib/api";
import { CSVUploadZone } from "./CSVUploadZone";

// Map well-known dataset names to data source types
const DATASET_TO_SOURCE: Record<string, DataSourceType> = {
  "Visual Novel Database": "vndb",
  "VNDB Staff Collaboration": "vndb_collaboration",
  Polymarket: "polymarket",
  "Steam Games": "steam",
};

interface DatasetPickerModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCreateSession: (
    dataSource: DataSourceType,
    name: string,
    datasetIds?: string[]
  ) => void;
  isCreating: boolean;
  publicDatasets: DatasetSummary[];
  userDatasets: DatasetSummary[];
  onUpload?: (files: File[]) => void;
  isUploading?: boolean;
}

export function DatasetPickerModal({
  isOpen,
  onClose,
  onCreateSession,
  isCreating,
  publicDatasets,
  userDatasets,
  onUpload,
  isUploading = false,
}: DatasetPickerModalProps) {
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [sessionName, setSessionName] = useState("");

  if (!isOpen) return null;

  const toggleDataset = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const ids = Array.from(selectedIds);

    // Determine data source from selected datasets
    let dataSource: DataSourceType = "custom";
    if (ids.length === 1) {
      const selected = [...publicDatasets, ...userDatasets].find(
        (d) => d.id === ids[0]
      );
      if (selected) {
        dataSource = DATASET_TO_SOURCE[selected.name] || "custom";
      }
    }

    onCreateSession(dataSource, sessionName.trim(), ids.length > 0 ? ids : undefined);
  };

  const handleClose = () => {
    if (!isCreating) {
      setSessionName("");
      setSelectedIds(new Set());
      onClose();
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/50" onClick={handleClose} />

      <div className="relative bg-white rounded-lg shadow-xl w-full max-w-lg mx-4 p-6 max-h-[90vh] overflow-y-auto">
        <h2 className="text-lg font-semibold mb-4">New Session</h2>

        <form onSubmit={handleSubmit}>
          {/* Session Name */}
          <div className="mb-4">
            <label
              htmlFor="session-name"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              Session Name
            </label>
            <input
              id="session-name"
              type="text"
              value={sessionName}
              onChange={(e) => setSessionName(e.target.value)}
              placeholder="Untitled Session"
              maxLength={100}
              className="w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              disabled={isCreating}
            />
          </div>

          {/* Public Datasets */}
          {publicDatasets.length > 0 && (
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Public Datasets
              </label>
              <div className="space-y-1">
                {publicDatasets.map((ds) => (
                  <label
                    key={ds.id}
                    className={`flex items-center p-2 border rounded cursor-pointer transition-colors ${
                      selectedIds.has(ds.id)
                        ? "border-blue-500 bg-blue-50"
                        : "hover:bg-gray-50"
                    }`}
                  >
                    <input
                      type="checkbox"
                      checked={selectedIds.has(ds.id)}
                      onChange={() => toggleDataset(ds.id)}
                      disabled={isCreating}
                      className="mr-3"
                    />
                    <div className="flex-1">
                      <div className="text-sm font-medium">{ds.name}</div>
                      <div className="text-xs text-gray-500">
                        {ds.table_count} table{ds.table_count !== 1 ? "s" : ""}{" "}
                        &middot; {ds.total_rows.toLocaleString()} rows
                      </div>
                    </div>
                  </label>
                ))}
              </div>
            </div>
          )}

          {/* User Datasets */}
          {userDatasets.length > 0 && (
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Your Datasets
              </label>
              <div className="space-y-1">
                {userDatasets.map((ds) => (
                  <label
                    key={ds.id}
                    className={`flex items-center p-2 border rounded cursor-pointer transition-colors ${
                      selectedIds.has(ds.id)
                        ? "border-blue-500 bg-blue-50"
                        : "hover:bg-gray-50"
                    }`}
                  >
                    <input
                      type="checkbox"
                      checked={selectedIds.has(ds.id)}
                      onChange={() => toggleDataset(ds.id)}
                      disabled={isCreating}
                      className="mr-3"
                    />
                    <div className="flex-1">
                      <div className="text-sm font-medium">{ds.name}</div>
                      <div className="text-xs text-gray-500">
                        {ds.table_count} table{ds.table_count !== 1 ? "s" : ""}{" "}
                        &middot; {ds.total_rows.toLocaleString()} rows
                      </div>
                    </div>
                  </label>
                ))}
              </div>
            </div>
          )}

          {/* Upload Zone */}
          {onUpload && (
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Or Upload New Data
              </label>
              <CSVUploadZone
                onUpload={onUpload}
                isUploading={isUploading}
                compact
              />
            </div>
          )}
          {!onUpload && (
            <div className="mb-4">
              <CSVUploadZone onUpload={() => {}} compact />
            </div>
          )}

          {/* Actions */}
          <div className="flex justify-end gap-3">
            <button
              type="button"
              onClick={handleClose}
              disabled={isCreating}
              className="px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 rounded-md disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isCreating}
              className="px-4 py-2 text-sm text-white bg-blue-600 hover:bg-blue-700 rounded-md disabled:opacity-50 flex items-center gap-2"
            >
              {isCreating && (
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                    fill="none"
                  />
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  />
                </svg>
              )}
              {isCreating ? "Creating..." : "Create Session"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
