"use client";

import React, { useState } from 'react';

export interface ThoughtItem {
  node?: string;
  phase?: string;
  title?: string;
  thought: string;
  model?: string;
  provider?: string;
  timestamp?: number;
}

interface ThinkingViewProps {
  thoughts: ThoughtItem[];
  isThinking?: boolean;
  elapsedSeconds?: number;
  activeModel?: string;
}

export const ThinkingView: React.FC<ThinkingViewProps> = ({
  thoughts,
  isThinking = false,
  elapsedSeconds = 0,
  activeModel = "qwen/qwen3.8-27b (Groq)"
}) => {
  const [isExpanded, setIsExpanded] = useState(true);

  if (!isThinking && (!thoughts || thoughts.length === 0)) {
    return null;
  }

  const formatElapsed = (sec: number) => {
    return sec < 60 ? `${sec.toFixed(1)}s` : `${Math.floor(sec / 60)}m ${(sec % 60).toFixed(1)}s`;
  };

  return (
    <div className="border-2 border-fra-black bg-[#0E0E0E] text-white shadow-brutal mb-4 overflow-hidden select-none">
      {/* Antigravity Thinking Bar Header */}
      <div
        className="flex items-center justify-between px-3 py-2 bg-[#171717] border-b-2 border-fra-black cursor-pointer hover:bg-[#202020] transition-colors"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center space-x-2.5">
          {/* Chevron */}
          <span className={`text-[10px] font-mono text-neutral-400 transform transition-transform duration-200 ${isExpanded ? 'rotate-90' : 'rotate-0'}`}>
            ▶
          </span>

          {/* Thinking Status Indicator */}
          {isThinking ? (
            <div className="flex items-center space-x-2">
              <span className="relative flex h-2.5 w-2.5">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-fra-yellow opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-fra-yellow"></span>
              </span>
              <span className="font-mono text-xs font-bold text-fra-yellow tracking-wide animate-pulse">
                Thinking...
              </span>
            </div>
          ) : (
            <div className="flex items-center space-x-2">
              <span className="inline-flex h-2 w-2 rounded-full bg-fra-green"></span>
              <span className="font-mono text-xs font-bold text-neutral-300">
                Thought for {formatElapsed(elapsedSeconds || 1.8)}
              </span>
            </div>
          )}

          <span className="text-neutral-600 font-mono text-xs">|</span>

          {/* Model Identification */}
          <span className="text-[10px] font-mono bg-neutral-800 text-neutral-300 px-1.5 py-0.5 border border-neutral-700">
            {activeModel}
          </span>
        </div>

        <div className="flex items-center space-x-2 text-[10px] font-mono text-neutral-400">
          <span>{thoughts.length} Thought {thoughts.length === 1 ? 'Block' : 'Blocks'}</span>
          <span className="text-xs">{isExpanded ? '[-]' : '[+]'}</span>
        </div>
      </div>

      {/* Accordion Content Body */}
      {isExpanded && (
        <div className="p-3.5 space-y-4 max-h-[420px] overflow-y-auto font-mono text-xs leading-relaxed select-text dark-scroll bg-[#0A0A0A]">
          {thoughts.length === 0 && isThinking ? (
            <div className="flex items-center space-x-3 py-4 text-neutral-400">
              <div className="w-3.5 h-3.5 border-2 border-fra-yellow border-t-transparent rounded-full animate-spin"></div>
              <span>Formulating cognitive decomposition and evaluating tool dependencies...</span>
            </div>
          ) : (
            thoughts.map((item, idx) => (
              <div key={idx} className="border-l-2 border-fra-yellow/70 pl-3.5 py-0.5 space-y-1.5">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <span className="text-[9px] font-black uppercase bg-fra-yellow text-black px-1 border border-black">
                      {item.phase || item.node || 'REASONING'}
                    </span>
                    <span className="font-bold text-neutral-200 text-xs">
                      {item.title || 'Autonomous Chain of Thought'}
                    </span>
                  </div>
                  {item.timestamp && (
                    <span className="text-[9px] text-neutral-500 font-mono">
                      {new Date(item.timestamp * 1000).toLocaleTimeString()}
                    </span>
                  )}
                </div>

                {/* Formatted Markdown Thought Content */}
                <div className="text-neutral-300 font-mono text-[11px] leading-relaxed whitespace-pre-wrap bg-[#121212] p-2.5 border border-neutral-800 rounded">
                  {item.thought}
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
};

export default ThinkingView;
