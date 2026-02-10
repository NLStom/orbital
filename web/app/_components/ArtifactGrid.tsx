"use client";

import { ArtifactSummary, DataSourceType } from "@/app/_lib/api";

interface ArtifactGridProps {
  artifacts: ArtifactSummary[];
  isLoading: boolean;
  onArtifactClick: (id: string) => void;
  onCopyLink: (id: string) => void;
}

const DATA_SOURCE_COLORS: Record<DataSourceType, string> = {
  vndb: "bg-purple-100 text-purple-700",
  vndb_collaboration: "bg-pink-100 text-pink-700",
  polymarket: "bg-blue-100 text-blue-700",
  steam: "bg-green-100 text-green-700",
  custom: "bg-gray-100 text-gray-700",
};

const DATA_SOURCE_LABELS: Record<DataSourceType, string> = {
  vndb: "VNDB",
  vndb_collaboration: "VNDB Collaboration",
  polymarket: "Polymarket",
  steam: "Steam",
  custom: "Custom",
};

function formatDate(isoString: string): string {
  const date = new Date(isoString);
  return date.toLocaleDateString();
}

function SkeletonCard() {
  return (
    <div
      data-testid="skeleton-card"
      className="p-4 border rounded-lg animate-pulse"
    >
      <div className="h-24 bg-gray-200 rounded mb-3" />
      <div className="h-4 bg-gray-200 rounded w-3/4 mb-2" />
      <div className="h-3 bg-gray-200 rounded w-1/2" />
    </div>
  );
}

function ChartIcon() {
  return (
    <svg
      className="w-8 h-8 text-gray-400"
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
  );
}

function GraphIcon() {
  return (
    <svg
      className="w-8 h-8 text-gray-400"
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
    >
      <circle cx="12" cy="5" r="2" strokeWidth={1.5} />
      <circle cx="5" cy="19" r="2" strokeWidth={1.5} />
      <circle cx="19" cy="19" r="2" strokeWidth={1.5} />
      <path strokeLinecap="round" strokeWidth={1.5} d="M12 7v4M7 17l3-6M17 17l-3-6" />
    </svg>
  );
}

function ReportIcon() {
  return (
    <svg
      className="w-8 h-8 text-gray-400"
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={1.5}
        d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
      />
    </svg>
  );
}

export function ArtifactGrid({
  artifacts,
  isLoading,
  onArtifactClick,
  onCopyLink,
}: ArtifactGridProps) {
  if (isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <SkeletonCard />
        <SkeletonCard />
        <SkeletonCard />
      </div>
    );
  }

  if (artifacts.length === 0) {
    return (
      <div className="text-center py-12 text-gray-500">
        <p className="text-lg">No artifacts yet</p>
        <p className="text-sm mt-1">
          Save insights from your sessions as shareable artifacts
        </p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {artifacts.map((artifact) => (
        <div
          key={artifact.id}
          className="border rounded-lg overflow-hidden hover:shadow-md cursor-pointer transition-shadow group"
          onClick={() => onArtifactClick(artifact.id)}
        >
          {/* Preview area */}
          <div className="h-32 bg-gray-50 flex items-center justify-center border-b">
            {artifact.visualizationType === "report" ? (
              <ReportIcon />
            ) : artifact.visualizationType === "chart" ? (
              <ChartIcon />
            ) : (
              <GraphIcon />
            )}
          </div>

          {/* Content */}
          <div className="p-3">
            <h3 className="font-medium text-gray-900 truncate">
              {artifact.name}
            </h3>
            {artifact.description && (
              <p className="text-sm text-gray-500 mt-1 line-clamp-2">
                {artifact.description}
              </p>
            )}
            <div className="mt-2 flex items-center justify-between">
              <span
                className={`px-2 py-0.5 text-xs rounded-full ${
                  DATA_SOURCE_COLORS[artifact.dataSource]
                }`}
              >
                {DATA_SOURCE_LABELS[artifact.dataSource]}
              </span>
              <div className="flex items-center gap-2">
                <span className="text-xs text-gray-400">
                  {formatDate(artifact.createdAt)}
                </span>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onCopyLink(artifact.id);
                  }}
                  className="p-1 text-gray-400 hover:text-blue-500 opacity-0 group-hover:opacity-100 transition-opacity"
                  title="Copy link"
                >
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
                </button>
              </div>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
