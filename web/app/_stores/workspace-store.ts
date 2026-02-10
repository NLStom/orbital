/**
 * Workspace store using Zustand for state management.
 *
 * Manages the state of a single workspace/session view.
 */
import { create } from "zustand";
import {
  api,
  Session,
  Message,
  ChartSpec,
  GraphSpec,
  ERDiagramSpec,
  DatasetFull,
  TablePreview,
  DerivedTable,
} from "@/app/_lib/api";
import { useModelStore } from "./model-store";

export type WorkspaceTab = "viz" | "data";
export type DataView = "preview" | "query";

// Interact result types for Phase 2
export interface GraphInteractResult {
  type: "graph_selection" | "graph_focus" | "graph_path_selection";
  selections?: string[];
  node_ids?: string[];
  path?: string[];
}

export interface ChartOverlay {
  overlay_type: "reference_line" | "reference_area" | "annotation";
  axis?: "x" | "y";
  value?: number;
  x1?: string;
  x2?: string;
  label?: string;
}

export interface ChartInteractResult {
  type: "chart_overlay" | "chart_zoom";
  overlay_type?: string;
  axis?: "x" | "y";
  value?: number;
  x1?: string;
  x2?: string;
}

export type InteractResult = GraphInteractResult | ChartInteractResult;

export interface ChartTab {
  id: string;
  title: string;
  vizType: "chart" | "graph";
  spec: ChartSpec | GraphSpec;
}

interface WorkspaceState {
  session: Session | null;
  activeTab: WorkspaceTab;
  isChatCollapsed: boolean;
  isInsightsPanelOpen: boolean;
  isLogPanelOpen: boolean;
  isLoading: boolean;
  isSending: boolean;
  sendStartedAt: number | null;
  error: string | null;

  // Current visualization state
  currentVisualization: ChartSpec | GraphSpec | null;
  currentQueryResult: { data: unknown[]; columns: string[] } | null;

  // Visualization tabs state
  visualizationTabs: ChartTab[];
  activeVizTabIndex: number | null;

  // Schema diagram state
  schemaDiagram: ERDiagramSpec | null;
  isSchemaLoading: boolean;
  schemaError: string | null;

  // Dataset upload state
  isUploading: boolean;
  sessionDatasets: DatasetFull[];

  // Data Explorer state
  selectedDatasetTable: { datasetId: string; tableName: string } | null;
  tablePreview: TablePreview | null;
  isPreviewLoading: boolean;
  activeDataView: DataView;

  // Derived tables (agent-created during session)
  derivedTables: DerivedTable[];

  // Interact state (Phase 2)
  interactStates: Record<string, InteractResult>;
  chartOverlays: Record<string, ChartOverlay[]>;

  // Actions
  loadSession: (id: string) => Promise<void>;
  sendMessage: (content: string) => Promise<void>;
  setActiveTab: (tab: WorkspaceTab) => void;
  toggleChat: () => void;
  toggleInsightsPanel: () => void;
  toggleLogPanel: () => void;
  setCurrentVisualization: (viz: ChartSpec | GraphSpec | null) => void;
  setActiveVizTab: (index: number) => void;
  selectVizByTabId: (tabId: string) => void;
  clearError: () => void;
  reset: () => void;
  loadSchemaDiagram: (sessionId: string) => Promise<void>;
  uploadCSV: (files: File[]) => Promise<void>;
  loadSessionDatasets: () => Promise<void>;
  shareDataset: (datasetId: string) => Promise<void>;
  shareAllDatasets: () => Promise<void>;
  loadTablePreview: (datasetId: string, tableName: string) => Promise<void>;
  switchDataView: (view: DataView) => void;
  // Derived tables actions
  loadDerivedTables: () => Promise<void>;
  promoteDerivedTable: (tableName: string, newName: string) => Promise<void>;

  // Interact actions (Phase 2)
  applyInteractResult: (vizId: string, result: InteractResult) => void;
  getInteractState: (vizId: string) => InteractResult | null;
  clearInteractState: (vizId: string) => void;
  getChartOverlays: (vizId: string) => ChartOverlay[];

  // Session name
  updateSessionName: (name: string) => void;
}

const initialState = {
  session: null,
  activeTab: "viz" as WorkspaceTab,
  isChatCollapsed: false,
  isInsightsPanelOpen: false,
  isLogPanelOpen: false,
  isLoading: false,
  isSending: false,
  sendStartedAt: null as number | null,
  error: null,
  currentVisualization: null,
  currentQueryResult: null,
  visualizationTabs: [] as ChartTab[],
  activeVizTabIndex: null as number | null,
  schemaDiagram: null,
  isSchemaLoading: false,
  schemaError: null,
  isUploading: false,
  sessionDatasets: [] as DatasetFull[],
  selectedDatasetTable: null,
  tablePreview: null,
  isPreviewLoading: false,
  activeDataView: "preview" as DataView,
  derivedTables: [] as DerivedTable[],
  interactStates: {} as Record<string, InteractResult>,
  chartOverlays: {} as Record<string, ChartOverlay[]>,
};

