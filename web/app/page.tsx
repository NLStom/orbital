"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useSessionsStore } from "./_stores/sessions-store";
import { SessionList } from "./_components/SessionList";
import { ArtifactGrid } from "./_components/ArtifactGrid";
import { DatasetPickerModal } from "./_components/DatasetPickerModal";
import { EmptyState } from "./_components/EmptyState";
import { api, DataSourceType, DatasetSummary } from "./_lib/api";

type Tab = "sessions" | "artifacts";

export default function Home() {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<Tab>("sessions");
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [publicDatasets, setPublicDatasets] = useState<DatasetSummary[]>([]);
  const [userDatasets, setUserDatasets] = useState<DatasetSummary[]>([]);
  const [isLoadingDatasets, setIsLoadingDatasets] = useState(false);
  const [isUploading, setIsUploading] = useState(false);

  const {
    sessions,
    artifacts,
    isLoading,
    isCreating,
    error,
    fetchSessions,
    fetchArtifacts,
    createSession,
    deleteSession,
    deleteEmptySessions,
    deleteArtifact,
    clearError,
  } = useSessionsStore();

  // Count empty sessions (no user messages)
  const emptySessionCount = sessions.filter(
    (s) => s.userMessageCount === 0
  ).length;

  useEffect(() => {
    fetchSessions();
    fetchArtifacts();
  }, [fetchSessions, fetchArtifacts]);

  // Fetch datasets on mount
  useEffect(() => {
    const loadDatasets = async () => {
      setIsLoadingDatasets(true);
      try {
        const [publicData, privateData] = await Promise.all([
          api.listDatasets("public"),
          api.listDatasets("private"),
        ]);
        setPublicDatasets(publicData);
        setUserDatasets(privateData);
      } catch (error) {
        console.error("Failed to load datasets:", error);
      } finally {
        setIsLoadingDatasets(false);
      }
    };
    loadDatasets();
  }, []);

  const handleSessionClick = (id: string) => {
    router.push(`/session/${id}`);
  };

  const handleSessionDelete = async (id: string) => {
    if (window.confirm("Are you sure you want to delete this session?")) {
      await deleteSession(id);
    }
  };

  const handleArtifactClick = (id: string) => {
    router.push(`/artifact/${id}`);
  };

  const handleCopyLink = (id: string) => {
    const url = `${window.location.origin}/artifact/${id}`;
    navigator.clipboard.writeText(url);
    // TODO: Show toast notification
  };

  const handleCreateSession = async (
    dataSource: DataSourceType,
    name: string,
    selectedDatasetIds?: string[]
  ) => {
    try {
      const id = await createSession(dataSource, name || undefined, selectedDatasetIds);
      setIsModalOpen(false);
      router.push(`/session/${id}`);
    } catch {
      // Error is handled in store
    }
  };

  const handleUploadCSV = async (files: File[]) => {
    setIsUploading(true);
    try {
      await api.uploadDataset(files);
      // Refresh user datasets to include the new upload
      const privateData = await api.listDatasets("private");
      setUserDatasets(privateData);
    } catch (error) {
      console.error("Failed to upload CSV:", error);
    } finally {
      setIsUploading(false);
    }
  };

  const handleSelectSampleData = async (dataSource: DataSourceType) => {
    try {
      const id = await createSession(dataSource, `${dataSource.toUpperCase()} Analysis`);
      router.push(`/session/${id}`);
    } catch {
      // Error is handled in store
    }
  };

  const handleDeleteEmptySessions = async () => {
    if (
      window.confirm(
        `Delete ${emptySessionCount} empty session${emptySessionCount === 1 ? "" : "s"}? This cannot be undone.`
      )
    ) {
      await deleteEmptySessions();
    }
  };

  // Show empty state when no sessions exist
  const showEmptyState = !isLoading && sessions.length === 0 && activeTab === "sessions";

  return (
    <main className="min-h-screen flex flex-col bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b sticky top-0 z-10">
        <div className="max-w-5xl mx-auto px-4">
          <div className="flex items-center justify-between h-16">
            <div>
              <h1 className="text-xl font-bold text-gray-900">Orbital</h1>
              <p className="text-xs text-gray-500">
                AI-powered exploratory data analysis
              </p>
            </div>
            {!showEmptyState && (
              <div className="flex items-center gap-2">
                {emptySessionCount > 0 && (
                  <button
                    onClick={handleDeleteEmptySessions}
                    className="px-3 py-2 text-gray-600 text-sm font-medium rounded-md hover:bg-gray-100 transition-colors"
                    title="Delete sessions with no messages"
                  >
                    Delete {emptySessionCount} empty
                  </button>
                )}
                <button
                  onClick={() => setIsModalOpen(true)}
                  className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700 transition-colors"
                >
                  New Session
                </button>
              </div>
            )}
          </div>

          {/* Tabs */}
          {!showEmptyState && (
            <div className="flex gap-1 -mb-px">
              <button
                onClick={() => setActiveTab("sessions")}
                className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                  activeTab === "sessions"
                    ? "text-blue-600 border-blue-600"
                    : "text-gray-500 border-transparent hover:text-gray-700"
                }`}
              >
                Sessions
              </button>
              <button
                onClick={() => setActiveTab("artifacts")}
                className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                  activeTab === "artifacts"
                    ? "text-blue-600 border-blue-600"
                    : "text-gray-500 border-transparent hover:text-gray-700"
                }`}
              >
                Artifacts
              </button>
            </div>
          )}
        </div>
      </header>

      {/* Error Banner */}
      {error && (
        <div className="bg-red-50 border-b border-red-200 px-4 py-3">
          <div className="max-w-5xl mx-auto flex items-center justify-between">
            <p className="text-sm text-red-700">{error}</p>
            <button
              onClick={clearError}
              className="text-red-500 hover:text-red-700"
            >
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                <path
                  fillRule="evenodd"
                  d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
                  clipRule="evenodd"
                />
              </svg>
            </button>
          </div>
        </div>
      )}

      {/* Content */}
      <div className="flex-1">
        {showEmptyState ? (
          <EmptyState
            onCreateSession={() => setIsModalOpen(true)}
            onSelectSampleData={handleSelectSampleData}
          />
        ) : (
          <div className="max-w-5xl mx-auto px-4 py-6">
            {activeTab === "sessions" ? (
              <SessionList
                sessions={sessions}
                isLoading={isLoading}
                onSessionClick={handleSessionClick}
                onSessionDelete={handleSessionDelete}
              />
            ) : (
              <ArtifactGrid
                artifacts={artifacts}
                isLoading={isLoading}
                onArtifactClick={handleArtifactClick}
                onCopyLink={handleCopyLink}
              />
            )}
          </div>
        )}
      </div>

      {/* Modal */}
      <DatasetPickerModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        publicDatasets={publicDatasets}
        userDatasets={userDatasets}
        onCreateSession={handleCreateSession}
        isCreating={isCreating}
        onUpload={handleUploadCSV}
        isUploading={isUploading}
      />
    </main>
  );
}
