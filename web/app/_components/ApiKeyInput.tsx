"use client";

import { useEffect, useState } from "react";
import { configureApiKey, getConfigStatus } from "@/app/_lib/api";

const STORAGE_KEY = "orbital_google_api_key";

export function ApiKeyInput() {
  const [key, setKey] = useState("");
  const [isConfigured, setIsConfigured] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState("");

  // On mount: check backend status and rehydrate from localStorage
  useEffect(() => {
    const rehydrate = async () => {
      try {
        const status = await getConfigStatus();
        if (status.google_api_key_set) {
          setIsConfigured(true);
          return;
        }
        // Backend doesn't have a key — push from localStorage if available
        const stored = localStorage.getItem(STORAGE_KEY);
        if (stored) {
          await configureApiKey(stored);
          setIsConfigured(true);
        }
      } catch {
        // Backend may be down; ignore
      }
    };
    rehydrate();
  }, []);

  const handleSave = async () => {
    const trimmed = key.trim();
    if (!trimmed) return;
    setIsSaving(true);
    setError("");
    try {
      await configureApiKey(trimmed);
      localStorage.setItem(STORAGE_KEY, trimmed);
      setIsConfigured(true);
      setKey("");
    } catch {
      setError("Failed to save key");
    } finally {
      setIsSaving(false);
    }
  };

  const handleClear = () => {
    localStorage.removeItem(STORAGE_KEY);
    setIsConfigured(false);
  };

  if (isConfigured) {
    return (
      <div className="flex items-center gap-2 text-sm">
        <span className="text-green-600 flex items-center gap-1">
          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
            <path
              fillRule="evenodd"
              d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
              clipRule="evenodd"
            />
          </svg>
          API key set
        </span>
        <button
          onClick={handleClear}
          className="text-gray-400 hover:text-gray-600 text-xs underline"
        >
          Clear
        </button>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-2">
      <input
        type="password"
        value={key}
        onChange={(e) => setKey(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && handleSave()}
        placeholder="Google API key"
        className="px-2 py-1.5 text-sm border rounded-md w-52 focus:outline-none focus:ring-1 focus:ring-blue-500"
      />
      <button
        onClick={handleSave}
        disabled={isSaving || !key.trim()}
        className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 transition-colors"
      >
        {isSaving ? "Saving..." : "Save"}
      </button>
      {error && <span className="text-xs text-red-500">{error}</span>}
    </div>
  );
}
