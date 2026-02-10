"use client";

import { useState, useRef, useEffect } from "react";
import { api } from "@/app/_lib/api";

type Mode = "view" | "edit" | "saving" | "generating";

interface EditableTitleProps {
  sessionId: string;
  initialTitle: string;
  hasContext: boolean;
  onTitleChange: (newTitle: string) => void;
  className?: string;
}

export function EditableTitle({
  sessionId,
  initialTitle,
  hasContext,
  onTitleChange,
  className = "",
}: EditableTitleProps) {
  const [mode, setMode] = useState<Mode>("view");
  const [title, setTitle] = useState(initialTitle);
  const [editValue, setEditValue] = useState(initialTitle);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Sync title with initialTitle prop
  useEffect(() => {
    setTitle(initialTitle);
    setEditValue(initialTitle);
  }, [initialTitle]);

  // Focus input when entering edit mode
  useEffect(() => {
    if (mode === "edit" && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [mode]);

  const handleSave = async () => {
    const trimmed = editValue.trim();
    if (!trimmed) {
      setError("Title cannot be empty");
      return;
    }
    if (trimmed.length > 100) {
      setError("Title must be 100 characters or less");
      return;
    }
    if (trimmed === title) {
      setMode("view");
      setError(null);
      return;
    }

    setMode("saving");
    setError(null);
    try {
      await api.updateSession(sessionId, { name: trimmed });
      setTitle(trimmed);
      onTitleChange(trimmed);
      setMode("view");
    } catch (err) {
      console.error("Failed to update title:", err);
      setError("Failed to save");
      setEditValue(title);
      setMode("edit");
    }
  };

  const handleCancel = () => {
    setEditValue(title);
    setError(null);
    setMode("view");
  };

  const handleGenerate = async () => {
    setMode("generating");
    setError(null);
    try {
      const response = await api.generateSessionTitle(sessionId);
      setEditValue(response.title);
      setMode("edit");
    } catch (err) {
      console.error("Failed to generate title:", err);
      setError("Failed to generate");
      setMode("view");
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleSave();
    }
    if (e.key === "Escape") {
      handleCancel();
    }
  };

  if (mode === "view") {
    return (
      <div className={`flex items-center gap-1.5 ${className}`}>
        <button
          onClick={() => setMode("edit")}
          className="font-medium text-gray-900 truncate max-w-xs hover:text-blue-600 hover:underline cursor-text text-left"
          title="Click to edit title"
        >
          {title}
        </button>
        {hasContext && (
          <button
            onClick={handleGenerate}
            className="p-1 text-gray-400 hover:text-blue-500 hover:bg-blue-50 rounded transition-colors"
            title="Generate title from context"
          >
            <SparklesIcon className="w-4 h-4" />
          </button>
        )}
      </div>
    );
  }

  if (mode === "generating") {
    return (
      <div className={`flex items-center gap-2 ${className}`}>
        <span className="text-gray-500 italic flex items-center gap-2">
          <LoaderIcon className="w-4 h-4 animate-spin" />
          Generating...
        </span>
      </div>
    );
  }

  // Edit or saving mode
  return (
    <div className={`flex items-center gap-1.5 ${className}`}>
      <div className="relative">
        <input
          ref={inputRef}
          type="text"
          value={editValue}
          onChange={(e) => {
            setEditValue(e.target.value);
            setError(null);
          }}
          onKeyDown={handleKeyDown}
          disabled={mode === "saving"}
          maxLength={100}
          className={`px-2 py-1 text-sm border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 w-64 ${
            error ? "border-red-500" : "border-gray-300"
          }`}
          placeholder="Session title"
        />
        {error && (
          <span className="absolute left-0 top-full text-xs text-red-500 mt-0.5">
            {error}
          </span>
        )}
      </div>
      <button
        onClick={handleSave}
        disabled={mode === "saving"}
        className="p-1 text-green-600 hover:bg-green-50 rounded disabled:opacity-50"
        title="Save"
      >
        {mode === "saving" ? (
          <LoaderIcon className="w-4 h-4 animate-spin" />
        ) : (
          <CheckIcon className="w-4 h-4" />
        )}
      </button>
      <button
        onClick={handleCancel}
        disabled={mode === "saving"}
        className="p-1 text-gray-500 hover:bg-gray-100 rounded disabled:opacity-50"
        title="Cancel"
      >
        <XIcon className="w-4 h-4" />
      </button>
    </div>
  );
}

// Simple inline icons to avoid external dependencies
function SparklesIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z"
      />
    </svg>
  );
}

function CheckIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M5 13l4 4L19 7"
      />
    </svg>
  );
}

function XIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M6 18L18 6M6 6l12 12"
      />
    </svg>
  );
}

function LoaderIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
      />
    </svg>
  );
}
