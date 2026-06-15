"use client";

import React, { useEffect, useRef } from "react";
import mermaid from "mermaid";

mermaid.initialize({
  startOnLoad: false,
  theme: "default",
  securityLevel: "loose",
  fontFamily: "inherit",
});

interface MermaidDiagramProps {
  chart: string;
}

export default function MermaidDiagram({ chart }: MermaidDiagramProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (containerRef.current && chart) {
      const renderChart = async () => {
        try {
          // Add a unique random id to prevent conflicts
          const id = `mermaid-${Math.random().toString(36).substring(7)}`;
          const { svg } = await mermaid.render(id, chart);
          if (containerRef.current) {
            containerRef.current.innerHTML = svg;
          }
        } catch (err) {
          console.error("Mermaid rendering error:", err);
          if (containerRef.current) {
            containerRef.current.innerHTML = `<p class="text-red-500 text-xs text-center border border-red-200 bg-red-50 p-3 rounded-lg">Failed to render diagram.</p>`;
          }
        }
      };
      renderChart();
    }
  }, [chart]);

  return (
    <div 
      ref={containerRef} 
      className="mermaid-container w-full overflow-x-auto my-4 flex justify-center bg-white dark:bg-zinc-800 p-4 rounded-xl border border-zinc-200 dark:border-zinc-700 shadow-sm" 
    />
  );
}
