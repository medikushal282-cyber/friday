"use client";
import React, { useState, useEffect } from "react";
import LatticeLoader from "@/components/LatticeLoader";
import ThinkingView, { ThoughtItem } from "@/components/ThinkingView";
import BrowserPreview from "@/components/BrowserPreview";
import ModelSelectorModal from "@/components/ModelSelector";

interface ToolActivity {
  id: string;
  type: string;
  title: string;
  detail?: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'approval_required';
  timestamp: string;
}

export default function FraidayWorkspace() {
  const [view, setView] = useState("conversation");
  const [workspaceMenuOpen, setWorkspaceMenuOpen] = useState(false);
  const [workspace, setWorkspace] = useState("Fraiday");
  const [workspaceRoot, setWorkspaceRoot] = useState("C:\\Projects\\RAGTEC\\Fraiday");
  const [runtimeInfo, setRuntimeInfo] = useState<any>(null);
  
  const [modeMenuOpen, setModeMenuOpen] = useState(false);
  const [mode, setMode] = useState("Autonomous");
  
  const [modelMenuOpen, setModelMenuOpen] = useState(false);
  const [model, setModel] = useState("openai/gpt-oss-120b");
  const [provider, setProvider] = useState("groq");
  const [modelSelectorOpen, setModelSelectorOpen] = useState(false);
  const [thoughts, setThoughts] = useState<ThoughtItem[]>([]);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewUrl, setPreviewUrl] = useState("http://localhost:8000/api/preview/index.html");
  const [thinkingElapsed, setThinkingElapsed] = useState(0);
  
  const [commandModalOpen, setCommandModalOpen] = useState(false);
  const [switches, setSwitches] = useState({ web: true, kb: true, tools: true });
  
  const [inputVal, setInputVal] = useState("");

  // --- PHASE 4.6 RUN STATE & ACTIVITY STREAM ---
  const [runId, setRunId] = useState<string | null>(null);
  const [runStatus, setRunStatus] = useState<string>('idle');
  const [runObjective, setRunObjective] = useState<string>('');
  const [runType, setRunType] = useState<'execution' | 'chat'>('execution');
  const [chatMessage, setChatMessage] = useState<string>('');
  const [planSteps, setPlanSteps] = useState<any[]>([]);
  const [nodes, setNodes] = useState<Record<string, string>>({});
  const [activityStream, setActivityStream] = useState<ToolActivity[]>([]);
  const [relevantFiles, setRelevantFiles] = useState<string[]>([]);
  const [artifacts, setArtifacts] = useState<any[]>([]);
  const [validationResult, setValidationResult] = useState<any>(null);
  const [finalResult, setFinalResult] = useState<any>(null);
  const [errorInfo, setErrorInfo] = useState<{ node?: string; message: string; error_type?: string } | null>(null);
  const [inspectorTab, setInspectorTab] = useState<'planning' | 'context' | 'files' | 'artifacts'>('planning');

  // Fetch real workspace and runtime information from backend on mount
  useEffect(() => {
    const fetchWorkspace = async () => {
      try {
        const res = await fetch("http://localhost:8000/api/workspace");
        if (res.ok) {
          const data = await res.json();
          if (data.name) setWorkspace(data.name);
          if (data.root_path) setWorkspaceRoot(data.root_path);
          if (data.runtime) setRuntimeInfo(data.runtime);
        }
      } catch (e) {
        console.warn("Backend workspace API not reachable yet", e);
      }
    };
    fetchWorkspace();
  }, []);

  // Thinking elapsed stopwatch
  useEffect(() => {
    let interval: any = null;
    if (runStatus === 'running' || runStatus === 'starting') {
      const start = performance.now();
      interval = setInterval(() => {
        setThinkingElapsed((performance.now() - start) / 1000);
      }, 100);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [runStatus]);

  const addActivity = (item: Omit<ToolActivity, 'id' | 'timestamp'>) => {
    const activity: ToolActivity = {
      ...item,
      id: Math.random().toString(36).substring(2, 9),
      timestamp: new Date().toLocaleTimeString()
    };
    setActivityStream(prev => [...prev, activity]);
  };

  const startRun = async () => {
    if (!inputVal.trim()) return;
    if (runStatus === 'running' || runStatus === 'starting') return;
    
    const objective = inputVal;
    setInputVal("");
    setRunId(null);
    setRunStatus('starting');
    setRunObjective(objective);
    setRunType('execution');
    setInspectorTab('planning');
    setChatMessage('');
    setPlanSteps([]);
    setNodes({});
    setActivityStream([]);
    setThoughts([]);
    setThinkingElapsed(0);
    setRelevantFiles([]);
    setArtifacts([]);
    setValidationResult(null);
    setFinalResult(null);
    setErrorInfo(null);
    
    try {
      const res = await fetch('http://localhost:8000/api/runs/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ objective, model, provider })
      });
      
      if (!res.ok) throw new Error('Failed to start run');
      const data = await res.json();
      setRunId(data.run_id);
      setRunStatus('running');
      
      const evtSource = new EventSource(`http://localhost:8000/api/runs/${data.run_id}/events`);
      
      evtSource.onmessage = async (event) => {
        try {
          const payload = JSON.parse(event.data);
          const { event: type, node, data: eventData } = payload;
          
          if (type === 'chat_response') {
            setRunType('chat');
            setChatMessage(eventData.text || '');
          } else if (type === 'thought_generated' || type === 'thought') {
            setThoughts(prev => [...prev, eventData]);
          } else if (type === 'browser_opened') {
            setPreviewUrl(eventData.url);
            setPreviewOpen(true);
          } else if (type === 'context_loaded') {
            addActivity({
              type: 'CONTEXT',
              title: `Workspace Context Initialized: ${eventData.workspace?.name || 'Fraiday'}`,
              detail: `Root: ${eventData.workspace?.root_path || workspaceRoot} | History turns: ${eventData.conversation_turns || 0}`,
              status: 'completed'
            });
          } else if (type === 'node_started') {
            setNodes(prev => ({ ...prev, [node]: 'running' }));
          } else if (type === 'node_completed') {
            setNodes(prev => ({ ...prev, [node]: 'completed' }));
          } else if (type === 'agent_thinking') {
            addActivity({
              type: (node || 'AGENT').toUpperCase(),
              title: eventData?.summary || 'Processing...',
              status: 'completed'
            });
          } else if (type === 'plan_created') {
            setPlanSteps(eventData?.steps || []);
            addActivity({
              type: 'PLAN',
              title: `Action Plan Generated: ${eventData?.steps?.length || 0} operational steps`,
              status: 'completed'
            });
          } else if (type === 'step_started') {
            setPlanSteps(prev => prev.map(s => s.id === eventData.step_id ? { ...s, status: 'running' } : s));
          } else if (type === 'step_completed') {
            setPlanSteps(prev => prev.map(s => s.id === eventData.step_id ? { ...s, status: 'completed' } : s));
          } else if (type === 'tool_call_started') {
            addActivity({
              type: 'ACTION',
              title: `Invoking Tool: ${eventData.tool?.toUpperCase()}`,
              detail: eventData.path ? `Target: ${eventData.path}` : (eventData.command ? `Command: ${eventData.command}` : undefined),
              status: 'running'
            });
          } else if (type === 'tool_call_completed') {
            const isSuccess = eventData.success !== false;
            const isApproval = eventData.status === 'approval_required';
            addActivity({
              type: 'RESULT',
              title: `Tool Result: ${eventData.tool?.toUpperCase()}`,
              detail: isApproval ? `APPROVAL REQUIRED: ${eventData.reason}` : (isSuccess ? 'Success' : `Error: ${typeof eventData.error === 'object' && eventData.error !== null ? (eventData.error.message || JSON.stringify(eventData.error)) : (eventData.error || eventData.reason)}`),
              status: isApproval ? 'approval_required' : (isSuccess ? 'completed' : 'failed')
            });
          } else if (type === 'file_created') {
            setRelevantFiles(prev => Array.from(new Set([...prev, eventData.path])));
            setArtifacts(prev => [...prev, { path: eventData.path, operation: 'created', type: 'file' }]);
            if (eventData.path && (eventData.path.endsWith('.html') || eventData.path.endsWith('.htm'))) {
              setPreviewUrl(`http://localhost:8000/api/preview/${eventData.path}`);
              setPreviewOpen(true);
            }
            addActivity({
              type: 'CRUD',
              title: `File Created: ${eventData.path}`,
              detail: `${eventData.lines || 0} lines written to workspace`,
              status: 'completed'
            });
          } else if (type === 'file_updated') {
            setRelevantFiles(prev => Array.from(new Set([...prev, eventData.path])));
            setArtifacts(prev => [...prev, { path: eventData.path, operation: 'updated', type: 'file' }]);
            if (eventData.path && (eventData.path.endsWith('.html') || eventData.path.endsWith('.htm'))) {
              setPreviewUrl(`http://localhost:8000/api/preview/${eventData.path}`);
            }
            addActivity({
              type: 'CRUD',
              title: `File Updated: ${eventData.path}`,
              detail: `Diff: ${eventData.diff || 'Modified'} (${eventData.lines || 0} lines)`,
              status: 'completed'
            });
          } else if (type === 'file_read') {
            setRelevantFiles(prev => Array.from(new Set([...prev, eventData.path])));
            addActivity({
              type: 'CRUD',
              title: `File Read: ${eventData.path}`,
              detail: eventData.success ? 'Content retrieved' : 'Not found',
              status: eventData.success ? 'completed' : 'failed'
            });
          } else if (type === 'file_deleted') {
            setRelevantFiles(prev => Array.from(new Set([...prev, eventData.path])));
            const isApproval = eventData.status === 'approval_required';
            addActivity({
              type: 'CRUD',
              title: `File Deletion: ${eventData.path}`,
              detail: isApproval ? 'Paused: Approval Required by Security Policy' : 'File deleted',
              status: isApproval ? 'approval_required' : 'completed'
            });
          } else if (type === 'command_started') {
            addActivity({
              type: 'PROCESS',
              title: `Executing: ${eventData.command}`,
              status: 'running'
            });
          } else if (type === 'command_completed') {
            const code = eventData.exit_code;
            addActivity({
              type: 'PROCESS_RESULT',
              title: `Command Completed (Exit ${code})`,
              detail: eventData.stdout ? `stdout: ${eventData.stdout.trim()}` : (eventData.stderr ? `stderr: ${eventData.stderr.trim()}` : undefined),
              status: code === 0 ? 'completed' : 'failed'
            });
          } else if (type === 'validation_result') {
            setValidationResult(eventData);
            addActivity({
              type: 'VALIDATION',
              title: eventData.valid ? `PASS: ${eventData.reason}` : `FAIL: ${eventData.reason}`,
              status: eventData.valid ? 'completed' : 'failed'
            });
          } else if (type === 'run_completed') {
            evtSource.close();
            setRunStatus('completed');
            
            try {
              const finalRes = await fetch(`http://localhost:8000/api/runs/${data.run_id}`);
              if (finalRes.ok) {
                const finalData = await finalRes.json();
                setFinalResult(finalData.state || {});
                if (finalData.state?.artifacts) setArtifacts(finalData.state.artifacts);
              }
            } catch (e) {
              console.error(e);
            }
          } else if (type === 'run_failed') {
            evtSource.close();
            setRunStatus('failed');
            const safeNode = node || eventData?.node || 'execution';
            const safeMsg = eventData?.message || eventData?.error || 'Run failed unexpectedly.';
            setErrorInfo({
              node: safeNode,
              message: safeMsg,
              error_type: eventData?.error_type || 'ExecutionError'
            });
            addActivity({
              type: 'ERROR',
              title: `${safeNode.toUpperCase()} FAILED: ${safeMsg}`,
              status: 'failed'
            });
          }
        } catch (err) {
          console.error("Error parsing SSE frame:", err);
        }
      };
      
      evtSource.onerror = (err) => {
        console.error("SSE Error:", err);
        evtSource.close();
        setRunStatus('error');
        setErrorInfo({
          node: 'connection',
          message: 'Lost connection to backend execution stream.',
          error_type: 'SSEConnectionError'
        });
      };
      
    } catch (err: any) {
      setRunStatus('error');
      setErrorInfo({
        node: 'client',
        message: err.message || 'Error connecting to backend.',
        error_type: 'NetworkError'
      });
    }
  };

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setCommandModalOpen(prev => !prev);
      }
      if (e.key === "Escape") {
        setCommandModalOpen(false);
        setWorkspaceMenuOpen(false);
        setModeMenuOpen(false);
        setModelMenuOpen(false);
      }
      if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
        if (inputVal.trim()) {
          startRun();
        }
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [inputVal, runStatus]);

  const toggleSwitch = (key: 'web' | 'kb' | 'tools') => {
    setSwitches(prev => ({ ...prev, [key]: !prev[key] }));
  };

  const createNewConversation = () => {
    setRunId(null);
    setRunStatus('idle');
    setRunObjective('');
    setPlanSteps([]);
    setNodes({});
    setActivityStream([]);
    setRelevantFiles([]);
    setArtifacts([]);
    setValidationResult(null);
    setFinalResult(null);
    setErrorInfo(null);
    setView('conversation');
  };

  return (
    <>
      {/* TopHeader */}
      <header className="h-14 border-b-2 border-fra-black bg-fra-cream flex items-center justify-between px-3 flex-shrink-0 z-30 select-none">
        <div className="flex items-center space-x-4">
          <div className="flex items-center cursor-pointer group" onClick={() => setView('conversation')}>
            <span className="font-extrabold text-2xl tracking-tighter font-sans bg-black text-white px-2 py-0.5 mr-1">FRAIDAY_</span>
          </div>
          <div className="border-l-2 border-fra-black pl-3 text-[9px] leading-tight font-mono font-bold tracking-tight text-neutral-800 hidden md:block">
            WORKSPACE ROOT: <span className="text-black font-extrabold">{workspaceRoot}</span><br/>
            RUNTIME: <span className="text-fra-green font-extrabold">Python {runtimeInfo?.python?.version || "3.x"} READY</span> | Node.js {runtimeInfo?.node?.version ? `${runtimeInfo.node.version} READY` : "READY"}
          </div>
        </div>

        <nav className="hidden lg:flex items-center space-x-6 text-[11px] font-mono font-semibold">
          <button className={`hover:underline underline-offset-4 decoration-2 ${view === 'conversation' ? 'underline font-bold' : ''}`} onClick={() => setView('conversation')}>Workspace</button>
          <button className={`hover:underline underline-offset-4 decoration-2 ${view === 'runs' ? 'underline font-bold' : ''}`} onClick={() => setView('runs')}>Runs</button>
          <button className={`hover:underline underline-offset-4 decoration-2 ${view === 'agents' ? 'underline font-bold' : ''}`} onClick={() => setView('agents')}>Agents</button>
          <button className={`hover:underline underline-offset-4 decoration-2 ${view === 'tools' ? 'underline font-bold' : ''}`} onClick={() => setView('tools')}>Tools</button>
          {previewUrl && (
            <button
              onClick={() => setPreviewOpen(!previewOpen)}
              className={`px-2 py-0.5 border-2 border-black text-[10px] font-black flex items-center space-x-1 shadow-brutal-sm transition-all ${previewOpen ? 'bg-black text-fra-yellow' : 'bg-fra-yellow text-black hover:bg-yellow-400'}`}
            >
              <span>{previewOpen ? 'Hide Browser Preview' : 'Open Browser Preview'}</span>
              <span>↗</span>
            </button>
          )}
        </nav>

        <div className="flex items-center space-x-3">
          <div className="relative">
            <button className="flex items-center space-x-2 border-2 border-fra-black bg-fra-cream-card px-2.5 py-1 text-[11px] font-bold shadow-brutal hover:bg-fra-yellow transition-colors" onClick={() => setWorkspaceMenuOpen(!workspaceMenuOpen)}>
              <span className="text-xs font-mono font-black">[WS]</span>
              <div className="flex flex-col text-left leading-none">
                <span className="text-[9px] font-mono uppercase text-neutral-500 font-bold">WORKSPACE</span>
                <span>{workspace} v</span>
              </div>
            </button>
            {workspaceMenuOpen && (
              <div className="absolute right-0 mt-1 w-64 border-2 border-fra-black bg-fra-cream-card shadow-brutal z-50 py-1 font-mono">
                <div className="px-3 py-1.5 border-b border-neutral-300 text-[10px] text-neutral-500 uppercase font-bold">Configured Root</div>
                <div className="px-3 py-1 text-[10px] font-bold text-black break-all">{workspaceRoot}</div>
                <div className="border-t-2 border-fra-black my-1"></div>
                <button className="w-full text-left px-3 py-1.5 hover:bg-fra-yellow font-bold text-[11px] flex items-center justify-between" onClick={() => setWorkspaceMenuOpen(false)}>
                  <span>{workspace}</span>
                  <span className="text-[9px] bg-black text-white px-1">ACTIVE</span>
                </button>
              </div>
            )}
          </div>
          <div className="border-l-2 border-fra-black pl-3 text-[9px] font-mono leading-none tracking-widest uppercase font-bold hidden sm:flex flex-col justify-center text-neutral-800">
            <span>PLAN</span><span>ACT</span><span>OBSERVE</span><span>VALIDATE</span>
          </div>
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden">
        {/* LeftSidebar */}
        <aside className="w-64 bg-fra-sidebar text-white border-r-2 border-fra-black flex flex-col justify-between flex-shrink-0 select-none z-20">
          <div className="overflow-y-auto dark-scroll p-3 flex-1">
            <button className="w-full bg-fra-yellow text-fra-black font-extrabold text-[12px] py-2 px-3 border-2 border-black flex items-center justify-center space-x-2 shadow-brutal hover:bg-fra-yellow-hover transition-all mb-4" onClick={createNewConversation}>
              <span className="text-base leading-none font-black">+</span>
              <span>New Run Session</span>
            </button>
            
            <div className="space-y-1 mb-5 text-[11px] font-mono">
              <div className="flex items-center space-x-2 text-neutral-300 hover:text-white px-2 py-1.5 rounded cursor-pointer hover:bg-neutral-900 transition-colors" onClick={() => setView('conversation')}>
                <span className="font-bold text-neutral-500">[HIST]</span><span>Execution Workspace</span>
              </div>
              <div className="flex items-center space-x-2 text-neutral-300 hover:text-white px-2 py-1.5 rounded cursor-pointer hover:bg-neutral-900 transition-colors" onClick={() => alert('Scheduled Tasks: Standalone recurring cron jobs scheduled for Phase 5.')}>
                <span className="font-bold text-neutral-500">[CRON]</span><span>Scheduled Tasks</span>
              </div>
            </div>

            <div className="mb-5">
              <div className="flex items-center justify-between text-neutral-400 font-mono text-[10px] uppercase font-bold tracking-wider mb-2 px-1">
                <span>Workspace Context</span>
              </div>
              <div className="space-y-0.5 mb-2">
                <div className="flex items-center space-x-1.5 text-neutral-300 font-mono text-[11px] px-1 py-1 font-bold">
                  <span className="text-fra-yellow">{"//"}</span><span>{workspace}</span>
                </div>
                <div className="pl-4 space-y-0.5">
                  <div className="text-neutral-400 hover:text-white px-2 py-1 text-[10px] font-mono break-all truncate" title={workspaceRoot}>
                    {workspaceRoot}
                  </div>
                  {relevantFiles.length > 0 && (
                    <div className="pt-2 border-t border-neutral-800">
                      <div className="text-[9px] text-neutral-500 font-bold uppercase mb-1">Active Files</div>
                      {relevantFiles.map(f => (
                        <div key={f} className="text-fra-yellow text-[10px] font-mono truncate">
                          &gt; {f}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>

            <div className="mb-4 pt-3 border-t border-neutral-800">
              <div className="text-neutral-500 font-mono text-[10px] uppercase font-bold tracking-wider mb-2 px-1">Control Center</div>
              <div className="space-y-0.5 text-[11px] font-mono">
                <button className="w-full flex items-center justify-between text-neutral-300 hover:text-white px-2 py-1.5 hover:bg-neutral-900 rounded cursor-pointer" onClick={() => setView('runs')}>
                  <span className="flex items-center gap-2"><span>[RUNS]</span> Active Runs</span>
                  <span className="bg-neutral-800 text-neutral-300 px-1 rounded text-[10px]">{runId ? '#001' : '#000'}</span>
                </button>
                <button className="w-full flex items-center space-x-2 text-neutral-300 hover:text-white px-2 py-1.5 hover:bg-neutral-900 rounded cursor-pointer" onClick={() => setView('agents')}>
                  <span>[AGENT]</span> <span>5 Graph Nodes</span>
                </button>
                <button className="w-full flex items-center space-x-2 text-neutral-300 hover:text-white px-2 py-1.5 hover:bg-neutral-900 rounded cursor-pointer" onClick={() => setView('tools')}>
                  <span>[TOOL]</span> <span>Controlled Tools</span>
                </button>
              </div>
            </div>
          </div>

          <div className="p-3 border-t-2 border-fra-black bg-neutral-950 flex-shrink-0">
            <div className="border border-neutral-800 p-2 text-[9px] font-mono leading-tight uppercase text-neutral-400 tracking-wider">
              <span className="text-white font-bold block mb-1">&quot;SMALL EXECUTIONS COMPOUND INTO BIG THINGS.&quot;</span>
              <span className="text-[8px] text-fra-green font-bold">ACTION-ORIENTED RUNTIME ACTIVE</span>
            </div>
          </div>
        </aside>

        {/* MainContentArea */}
        <main className="flex-1 flex flex-col overflow-hidden bg-fra-cream">
          {view === 'conversation' && (
            <div className="flex-1 flex overflow-hidden">
              {/* Chat Stream */}
              <section className="flex-1 flex flex-col border-r-2 border-fra-black overflow-hidden bg-fra-cream">
                
                <div className="p-4 border-b-2 border-fra-black bg-fra-cream flex-shrink-0">
                  <div className="flex items-center justify-between mb-1.5">
                    <div className="flex items-center space-x-2 text-[11px] text-neutral-600 font-mono">
                      <span className="font-bold text-neutral-800">Fraiday</span>
                      <span>&gt;</span>
                      <span className="text-black font-semibold">Active Run</span>
                    </div>
                    {runId && <div className="text-[9px] font-bold bg-neutral-200 border border-neutral-300 px-1.5 py-0.5 font-mono">ID: {runId}</div>}
                  </div>
                </div>

                <div className="flex-1 overflow-y-auto p-4 space-y-6">
                  {runObjective && (
                    <div className="flex items-start justify-end max-w-2xl ml-auto">
                      <div className="bg-white border-2 border-fra-black p-3 shadow-brutal text-sm text-black font-mono">
                        {runObjective}
                      </div>
                    </div>
                  )}

                  {(runStatus !== 'idle') && (
                    runType === 'chat' ? (
                      <div className="flex items-start max-w-3xl animate-in fade-in duration-200">
                        <div className="w-8 h-8 rounded bg-black flex-shrink-0 mr-3 flex items-center justify-center text-white font-bold text-sm">F_</div>
                        <div className="flex-1 space-y-3">
                          {thoughts.length > 0 && (
                            <ThinkingView
                              thoughts={thoughts}
                              isThinking={runStatus === 'running' || runStatus === 'starting'}
                              elapsedSeconds={thinkingElapsed}
                              activeModel={`${model} (${provider.toUpperCase()})`}
                            />
                          )}

                          <div className="bg-white border-2 border-fra-black shadow-brutal p-4 text-sm font-sans leading-relaxed text-black whitespace-pre-wrap">
                            {chatMessage || (
                              <div className="flex items-center space-x-2 text-neutral-500 font-mono text-xs">
                                <span className="w-2 h-2 rounded-full bg-fra-yellow animate-ping" />
                                <span>frAIday is thinking...</span>
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    ) : (
                    <div className="flex items-start max-w-4xl">
                      <div className="w-8 h-8 rounded bg-black flex-shrink-0 mr-3 flex items-center justify-center text-white font-bold text-sm">F_</div>
                      <div className="flex-1 space-y-4">
                        
                        {/* Live Agentic Browser Preview Dock */}
                        {previewOpen && (
                          <BrowserPreview
                            url={previewUrl}
                            isOpen={previewOpen}
                            onClose={() => setPreviewOpen(false)}
                            title="frAIday Live Agentic Web Preview"
                          />
                        )}

                        {/* Antigravity-Style Thoughts View */}
                        <ThinkingView
                          thoughts={thoughts}
                          isThinking={runStatus === 'running' || runStatus === 'starting'}
                          elapsedSeconds={thinkingElapsed}
                          activeModel={`${model} (${provider.toUpperCase()})`}
                        />
                        {/* Clean Agent Output & Artifacts Card */}
                        <div className="bg-white border-2 border-fra-black shadow-brutal p-4 font-mono space-y-3">
                          <div className="flex items-center justify-between border-b-2 border-fra-black pb-2">
                            <div className="flex items-center space-x-2">
                              {runStatus === 'running' || runStatus === 'starting' ? (
                                <>
                                  <span className="bg-fra-yellow text-black font-extrabold px-1.5 py-0.5 text-[10px] border border-black animate-pulse">[RUNNING]</span>
                                  <span className="font-bold text-xs uppercase tracking-wider">Executing Objective</span>
                                </>
                              ) : runStatus === 'completed' ? (
                                <>
                                  <span className="bg-fra-green text-white font-extrabold px-1.5 py-0.5 text-[10px] border border-black">[COMPLETED]</span>
                                  <span className="font-bold text-xs uppercase tracking-wider">Objective Verified & Finished</span>
                                </>
                              ) : runStatus === 'error' ? (
                                <>
                                  <span className="bg-red-500 text-white font-extrabold px-1.5 py-0.5 text-[10px] border border-black">[FAILED]</span>
                                  <span className="font-bold text-xs uppercase tracking-wider">Execution Interrupted</span>
                                </>
                              ) : null}
                            </div>
                            
                            <button
                              onClick={() => setInspectorTab('planning')}
                              className="text-[10px] font-bold bg-neutral-100 hover:bg-fra-yellow border border-black px-2 py-0.5 transition-colors flex items-center space-x-1"
                            >
                              <span>View Planning</span>
                              <span>&rarr;</span>
                            </button>
                          </div>

                          {/* Running State with LatticeLoader */}
                          {(runStatus === 'running' || runStatus === 'starting') && (
                            <div className="py-4 flex flex-col items-center justify-center space-y-2 text-center bg-neutral-50 border border-neutral-200">
                              <LatticeLoader
                                status="working"
                                label="Executing autonomous workspace actions"
                                doneLabel="Completed in"
                                errorLabel="Halted"
                                pattern="orbit"
                                grid={3}
                                shape="round"
                                cellSize={6}
                                gap={2}
                                fontSize={12}
                                step={90}
                                showTimer
                              />
                              <span className="text-[10px] text-neutral-400">Live DAG and activity streaming in the Planning panel on the right</span>
                            </div>
                          )}

                          {/* Completed Message */}
                          {runStatus === 'completed' && (
                            <div className="space-y-3">
                              <div className="text-xs text-neutral-900 leading-relaxed">
                                {chatMessage ? (
                                  <div className="whitespace-pre-wrap">{chatMessage}</div>
                                ) : (
                                  <div>
                                    Autonomous execution completed successfully for objective:
                                    <div className="mt-1.5 p-2 bg-neutral-50 border border-neutral-200 font-bold text-black text-[11px]">
                                      &quot;{runObjective}&quot;
                                    </div>
                                  </div>
                                )}
                              </div>

                              {/* Web Preview Launcher Button if web files were touched */}
                              {artifacts.some(a => a.path?.endsWith('.html') || a.path?.endsWith('.htm')) && (
                                <div className="pt-2">
                                  <button
                                    onClick={() => {
                                      const htmlArt = artifacts.find(a => a.path?.endsWith('.html') || a.path?.endsWith('.htm'));
                                      if (htmlArt) {
                                        setPreviewUrl(`http://localhost:8000/api/preview/${htmlArt.path}`);
                                        setPreviewOpen(true);
                                      }
                                    }}
                                    className="bg-fra-yellow text-black border-2 border-black px-3 py-1.5 text-xs font-bold shadow-brutal-sm hover:bg-black hover:text-white transition-colors flex items-center space-x-2"
                                  >
                                    <span>Open in Live Browser Preview ↗</span>
                                  </button>
                                </div>
                              )}

                              {/* Generated / Touched Workspace Files */}
                              {artifacts.length > 0 && (
                                <div className="pt-2 border-t border-neutral-200">
                                  <span className="text-[10px] uppercase font-bold text-neutral-500 block mb-1">Generated / Modified Files:</span>
                                  <div className="flex flex-wrap gap-1.5">
                                    {artifacts.map((a, idx) => (
                                      <span key={idx} className="bg-neutral-100 border border-neutral-300 px-2 py-0.5 text-[10px] font-bold text-neutral-800">
                                        {a.path}
                                      </span>
                                    ))}
                                  </div>
                                </div>
                              )}
                            </div>
                          )}

                          {/* Error State */}
                          {runStatus === 'error' && (
                            <div className="p-3 bg-red-50 border border-red-300 text-red-900 space-y-1">
                              <div className="font-bold text-xs">{errorInfo?.message || "Execution encountered an error."}</div>
                              {errorInfo?.node && <div className="text-[10px] text-neutral-600">Failed at node: {errorInfo.node}</div>}
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                    )
                  )}
                </div>

                {/* BottomPromptDock */}
                <div className="p-3 border-t-2 border-fra-black bg-fra-cream flex-shrink-0">
                  {/* AI Thinking Bar */}
                  {(runStatus === 'starting' || runStatus === 'running') && (
                    <div className="mb-2 px-3 py-2 bg-black text-white border-2 border-black flex items-center justify-between shadow-brutal-sm">
                      <div className="flex items-center space-x-3">
                        <span className="bg-fra-yellow text-black font-extrabold px-1.5 py-0.5 text-[10px] font-mono border border-black">
                          AI AGENT
                        </span>
                        <LatticeLoader
                          status="working"
                          label="Thinking & reasoning..."
                          pattern="orbit"
                          grid={3}
                          shape="round"
                          color="#ffffff"
                          cellSize={6}
                          gap={2}
                          fontSize={12}
                          step={90}
                          idleOpacity={0.2}
                          glow={false}
                          showTimer
                        />
                      </div>
                      <div className="hidden sm:flex items-center space-x-2 text-[10px] font-mono text-neutral-400">
                        <span className="w-2 h-2 rounded-full bg-fra-yellow animate-ping" />
                        <span>Autonomous DAG execution in progress</span>
                      </div>
                    </div>
                  )}

                  <div className="border-2 border-fra-black bg-white shadow-brutal p-2 mb-2">
                    <textarea 
                      className="w-full text-xs font-mono border-0 focus:ring-0 resize-none p-1 text-black placeholder-neutral-500" 
                      placeholder="Enter instruction for autonomous execution in workspace..." 
                      rows={2}
                      value={inputVal}
                      onChange={(e) => setInputVal(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.ctrlKey && e.key === 'Enter') {
                          e.preventDefault();
                          startRun();
                        }
                      }}
                    ></textarea>
                    <div className="flex items-center justify-between pt-1 border-t border-neutral-200 mt-1">
                      <div className="flex items-center space-x-3 text-neutral-600 text-sm pl-1">
                        <button className="hover:text-black font-mono font-bold text-xs" onClick={() => setInputVal(prev => prev + ' ```\n\n```')}>&lt;/&gt;</button>
                      </div>
                      <div className="flex items-center space-x-2">
                        <span className="text-[10px] text-neutral-500 font-mono hidden sm:inline">Ctrl + Enter</span>
                        <button 
                          disabled={runStatus === 'starting' || runStatus === 'running'}
                          className={`px-4 py-1.5 text-xs font-bold border-2 border-black flex items-center space-x-1.5 shadow-brutal-sm ${runStatus === 'starting' || runStatus === 'running' ? 'bg-neutral-400 text-neutral-600 cursor-not-allowed' : 'bg-black text-white hover:bg-neutral-800'}`}
                          onClick={startRun}
                        >
                          <span>{runStatus === 'starting' || runStatus === 'running' ? 'Running...' : 'Send'}</span><span>-&gt;</span>
                        </button>
                      </div>
                    </div>
                  </div>
                  
                  <div className="flex flex-wrap items-center justify-between gap-2 text-[10px] font-mono">
                    <div className="flex flex-wrap items-center gap-2">
                      <div className="relative">
                        <button className="border-2 border-fra-black bg-white px-2.5 py-1 font-bold flex items-center space-x-1.5 shadow-brutal-sm hover:bg-neutral-100" onClick={() => { setModeMenuOpen(!modeMenuOpen); setModelMenuOpen(false); }}>
                          <span>Working Mode</span><span className="bg-fra-yellow px-1 py-0.2 border border-black">{mode}</span><span className="text-[8px]">v</span>
                        </button>
                        {modeMenuOpen && (
                          <div className="absolute bottom-8 left-0 w-60 bg-white border-2 border-fra-black shadow-brutal z-50 p-1 space-y-1">
                            {['Autonomous', 'Assisted', 'Planning', 'Review'].map(m => (
                              <div key={m} className="p-1.5 hover:bg-fra-yellow cursor-pointer border border-transparent hover:border-black flex items-center justify-between" onClick={() => { setMode(m); setModeMenuOpen(false); }}>
                                <div><div className="font-bold text-[11px]">{m}</div></div>
                                {mode === m && <span className="text-xs font-bold">[x]</span>}
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                      <div className="relative">
                        <button
                          className="border-2 border-fra-black bg-white px-2.5 py-1 font-bold flex items-center space-x-1.5 shadow-brutal-sm hover:bg-yellow-50/80 transition-colors"
                          onClick={() => setModelSelectorOpen(true)}
                        >
                          <span>Model</span>
                          <span className="font-bold text-black bg-fra-yellow px-1 border border-black">{model}</span>
                          <span className="text-[9px] bg-black text-white px-1 uppercase">{provider}</span>
                          <span className="text-[8px]">v</span>
                        </button>
                      </div>
                    </div>
                    
                    <div className="flex items-center space-x-2">
                      {(['web', 'kb', 'tools'] as const).map(key => (
                        <button key={key} className="border-2 border-fra-black bg-white px-2 py-1 font-bold flex items-center space-x-1.5 shadow-brutal-sm" onClick={() => toggleSwitch(key)}>
                          <span>{key === 'web' ? '[WEB] Search' : key === 'kb' ? '[KB] Knowledge' : '[TOOL] Tools'}</span>
                          <span className={`w-2.5 h-2.5 rounded-full border border-black ${switches[key] ? 'bg-fra-yellow' : 'bg-neutral-300'}`}></span>
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              </section>

              {/* RightInspectorPanel */}
              <aside className="w-96 bg-fra-cream border-l-2 border-fra-black flex flex-col overflow-y-auto select-none font-mono flex-shrink-0">
                <div className="grid grid-cols-4 border-b-2 border-fra-black text-[11px] font-bold text-center">
                  <button 
                    className={`py-2.5 border-r-2 border-fra-black font-extrabold transition-colors ${
                      inspectorTab === 'planning' ? 'bg-fra-yellow text-black' : 'bg-neutral-200 text-neutral-700 hover:bg-fra-yellow/50'
                    }`}
                    onClick={() => setInspectorTab('planning')}
                  >
                    Planning
                  </button>
                  <button 
                    className={`py-2.5 border-r-2 border-fra-black font-extrabold transition-colors ${
                      inspectorTab === 'context' ? 'bg-fra-yellow text-black' : 'bg-neutral-200 text-neutral-700 hover:bg-fra-yellow/50'
                    }`}
                    onClick={() => setInspectorTab('context')}
                  >
                    Context
                  </button>
                  <button 
                    className={`py-2.5 border-r-2 border-fra-black font-extrabold transition-colors ${
                      inspectorTab === 'files' ? 'bg-fra-yellow text-black' : 'bg-neutral-200 text-neutral-700 hover:bg-fra-yellow/50'
                    }`}
                    onClick={() => setInspectorTab('files')}
                  >
                    Files
                  </button>
                  <button 
                    className={`py-2.5 font-extrabold transition-colors ${
                      inspectorTab === 'artifacts' ? 'bg-fra-yellow text-black' : 'bg-neutral-200 text-neutral-700 hover:bg-fra-yellow/50'
                    }`}
                    onClick={() => setInspectorTab('artifacts')}
                  >
                    Artifacts
                  </button>
                </div>

                <div className="p-3 space-y-4 flex-1 overflow-y-auto">
                  
                  {/* PLANNING TAB */}
                  {inspectorTab === 'planning' && (
                    <div className="space-y-3">
                      {/* Agent Status Bar */}
                      <div className="border-2 border-fra-black bg-white p-2.5 shadow-brutal-sm">
                        <div className="flex items-center justify-between mb-2">
                          <span className="font-bold text-[11px] uppercase tracking-wider">Agent Telemetry</span>
                          {runStatus === 'running' || runStatus === 'starting' ? (
                            <span className="bg-fra-yellow text-black px-1.5 py-0.5 text-[9px] font-bold border border-black animate-pulse">[RUNNING]</span>
                          ) : runStatus === 'completed' ? (
                            <span className="bg-fra-green text-white px-1.5 py-0.5 text-[9px] font-bold border border-black">[COMPLETED]</span>
                          ) : runStatus === 'error' ? (
                            <span className="bg-red-500 text-white px-1.5 py-0.5 text-[9px] font-bold border border-black">[FAILED]</span>
                          ) : (
                            <span className="bg-neutral-200 text-neutral-600 px-1.5 py-0.5 text-[9px] font-bold border border-neutral-300">[IDLE]</span>
                          )}
                        </div>
                        <LatticeLoader
                          status={runStatus === 'running' || runStatus === 'starting' ? 'working' : runStatus === 'completed' ? 'done' : 'idle'}
                          label="Orchestrating Plan"
                          doneLabel="Executed in"
                          errorLabel="Halted after"
                          pattern="orbit"
                          grid={3}
                          shape="round"
                          cellSize={5}
                          gap={2}
                          fontSize={11}
                          step={90}
                          showTimer
                        />
                      </div>

                      {/* Execution Progress Nodes */}
                      <div className="border-2 border-fra-black bg-white p-2.5 shadow-brutal-sm">
                        <div className="font-bold text-[11px] uppercase tracking-wider mb-2">Execution Progress DAG</div>
                        <div className="grid grid-cols-2 gap-1.5 text-[10px]">
                          {['orchestrator', 'researcher', 'executor', 'validator', 'recovery'].map((node) => (
                            <div
                              key={node}
                              className={`border border-fra-black p-1.5 flex items-center justify-between ${
                                nodes[node] === 'running' ? 'bg-fra-yellow' : nodes[node] === 'completed' ? 'bg-green-50' : 'bg-neutral-50'
                              } ${node === 'recovery' ? 'col-span-2' : ''}`}
                            >
                              <span className="capitalize font-bold text-neutral-800">{node}</span>
                              <span className={`font-black ${
                                nodes[node] === 'completed' ? 'text-fra-green' :
                                nodes[node] === 'running' ? 'text-black animate-pulse' :
                                'text-neutral-400'
                              }`}>
                                {nodes[node] === 'completed' ? '[OK]' : nodes[node] === 'running' ? '[*]' : '[-]'}
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>

                      {/* Work Plan Checklist */}
                      <div className="border-2 border-fra-black bg-white p-2.5 shadow-brutal-sm">
                        <div className="flex items-center justify-between mb-2">
                          <span className="font-bold text-[11px] uppercase tracking-wider">Work Plan</span>
                          <span className="text-[9px] bg-neutral-200 px-1 border border-neutral-300">{planSteps.length} Steps</span>
                        </div>
                        {planSteps.length === 0 ? (
                          <div className="text-[10px] text-neutral-400 italic py-1">No active plan. Input a goal to synthesize.</div>
                        ) : (
                          <div className="space-y-2 text-[10px]">
                            {planSteps.map(step => (
                              <div key={step.id} className="border-b border-neutral-100 pb-1.5 flex items-start space-x-1.5">
                                <span className={`font-bold text-xs ${
                                  step.status === 'completed' ? 'text-fra-green' :
                                  step.status === 'running' ? 'text-fra-amber animate-spin' :
                                  'text-neutral-400'
                                }`}>
                                  {step.status === 'completed' ? '[x]' : step.status === 'running' ? '[*]' : '[-]'}
                                </span>
                                <div className="flex-1 min-w-0">
                                  <div className={`font-bold leading-snug ${step.status === 'pending' ? 'text-neutral-500' : 'text-black'}`}>
                                    {step.description}
                                  </div>
                                  {step.action && <div className="text-[8px] text-neutral-400 uppercase mt-0.5">Action: {step.action}</div>}
                                </div>
                                <span className="text-[8px] uppercase font-mono px-1 border border-neutral-200 text-neutral-500">{step.agent}</span>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>

                      {/* Agent Activity Stream */}
                      <div className="border-2 border-fra-black bg-white p-2.5 shadow-brutal-sm">
                        <div className="flex items-center justify-between mb-2">
                          <span className="font-bold text-[11px] uppercase tracking-wider">Activity Stream</span>
                          <span className="text-[9px] bg-neutral-200 px-1 border border-neutral-300">{activityStream.length} Events</span>
                        </div>
                        {activityStream.length === 0 ? (
                          <div className="text-[10px] text-neutral-400 italic py-1">Awaiting workspace events...</div>
                        ) : (
                          <div className="space-y-1.5 text-[10px] max-h-48 overflow-y-auto pr-1">
                            {activityStream.map((act) => (
                              <div key={act.id} className="border-l-2 border-fra-black pl-1.5 py-0.5">
                                <div className="flex items-center justify-between">
                                  <span className={`text-[8px] font-black px-1 border border-black ${
                                    act.status === 'approval_required' ? 'bg-orange-400 text-black' :
                                    act.status === 'completed' ? 'bg-fra-green text-white' :
                                    act.status === 'failed' ? 'bg-red-500 text-white' :
                                    'bg-fra-yellow text-black'
                                  }`}>
                                    {act.type}
                                  </span>
                                  <span className="text-[8px] text-neutral-400">{act.timestamp}</span>
                                </div>
                                <div className="font-bold text-neutral-900 text-[9px] mt-0.5 truncate" title={act.title}>{act.title}</div>
                                {act.detail && (
                                  <div className="text-[8px] text-neutral-600 bg-neutral-50 p-1 border border-neutral-200 break-all mt-0.5">
                                    {act.detail}
                                  </div>
                                )}
                              </div>
                            ))}
                          </div>
                        )}
                      </div>

                      {/* Validation Result Box */}
                      {validationResult && (
                        <div className={`border-2 border-fra-black p-2.5 shadow-brutal-sm text-[10px] ${
                          validationResult.status === 'approval_required' ? 'bg-orange-50 border-orange-600' :
                          validationResult.valid ? 'bg-green-50' : 'bg-red-50'
                        }`}>
                          <div className="font-bold uppercase tracking-wider mb-1">Validation Result</div>
                          <div className={`font-bold ${
                            validationResult.status === 'approval_required' ? 'text-orange-700' :
                            validationResult.valid ? 'text-fra-green' : 'text-red-600'
                          }`}>
                            {validationResult.status === 'approval_required' ? 'APPROVAL REQUIRED: ' : (validationResult.valid ? 'PASS: ' : 'FAIL: ')}
                            {validationResult.reason}
                          </div>
                        </div>
                      )}

                      {/* STDOUT output */}
                      {finalResult?.observations?.[0] && (
                        <div className="border-2 border-fra-black bg-black text-white p-2.5 shadow-brutal text-[9px] overflow-x-auto">
                          <div className="font-bold text-fra-yellow uppercase tracking-wider mb-1">
                            STDOUT [{finalResult.observations[0].filename || finalResult.observations[0].tool || "output"}]
                          </div>
                          <pre className="text-neutral-200 whitespace-pre-wrap max-h-32 overflow-y-auto">{finalResult.observations[0].stdout || '(empty)'}</pre>
                          <div className="font-bold text-neutral-400 mt-1 uppercase">
                            EXIT: {finalResult.observations[0].exit_code} | DURATION: {finalResult.observations[0].duration || 0}s
                          </div>
                        </div>
                      )}
                    </div>
                  )}

                  {/* CONTEXT TAB */}
                  {inspectorTab === 'context' && (
                    <div className="space-y-3">
                      <div className="border-2 border-fra-black bg-white p-3 shadow-brutal">
                        <div className="font-bold text-[11px] uppercase tracking-wider mb-2">RUN CONTEXT</div>
                        <div className="space-y-1.5 text-[10px]">
                          <div className="flex justify-between border-b border-neutral-200 pb-1">
                            <span className="text-neutral-600">WORKSPACE</span>
                            <span className="font-bold text-black">{workspace}</span>
                          </div>
                          <div className="flex justify-between border-b border-neutral-200 pb-1">
                            <span className="text-neutral-600">ROOT DIRECTORY</span>
                            <span className="font-bold text-black truncate max-w-[160px]" title={workspaceRoot}>{workspaceRoot}</span>
                          </div>
                          <div className="flex justify-between border-b border-neutral-200 pb-1">
                            <span className="text-neutral-600">ACTIVE RUNTIME</span>
                            <span className="font-bold text-fra-green">Python {runtimeInfo?.python?.version || "3.x"}</span>
                          </div>
                          <div className="pt-1">
                            <span className="text-neutral-600 block mb-1">RELEVANT FILES:</span>
                            {relevantFiles.length === 0 ? (
                              <span className="text-neutral-400 italic">None accessed yet</span>
                            ) : (
                              <div className="space-y-0.5">
                                {relevantFiles.map(f => (
                                  <div key={f} className="text-black font-bold bg-neutral-100 px-1 border border-neutral-300">
                                    {f}
                                  </div>
                                ))}
                              </div>
                            )}
                          </div>
                        </div>
                      </div>

                      <div className="border-2 border-fra-black bg-white p-3 shadow-brutal">
                        <div className="font-bold text-[11px] uppercase tracking-wider mb-2">WORKSPACE RUNTIME</div>
                        <div className="space-y-1.5 text-[10px]">
                          <div className="flex justify-between border-b border-neutral-200 pb-1">
                            <span className="text-neutral-600">Python Runtime</span>
                            <span className="font-bold text-fra-green">
                              {runtimeInfo?.python?.version ? `v${runtimeInfo.python.version} READY` : "READY"}
                            </span>
                          </div>
                          <div className="flex justify-between border-b border-neutral-200 pb-1">
                            <span className="text-neutral-600">Node.js Engine</span>
                            <span className="font-bold text-fra-green">
                              {runtimeInfo?.node?.version ? `v${runtimeInfo.node.version} READY` : "READY"}
                            </span>
                          </div>
                          <div className="flex justify-between border-b border-neutral-200 pb-1">
                            <span className="text-neutral-600">Git SCM</span>
                            <span className="font-bold text-fra-green">
                              {runtimeInfo?.git?.version ? `v${runtimeInfo.git.version} READY` : "READY"}
                            </span>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* FILES TAB */}
                  {inspectorTab === 'files' && (
                    <div className="space-y-3">
                      <div className="border-2 border-fra-black bg-white p-3 shadow-brutal">
                        <div className="flex items-center justify-between mb-2">
                          <span className="font-bold text-[11px] uppercase tracking-wider">Workspace Files</span>
                          <span className="text-[9px] bg-neutral-100 border border-neutral-300 px-1 font-bold">ROOT</span>
                        </div>
                        <div className="text-[10px] text-neutral-600 mb-2 truncate" title={workspaceRoot}>
                          📁 {workspaceRoot}
                        </div>
                        <div className="space-y-1 text-[10px]">
                          {artifacts.length > 0 ? (
                            artifacts.map((a, i) => (
                              <div key={i} className="flex items-center justify-between p-1 border border-neutral-200 bg-neutral-50 hover:bg-fra-yellow/30 cursor-pointer">
                                <span className="font-bold truncate">{a.path}</span>
                                <span className="text-[8px] bg-black text-white px-1">FILE</span>
                              </div>
                            ))
                          ) : (
                            <div className="text-neutral-400 italic text-[10px] py-1">
                              Files will appear here as they are generated or inspected.
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  )}

                  {/* ARTIFACTS TAB */}
                  {inspectorTab === 'artifacts' && (
                    <div className="space-y-3">
                      <div className="border-2 border-fra-black bg-white p-3 shadow-brutal">
                        <div className="font-bold text-[11px] uppercase tracking-wider mb-2">RUN ARTIFACTS</div>
                        {artifacts.length === 0 ? (
                          <div className="text-[10px] text-neutral-400 italic">No artifacts generated yet.</div>
                        ) : (
                          <div className="space-y-1.5 text-[10px]">
                            {artifacts.map((art, idx) => (
                              <div key={idx} className="flex items-center justify-between border border-black bg-white p-1.5">
                                <span className="font-bold truncate max-w-[180px]">{art.path}</span>
                                <div className="flex items-center space-x-1">
                                  <span className="text-[9px] uppercase font-bold bg-fra-yellow px-1 border border-black">{art.operation}</span>
                                  {(art.path?.endsWith('.html') || art.path?.endsWith('.htm')) && (
                                    <button
                                      onClick={() => {
                                        setPreviewUrl(`http://localhost:8000/api/preview/${art.path}`);
                                        setPreviewOpen(true);
                                      }}
                                      className="text-[9px] bg-black text-white px-1 hover:bg-fra-yellow hover:text-black font-bold border border-black"
                                    >
                                      PREVIEW ↗
                                    </button>
                                  )}
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  )}

                </div>

                <div className="p-3 border-t-2 border-fra-black bg-white">
                  <div className="font-bold text-[11px] uppercase tracking-wider mb-2">QUICK ACTIONS</div>
                  <div className="grid grid-cols-2 gap-2 text-[11px]">
                    <button className="border-2 border-fra-black bg-white p-2 font-bold shadow-brutal-sm hover:bg-fra-yellow flex items-center justify-center space-x-1" onClick={() => setView('runs')}>
                      <span>View Runs</span>
                    </button>
                    <button className="border-2 border-fra-black bg-white p-2 font-bold shadow-brutal-sm hover:bg-fra-yellow flex items-center justify-center space-x-1" onClick={() => alert('Files in: ' + workspaceRoot)}>
                      <span>Open Root</span>
                    </button>
                  </div>
                </div>
              </aside>
            </div>
          )}

          {view === 'runs' && (
            <div className="flex-1 flex overflow-hidden bg-fra-cream p-4 flex-col font-mono">
              <h1 className="text-3xl font-extrabold font-sans mb-4">RUNS</h1>
              <div className="border-2 border-fra-black bg-white p-4 shadow-brutal mb-4">
                <div className="text-xs text-neutral-600 mb-2 font-bold uppercase">Active Workspace Runs</div>
                {runId ? (
                  <div className="p-3 border-2 border-black bg-fra-cream-card flex justify-between items-center text-xs shadow-brutal">
                    <span className="font-bold font-mono">ID: {runId} | {runObjective}</span>
                    <LatticeLoader
                      status={runStatus === 'running' || runStatus === 'starting' ? 'working' : runStatus === 'completed' ? 'done' : 'error'}
                      label="Thinking"
                      doneLabel="Done in"
                      errorLabel="Failed after"
                      pattern="orbit"
                      grid={3}
                      shape="round"
                      doneColor="#22c55e"
                      errorColor="#ef4444"
                      cellSize={6}
                      gap={2}
                      fontSize={12}
                      step={90}
                      showTimer
                    />
                  </div>
                ) : (
                  <div className="text-neutral-500 text-xs italic">No runs active in current session. Enter an instruction in the Workspace to begin.</div>
                )}
              </div>
            </div>
          )}
          
          {view === 'agents' && (
            <div className="flex-1 flex overflow-hidden bg-fra-cream p-4 flex-col font-mono">
              <h1 className="text-3xl font-extrabold font-sans mb-4">AGENT GRAPH NODES</h1>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 text-xs">
                <div className="border-2 border-fra-black bg-white p-3 shadow-brutal">
                  <div className="font-bold text-sm mb-2">[ORCH] Orchestrator</div>
                  <p className="text-[10px] text-neutral-600 mb-3">Plans, decomposes, and coordinates the execution workflow.</p>
                </div>
                <div className="border-2 border-fra-black bg-white p-3 shadow-brutal">
                  <div className="font-bold text-sm mb-2">[RESEARCH] Researcher</div>
                  <p className="text-[10px] text-neutral-600 mb-3">Finds, reads, and synthesizes technical information.</p>
                </div>
                <div className="border-2 border-fra-black bg-fra-yellow p-3 shadow-brutal">
                  <div className="font-black text-sm mb-2">&gt;_ Executor</div>
                  <p className="text-[10px] font-semibold mb-3">Invokes controlled workspace tools (CRUD & commands) in real workspace.</p>
                </div>
                <div className="border-2 border-fra-black bg-white p-3 shadow-brutal">
                  <div className="font-bold text-sm mb-2">[VALID] Validator</div>
                  <p className="text-[10px] text-neutral-600 mb-3">Asserts exit codes, stdout outputs, and result correctness.</p>
                </div>
                <div className="border-2 border-fra-black bg-white p-3 shadow-brutal">
                  <div className="font-bold text-sm mb-2">[RECOV] Recovery</div>
                  <p className="text-[10px] text-neutral-600 mb-3">Checks for execution failures and recovery routes.</p>
                </div>
              </div>
            </div>
          )}

          {view === 'tools' && (
            <div className="flex-1 flex overflow-hidden bg-fra-cream p-4 flex-col font-mono">
              <h1 className="text-3xl font-extrabold font-sans mb-4">CONTROLLED WORKSPACE TOOLS</h1>
              <div className="grid grid-cols-2 gap-4 text-xs">
                <div className="border-2 border-black bg-white p-3 shadow-brutal">
                  <div className="font-bold mb-1">list_directory / read_file</div>
                  <p className="text-[10px] text-neutral-600 mb-2">Read files and directories inside workspace root with strict path containment.</p>
                  <span className="bg-green-100 text-green-800 border border-black px-1 text-[9px] font-bold">READY</span>
                </div>
                <div className="border-2 border-black bg-white p-3 shadow-brutal">
                  <div className="font-bold mb-1">create_file / update_file</div>
                  <p className="text-[10px] text-neutral-600 mb-2">Author and update source files with diff tracking and artifact emission.</p>
                  <span className="bg-green-100 text-green-800 border border-black px-1 text-[9px] font-bold">READY</span>
                </div>
                <div className="border-2 border-black bg-white p-3 shadow-brutal">
                  <div className="font-bold mb-1">run_command</div>
                  <p className="text-[10px] text-neutral-600 mb-2">Execute safe CLI commands (Python, Node, npm, git) with cwd = workspace_root.</p>
                  <span className="bg-green-100 text-green-800 border border-black px-1 text-[9px] font-bold">READY</span>
                </div>
                <div className="border-2 border-black bg-white p-3 shadow-brutal">
                  <div className="font-bold mb-1">delete_file</div>
                  <p className="text-[10px] text-neutral-600 mb-2">Destructive file operations governed by security policy requiring explicit approval.</p>
                  <span className="bg-orange-100 text-orange-800 border border-black px-1 text-[9px] font-bold">APPROVAL PROTECTED</span>
                </div>
              </div>
            </div>
          )}

        </main>
      </div>

      <footer className="h-6 border-t-2 border-fra-black bg-fra-cream px-3 flex items-center justify-between text-[10px] font-mono select-none flex-shrink-0 z-30">
        <div className="flex items-center space-x-3">
          <span className="font-bold">FRAIDAY v0.3.0</span><span>|</span><span className="text-neutral-700">{workspace} ({workspaceRoot})</span><span>|</span><span className="text-fra-green font-bold">Runtime Healthy</span>
        </div>
        <div className="font-bold uppercase tracking-widest text-neutral-800">IDEAS TODAY. EXECUTION TOMORROW.</div>
      </footer>

      {commandModalOpen && (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4 backdrop-blur-sm">
          <div className="w-full max-w-xl border-2 border-fra-black bg-fra-cream shadow-brutal-lg p-3 font-mono">
            <div className="flex items-center justify-between border-b-2 border-fra-black pb-2 mb-3">
              <span className="font-bold text-xs uppercase flex items-center gap-2"><span>[CMD]</span> Quick Navigator (Cmd + K)</span>
              <button className="font-black text-sm px-1.5 hover:bg-neutral-200" onClick={() => setCommandModalOpen(false)}>X</button>
            </div>
            <input autoFocus className="w-full border-2 border-fra-black bg-white p-2 text-xs font-mono mb-3 focus:outline-none shadow-brutal-sm" placeholder="Type to search..." type="text"/>
            <div className="space-y-1 text-xs">
              <div className="p-2 border border-black hover:bg-fra-yellow cursor-pointer flex justify-between items-center bg-white" onClick={() => { setView('conversation'); setCommandModalOpen(false); }}>
                <span className="font-bold">&gt; Active Workspace</span><span className="text-[9px] bg-black text-white px-1">ACTIVE</span>
              </div>
              <div className="p-2 border border-black hover:bg-fra-yellow cursor-pointer flex justify-between items-center bg-white" onClick={() => { setView('runs'); setCommandModalOpen(false); }}>
                <span>&gt; View All Runs</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Agentic Model Selector Modal */}
      <ModelSelectorModal
        isOpen={modelSelectorOpen}
        onClose={() => setModelSelectorOpen(false)}
        selectedModel={model}
        selectedProvider={provider}
        onSelect={(m, p) => {
          setModel(m);
          setProvider(p);
          setModelSelectorOpen(false);
        }}
      />
    </>
  );
}
