"use client";

import { useState } from "react";
import type { Message, TokenUsage } from "@/app/_lib/api";
import { LogEntry } from "./LogEntry";

interface LogPanelProps {
  isOpen: boolean;
  messages: Message[];
  onClose: () => void;
}

function formatTime(timestamp: string): string {
  return new Date(timestamp).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function truncate(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text;
  return text.slice(0, maxLength) + "...";
}

function formatTokenCount(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(n % 1_000_000 === 0 ? 0 : 1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(n % 1_000 === 0 ? 0 : 1)}K`;
  return String(n);
}

function getLastTokenUsage(messages: Message[]): TokenUsage | null {
  for (let i = messages.length - 1; i >= 0; i--) {
    if (messages[i].role === "assistant" && messages[i].tokenUsage) {
      return messages[i].tokenUsage!;
    }
  }
  return null;
}

export function LogPanel({ isOpen, messages, onClose }: LogPanelProps) {
  const [copyState, setCopyState] = useState<"idle" | "copied">("idle");

  if (!isOpen) return null;

  // Group messages into user-assistant pairs with tool calls
  type MessageGroup = { userMessage: Message; assistantMessage: Message };
  const messageGroups: MessageGroup[] = [];

  for (let i = 0; i < messages.length; i++) {
    const msg = messages[i];
    if (msg.role === "user" && i + 1 < messages.length) {
      const nextMsg = messages[i + 1];
      if (nextMsg.role === "assistant" && nextMsg.toolCalls && nextMsg.toolCalls.length > 0) {
        messageGroups.push({ userMessage: msg, assistantMessage: nextMsg });
      }
    }
  }

  const handleCopyAll = () => {
    const lines: string[] = [];
    for (const { userMessage, assistantMessage } of messageGroups) {
      lines.push(`> ${userMessage.content}`);
      for (const tc of assistantMessage.toolCalls ?? []) {
        const status = tc.error ? "ERROR" : "OK";
        const duration = tc.durationMs ? ` (${tc.durationMs}ms)` : "";
        lines.push(`  ${status} ${tc.tool}${duration}`);
        if (tc.error) lines.push(`    Error: ${tc.error}`);
        lines.push(`    Input: ${JSON.stringify(tc.input)}`);
        if (tc.output) lines.push(`    Output: ${tc.output.slice(0, 200)}`);
      }
      lines.push("");
    }
    navigator.clipboard.writeText(lines.join("\n")).then(() => {
      setCopyState("copied");
      setTimeout(() => setCopyState("idle"), 1500);
    });
  };

  const tokenUsage = getLastTokenUsage(messages);
  const fillPercent = tokenUsage
    ? Math.min((tokenUsage.inputTokens / tokenUsage.contextLimit) * 100, 100)
    : null;
  const barColor =
    fillPercent === null
      ? ""
      : fillPercent >= 80
        ? "bg-red-500"
        : fillPercent >= 50
          ? "bg-yellow-500"
          : "bg-gray-400";

  return (
    <div className="fixed right-0 top-14 bottom-0 w-80 bg-white border-l shadow-lg z-40 flex flex-col">
      {/* Header */}
      <div className="px-4 py-3 border-b">
        <div className="flex items-center justify-between">
          <h2 className="font-medium text-gray-900">Agent Logs</h2>
          <div className="flex items-center gap-1">
            <button
              onClick={handleCopyAll}
              className={`p-1 rounded ${copyState === "copied" ? "text-green-500" : "text-gray-400 hover:text-gray-600"}`}
              title={copyState === "copied" ? "Copied!" : "Copy all logs"}
            >
              {copyState === "copied" ? (
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              ) : (
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
              )}
            </button>
            <button
              onClick={onClose}
              className="p-1 text-gray-400 hover:text-gray-600 rounded"
              title="Close"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>
        {tokenUsage && fillPercent !== null && (
          <div className="mt-2" data-testid="context-usage">
            <div className="flex items-center justify-between text-xs text-gray-500 mb-1">
              <span>Context: {formatTokenCount(tokenUsage.inputTokens)} / {formatTokenCount(tokenUsage.contextLimit)} tokens</span>
              <span>{fillPercent.toFixed(0)}%</span>
            </div>
            <div className="w-full h-1.5 bg-gray-200 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full ${barColor}`}
                style={{ width: `${fillPercent}%` }}
              />
            </div>
          </div>
        )}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4">
        {messageGroups.length === 0 ? (
          <div className="text-center text-gray-500 py-8">
            <svg className="w-12 h-12 mx-auto mb-3 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
            </svg>
            <p>No tool calls yet</p>
            <p className="text-sm mt-1">Tool calls will appear here as the agent processes requests.</p>
          </div>
        ) : (
          <div className="space-y-4">
            {messageGroups.map(({ userMessage, assistantMessage }) => (
              <div key={assistantMessage.id} className="border rounded-lg p-3">
                {/* Timestamp and user message preview */}
                <div className="flex items-center gap-2 mb-2 text-xs text-gray-500">
                  <span>{formatTime(assistantMessage.timestamp)}</span>
                  <span className="truncate flex-1">
                    &quot;{truncate(userMessage.content, 30)}&quot;
                  </span>
                </div>

                {/* Tool calls */}
                <div className="space-y-1">
                  {assistantMessage.toolCalls?.map((tc, idx) => (
                    <LogEntry
                      key={`${assistantMessage.id}-${idx}`}
                      tool={tc.tool}
                      input={tc.input}
                      durationMs={tc.durationMs}
                      error={tc.error}
                      output={tc.output}
                    />
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
