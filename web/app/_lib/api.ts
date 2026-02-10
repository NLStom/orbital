/**
 * API client for Orbital backend.
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8787";

export interface ChatRequest {
  sessionId: string;
  message: string;
  model?: string;
}

export interface DataSource {
  id: string;
  name: string;
  description: string;
  path: string;
}

export interface ChartSpec {
  type: "bar" | "line" | "scatter" | "pie" | "area";
  title: string;
  data: Record<string, unknown>[];
  x: string;
  y: string;
  color?: string;
  x_label?: string;
  y_label?: string;
}

export interface GraphSpec {
  type: "network";
  title: string;
  nodes: { id: string; label: string }[];
  edges: { source: string; target: string; weight?: number }[];
  layout: string;
}

export interface ToolCall {
  tool: string;
  input: Record<string, unknown>;
  durationMs?: number;
  error?: string;
  output?: string;
}

export interface QueryResult {
  data: Record<string, unknown>[];
  columns: string[];
  row_count: number;
}

export interface TokenUsage {
  inputTokens: number;
  contextLimit: number;
}

export interface ChatResponse {
  messageId: string;
  response: string;
  visualizations: (ChartSpec | GraphSpec)[];
  model?: string;
  toolCalls: ToolCall[];
  queryResults?: QueryResult[];
  tokenUsage?: TokenUsage;
}

export interface HealthResponse {
  status: string;
}

// Session types
export type DataSourceType =
  | "vndb"
  | "vndb_collaboration"
  | "polymarket"
  | "steam"
  | "custom";

export interface SessionSummary {
  id: string;
  name: string;
  dataSource: DataSourceType;
  createdBy: string;
  createdAt: string;
  updatedAt: string;
  messageCount: number;
  userMessageCount: number;
  artifactCount: number;
  datasetCount: number;
}

export interface MemoryEntry {
  content: string;
  added_at: string;
}

export interface Memory {
  facts: MemoryEntry[];
  preferences: MemoryEntry[];
  corrections: MemoryEntry[];
  conclusions: MemoryEntry[];
}

export interface Session extends SessionSummary {
  messages: Message[];
  insights: Insight[];
  datasets?: string[];
  memory?: Memory;
}

export interface SystemEvent {
  type: string;
  summary: string;
  metadata?: Record<string, unknown> | null;
}

export interface Message {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: string;
  charts?: ChartSpec[];
  graphs?: GraphSpec[];
  toolCalls?: ToolCall[];
  queryResults?: QueryResult[];
  systemEvent?: SystemEvent;
  isError?: boolean; // When true, message displays as an error with copy functionality
  tokenUsage?: TokenUsage;
}

export interface Insight {
  id: string;
  title: string;
  summary: string;
  createdAt: string;
  messageId?: string;
  visualization?: ChartSpec | GraphSpec;
  savedAsArtifact?: string;
}

// Artifact types
export interface ArtifactSummary {
  id: string;
  name: string;
  description: string;
  createdAt: string;
  dataSource: DataSourceType;
  visualizationType: "chart" | "graph" | "report";
}

export interface DataSnapshot {
  query?: string;
  data: unknown[];
  columns: string[];
  rowCount: number;
  capturedAt: string;
}

export interface Artifact extends ArtifactSummary {
  sessionId: string;
  insightId?: string;
  visualization: ChartSpec | GraphSpec | Record<string, unknown>;
  dataSnapshot: DataSnapshot;
}

// Schema diagram types
export interface ColumnSpec {
  name: string;
  type: string;
  isPrimaryKey: boolean;
  isForeignKey: boolean;
  references?: string | null;
}

export interface TableSpec {
  name: string;
  columns: ColumnSpec[];
  rowCount: number;
}

export interface RelationshipSpec {
  from: string;
  to: string;
  type: "one-to-one" | "one-to-many" | "many-to-one" | "many-to-many";
}

export interface ERDiagramSpec {
  dataSource: string;
  generatedAt: string;
  tables: TableSpec[];
  relationships: RelationshipSpec[];
}

/**
 * Send a chat message to the backend.
 * Backend handles message persistence - saves both user and assistant messages.
 */
