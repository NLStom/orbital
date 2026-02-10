/**
 * Sessions store using Zustand for state management.
 */
import { create } from "zustand";
import {
  api,
  SessionSummary,
  ArtifactSummary,
  DataSourceType,
} from "@/app/_lib/api";

interface SessionsState {
  sessions: SessionSummary[];
  artifacts: ArtifactSummary[];
  isLoading: boolean;
  isCreating: boolean;
  error: string | null;

  // Actions
  fetchSessions: () => Promise<void>;
  fetchArtifacts: () => Promise<void>;
  createSession: (dataSource: DataSourceType, name?: string, datasetIds?: string[]) => Promise<string>;
  deleteSession: (id: string) => Promise<void>;
  deleteEmptySessions: () => Promise<number>;
  deleteArtifact: (id: string) => Promise<void>;
  clearError: () => void;
}

export const useSessionsStore = create<SessionsState>((set, get) => ({
  sessions: [],
  artifacts: [],
  isLoading: false,
  isCreating: false,
  error: null,

  fetchSessions: async () => {
    set({ isLoading: true, error: null });
    try {
      const sessions = await api.listSessions();
      set({ sessions, isLoading: false });
    } catch (error) {
      set({
        isLoading: false,
        error: error instanceof Error ? error.message : "Failed to load sessions",
      });
    }
  },

  fetchArtifacts: async () => {
    set({ isLoading: true, error: null });
    try {
      const artifacts = await api.listArtifacts();
      set({ artifacts, isLoading: false });
    } catch (error) {
      set({
        isLoading: false,
        error: error instanceof Error ? error.message : "Failed to load artifacts",
      });
    }
  },

  createSession: async (dataSource: DataSourceType, name?: string, datasetIds?: string[]) => {
    set({ isCreating: true, error: null });
    try {
      const session = await api.createSession(dataSource, name, datasetIds);
      // Refresh sessions list
      const sessions = await api.listSessions();
      set({ sessions, isCreating: false });
      return session.id;
    } catch (error) {
      set({
        isCreating: false,
        error: error instanceof Error ? error.message : "Failed to create session",
      });
      throw error;
    }
  },

  deleteSession: async (id: string) => {
    try {
      await api.deleteSession(id);
      // Remove from local state
      set((state) => ({
        sessions: state.sessions.filter((s) => s.id !== id),
      }));
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "Failed to delete session",
      });
      throw error;
    }
  },

  deleteEmptySessions: async () => {
    try {
      const deletedCount = await api.deleteEmptySessions();
      // Refresh sessions list
      const sessions = await api.listSessions();
      set({ sessions });
      return deletedCount;
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "Failed to delete empty sessions",
      });
      throw error;
    }
  },

  deleteArtifact: async (id: string) => {
    try {
      await api.deleteArtifact(id);
      // Remove from local state
      set((state) => ({
        artifacts: state.artifacts.filter((a) => a.id !== id),
      }));
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "Failed to delete artifact",
      });
      throw error;
    }
  },

  clearError: () => {
    set({ error: null });
  },
}));
