"use client";

import React, { useEffect, useState } from "react";
import mermaid from "mermaid";
import { Maximize2, Minimize2, X } from "lucide-react";
import { createPortal } from "react-dom";

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
  const [svgContent, setSvgContent] = useState<string>("");
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (chart) {
      const renderChart = async () => {
        try {
          const id = `mermaid-${Math.random().toString(36).substring(7)}`;
          const { svg } = await mermaid.render(id, chart);
          setSvgContent(svg);
        } catch (err) {
          console.error("Mermaid rendering error:", err);
          setSvgContent(`<p class="text-red-500 text-xs text-center border border-red-200 bg-red-50 p-3 rounded-lg">Failed to render diagram.</p>`);
        }
      };
      renderChart();
    }
  }, [chart]);

  const diagramContent = (
    <div 
      className="mermaid-container w-full overflow-x-auto flex justify-center"
      dangerouslySetInnerHTML={{ __html: svgContent }}
    />
  );

  return (
    <>
      {/* Inline View */}
      <div className="relative group my-4 bg-white dark:bg-zinc-800 p-4 rounded-xl border border-zinc-200 dark:border-zinc-700 shadow-sm">
        <button
          onClick={() => setIsFullscreen(true)}
          className="absolute top-2 right-2 p-2 rounded-lg bg-white/80 dark:bg-zinc-800/80 hover:bg-zinc-100 dark:hover:bg-zinc-700 text-zinc-600 dark:text-zinc-300 shadow-sm border border-zinc-200 dark:border-zinc-700 transition-opacity z-10 opacity-0 group-hover:opacity-100"
          title="Fullscreen"
        >
          <Maximize2 size={16} />
        </button>
        {diagramContent}
      </div>

      {/* Fullscreen Portal */}
      {mounted && isFullscreen && createPortal(
        <div className="fixed inset-0 z-[9999] bg-white/95 dark:bg-zinc-950/95 backdrop-blur-md flex flex-col items-center justify-center p-4 md:p-8 animate-in fade-in duration-200">
          <button
            onClick={() => setIsFullscreen(false)}
            className="absolute top-6 right-6 p-3 rounded-full bg-zinc-100 dark:bg-zinc-800 hover:bg-zinc-200 dark:hover:bg-zinc-700 text-zinc-700 dark:text-zinc-300 shadow-md transition-colors z-50"
            title="Exit Fullscreen"
          >
            <X size={24} />
          </button>
          <div className="w-full max-w-6xl max-h-[90vh] overflow-auto bg-white dark:bg-zinc-900 rounded-2xl shadow-2xl border border-zinc-200 dark:border-zinc-800 p-8">
            {diagramContent}
          </div>
        </div>,
        document.body
      )}
    </>
  );
}
