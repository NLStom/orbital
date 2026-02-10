"use client";

import { DatasetFull } from "@/app/_lib/api";
import { CSVUploadZone } from "./CSVUploadZone";

interface DatasetPanelProps {
  datasets: DatasetFull[];
  isUploading: boolean;
  onUpload: (files: File[]) => void;
  onShare: (datasetId: string) => void;
  onShareAll: () => void;
}

export function DatasetPanel({
  datasets,
  isUploading,
  onUpload,
  onShare,
  onShareAll,
}: DatasetPanelProps) {
  const hasPrivate = datasets.some(
    (d) => d.visibility === "private" && d.owner !== "system"
  );

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium text-gray-700">Datasets</h3>
        {hasPrivate && (
          <button
            onClick={onShareAll}
            className="text-xs text-blue-600 hover:text-blue-700"
          >
            Share all
          </button>
        )}
      </div>

      {datasets.map((ds) => (
        <div
          key={ds.id}
          className="flex items-center justify-between p-2 bg-gray-50 rounded text-sm"
        >
          <div>
            <span className="font-medium">{ds.name}</span>
            <span className="ml-2 text-xs text-gray-400">
              {ds.tables.length} table{ds.tables.length !== 1 ? "s" : ""}
            </span>
          </div>
          {ds.visibility === "private" && ds.owner !== "system" && (
            <button
              onClick={() => onShare(ds.id)}
              className="text-xs px-2 py-1 bg-blue-100 text-blue-700 rounded hover:bg-blue-200"
            >
              Share
            </button>
          )}
          {ds.visibility === "public" && (
            <span className="text-xs text-green-600">Public</span>
          )}
        </div>
      ))}

      <CSVUploadZone onUpload={onUpload} isUploading={isUploading} compact />
    </div>
  );
}
