"use client";

import { useState } from "react";
import Link from "next/link";
import { ModelSelector } from "./ModelSelector";
import { EditableTitle } from "./EditableTitle";

interface WorkspaceHeaderProps {
  sessionId: string;
  sessionName: string;
  createdBy?: string;
  messageCount: number;
  datasetCount: number;
  insightCount: number;
  toolCallCount: number;
  onToggleChat: () => void;
  onToggleLogs: () => void;
  onOpenInsights: () => void;
  onShare: () => void;
  onExport: (format: "artifact" | "png" | "svg" | "csv" | "report") => void;
  isChatCollapsed: boolean;
  isLogPanelOpen: boolean;
  onTitleChange: (newTitle: string) => void;
}

export function WorkspaceHeader({
  sessionId,
  sessionName,
  createdBy,
  messageCount,
  datasetCount,
  insightCount,
  toolCallCount,
  onToggleChat,
  onToggleLogs,
  onOpenInsights,
  onShare,
  onExport,
  isChatCollapsed,
  isLogPanelOpen,
  onTitleChange,
}: WorkspaceHeaderProps) {
  const hasContext = messageCount > 0 || datasetCount > 0;
  const [isExportOpen, setIsExportOpen] = useState(false);

  return (
    <header className="bg-white border-b px-4 h-14 flex items-center justify-between">
      {/* Left: Back button and title */}
      <div className="flex items-center gap-3">
        <Link
          href="/"
          className="p-1.5 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-md"
          title="Back to home"
        >
          <svg
            className="w-5 h-5"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M15 19l-7-7 7-7"
            />
          </svg>
        </Link>
        <EditableTitle
          sessionId={sessionId}
          initialTitle={sessionName}
          hasContext={hasContext}
          onTitleChange={onTitleChange}
        />
        {createdBy && createdBy !== "unknown" && (
          <span className="text-xs text-gray-400">by {createdBy}</span>
        )}
      </div>

      {/* Right: Actions */}
      <div className="flex items-center gap-2">
        {/* Logs Button - LEFT of Chat */}
        <button
          onClick={onToggleLogs}
          className={`flex items-center gap-1 p-2 rounded-md transition-colors ${
            isLogPanelOpen
              ? "text-blue-600 bg-blue-50 hover:bg-blue-100"
              : "text-gray-500 hover:text-gray-700 hover:bg-gray-100"
          }`}
          title={isLogPanelOpen ? "Hide logs" : "Show logs"}
        >
          <svg
            className="w-5 h-5"
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
          {toolCallCount > 0 && (
            <span className="px-1.5 py-0.5 text-xs bg-blue-100 text-blue-700 rounded-full">
              {toolCallCount}
            </span>
          )}
        </button>

        {/* Toggle Chat Button */}
        <button
          onClick={onToggleChat}
          className={`p-2 rounded-md transition-colors ${
            isChatCollapsed
              ? "text-gray-500 hover:text-gray-700 hover:bg-gray-100"
              : "text-blue-600 bg-blue-50 hover:bg-blue-100"
          }`}
          title={isChatCollapsed ? "Show chat" : "Hide chat"}
        >
          <svg
            className="w-5 h-5"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
            />
          </svg>
        </button>

        {/* Model Selector */}
        <ModelSelector />

        {/* Insights Button */}
        <button
          onClick={onOpenInsights}
          className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-100 rounded-md transition-colors"
          title="View insights"
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
              d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
            />
          </svg>
          Insights
          {insightCount > 0 && (
            <span className="px-1.5 py-0.5 text-xs bg-blue-100 text-blue-700 rounded-full">
              {insightCount}
            </span>
          )}
        </button>

        {/* Share Button */}
        <button
          onClick={onShare}
          className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-md"
          title="Share"
        >
          <svg
            className="w-5 h-5"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z"
            />
          </svg>
        </button>

        {/* Export Dropdown */}
        <div className="relative">
          <button
            onClick={() => setIsExportOpen(!isExportOpen)}
            className="flex items-center gap-1 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-100 rounded-md transition-colors"
          >
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

          {isExportOpen && (
            <>
              <div
                className="fixed inset-0 z-10"
                onClick={() => setIsExportOpen(false)}
              />
              <div className="absolute right-0 mt-1 w-40 bg-white border rounded-md shadow-lg z-20">
                <button
                  onClick={() => {
                    onExport("report");
                    setIsExportOpen(false);
                  }}
                  className="w-full px-3 py-2 text-left text-sm hover:bg-gray-100"
                >
                  Generate Report
                </button>
                <div className="border-t my-1" />
                <button
                  onClick={() => {
                    onExport("artifact");
                    setIsExportOpen(false);
                  }}
                  className="w-full px-3 py-2 text-left text-sm hover:bg-gray-100"
                >
                  Save as Artifact
                </button>
                <button
                  onClick={() => {
                    onExport("png");
                    setIsExportOpen(false);
                  }}
                  className="w-full px-3 py-2 text-left text-sm hover:bg-gray-100"
                >
                  Export PNG
                </button>
                <button
                  onClick={() => {
                    onExport("svg");
                    setIsExportOpen(false);
                  }}
                  className="w-full px-3 py-2 text-left text-sm hover:bg-gray-100"
                >
                  Export SVG
                </button>
                <button
                  onClick={() => {
                    onExport("csv");
                    setIsExportOpen(false);
                  }}
                  className="w-full px-3 py-2 text-left text-sm hover:bg-gray-100"
                >
                  Export CSV
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
