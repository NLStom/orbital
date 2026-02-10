"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api, Artifact, ChartSpec, DataSourceType } from "@/app/_lib/api";
import { ChartRenderer } from "@/app/_components/visualization/ChartRenderer";
import { ReportRenderer, type ReportSection } from "@/app/_components/ReportRenderer";

const DATA_SOURCE_LABELS: Record<DataSourceType, string> = {
  custom: "Custom",
};

function formatDate(isoString: string): string {
  const date = new Date(isoString);
  return date.toLocaleDateString([], {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

function isReportViz(viz: Record<string, unknown>): boolean {
  return viz.type === "report";
}

export default function ArtifactPage() {
  const params = useParams();
  const artifactId = params.id as string;

  const [artifact, setArtifact] = useState<Artifact | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    async function loadArtifact() {
      try {
        const data = await api.getArtifact(artifactId);
        setArtifact(data);
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "Failed to load artifact"
        );
      } finally {
        setIsLoading(false);
      }
    }
    loadArtifact();
  }, [artifactId]);

  const handleCopyLink = () => {
    const url = window.location.href;
    navigator.clipboard.writeText(url);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleExport = (format: "png" | "svg" | "csv" | "json") => {
    // TODO: Implement export functionality
    console.log("Export:", format);
  };

  // Loading state
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-gray-500">Loading artifact...</p>
        </div>
      </div>
    );
  }

  // Error state
  if (error || !artifact) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center max-w-md mx-auto p-8">
          <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg
              className="w-8 h-8 text-red-600"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
              />
            </svg>
          </div>
          <h2 className="text-xl font-semibold text-gray-900 mb-2">
            {error === "Artifact not found" ? "Artifact Not Found" : "Error"}
          </h2>
          <p className="text-gray-500 mb-6">
            {error || "This artifact could not be found."}
          </p>
          <Link
            href="/"
            className="inline-block px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
          >
            Go to Home
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b">
        <div className="max-w-5xl mx-auto px-4 py-6">
          <div className="flex items-start justify-between">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-2">
                <span className="px-2 py-0.5 text-xs bg-gray-100 text-gray-600 rounded-full">
                  {DATA_SOURCE_LABELS[artifact.dataSource]}
                </span>
                <span className="text-xs text-gray-400">
                  Created {formatDate(artifact.createdAt)}
                </span>
              </div>
              <h1 className="text-2xl font-bold text-gray-900 mb-2">
                {artifact.name}
              </h1>
              {artifact.description && (
                <p className="text-gray-600">{artifact.description}</p>
              )}
            </div>

            {/* Actions */}
            <div className="flex items-center gap-2 ml-4">
              <button
                onClick={handleCopyLink}
                className="flex items-center gap-2 px-3 py-2 text-sm border rounded-md hover:bg-gray-50"
              >
                {copied ? (
                  <>
                    <svg
                      className="w-4 h-4 text-green-600"
                      fill="currentColor"
                      viewBox="0 0 20 20"
                    >
                      <path
                        fillRule="evenodd"
                        d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                        clipRule="evenodd"
                      />
                    </svg>
                    Copied!
                  </>
                ) : (
                  <>
                    <svg
                      className="w-4 h-4"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"
                      />
                    </svg>
                    Copy Link
                  </>
                )}
              </button>

              {!isReportViz(artifact.visualization as Record<string, unknown>) && (
                <div className="relative group">
                  <button className="flex items-center gap-1 px-3 py-2 text-sm border rounded-md hover:bg-gray-50">
                    Export
                    <svg
                      className="w-4 h-4"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M19 9l-7 7-7-7"
                      />
                    </svg>
                  </button>
                  <div className="absolute right-0 mt-1 w-32 bg-white border rounded-md shadow-lg opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all">
                    <button
                      onClick={() => handleExport("png")}
                      className="w-full px-3 py-2 text-left text-sm hover:bg-gray-100"
                    >
                      PNG
                    </button>
                    <button
                      onClick={() => handleExport("svg")}
                      className="w-full px-3 py-2 text-left text-sm hover:bg-gray-100"
                    >
                      SVG
                    </button>
                    <button
                      onClick={() => handleExport("csv")}
                      className="w-full px-3 py-2 text-left text-sm hover:bg-gray-100"
                    >
                      CSV
                    </button>
                    <button
                      onClick={() => handleExport("json")}
                      className="w-full px-3 py-2 text-left text-sm hover:bg-gray-100"
                    >
                      JSON
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Visualization */}
      <div className="max-w-5xl mx-auto px-4 py-8">
        <div className="bg-white rounded-lg border shadow-sm p-6 min-h-[400px]">
          {(artifact.visualization as Record<string, unknown>).type ===
          "report" ? (
            <ReportRenderer
              sections={
                (artifact.visualization as Record<string, unknown>)
                  .sections as ReportSection[]
              }
            />
          ) : (
            <ChartRenderer
              spec={artifact.visualization as unknown as Record<string, unknown>}
            />
          )}
        </div>

        {/* Data Snapshot Info */}
        <div className="mt-6 p-4 bg-gray-50 rounded-lg border">
          <h3 className="text-sm font-medium text-gray-700 mb-2">
            Data Snapshot
          </h3>
          <div className="flex flex-wrap gap-4 text-sm text-gray-500">
            <span>
              {artifact.dataSnapshot.rowCount} row
              {artifact.dataSnapshot.rowCount !== 1 ? "s" : ""}
            </span>
            <span>
              {artifact.dataSnapshot.columns.length} column
              {artifact.dataSnapshot.columns.length !== 1 ? "s" : ""}
            </span>
            <span>
              Captured {formatDate(artifact.dataSnapshot.capturedAt)}
            </span>
          </div>
          {artifact.dataSnapshot.columns.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-1">
              {artifact.dataSnapshot.columns.map((col) => (
                <span
                  key={col}
                  className="px-2 py-0.5 text-xs bg-white border rounded"
                >
                  {col}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Footer */}
      <footer className="border-t bg-white py-6">
        <div className="max-w-5xl mx-auto px-4 flex items-center justify-between">
          <Link href="/" className="text-sm text-gray-500 hover:text-gray-700">
            Powered by Orbital
          </Link>
          <p className="text-xs text-gray-400">
            This artifact is publicly accessible to anyone with the link.
          </p>
        </div>
      </footer>
    </div>
  );
}
