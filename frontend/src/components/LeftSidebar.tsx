import React, { useState, useEffect } from "react";

export function LeftSidebar({ 
  workspaces, 
  activeWorkspace, 
  setActiveWorkspace,
  conversations,
  activeConversationId,
  setActiveConversationId,
  onNewConversation
}: any) {
  return (
    <aside className="w-64 bg-fra-cream border-r-2 border-fra-black flex flex-col font-mono select-none flex-shrink-0">
      <div className="p-3 border-b-2 border-fra-black bg-fra-yellow font-extrabold text-black uppercase tracking-widest text-sm flex items-center justify-between">
        <span>FRAIDAY_</span>
      </div>
      
      <div className="p-3 border-b-2 border-fra-black bg-white">
        <label className="text-[10px] font-bold text-neutral-500 uppercase">Workspace</label>
        <select 
          className="w-full mt-1 border-2 border-fra-black p-1 text-xs font-bold"
          value={activeWorkspace?.id || ""}
          onChange={(e) => setActiveWorkspace(workspaces.find((w: any) => w.id === e.target.value))}
        >
          {workspaces.map((w: any) => (
            <option key={w.id} value={w.id}>{w.name}</option>
          ))}
        </select>
      </div>

      <div className="flex-1 overflow-y-auto">
        <div className="p-3 border-b-2 border-fra-black bg-neutral-200 hover:bg-neutral-300 cursor-pointer text-center font-bold text-xs" onClick={onNewConversation}>
          + New Chat
        </div>
        <div className="p-2 space-y-1">
          {conversations.map((c: any) => (
            <div 
              key={c.id} 
              onClick={() => setActiveConversationId(c.id)}
              className={`p-2 border-2 cursor-pointer text-xs truncate ${
                activeConversationId === c.id 
                  ? 'border-fra-black bg-fra-yellow font-bold shadow-brutal-sm' 
                  : 'border-transparent hover:border-neutral-300'
              }`}
            >
              {c.title || "Untitled Conversation"}
            </div>
          ))}
        </div>
      </div>
    </aside>
  );
}
