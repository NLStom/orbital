"use client";

import { useCallback, useRef, useState } from "react";

interface CSVUploadZoneProps {
  onUpload: (files: File[]) => void;
  isUploading?: boolean;
  compact?: boolean;
}

export function CSVUploadZone({
  onUpload,
  isUploading = false,
  compact = false,
}: CSVUploadZoneProps) {
  const [isDragOver, setIsDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFiles = useCallback(
    (fileList: FileList | null) => {
      if (!fileList || fileList.length === 0) return;
      const csvFiles = Array.from(fileList).filter(
        (f) => f.name.endsWith(".csv") || f.type === "text/csv"
      );
      if (csvFiles.length > 0) {
        onUpload(csvFiles);
      }
    },
    [onUpload]
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragOver(false);
      handleFiles(e.dataTransfer.files);
    },
    [handleFiles]
  );

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback(() => {
    setIsDragOver(false);
  }, []);

  if (isUploading) {
    return (
      <div
        className={`flex items-center justify-center border-2 border-dashed border-blue-300 bg-blue-50 rounded-lg ${compact ? "p-3" : "p-8"}`}
      >
        <div className="flex items-center gap-2 text-blue-600 text-sm">
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
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
            />
          </svg>
          Uploading...
        </div>
      </div>
    );
  }

  return (
    <div
      onDrop={handleDrop}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onClick={() => inputRef.current?.click()}
      className={`flex flex-col items-center justify-center border-2 border-dashed rounded-lg cursor-pointer transition-colors ${
        isDragOver
          ? "border-blue-500 bg-blue-50"
          : "border-gray-300 hover:border-gray-400 hover:bg-gray-50"
      } ${compact ? "p-3 gap-1" : "p-8 gap-2"}`}
    >
      <input
        ref={inputRef}
        type="file"
        accept=".csv"
        multiple
        className="hidden"
        onChange={(e) => handleFiles(e.target.files)}
      />
      <span className={`text-gray-500 ${compact ? "text-xs" : "text-sm"}`}>
        Drag CSV files here or click to browse
      </span>
      {!compact && (
        <span className="text-xs text-gray-400">Max 50MB per file</span>
      )}
    </div>
  );
}
