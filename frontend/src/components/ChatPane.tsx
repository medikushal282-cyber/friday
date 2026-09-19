import React, { useRef, useEffect } from "react";

export function ChatPane({
  messages,
  input,
  setInput,
  isGenerating,
  onSubmit,
  onStop
}: any) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, isGenerating]);

  return (
    <div className="flex-1 flex flex-col bg-white overflow-hidden relative">
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((m: any, i: number) => (
          <div key={i} className={`flex flex-col ${m.role === 'user' ? 'items-end' : 'items-start'}`}>
            <div className={`max-w-[80%] p-3 border-2 border-fra-black shadow-brutal-sm font-mono text-xs ${
              m.role === 'user' ? 'bg-fra-yellow' : 'bg-neutral-100'
            }`}>
              <div className="whitespace-pre-wrap">{m.content}</div>
              {m.artifacts?.length > 0 && (
                <div className="mt-2 pt-2 border-t border-fra-black/20 text-[10px]">
                  <strong>Artifacts generated:</strong> {m.artifacts.length}
                </div>
              )}
            </div>
          </div>
        ))}
        {isGenerating && (
          <div className="flex flex-col items-start">
            <div className="max-w-[80%] p-3 border-2 border-fra-black shadow-brutal-sm font-mono text-xs bg-neutral-100 flex items-center space-x-2">
              <span className="cursor-blink"></span>
              <span>Agent is thinking...</span>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="p-3 bg-white border-t-2 border-fra-black">
        <form 
          className="flex items-center space-x-2"
          onSubmit={(e) => { e.preventDefault(); if(isGenerating) onStop(); else onSubmit(); }}
        >
          <input 
            type="text" 
            className="flex-1 border-2 border-fra-black p-2 font-mono text-xs shadow-brutal-sm focus:outline-none"
            placeholder="What do you want to build today?"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={isGenerating}
          />
          {isGenerating ? (
            <button 
              type="button"
              onClick={onStop}
              className="px-4 py-2 bg-red-500 text-white font-bold text-xs border-2 border-black shadow-brutal-sm flex items-center hover:bg-red-600 group"
            >
              <div className="w-3 h-3 bg-white border border-black mr-2 group-hover:scale-90 transition-transform"></div>
              <span>STOP</span>
            </button>
          ) : (
            <button 
              type="submit"
              className="px-4 py-2 bg-black text-white font-bold text-xs border-2 border-black shadow-brutal-sm hover:bg-neutral-800"
            >
              Send -&gt;
            </button>
          )}
        </form>
      </div>
    </div>
  );
}
