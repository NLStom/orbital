"use client";

import { useRef, useEffect } from "react";
import { ChartTab } from "@/app/_stores/workspace-store";

interface ChartTabBarProps {
  tabs: ChartTab[];
  activeIndex: number | null;
  onTabClick: (index: number) => void;
}

function ChartIcon() {
  return (
    <svg className="w-3 h-3 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
      />
    </svg>
  );
}

function GraphIcon() {
  return (
    <svg className="w-3 h-3 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <circle cx="12" cy="5" r="2" strokeWidth={2} />
      <circle cx="5" cy="19" r="2" strokeWidth={2} />
      <circle cx="19" cy="19" r="2" strokeWidth={2} />
      <path strokeLinecap="round" strokeWidth={2} d="M12 7v4M7 17l3-6M17 17l-3-6" />
    </svg>
  );
}

export function ChartTabBar({ tabs, activeIndex, onTabClick }: ChartTabBarProps) {
  const tabRefs = useRef<(HTMLButtonElement | null)[]>([]);

  useEffect(() => {
    if (activeIndex !== null && tabRefs.current[activeIndex]) {
      tabRefs.current[activeIndex]?.scrollIntoView?.({
        behavior: "smooth",
        block: "nearest",
        inline: "nearest",
      });
    }
  }, [activeIndex]);

  if (tabs.length === 0) {
    return null;
  }

  return (
    <div className="flex overflow-x-auto border-b bg-gray-50 scrollbar-hide">
      {tabs.map((tab, i) => (
        <button
          key={tab.id}
          ref={(el) => { tabRefs.current[i] = el; }}
          onClick={() => onTabClick(i)}
          title={tab.title}
          className={`flex items-center gap-1 px-3 py-1.5 text-xs whitespace-nowrap border-r min-w-[70px] max-w-[100px] ${
            activeIndex === i
              ? "bg-white text-blue-600 font-medium border-b-2 border-blue-600"
              : "text-gray-500 hover:text-gray-700 hover:bg-gray-100"
          }`}
        >
          {tab.vizType === "chart" ? <ChartIcon /> : <GraphIcon />}
          <span className="truncate">{tab.title}</span>
        </button>
      ))}
    </div>
  );
}
