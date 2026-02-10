"use client";

import { DataSourceType } from "@/app/_lib/api";

interface EmptyStateProps {
  onCreateSession: () => void;
  onSelectSampleData: (dataSource: DataSourceType) => void;
}

const SAMPLE_DATASETS: {
  id: DataSourceType;
  name: string;
  description: string;
  examples: string[];
}[] = [
  {
    id: "vndb",
    name: "Visual Novel Database",
    description: "728 visual novels with characters, tags, and relationships",
    examples: ["Top rated VNs by genre", "Character relationship networks", "Tag co-occurrence patterns"],
  },
  {
    id: "vndb_collaboration",
    name: "VNDB Staff Collaboration",
    description: "Staff collaboration graph with alias metadata",
    examples: [
      "Most connected staff clusters",
      "Cross-studio collaboration",
      "Team structures by VN",
    ],
  },
  {
    id: "polymarket",
    name: "Polymarket",
    description: "7,653 prediction markets with price history",
    examples: ["Market volume trends", "Category analysis", "Outcome correlations"],
  },
  {
    id: "steam",
    name: "Steam Games",
    description: "122,611 games with reviews and metadata",
    examples: ["Genre popularity over time", "Review sentiment analysis", "Publisher networks"],
  },
];

export function EmptyState({
  onCreateSession,
  onSelectSampleData,
}: EmptyStateProps) {
  return (
    <div className="max-w-2xl mx-auto py-12 px-4">
      {/* Welcome */}
      <div className="text-center mb-8">
        <h2 className="text-2xl font-bold text-gray-900 mb-2">
          Welcome to Orbital
        </h2>
        <p className="text-gray-600">
          AI-powered exploratory data analysis. Ask questions in natural language
          and get visualizations instantly.
        </p>
      </div>

      {/* Create Session Button */}
      <div className="text-center mb-8">
        <button
          onClick={onCreateSession}
          className="px-6 py-3 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition-colors"
        >
          Create Your First Session
        </button>
      </div>

      {/* Divider */}
      <div className="flex items-center gap-4 mb-8">
        <div className="flex-1 border-t" />
        <span className="text-sm text-gray-500">or start with sample data</span>
        <div className="flex-1 border-t" />
      </div>

      {/* Sample Datasets */}
      <div className="space-y-4">
        {SAMPLE_DATASETS.map((dataset) => (
          <button
            key={dataset.id}
            onClick={() => onSelectSampleData(dataset.id)}
            className="w-full text-left p-4 border rounded-lg hover:bg-gray-50 transition-colors"
          >
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <h3 className="font-medium text-gray-900">{dataset.name}</h3>
                <p className="text-sm text-gray-500 mt-0.5">
                  {dataset.description}
                </p>
                <div className="mt-2 flex flex-wrap gap-2">
                  {dataset.examples.map((example, i) => (
                    <span
                      key={i}
                      className="text-xs px-2 py-1 bg-gray-100 text-gray-600 rounded"
                    >
                      {example}
                    </span>
                  ))}
                </div>
              </div>
              <svg
                className="w-5 h-5 text-gray-400 flex-shrink-0 ml-4"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 5l7 7-7 7"
                />
              </svg>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
