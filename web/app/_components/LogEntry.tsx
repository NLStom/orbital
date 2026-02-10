"use client";

import { useState } from "react";

interface LogEntryProps {
  tool: string;
  input: Record<string, unknown>;
  durationMs?: number;
  error?: string;
  output?: string;
}

function formatDuration(ms: number): string {
  if (ms >= 1000) {
    return `${(ms / 1000).toFixed(1)}s`;
  }
  return `${ms}ms`;
}

function formatOutput(raw: string): string {
  try {
    return JSON.stringify(JSON.parse(raw), null, 2);
  } catch {
    return raw;
  }
}

export function LogEntry({ tool, input, durationMs, error, output }: LogEntryProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  const isMemoryTool = tool === "update_memory";
  const memoryAction = isMemoryTool ? (input.action as string) : null;
  const memoryCategory = isMemoryTool ? (input.category as string) : null;
  const memoryContent = isMemoryTool ? (input.content as string) : null;

  return (
    <div className="border-l-2 border-gray-200 pl-3 py-1">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex items-center gap-2 w-full text-left text-sm hover:bg-gray-50 rounded px-1 -ml-1"
      >
        {/* Status icon */}
        {error ? (
          <span data-testid="error-icon" className="text-red-500">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </span>
        ) : (
          <span data-testid="success-icon" className="text-green-500">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </span>
        )}

        {/* Tool name */}
        <span className={`font-mono ${error ? "text-red-600" : "text-gray-700"}`}>
          {tool}
        </span>

        {/* Memory badge */}
        {isMemoryTool && memoryCategory && (
          <span
            className={`text-xs px-1.5 py-0.5 rounded font-medium ${
              memoryAction === "remove"
                ? "bg-red-100 text-red-700"
                : "bg-blue-100 text-blue-700"
            }`}
          >
            {memoryAction === "remove" ? "-" : "+"}{memoryCategory}
          </span>
        )}

        {/* Duration */}
        {durationMs !== undefined && (
          <span className="text-gray-400 text-xs ml-auto">
            {formatDuration(durationMs)}
          </span>
        )}

        {/* Expand indicator */}
        <svg
          className={`w-3 h-3 text-gray-400 transition-transform ${isExpanded ? "rotate-90" : ""}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
        </svg>
      </button>

      {/* Memory content preview (always visible for memory tool) */}
      {isMemoryTool && memoryContent && (
        <div className="ml-6 mt-1 text-xs text-gray-500 truncate">
          {memoryContent}
        </div>
      )}

      {/* Expanded details */}
      {isExpanded && (
        <div className="mt-2 ml-6 text-xs">
          {error && (
            <div className="text-red-600 mb-2 p-2 bg-red-50 rounded">
              {error}
            </div>
          )}
          {output ? (
            <div className="space-y-2">
              <div>
                <div className="text-gray-500 font-medium mb-1">Input</div>
                <div className="bg-gray-50 p-2 rounded font-mono overflow-x-auto">
                  <pre className="whitespace-pre-wrap">
                    {JSON.stringify(input, null, 2)}
                  </pre>
                </div>
              </div>
              <div>
                <div className="text-gray-500 font-medium mb-1">Output</div>
                <div className="bg-gray-50 p-2 rounded font-mono overflow-x-auto">
                  <pre className="whitespace-pre-wrap">
                    {formatOutput(output)}
                  </pre>
                </div>
              </div>
            </div>
          ) : (
            <div className="bg-gray-50 p-2 rounded font-mono overflow-x-auto">
              <pre className="whitespace-pre-wrap">
                {JSON.stringify(input, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
