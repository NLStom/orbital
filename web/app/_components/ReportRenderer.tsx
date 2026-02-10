"use client";

import Markdown from "react-markdown";
import { ChartRenderer } from "@/app/_components/visualization/ChartRenderer";

interface TextSection {
  type: "text";
  content: string;
}

interface ChartSection {
  type: "chart";
  title?: string;
  chartSpec: Record<string, unknown>;
}

export type ReportSection = TextSection | ChartSection;

interface ReportRendererProps {
  sections: ReportSection[];
}

export function ReportRenderer({ sections }: ReportRendererProps) {
  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {sections.map((section, index) => {
        if (section.type === "text") {
          return (
            <div key={index} className="prose prose-gray max-w-none">
              <Markdown>{section.content}</Markdown>
            </div>
          );
        }

        if (section.type === "chart") {
          return (
            <div key={index}>
              {section.title && (
                <h3 className="text-lg font-semibold mb-2">{section.title}</h3>
              )}
              <ChartRenderer spec={section.chartSpec} />
            </div>
          );
        }

        return null;
      })}
    </div>
  );
}
