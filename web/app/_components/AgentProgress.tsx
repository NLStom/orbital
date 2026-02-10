"use client";

import { useState, useEffect } from "react";

interface AgentProgressProps {
  startedAt: number | null;
}

function formatElapsed(ms: number): string {
  const seconds = Math.floor(ms / 1000);
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  const remaining = seconds % 60;
  return `${minutes}m ${remaining}s`;
}

export function AgentProgress({ startedAt }: AgentProgressProps) {
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    if (!startedAt) return;
    setElapsed(Date.now() - startedAt);
    const interval = setInterval(() => {
      setElapsed(Date.now() - startedAt);
    }, 1000);
    return () => clearInterval(interval);
  }, [startedAt]);

  return (
    <div className="flex justify-start">
      <div className="bg-gray-100 rounded-lg px-4 py-3">
        <div className="flex items-center gap-3">
          {/* Bouncing dots */}
          <div className="flex gap-1">
            <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" />
            <div
              className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
              style={{ animationDelay: "0.1s" }}
            />
            <div
              className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
              style={{ animationDelay: "0.2s" }}
            />
          </div>
          {/* Timer */}
          <span className="text-xs text-gray-500">
            Thinking... {formatElapsed(elapsed)}
          </span>
        </div>
      </div>
    </div>
  );
}