export const useWorkspaceStore = create<WorkspaceState>((set, get) => ({
  ...initialState,

  loadSession: async (id: string) => {
    set({ isLoading: true, error: null });
    try {
      const session = await api.getSession(id);
      const tabs = buildVizTabs(session.messages);
      const lastQueryResult = findLastQueryResult(session.messages);
      set({
        session,
        isLoading: false,
        visualizationTabs: tabs,
        activeVizTabIndex: tabs.length > 0 ? tabs.length - 1 : null,
        currentVisualization: tabs.length > 0 ? tabs[tabs.length - 1].spec : null,
        currentQueryResult: lastQueryResult,
      });
    } catch (error) {
      set({
        isLoading: false,
        error: error instanceof Error ? error.message : "Failed to load session",
      });
    }
  },

  sendMessage: async (content: string) => {
    const { session } = get();
    if (!session) return;

    set({ isSending: true, sendStartedAt: Date.now(), error: null });

    // Optimistically add user message to UI
    const tempUserMessage: Message = {
      id: `temp-${Date.now()}`,
      role: "user",
      content,
      timestamp: new Date().toISOString(),
    };

    set({
      session: {
        ...session,
        messages: [...session.messages, tempUserMessage],
      },
    });

    try {
      // Get selected model from model store
      const selectedModel = useModelStore.getState().selectedModel;

      // Single API call - backend handles persistence of both messages
      const response = await api.sendMessage(session.id, content, selectedModel || undefined);

      // Separate visualizations into charts and graphs for message storage
      const charts = response.visualizations.filter(
        (v): v is ChartSpec => v.type !== "network"
      );
      const graphs = response.visualizations.filter(
        (v): v is GraphSpec => v.type === "network"
      );

      // Replace temp message and add assistant response
      const userMessage: Message = {
        id: `user-${response.messageId}`,
        role: "user",
        content,
        timestamp: new Date().toISOString(),
      };

      const queryResults = response.queryResults;

      const assistantMessage: Message = {
        id: response.messageId,
        role: "assistant",
        content: response.response,
        timestamp: new Date().toISOString(),
        charts: charts.length > 0 ? charts : undefined,
        graphs: graphs.length > 0 ? graphs : undefined,
        toolCalls: response.toolCalls.length > 0 ? response.toolCalls : undefined,
        queryResults: queryResults && queryResults.length > 0 ? queryResults : undefined,
        tokenUsage: response.tokenUsage,
      };

      // Build new tabs from this response
      const newChartTabs: ChartTab[] = charts.map((chart, i) => ({
        id: `${response.messageId}-chart-${i}`,
        title: chart.title || `Chart ${i + 1}`,
        vizType: "chart" as const,
        spec: chart,
      }));
      const newGraphTabs: ChartTab[] = graphs.map((graph, i) => ({
        id: `${response.messageId}-graph-${i}`,
        title: graph.title || `Graph ${i + 1}`,
        vizType: "graph" as const,
        spec: graph,
      }));
      const updatedTabs = [...get().visualizationTabs, ...newChartTabs, ...newGraphTabs];
      const newActiveIndex = updatedTabs.length > 0 ? updatedTabs.length - 1 : null;

      const newQueryResult = queryResults && queryResults.length > 0
        ? { data: queryResults[queryResults.length - 1].data, columns: queryResults[queryResults.length - 1].columns }
        : get().currentQueryResult;

      set({
        session: {
          ...session,
          messages: [
            ...session.messages.filter((m) => m.id !== tempUserMessage.id),
            userMessage,
            assistantMessage,
          ],
        },
        isSending: false,
        sendStartedAt: null,
        visualizationTabs: updatedTabs,
        activeVizTabIndex: newActiveIndex,
        currentVisualization: newActiveIndex !== null ? updatedTabs[newActiveIndex].spec : get().currentVisualization,
        currentQueryResult: newQueryResult,
        // Switch data view to query when agent returns results
        activeDataView: newQueryResult ? "query" : get().activeDataView,
      });
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Failed to send message";

      // Create error message that persists in chat with copy functionality
      const errorChatMessage: Message = {
        id: `error-${Date.now()}`,
        role: "assistant",
        content: errorMessage,
        timestamp: new Date().toISOString(),
        isError: true,
      };

      set({
        isSending: false,
        sendStartedAt: null,
        error: errorMessage,
        // Keep user message and add error message
        session: {
          ...session,
          messages: [...session.messages, tempUserMessage, errorChatMessage],
        },
      });
    }
  },

  setActiveTab: (tab: WorkspaceTab) => {
    set({ activeTab: tab });
  },

  toggleChat: () => {
    set((state) => ({ isChatCollapsed: !state.isChatCollapsed }));
  },

  toggleInsightsPanel: () => {
    set((state) => ({ isInsightsPanelOpen: !state.isInsightsPanelOpen }));
  },

  toggleLogPanel: () => {
    set((state) => ({ isLogPanelOpen: !state.isLogPanelOpen }));
  },

  setCurrentVisualization: (viz: ChartSpec | GraphSpec | null) => {
    set({ currentVisualization: viz });
  },

  setActiveVizTab: (index: number) => {
    const tabs = get().visualizationTabs;
    if (index >= 0 && index < tabs.length) {
      set({
        activeVizTabIndex: index,
        currentVisualization: tabs[index].spec,
        activeTab: "viz",
      });
    }
  },

  selectVizByTabId: (tabId: string) => {
    const tabs = get().visualizationTabs;
    const index = tabs.findIndex((t) => t.id === tabId);
    if (index !== -1) {
      get().setActiveVizTab(index);
    }
  },

  clearError: () => {
    set({ error: null });
  },

  reset: () => {
    set(initialState);
  },

  loadSchemaDiagram: async (sessionId: string) => {
    set({ isSchemaLoading: true, schemaError: null });
    try {
      const schema = await api.getSessionSchema(sessionId);
      set({
        schemaDiagram: schema,
        isSchemaLoading: false,
      });
    } catch (error) {
      set({
        isSchemaLoading: false,
        schemaError: error instanceof Error ? error.message : "Failed to load schema",
      });
    }
  },

  uploadCSV: async (files: File[]) => {
    const { session } = get();
    if (!session) return;

    set({ isUploading: true, error: null });
    try {
      const dataset = await api.uploadDataset(files, undefined, session.id);
      await api.attachDatasetToSession(session.id, dataset.id);

      const datasets = await api.listSessionDatasets(session.id);

      // Build messages locally — no agent call needed
      const fileNames = files.map((f) => f.name).join(", ");
      const { userContent, assistantContent } = buildUploadSummary(dataset, fileNames);
      const now = new Date().toISOString();

      const userMessage: Message = {
        id: `upload-user-${Date.now()}`,
        role: "user",
        content: userContent,
        timestamp: now,
      };
      const assistantMessage: Message = {
        id: `upload-assistant-${Date.now()}`,
        role: "assistant",
        content: assistantContent,
        timestamp: now,
      };

      set({
        sessionDatasets: datasets,
        isUploading: false,
        activeTab: "data",
        session: {
          ...session,
          messages: [...session.messages, userMessage, assistantMessage],
        },
      });
    } catch (e) {
      set({
        error: e instanceof Error ? e.message : "Upload failed",
        isUploading: false,
      });
    }
  },

  loadSessionDatasets: async () => {
    const { session } = get();
    if (!session) return;
    try {
      const datasets = await api.listSessionDatasets(session.id);
      set({ sessionDatasets: datasets });
    } catch {
      // Silently fail - datasets are optional
    }
  },

  shareDataset: async (datasetId: string) => {
    try {
      await api.updateDataset(datasetId, { visibility: "public" });
      const { session } = get();
      if (session) {
        const datasets = await api.listSessionDatasets(session.id);
        set({ sessionDatasets: datasets });
      }
    } catch (e) {
      set({ error: e instanceof Error ? e.message : "Failed to share dataset" });
    }
  },

  shareAllDatasets: async () => {
    const { sessionDatasets, session } = get();
    try {
      const privateSets = sessionDatasets.filter(
        (d) => d.visibility === "private" && d.owner !== "system"
      );
      await Promise.all(
        privateSets.map((d) => api.updateDataset(d.id, { visibility: "public" }))
      );
      if (session) {
        const datasets = await api.listSessionDatasets(session.id);
        set({ sessionDatasets: datasets });
      }
    } catch (e) {
      set({ error: e instanceof Error ? e.message : "Failed to share datasets" });
    }
  },

  loadTablePreview: async (datasetId: string, tableName: string) => {
    set({
      isPreviewLoading: true,
      selectedDatasetTable: { datasetId, tableName },
      activeDataView: "preview",
    });
    try {
      const preview = await api.previewDatasetTable(datasetId, tableName);
      set({ tablePreview: preview, isPreviewLoading: false });
    } catch (e) {
      set({
        isPreviewLoading: false,
        error: e instanceof Error ? e.message : "Failed to load preview",
      });
    }
  },

  switchDataView: (view: DataView) => {
    set({ activeDataView: view });
  },

  // Derived tables actions
  loadDerivedTables: async () => {
    const { session } = get();
    if (!session) return;
    try {
      const derivedTables = await api.listDerivedTables(session.id);
      set({ derivedTables });
    } catch {
      // Silently fail - derived tables are optional
    }
  },

  promoteDerivedTable: async (tableName: string, newName: string) => {
    const { session } = get();
    if (!session) return;
    try {
      await api.promoteTable(session.id, tableName, newName);
      // Refresh both lists
      const [datasets, derivedTables] = await Promise.all([
        api.listSessionDatasets(session.id),
        api.listDerivedTables(session.id),
      ]);
      set({ sessionDatasets: datasets, derivedTables });
    } catch (e) {
      set({ error: e instanceof Error ? e.message : "Failed to promote table" });
      throw e;
    }
  },

  // Interact actions (Phase 2)
  applyInteractResult: (vizId: string, result: InteractResult) => {
    if (result.type === "chart_overlay") {
      const chartResult = result as ChartInteractResult;
      const overlay: ChartOverlay = {
        overlay_type: chartResult.overlay_type as ChartOverlay["overlay_type"],
        axis: chartResult.axis,
        value: chartResult.value,
        x1: chartResult.x1,
        x2: chartResult.x2,
      };
      set((state) => ({
        chartOverlays: {
          ...state.chartOverlays,
          [vizId]: [...(state.chartOverlays[vizId] || []), overlay],
        },
      }));
    } else {
      set((state) => ({
        interactStates: {
          ...state.interactStates,
          [vizId]: result,
        },
      }));
    }
  },

  getInteractState: (vizId: string): InteractResult | null => {
    return get().interactStates[vizId] || null;
  },

  clearInteractState: (vizId: string) => {
    set((state) => {
      const { [vizId]: _, ...rest } = state.interactStates;
      const { [vizId]: __, ...overlaysRest } = state.chartOverlays;
      return {
        interactStates: rest,
        chartOverlays: overlaysRest,
      };
    });
  },

  getChartOverlays: (vizId: string): ChartOverlay[] => {
    return get().chartOverlays[vizId] || [];
  },

  updateSessionName: (name: string) => {
    set((state) => ({
      session: state.session ? { ...state.session, name } : null,
    }));
  },
}));

