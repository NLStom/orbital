"use client";

import { SessionSummary, DataSourceType } from "@/app/_lib/api";

interface SessionListProps {
  sessions: SessionSummary[];
  isLoading: boolean;
  onSessionClick: (id: string) => void;
  onSessionDelete: (id: string) => void;
}

const DATA_SOURCE_COLORS: Record<DataSourceType, string> = {
  custom: "bg-gray-100 text-gray-700",
};

const DATA_SOURCE_LABELS: Record<DataSourceType, string> = {
  custom: "Custom",
};

function formatDate(isoString: string): string {
  const date = new Date(isoString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffHours = diffMs / (1000 * 60 * 60);
  const diffDays = diffMs / (1000 * 60 * 60 * 24);

  if (diffHours < 1) {
    const diffMins = Math.floor(diffMs / (1000 * 60));
    return diffMins <= 1 ? "just now" : `${diffMins}m ago`;
  }
  if (diffHours < 24) {
    return `${Math.floor(diffHours)}h ago`;
  }
  if (diffDays < 7) {
    return `${Math.floor(diffDays)}d ago`;
  }
  return date.toLocaleDateString();
}

function SkeletonCard() {
  return (
    <div
      data-testid="skeleton-card"
      className="p-4 border rounded-lg animate-pulse"
    >
      <div className="h-5 bg-gray-200 rounded w-3/4 mb-2" />
      <div className="h-4 bg-gray-200 rounded w-1/4 mb-3" />
      <div className="flex gap-2">
        <div className="h-3 bg-gray-200 rounded w-20" />
        <div className="h-3 bg-gray-200 rounded w-20" />
      </div>
    </div>
  );
}

export function SessionList({
  sessions,
  isLoading,
  onSessionClick,
  onSessionDelete,
}: SessionListProps) {
  if (isLoading) {
    return (
      <div className="space-y-3">
        <SkeletonCard />
        <SkeletonCard />
        <SkeletonCard />
      </div>
    );
  }

  if (sessions.length === 0) {
    return (
      <div className="text-center py-12 text-gray-500">
        <p className="text-lg">No sessions yet</p>
        <p className="text-sm mt-1">Create a new session to get started</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {sessions.map((session) => (
        <div
          key={session.id}
          className="p-4 border rounded-lg hover:bg-gray-50 cursor-pointer transition-colors group"
          onClick={() => onSessionClick(session.id)}
        >
          <div className="flex items-start justify-between">
            <div className="flex-1 min-w-0">
              <h3 className="font-medium text-gray-900 truncate">
                {session.name}
              </h3>
              <span
                className={`inline-block mt-1 px-2 py-0.5 text-xs rounded-full ${
                  DATA_SOURCE_COLORS[session.dataSource]
                }`}
              >
                {DATA_SOURCE_LABELS[session.dataSource]}
              </span>
            </div>
            <button
              onClick={(e) => {
                e.stopPropagation();
                onSessionDelete(session.id);
              }}
              className="p-1.5 text-gray-400 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-opacity"
              title="Delete session"
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
                  d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                />
              </svg>
            </button>
          </div>
          <div className="mt-2 flex items-center gap-4 text-xs text-gray-500">
            <span>{session.messageCount} messages</span>
            {session.artifactCount > 0 && (
              <span>{session.artifactCount} artifacts</span>
            )}
            {session.createdBy && session.createdBy !== "unknown" && (
              <span className="text-gray-400">by {session.createdBy}</span>
            )}
            <span className="ml-auto">{formatDate(session.updatedAt)}</span>
          </div>
        </div>
      ))}
    </div>
  );
}