export async function sendMessage(
  sessionId: string,
  message: string,
  model?: string
): Promise<ChatResponse> {
  const response = await fetch(`${API_BASE_URL}/api/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ sessionId, message, model }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || `Failed to send message`);
  }

  return response.json();
}

/**
 * Check backend health.
 */
export async function checkHealth(): Promise<HealthResponse> {
  const response = await fetch(`${API_BASE_URL}/health`);

  if (!response.ok) {
    throw new Error(`Health check failed: ${response.status}`);
  }

  return response.json();
}

/**
 * Fetch available data sources.
 */
export async function fetchSources(): Promise<DataSource[]> {
  const response = await fetch(`${API_BASE_URL}/api/sources`);

  if (!response.ok) {
    throw new Error(`Failed to fetch sources: ${response.status}`);
  }

  return response.json();
}

// Session API functions
export async function listSessions(): Promise<SessionSummary[]> {
  const response = await fetch(`${API_BASE_URL}/api/sessions`);
  if (!response.ok) {
    throw new Error(`Failed to fetch sessions: ${response.status}`);
  }
  const data = await response.json();
  return data.sessions;
}

export async function getSession(id: string): Promise<Session> {
  const response = await fetch(`${API_BASE_URL}/api/sessions/${id}`);
  if (!response.ok) {
    if (response.status === 404) {
      throw new Error("Session not found");
    }
    throw new Error(`Failed to fetch session: ${response.status}`);
  }
  return response.json();
}

export async function createSession(
  dataSource: DataSourceType,
  name?: string,
  datasetIds?: string[]
): Promise<Session> {
  const body: {
    dataSource: DataSourceType;
    name?: string;
    dataset_ids?: string[];
  } = { dataSource };
  if (name) body.name = name;
  if (datasetIds && datasetIds.length > 0) body.dataset_ids = datasetIds;

  const response = await fetch(`${API_BASE_URL}/api/sessions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || `Failed to create session: ${response.status}`);
  }
  return response.json();
}

export async function deleteSession(id: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/sessions/${id}`, {
    method: "DELETE",
  });
  if (!response.ok) {
    if (response.status === 404) {
      throw new Error("Session not found");
    }
    throw new Error(`Failed to delete session: ${response.status}`);
  }
}

export async function deleteEmptySessions(): Promise<number> {
  const response = await fetch(`${API_BASE_URL}/api/sessions`, {
    method: "DELETE",
  });
  if (!response.ok) {
    throw new Error(`Failed to delete empty sessions: ${response.status}`);
  }
  const data = await response.json();
  return data.deleted;
}

export interface SessionUpdateRequest {
  name?: string;
  addMessage?: {
    role: "user" | "assistant";
    content: string;
    charts?: ChartSpec[];
    graphs?: GraphSpec[];
    toolCalls?: ToolCall[];
  };
  addInsight?: {
    title: string;
    summary: string;
    messageId?: string;
    visualization?: ChartSpec | GraphSpec;
  };
  updateInsight?: {
    id: string;
    savedAsArtifact?: string | null;
  };
}

export async function updateSession(
  id: string,
  updates: SessionUpdateRequest
): Promise<Session> {
  const response = await fetch(`${API_BASE_URL}/api/sessions/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(updates),
  });
  if (!response.ok) {
    if (response.status === 404) {
      throw new Error("Session not found");
    }
    const error = await response.json();
    throw new Error(error.error || `Failed to update session: ${response.status}`);
  }
  return response.json();
}

// Artifact API functions
export async function listArtifacts(): Promise<ArtifactSummary[]> {
  const response = await fetch(`${API_BASE_URL}/api/artifacts`);
  if (!response.ok) {
    throw new Error(`Failed to fetch artifacts: ${response.status}`);
  }
  const data = await response.json();
  return data.artifacts;
}

export async function getArtifact(id: string): Promise<Artifact> {
  const response = await fetch(`${API_BASE_URL}/api/artifacts/${id}`);
  if (!response.ok) {
    if (response.status === 404) {
      throw new Error("Artifact not found");
    }
    throw new Error(`Failed to fetch artifact: ${response.status}`);
  }
  return response.json();
}

export async function createArtifact(
  sessionId: string,
  insightId: string,
  name: string,
  description?: string
): Promise<Artifact> {
  const response = await fetch(`${API_BASE_URL}/api/artifacts`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ sessionId, insightId, name, description }),
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || `Failed to create artifact: ${response.status}`);
  }
  return response.json();
}

