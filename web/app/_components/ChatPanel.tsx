"use client";

import { useState, useRef, useEffect } from "react";
import { Message } from "@/app/_lib/api";
import { Markdown } from "@/app/_components/ui/markdown";
import { AgentProgress } from "./AgentProgress";

interface ChatPanelProps {
  messages: Message[];
  isCollapsed: boolean;
  isLoading: boolean;
  onSendMessage: (content: string) => void;
  onViewVisualization: (tabId: string) => void;
  onUpload?: (files: File[]) => void;
  isUploading?: boolean;
  sendStartedAt?: number | null;
}

function formatTime(timestamp: string): string {
  const date = new Date(timestamp);
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

export function ChatMessage({
  message,
  onViewVisualization,
}: {
  message: Message;
  onViewVisualization: (tabId: string) => void;
}) {
  const [copied, setCopied] = useState(false);
  const isUser = message.role === "user";
  const isError = message.isError === true;
  const hasViz = (message.charts?.length || 0) + (message.graphs?.length || 0) > 0;

  const handleCopyError = async () => {
    try {
      await navigator.clipboard.writeText(message.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback for older browsers
      const textArea = document.createElement("textarea");
      textArea.value = message.content;
      document.body.appendChild(textArea);
      textArea.select();
      document.execCommand("copy");
      document.body.removeChild(textArea);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  // Error message styling
  if (isError) {
    return (
      <div className="flex justify-start">
        <div className="max-w-[85%] rounded-lg px-4 py-2 bg-red-50 border border-red-200">
          <div className="flex items-start gap-2">
            <svg className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <div className="flex-1">
              <p className="text-sm text-red-700 font-medium">Error</p>
              <p className="text-sm text-red-600 mt-1 whitespace-pre-wrap">{message.content}</p>
              <button
                onClick={handleCopyError}
                className="mt-2 inline-flex items-center gap-1 px-2 py-1 text-xs rounded bg-red-100 hover:bg-red-200 text-red-700 transition-colors"
              >
                {copied ? (
                  <>
                    <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                    Copied!
                  </>
                ) : (
                  <>
                    <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                    </svg>
                    Copy error
                  </>
                )}
              </button>
            </div>
          </div>
          <p className="text-xs text-red-400 mt-2">
            {formatTime(message.timestamp)}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div
      className={`flex ${isUser ? "justify-end" : "justify-start"}`}
    >
      <div
        className={`max-w-[85%] rounded-lg px-4 py-2 ${
          isUser
            ? "bg-blue-600 text-white"
            : "bg-gray-100 text-gray-900"
        }`}
      >
        {isUser ? (
          <p className="whitespace-pre-wrap text-sm">{message.content}</p>
        ) : (
          <Markdown className="text-sm prose-p:my-1 prose-headings:my-2 prose-ul:my-1 prose-ol:my-1 prose-li:my-0.5 prose-pre:my-2">
            {message.content}
          </Markdown>
        )}

        {/* Visualization badges */}
        {hasViz && (
          <div className="mt-2 flex flex-wrap gap-1">
            {message.charts?.map((chart, i) => (
              <button
                key={`chart-${i}`}
                onClick={() => onViewVisualization(`${message.id}-chart-${i}`)}
                className={`inline-flex items-center gap-1 px-2 py-1 text-xs rounded ${
                  isUser
                    ? "bg-blue-500 hover:bg-blue-400"
                    : "bg-gray-200 hover:bg-gray-300 text-gray-700"
                }`}
              >
                <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
                {chart.title || `Chart ${i + 1}`}
              </button>
            ))}
            {message.graphs?.map((graph, i) => (
              <button
                key={`graph-${i}`}
                onClick={() => onViewVisualization(`${message.id}-graph-${i}`)}
                className={`inline-flex items-center gap-1 px-2 py-1 text-xs rounded ${
                  isUser
                    ? "bg-blue-500 hover:bg-blue-400"
                    : "bg-gray-200 hover:bg-gray-300 text-gray-700"
                }`}
              >
                <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <circle cx="12" cy="5" r="2" strokeWidth={2} />
                  <circle cx="5" cy="19" r="2" strokeWidth={2} />
                  <circle cx="19" cy="19" r="2" strokeWidth={2} />
                  <path strokeLinecap="round" strokeWidth={2} d="M12 7v4M7 17l3-6M17 17l-3-6" />
                </svg>
                {graph.title || `Graph ${i + 1}`}
              </button>
            ))}
          </div>
        )}

        <p
          className={`text-xs mt-1 ${
            isUser ? "text-blue-200" : "text-gray-500"
          }`}
        >
          {formatTime(message.timestamp)}
        </p>
      </div>
    </div>
  );
}

/**
 * Renders grouped system messages as a collapsed summary.
 */
function SystemMessageGroup({ messages }: { messages: Message[] }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="flex justify-center">
      <button
        onClick={() => setExpanded(!expanded)}
        className="text-xs text-gray-400 hover:text-gray-600 transition-colors"
      >
        {expanded ? "Hide" : `${messages.length} background action${messages.length !== 1 ? "s" : ""}`}
      </button>
      {expanded && (
        <div className="absolute mt-5 flex flex-wrap gap-1 justify-center">
          {messages.map((msg) => (
            <span
              key={msg.id}
              className="inline-block px-2 py-0.5 text-xs text-gray-500 bg-gray-100 rounded-full"
            >
              {msg.content}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

/**
 * Groups consecutive system messages together for rendering.
 */
function groupMessages(messages: Message[]) {
  const groups: ({ type: "message"; message: Message } | { type: "system"; messages: Message[] })[] = [];
  let i = 0;
  while (i < messages.length) {
    if (messages[i].role === "system") {
      const systemMsgs: Message[] = [];
      while (i < messages.length && messages[i].role === "system") {
        systemMsgs.push(messages[i]);
        i++;
      }
      groups.push({ type: "system", messages: systemMsgs });
    } else {
      groups.push({ type: "message", message: messages[i] });
      i++;
    }
  }
  return groups;
}

export function ChatPanel({
  messages,
  isCollapsed,
  isLoading,
  onSendMessage,
  onViewVisualization,
  onUpload,
  isUploading,
  sendStartedAt,
}: ChatPanelProps) {
  const [input, setInput] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Focus input on mount
  useEffect(() => {
    if (!isCollapsed) {
      inputRef.current?.focus();
    }
  }, [isCollapsed]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (input.trim() && !isLoading) {
      onSendMessage(input.trim());
      setInput("");
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && onUpload) {
      onUpload(Array.from(e.target.files));
      e.target.value = "";
    }
  };

  const handleMessagesClick = (e: React.MouseEvent) => {
    const target = e.target as HTMLElement;
    if (target.tagName === "A" && target.getAttribute("href") === "#ask") {
      e.preventDefault();
      const text = target.textContent?.trim();
      if (text && !isLoading) onSendMessage(text);
    }
  };

  if (isCollapsed) {
    return null;
  }

  const messageGroups = groupMessages(messages);

  return (
    <div className="flex flex-col h-full bg-white">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4" onClick={handleMessagesClick}>
        {messages.length === 0 ? (
          <div className="h-full flex items-center justify-center text-gray-500">
            <div className="text-center">
              <p className="text-lg mb-2">Start a conversation</p>
              <p className="text-sm">
                Ask questions about your data in natural language
              </p>
            </div>
          </div>
        ) : (
          <>
            {messageGroups.map((group, idx) => {
              if (group.type === "system") {
                return <SystemMessageGroup key={`sys-${idx}`} messages={group.messages} />;
              }
              return (
                <ChatMessage
                  key={group.message.id}
                  message={group.message}
                  onViewVisualization={onViewVisualization}
                />
              );
            })}
            {isLoading && <AgentProgress startedAt={sendStartedAt ?? null} />}
            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      {/* Input */}
      <form onSubmit={handleSubmit} className="p-4 border-t">
        <div className="flex gap-2">
          {/* Upload button */}
          {onUpload && (
            <>
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                disabled={isUploading}
                className="px-2 py-2 text-gray-400 hover:text-gray-600 disabled:opacity-50 transition-colors"
                title="Upload CSV"
              >
                {isUploading ? (
                  <svg className="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                ) : (
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                  </svg>
                )}
              </button>
              <input
                ref={fileInputRef}
                type="file"
                accept=".csv"
                multiple
                className="hidden"
                onChange={handleFileChange}
              />
            </>
          )}
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask a question about your data..."
            rows={1}
            disabled={isLoading}
            className="flex-1 px-3 py-2 border rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={!input.trim() || isLoading}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isLoading ? (
              <svg
                className="w-5 h-5 animate-spin"
                fill="none"
                viewBox="0 0 24 24"
              >
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                />
              </svg>
            ) : (
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
                  d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"
                />
              </svg>
            )}
          </button>
        </div>
        {input.length > 45000 && (
          <p className="text-xs text-gray-500 mt-1">
            {input.length}/50000 characters
          </p>
        )}
      </form>
    </div>
  );
}
