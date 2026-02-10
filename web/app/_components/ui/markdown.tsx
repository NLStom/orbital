"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface MarkdownProps {
  children: string;
  className?: string;
}

export function Markdown({ children, className = "" }: MarkdownProps) {
  return (
    <div className={`prose prose-sm max-w-none ${className}`}>
      <ReactMarkdown remarkPlugins={[remarkGfm]}>
        {children}
      </ReactMarkdown>
    </div>
  );
}