export async function deleteArtifact(id: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/artifacts/${id}`, {
    method: "DELETE",
  });
  if (!response.ok) {
    if (response.status === 404) {
      throw new Error("Artifact not found");
    }
    throw new Error(`Failed to delete artifact: ${response.status}`);
  }
}

/**
 * Fetch ER diagram schema for a data source.
 */
export async function getSchemadiagram(sourceId: string): Promise<ERDiagramSpec> {
  const response = await fetch(`${API_BASE_URL}/api/sources/${sourceId}/schema`);

  if (!response.ok) {
    if (response.status === 404) {
      const error = await response.json();
      throw new Error(error.detail?.error || "Data source not found");
    }
    throw new Error(`Failed to fetch schema: ${response.status}`);
  }

  return response.json();
}

// Layout persistence types
export interface SchemaLayout {
  nodePositions: Record<string, { x: number; y: number }>;
  viewport: { x: number; y: number; zoom: number };
  updatedAt?: string;
}

export async function getSchemaLayout(sourceId: string): Promise<SchemaLayout | null> {
  const response = await fetch(`${API_BASE_URL}/api/sources/${sourceId}/schema/layout`);
  if (!response.ok) {
    throw new Error(`Failed to fetch layout: ${response.status}`);
  }
  return response.json();
}

export async function saveSchemaLayout(
  sourceId: string,
  layout: Omit<SchemaLayout, "updatedAt">
): Promise<SchemaLayout> {
  const response = await fetch(`${API_BASE_URL}/api/sources/${sourceId}/schema/layout`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(layout),
  });
  if (!response.ok) {
    throw new Error(`Failed to save layout: ${response.status}`);
  }
  return response.json();
}

export async function deleteSchemaLayout(sourceId: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/sources/${sourceId}/schema/layout`, {
    method: "DELETE",
  });
  if (!response.ok && response.status !== 404) {
    throw new Error(`Failed to delete layout: ${response.status}`);
  }
}

// Data quality types
export interface QualityIssue {
  severity: "error" | "warning" | "info";
  message: string;
  column?: string;
  affected_count: number;
  affected_rows: number[];
}

export interface QualityReport {
  table_name: string;
  issues: QualityIssue[];
  quality_score: number;
}

// Dataset types
export interface DatasetTableInfo {
  name: string;
  pg_table_name: string;
  row_count: number;
  columns: string[];
  dtypes: Record<string, string>;
}

export interface DatasetFull {
  id: string;
  name: string;
  owner: string;
  visibility: "public" | "private";
  derived_from: string | null;
  tables: DatasetTableInfo[];
  created_at: string;
  updated_at: string;
  quality_reports?: QualityReport[] | null;
  suggested_questions?: string[] | null;
}

export interface DatasetSummary {
  id: string;
  name: string;
  owner: string;
  visibility: "public" | "private";
  derived_from: string | null;
  table_count: number;
  total_rows: number;
  created_at: string;
}

// Dataset API functions
export async function listDatasets(visibility?: string): Promise<DatasetSummary[]> {
  const params = visibility ? `?visibility=${visibility}` : "";
  const res = await fetch(`${API_BASE_URL}/api/datasets${params}`);
  if (!res.ok) throw new Error("Failed to list datasets");
  const data = await res.json();
  return data.datasets;
}

export async function getDataset(id: string): Promise<DatasetFull> {
  const res = await fetch(`${API_BASE_URL}/api/datasets/${id}`);
  if (!res.ok) throw new Error("Dataset not found");
  return res.json();
}

export async function uploadDataset(
  files: File[],
  name?: string,
  sessionId?: string
): Promise<DatasetFull> {
  const formData = new FormData();
  files.forEach((f) => formData.append("files", f));
  if (name) formData.append("name", name);
  if (sessionId) formData.append("session_id", sessionId);

  const res = await fetch(`${API_BASE_URL}/api/datasets/upload`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.error || "Upload failed");
  }
  return res.json();
}

export async function updateDataset(
  id: string,
  updates: { name?: string; visibility?: string }
): Promise<DatasetFull> {
  const res = await fetch(`${API_BASE_URL}/api/datasets/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(updates),
  });
  if (!res.ok) throw new Error("Failed to update dataset");
  return res.json();
}

export async function deleteDataset(id: string): Promise<void> {
  const res = await fetch(`${API_BASE_URL}/api/datasets/${id}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error("Failed to delete dataset");
}

export async function promoteTable(
  sessionId: string,
  tableName: string,
  newName: string
): Promise<DatasetFull> {
  const params = new URLSearchParams({
    session_id: sessionId,
    table_name: tableName,
    new_name: newName,
  });
  const res = await fetch(`${API_BASE_URL}/api/datasets/promote?${params}`, {
    method: "POST",
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.error || "Failed to promote table");
  }
  return res.json();
}

export async function attachDatasetToSession(
  sessionId: string,
  datasetId: string
): Promise<void> {
  const res = await fetch(
    `${API_BASE_URL}/api/sessions/${sessionId}/datasets`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ dataset_id: datasetId }),
    }
  );
  if (!res.ok) throw new Error("Failed to attach dataset");
}

