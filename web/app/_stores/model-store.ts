/**
 * Model store using Zustand for LLM model selection.
 *
 * Manages which LLM model the user has selected and persists the choice.
 */
import { create } from "zustand";
import { persist } from "zustand/middleware";

export interface ModelInfo {
  key: string;
  display_name: string;
  provider: "claude" | "gemini" | "vertex_ai" | "openai";
}

interface ModelState {
  selectedModel: string;
  availableModels: ModelInfo[];
  defaultModel: string;
  isLoading: boolean;
  error: string | null;

  // Actions
  setSelectedModel: (model: string) => void;
  loadModels: () => Promise<void>;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8787";

export const useModelStore = create<ModelState>()(
  persist(
    (set, get) => ({
      selectedModel: "",
      availableModels: [],
      defaultModel: "vertex-gemini-3-pro",
      isLoading: false,
      error: null,

      setSelectedModel: (model: string) => {
        set({ selectedModel: model });
      },

      loadModels: async () => {
        set({ isLoading: true, error: null });
        try {
          const response = await fetch(`${API_BASE_URL}/api/models`);
          if (!response.ok) {
            throw new Error("Failed to fetch models");
          }
          const data = await response.json();

          const { selectedModel } = get();
          const availableKeys = data.models.map((m: ModelInfo) => m.key);

          // If current selection is invalid, use default or first available
          let newSelection = selectedModel;
          if (!selectedModel || !availableKeys.includes(selectedModel)) {
            newSelection = data.default || data.models[0]?.key || "";
          }

          set({
            availableModels: data.models,
            defaultModel: data.default,
            selectedModel: newSelection,
            isLoading: false,
          });
        } catch (error) {
          set({
            isLoading: false,
            error: error instanceof Error ? error.message : "Failed to load models",
          });
        }
      },
    }),
    {
      name: "orbital-model",
      partialize: (state) => ({ selectedModel: state.selectedModel }),
    }
  )
);

/**
 * Get provider icon path based on provider type.
 */
export function getProviderIconPath(provider: string): string {
  const icons: Record<string, string> = {
    claude: "/icons/claude.svg",
    gemini: "/icons/gemini.svg",
    vertex_ai: "/icons/gemini.svg",
    openai: "/icons/openai.svg",
  };
  return icons[provider] || "";
}