/**
 * Find the last query result from session messages.
 */
function findLastQueryResult(messages: Message[]): { data: unknown[]; columns: string[] } | null {
  for (let i = messages.length - 1; i >= 0; i--) {
    const msg = messages[i];
    if (msg.role === "assistant" && msg.queryResults && msg.queryResults.length > 0) {
      const last = msg.queryResults[msg.queryResults.length - 1];
      return { data: last.data, columns: last.columns };
    }
  }
  return null;
}

/**
 * Build user + assistant message content from a dataset upload response.
 * Used to skip the agent call after CSV upload.
 */
export function buildUploadSummary(
  dataset: DatasetFull,
  fileNames: string
): { userContent: string; assistantContent: string } {
  const tableCount = dataset.tables.length;
  const tableSummaries = dataset.tables
    .map((t) => `${t.name} [${t.row_count.toLocaleString()} rows]`)
    .join(", ");
  const userContent = `I uploaded ${fileNames} (${tableCount} table${tableCount !== 1 ? "s" : ""}: ${tableSummaries})`;

  const tableLines = dataset.tables
    .map((t) => `- **${t.name}** (${t.row_count.toLocaleString()} rows, ${t.columns.length} columns)`)
    .join("\n");

  let assistantContent = `Dataset uploaded successfully.\n\n${tableLines}`;

  const questions = dataset.suggested_questions;
  if (questions && questions.length > 0) {
    const questionLinks = questions.map((q) => `- [${q}](#ask)`).join("\n");
    assistantContent += `\n\nHere are some questions you can ask:\n${questionLinks}`;
  }

  return { userContent, assistantContent };
}

/**
 * Build visualization tabs from session messages.
 */
export function buildVizTabs(messages: Message[]): ChartTab[] {
  const tabs: ChartTab[] = [];
  for (const msg of messages) {
    if (msg.role !== "assistant") continue;
    msg.charts?.forEach((chart, i) => {
      tabs.push({
        id: `${msg.id}-chart-${i}`,
        title: chart.title || `Chart ${i + 1}`,
        vizType: "chart",
        spec: chart,
      });
    });
    msg.graphs?.forEach((graph, i) => {
      tabs.push({
        id: `${msg.id}-graph-${i}`,
        title: graph.title || `Graph ${i + 1}`,
        vizType: "graph",
        spec: graph,
      });
    });
  }
  return tabs;
}
