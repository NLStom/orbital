"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { Group, Panel, Separator } from "react-resizable-panels";
import { useWorkspaceStore } from "@/app/_stores/workspace-store";
import { WorkspaceHeader } from "@/app/_components/WorkspaceHeader";
import { ChatPanel } from "@/app/_components/ChatPanel";
import { VizPanel } from "@/app/_components/VizPanel";
import { LogPanel } from "@/app/_components/LogPanel";
export default function WorkspacePage() {
  const params = useParams();
  const router = useRouter();
  const sessionId = params.id as string;

  const {
    session,
    activeTab,
    isChatCollapsed,
    isInsightsPanelOpen,
    isLogPanelOpen,
    isLoading,
    isSending,
    error,
    currentVisualization,
    currentQueryResult,
    visualizationTabs,
    activeVizTabIndex,
    schemaDiagram,
    isSchemaLoading,
    schemaError,
    isUploading,
    sessionDatasets,
    selectedDatasetTable,
    tablePreview,
    isPreviewLoading,
    activeDataView,
    loadSession,
    sendMessage,
    setActiveTab,
    toggleChat,
    toggleInsightsPanel,
    toggleLogPanel,
    setActiveVizTab,
    selectVizByTabId,
    clearError,
    reset,
    loadSchemaDiagram,
    uploadCSV,
    loadSessionDatasets,
    loadTablePreview,
    switchDataView,
    derivedTables,
    loadDerivedTables,
    promoteDerivedTable,
    updateSessionName,
    sendStartedAt,
  } = useWorkspaceStore();

  // Persist resizable panel layout to localStorage (SSR-safe)
  type Layout = { [id: string]: number };
  const [defaultLayout, setDefaultLayout] = useState<Layout | undefined>(undefined);

  useEffect(() => {
    const saved = localStorage.getItem("workspace-layout");
    if (saved) {
      try {
        setDefaultLayout(JSON.parse(saved));
      } catch {
        // Ignore invalid JSON
      }
    }
  }, []);

  const onLayoutChanged = (layout: Layout) => {
    localStorage.setItem("workspace-layout", JSON.stringify(layout));
  };

  // Calculate tool call count from most recent assistant message
  // Must be before any early returns to satisfy React hooks rules
  const toolCallCount = useMemo(() => {
    if (!session?.messages) return 0;
    for (let i = session.messages.length - 1; i >= 0; i--) {
      if (session.messages[i].role === "assistant" && session.messages[i].toolCalls) {
        return session.messages[i].toolCalls!.length;
      }
    }
    return 0;
  }, [session?.messages]);

  // Load session on mount
  useEffect(() => {
    loadSession(sessionId);
    return () => reset();
  }, [sessionId, loadSession, reset]);

  // Load schema when session is loaded or datasets change
  useEffect(() => {
    if (session?.id) {
      loadSchemaDiagram(session.id);
    }
  }, [session?.id, sessionDatasets, loadSchemaDiagram]);

  // Load session datasets
  useEffect(() => {
    if (session?.id) {
      loadSessionDatasets();
    }
  }, [session?.id, loadSessionDatasets]);

  // Load derived tables (refresh after messages change, as agent may create new ones)
  useEffect(() => {
    if (session?.id) {
      loadDerivedTables();
    }
  }, [session?.id, session?.messages.length, loadDerivedTables]);

  const handleShare = () => {
    const url = `${window.location.origin}/session/${sessionId}`;
    navigator.clipboard.writeText(url);
  };

  const handleExport = (format: "artifact" | "png" | "svg" | "csv" | "report") => {
    if (format === "report") {
      sendMessage("Generate a report summarizing our analysis");
      return;
    }
    console.log("Export:", format);
  };

  const handleViewVisualization = (tabId: string) => {
    selectVizByTabId(tabId);
  };

  // Loading state
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-gray-500">Loading session...</p>
        </div>
      </div>
    );
  }

  // Error state
  if (error && !session) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center max-w-md mx-auto p-8">
          <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg
              className="w-8 h-8 text-red-600"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
              />
            </svg>
          </div>
          <h2 className="text-xl font-semibold text-gray-900 mb-2">
            {error === "Session not found" ? "Session Not Found" : "Error"}
          </h2>
          <p className="text-gray-500 mb-6">{error}</p>
          <button
            onClick={() => router.push("/")}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
          >
            Back to Home
          </button>
        </div>
      </div>
    );
  }

  if (!session) {
    return null;
  }

  return (
    <div className="h-screen flex flex-col">
      {/* Header */}
      <WorkspaceHeader
        sessionId={session.id}
        sessionName={session.name}
        createdBy={session.createdBy}
        messageCount={session.messages.length}
        datasetCount={session.datasets?.length ?? 0}
        insightCount={session.insights.length}
        toolCallCount={toolCallCount}
        onToggleChat={toggleChat}
        onToggleLogs={toggleLogPanel}
        onOpenInsights={toggleInsightsPanel}
        onShare={handleShare}
        onExport={handleExport}
        isChatCollapsed={isChatCollapsed}
        isLogPanelOpen={isLogPanelOpen}
        onTitleChange={updateSessionName}
      />

      {/* Error Banner */}
      {error && (
        <div className="bg-red-50 border-b border-red-200 px-4 py-2 flex items-center justify-between">
          <p className="text-sm text-red-700">{error}</p>
          <button onClick={clearError} className="text-red-500 hover:text-red-700">
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
              <path
                fillRule="evenodd"
                d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
                clipRule="evenodd"
              />
            </svg>
          </button>
        </div>
      )}

      {/* Main Content */}
      <div className="flex-1 overflow-hidden">
        <Group
          orientation="horizontal"
          defaultLayout={defaultLayout}
          onLayoutChanged={onLayoutChanged}
        >
          {!isChatCollapsed && (
            <>
              <Panel id="chat" defaultSize="38%" minSize="20%" maxSize="60%">
                <ChatPanel
                  messages={session.messages}
                  isCollapsed={isChatCollapsed}
                  isLoading={isSending}
                  onSendMessage={sendMessage}
                  onViewVisualization={handleViewVisualization}
                  onUpload={uploadCSV}
                  isUploading={isUploading}
                  sendStartedAt={sendStartedAt}
                />
              </Panel>
              <Separator className="w-1.5 bg-gray-200 hover:bg-blue-400 active:bg-blue-500 transition-colors flex items-center justify-center">
                <div className="w-0.5 h-6 bg-gray-400 rounded-full" />
              </Separator>
            </>
          )}
          <Panel id="viz" defaultSize="62%" minSize="30%">
            <VizPanel
              activeTab={activeTab}
              onTabChange={setActiveTab}
              currentVisualization={currentVisualization as import("@/app/_lib/api").ChartSpec | null}
              queryResult={currentQueryResult}
              visualizationTabs={visualizationTabs}
              activeVizTabIndex={activeVizTabIndex}
              onVizTabClick={setActiveVizTab}
              sessionDatasets={sessionDatasets}
              tablePreview={tablePreview}
              isPreviewLoading={isPreviewLoading}
              selectedDatasetTable={selectedDatasetTable}
              activeDataView={activeDataView}
              onSelectTable={loadTablePreview}
              onSwitchDataView={switchDataView}
              derivedTables={derivedTables}
              onPromoteDerivedTable={promoteDerivedTable}
            />
          </Panel>
        </Group>
      </div>

      {/* Insights Panel (slide-over) */}
      {isInsightsPanelOpen && (
        <div className="fixed inset-0 z-50">
          <div
            className="absolute inset-0 bg-black/50"
            onClick={toggleInsightsPanel}
          />
          <div className="absolute right-0 top-0 bottom-0 w-96 bg-white shadow-xl">
            <div className="p-4 border-b flex items-center justify-between">
              <h2 className="font-semibold">Insights</h2>
              <button
                onClick={toggleInsightsPanel}
                className="p-1 hover:bg-gray-100 rounded"
              >
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
                    d="M6 18L18 6M6 6l12 12"
                  />
                </svg>
              </button>
            </div>
            <div className="p-4">
              {session.insights.length === 0 ? (
                <p className="text-gray-500 text-center py-8">
                  No insights extracted yet
                </p>
              ) : (
                <div className="space-y-4">
                  {session.insights.map((insight) => (
                    <div
                      key={insight.id}
                      className="p-3 border rounded-lg hover:bg-gray-50 cursor-pointer"
                    >
                      <h3 className="font-medium">{insight.title}</h3>
                      <p className="text-sm text-gray-500 mt-1">
                        {insight.summary}
                      </p>
                      {insight.savedAsArtifact && (
                        <span className="inline-block mt-2 text-xs text-green-600">
                          Saved as artifact
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Log Panel */}
      <LogPanel
        isOpen={isLogPanelOpen}
        messages={session.messages}
        onClose={toggleLogPanel}
      />
    </div>
  );
}
