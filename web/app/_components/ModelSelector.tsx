"use client";

import { useEffect, useState } from "react";
import { useModelStore, getProviderIconPath } from "@/app/_stores/model-store";

export function ModelSelector() {
  const {
    selectedModel,
    availableModels,
    isLoading,
    setSelectedModel,
    loadModels,
  } = useModelStore();

  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    loadModels();
  }, [loadModels]);

  const currentModel = availableModels.find((m) => m.key === selectedModel);

  if (isLoading || availableModels.length === 0) {
    return (
      <div className="px-3 py-1.5 text-sm text-gray-400">
        Loading models...
      </div>
    );
  }

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-100 rounded-md transition-colors"
        title="Select AI model"
      >
        {currentModel && <img src={getProviderIconPath(currentModel.provider)} alt="" className="w-4 h-4" />}
        <span className="hidden sm:inline">{currentModel?.display_name || "Select model"}</span>
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

      {isOpen && (
        <>
          <div
            className="fixed inset-0 z-10"
            onClick={() => setIsOpen(false)}
          />
          <div className="absolute right-0 mt-1 w-48 bg-white border rounded-md shadow-lg z-20">
            {availableModels.map((model) => (
              <button
                key={model.key}
                onClick={() => {
                  setSelectedModel(model.key);
                  setIsOpen(false);
                }}
                className={`w-full px-3 py-2 text-left text-sm flex items-center gap-2 hover:bg-gray-100 ${
                  model.key === selectedModel ? "bg-blue-50 text-blue-700" : ""
                }`}
              >
                <img src={getProviderIconPath(model.provider)} alt="" className="w-4 h-4" />
                <span>{model.display_name}</span>
                {model.key === selectedModel && (
                  <svg
                    className="w-4 h-4 ml-auto"
                    fill="currentColor"
                    viewBox="0 0 20 20"
                  >
                    <path
                      fillRule="evenodd"
                      d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                      clipRule="evenodd"
                    />
                  </svg>
                )}
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