export async function detachDatasetFromSession(
  sessionId: string,
  datasetId: string
): Promise<void> {
  const res = await fetch(
    `${API_BASE_URL}/api/sessions/${sessionId}/datasets/${datasetId}`,
    { method: "DELETE" }
  );
  if (!res.ok) throw new Error("Failed to detach dataset");
}

export async function listSessionDatasets(
  sessionId: string
): Promise<DatasetFull[]> {
  const res = await fetch(
    `${API_BASE_URL}/api/sessions/${sessionId}/datasets`
  );
  if (!res.ok) throw new Error("Failed to list session datasets");
  const data = await res.json();
  return data.datasets;
}

// Derived tables (agent-created tables during session)
export interface DerivedTable {
  name: string;
  pg_table_name: string;
  row_count: number;
  columns: string[];
  dtypes: Record<string, string>;
}

export async function listDerivedTables(
  sessionId: string
): Promise<DerivedTable[]> {
  const res = await fetch(
    `${API_BASE_URL}/api/sessions/${sessionId}/derived-tables`
  );
  if (!res.ok) throw new Error("Failed to list derived tables");
  const data = await res.json();
  return data.derived_tables;
}

// Dataset table preview
export interface TablePreview {
  columns: string[];
  data: Record<string, unknown>[];
  total_rows: number;
  limit: number;
  offset: number;
}

export async function previewDatasetTable(
  datasetId: string,
  tableName: string,
  limit?: number,
  offset?: number
): Promise<TablePreview> {
  const params = new URLSearchParams();
  if (limit != null) params.set("limit", String(limit));
  if (offset != null) params.set("offset", String(offset));
  const qs = params.toString() ? `?${params.toString()}` : "";
  const res = await fetch(
    `${API_BASE_URL}/api/datasets/${datasetId}/tables/${tableName}/preview${qs}`
  );
  if (!res.ok) throw new Error("Failed to load table preview");
  return res.json();
}

// Session-scoped schema
export async function getSessionSchema(
  sessionId: string
): Promise<ERDiagramSpec> {
  const res = await fetch(
    `${API_BASE_URL}/api/sessions/${sessionId}/schema`
  );
  if (!res.ok) {
    if (res.status === 404) throw new Error("Session not found");
    throw new Error(`Failed to fetch schema: ${res.status}`);
  }
  return res.json();
}

// Generate session title
export async function generateSessionTitle(
  sessionId: string
): Promise<{ title: string }> {
  const res = await fetch(
    `${API_BASE_URL}/api/sessions/${sessionId}/generate-title`,
    { method: "POST" }
  );
  if (!res.ok) {
    if (res.status === 404) throw new Error("Session not found");
    throw new Error("Failed to generate title");
  }
  return res.json();
}

// System events
export async function logSystemEvent(
  sessionId: string,
  type: string,
  summary: string,
  metadata?: Record<string, unknown>
): Promise<Message> {
  const res = await fetch(
    `${API_BASE_URL}/api/sessions/${sessionId}/events`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ type, summary, metadata }),
    }
  );
  if (!res.ok) throw new Error("Failed to log system event");
  return res.json();
}

export const api = {
  sendMessage,
  checkHealth,
  fetchSources,
  // Sessions
  listSessions,
  getSession,
  createSession,
  updateSession,
  deleteSession,
  deleteEmptySessions,
  generateSessionTitle,
  // Artifacts
  listArtifacts,
  getArtifact,
  createArtifact,
  deleteArtifact,
  // Schema
  getSchemadiagram,
  // Layout
  getSchemaLayout,
  saveSchemaLayout,
  deleteSchemaLayout,
  // Session schema
  getSessionSchema,
  // Dataset preview
  previewDatasetTable,
  // System events
  logSystemEvent,
  // Datasets
  listDatasets,
  getDataset,
  uploadDataset,
  updateDataset,
  deleteDataset,
  promoteTable,
  attachDatasetToSession,
  detachDatasetFromSession,
  listSessionDatasets,
  listDerivedTables,
};
