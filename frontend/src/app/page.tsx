"use client";
import React, { useState, useEffect, useRef } from "react";

interface ToolActivity {
  id: string;
  type: string;
  title: string;
  detail?: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'approval_required';
  timestamp: string;
}

interface ExecutionObs {
  tool?: string;
  action?: string;
  target?: string;
  filename?: string;
  command?: string;
  stdout?: string;
  stderr?: string;
  exit_code?: number;
  success?: boolean;
  duration?: number;
  summary?: string;
  detail?: string;
  kind?: string;
}

interface RunData {
  runId: string;
  conversationId: string;
  objective: string;
  status: 'starting' | 'running' | 'completed' | 'failed' | 'error';
  planSteps: any[];
  nodes: Record<string, string>;
  activityStream: ToolActivity[];
  relevantFiles: string[];
  artifacts: any[];
  observations: ExecutionObs[];
  validationResult: any;
  finalResult: any;
  errorInfo: { node?: string; message: string; error_type?: string } | null;
  selectedObsIndex: number;
}

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content?: string;
  timestamp?: string;
  runData?: RunData;
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
  const [model, setModel] = useState("qwen/qwen3.8-27b (Groq)");
  
  const [commandModalOpen, setCommandModalOpen] = useState(false);
  const [switches, setSwitches] = useState({ web: true, kb: true, tools: true });
  
  const [inputVal, setInputVal] = useState("");

  // --- CONVERSATION & MULTI-TURN STATE ---
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [activeRunId, setActiveRunId] = useState<string | null>(null);
  const [activeRunStatus, setActiveRunStatus] = useState<string>('idle');
  const chatScrollRef = useRef<HTMLDivElement>(null);

  // --- TERMINAL & RUNNER STATE ---
  const [terminalLogs, setTerminalLogs] = useState<Array<{ command: string; stdout?: string; stderr?: string; exit_code?: number; duration?: number; status?: string }>>([]);
  const [terminalInput, setTerminalInput] = useState("");
  const [terminalRunning, setTerminalRunning] = useState(false);
  const [previewInfo, setPreviewInfo] = useState<{ status: string; url?: string; main_file?: string }>({ status: 'stopped' });

  const fetchPreviewStatus = async () => {
    try {
      const res = await fetch("http://localhost:8000/api/workspace/preview/status");
      if (res.ok) {
        const data = await res.json();
        setPreviewInfo({ status: data.status, url: data.url });
      }
    } catch (e) {
      console.warn("Preview status check failed", e);
    }
  };

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
    fetchPreviewStatus();
  }, []);

  const handleRunCommand = async (cmdToRun?: string) => {
    const cmd = (cmdToRun || terminalInput).trim();
    if (!cmd || terminalRunning) return;
    if (!cmdToRun) setTerminalInput("");

    setTerminalRunning(true);
    const startEntry = { command: cmd, stdout: "Executing process in workspace...", exit_code: undefined };
    setTerminalLogs(prev => [...prev, startEntry]);

    try {
      const res = await fetch("http://localhost:8000/api/workspace/execute", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ command: cmd, timeout: 30, run_id: activeRunId || undefined })
      });
      const data = await res.json();
      setTerminalLogs(prev => prev.map(entry => entry.command === cmd && entry.stdout === "Executing process in workspace..." ? {
        command: cmd,
        stdout: data.stdout || (data.success ? "(process output empty)" : ""),
        stderr: data.stderr || "",
        exit_code: data.exit_code ?? (data.success ? 0 : 1),
        duration: data.duration || 0,
        status: data.success ? "success" : "failed"
      } : entry));
    } catch (e: any) {
      setTerminalLogs(prev => prev.map(entry => entry.command === cmd && entry.stdout === "Executing process in workspace..." ? {
        command: cmd,
        stdout: "",
        stderr: `Execution failed: ${e.message}`,
        exit_code: 1,
        duration: 0,
        status: "failed"
      } : entry));
    } finally {
      setTerminalRunning(false);
    }
  };

  const startPreviewServer = async (filename: string = "index.html") => {
    try {
      const res = await fetch("http://localhost:8000/api/workspace/preview/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ filename, run_id: activeRunId || undefined })
      });
      if (res.ok) {
        const data = await res.json();
        setPreviewInfo({ status: "running", url: data.preview_url || data.url, main_file: filename });
        setTerminalLogs(prev => [...prev, {
          command: `Starting application preview for ${filename}`,
          stdout: `Local HTTP server running at ${data.preview_url || data.url}\nApplication available for instant workspace preview.`,
          exit_code: 0,
          duration: 0.05,
          status: "success"
        }]);
      }
    } catch (e: any) {
      alert("Failed to start preview server: " + e.message);
    }
  };

  const stopPreviewServer = async () => {
    try {
      const res = await fetch("http://localhost:8000/api/workspace/preview/stop", {
        method: "POST"
      });
      if (res.ok) {
        setPreviewInfo({ status: "stopped" });
        setTerminalLogs(prev => [...prev, {
          command: "Stopping application preview server",
          stdout: "Server stopped successfully.",
          exit_code: 0,
          duration: 0.01,
          status: "success"
        }]);
      }
    } catch (e: any) {
      alert("Failed to stop preview server: " + e.message);
    }
  };

  useEffect(() => {
    if (chatScrollRef.current) {
      chatScrollRef.current.scrollTop = chatScrollRef.current.scrollHeight;
    }
  }, [messages]);

  const startRun = async () => {
    if (!inputVal.trim()) return;
    if (activeRunStatus === 'running' || activeRunStatus === 'starting') return;
    
    const objective = inputVal;
    setInputVal("");
    setActiveRunStatus('starting');

    const userMsgId = `usr_${Date.now()}`;
    const userMsg: ChatMessage = {
      id: userMsgId,
      role: 'user',
      content: objective,
      timestamp: new Date().toLocaleTimeString()
    };

    setMessages(prev => [...prev, userMsg]);
    
    try {
      const res = await fetch('http://localhost:8000/api/runs/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          objective,
          conversation_id: conversationId || undefined
        })
      });
      
      if (!res.ok) throw new Error('Failed to start run');
      const data = await res.json();
      
      const newRunId = data.run_id;
      const newConvId = data.conversation_id;
      setConversationId(newConvId);
      setActiveRunId(newRunId);
      setActiveRunStatus('running');

      const initialRunData: RunData = {
        runId: newRunId,
        conversationId: newConvId,
        objective,
        status: 'running',
        planSteps: [],
        nodes: {},
        activityStream: [],
        relevantFiles: [],
        artifacts: [],
        observations: [],
        validationResult: null,
        finalResult: null,
        errorInfo: null,
        selectedObsIndex: 0
      };

      const asstMsgId = `asst_${newRunId}`;
      const asstMsg: ChatMessage = {
        id: asstMsgId,
        role: 'assistant',
        runData: initialRunData
      };

      setMessages(prev => [...prev, asstMsg]);
      
      let isFinished = false;
      const evtSource = new EventSource(`http://localhost:8000/api/runs/${newRunId}/events`);
      
      evtSource.onmessage = async (event) => {
        try {
          const payload = JSON.parse(event.data);
          const { event: type, node, data: eventData } = payload;

          setMessages(prev => prev.map(msg => {
            if (msg.id !== asstMsgId || !msg.runData) return msg;
            const rd = { ...msg.runData };
            const newStream = [...rd.activityStream];
            
            const addAct = (item: Omit<ToolActivity, 'id' | 'timestamp'>) => {
              newStream.push({
                ...item,
                id: Math.random().toString(36).substring(2, 9),
                timestamp: new Date().toLocaleTimeString()
              });
            };

            if (type === 'context_loaded') {
              addAct({
                type: 'CONTEXT',
                title: `Workspace Context Initialized: ${eventData.workspace?.name || 'Fraiday'}`,
                detail: `Root: ${eventData.workspace?.root_path || workspaceRoot} | History turns: ${eventData.conversation_turns || 0}`,
                status: 'completed'
              });
            } else if (type === 'node_started') {
              rd.nodes = { ...rd.nodes, [node]: 'running' };
            } else if (type === 'node_completed') {
              rd.nodes = { ...rd.nodes, [node]: 'completed' };
            } else if (type === 'agent_thinking') {
              addAct({
                type: (node || 'AGENT').toUpperCase(),
                title: eventData?.summary || 'Processing...',
                status: 'completed'
              });
            } else if (type === 'plan_created') {
              rd.planSteps = eventData?.steps || [];
              addAct({
                type: 'PLAN',
                title: `Action Plan Generated: ${eventData?.steps?.length || 0} operational steps`,
                status: 'completed'
              });
            } else if (type === 'step_started') {
              rd.planSteps = rd.planSteps.map(s => s.id === eventData.step_id ? { ...s, status: 'running' } : s);
            } else if (type === 'step_completed') {
              rd.planSteps = rd.planSteps.map(s => s.id === eventData.step_id ? { ...s, status: 'completed' } : s);
            } else if (type === 'tool_call_started') {
              addAct({
                type: 'ACTION',
                title: `Invoking Tool: ${eventData.tool?.toUpperCase()}`,
                detail: eventData.path ? `Target: ${eventData.path}` : (eventData.command ? `Command: ${eventData.command}` : undefined),
                status: 'running'
              });
            } else if (type === 'tool_call_completed') {
              const isSuccess = eventData.success !== false;
              const isApproval = eventData.status === 'approval_required';
              addAct({
                type: 'RESULT',
                title: `Tool Result: ${eventData.tool?.toUpperCase()}`,
                detail: isApproval ? `APPROVAL REQUIRED: ${eventData.reason}` : (isSuccess ? 'Success' : `Error: ${typeof eventData.error === 'object' && eventData.error !== null ? (eventData.error.message || JSON.stringify(eventData.error)) : (eventData.error || eventData.reason)}`),
                status: isApproval ? 'approval_required' : (isSuccess ? 'completed' : 'failed')
              });
            } else if (type === 'file_created') {
              rd.relevantFiles = Array.from(new Set([...rd.relevantFiles, eventData.path]));
              rd.artifacts = [...rd.artifacts, { path: eventData.path, operation: 'created', type: 'file' }];
              addAct({
                type: 'CRUD',
                title: `File Created: ${eventData.path}`,
                detail: `${eventData.lines || 0} lines written to workspace`,
                status: 'completed'
              });
            } else if (type === 'file_updated') {
              rd.relevantFiles = Array.from(new Set([...rd.relevantFiles, eventData.path]));
              rd.artifacts = [...rd.artifacts, { path: eventData.path, operation: 'updated', type: 'file' }];
              addAct({
                type: 'CRUD',
                title: `File Updated: ${eventData.path}`,
                detail: `Diff: ${eventData.diff || 'Modified'} (${eventData.lines || 0} lines)`,
                status: 'completed'
              });
            } else if (type === 'file_read') {
              rd.relevantFiles = Array.from(new Set([...rd.relevantFiles, eventData.path]));
              addAct({
                type: 'CRUD',
                title: `File Read: ${eventData.path}`,
                detail: eventData.success ? 'Content retrieved' : 'Not found',
                status: eventData.success ? 'completed' : 'failed'
              });
            } else if (type === 'file_deleted') {
              rd.relevantFiles = Array.from(new Set([...rd.relevantFiles, eventData.path]));
              const isApproval = eventData.status === 'approval_required';
              addAct({
                type: 'CRUD',
                title: `File Deletion: ${eventData.path}`,
                detail: isApproval ? 'Paused: Approval Required by Security Policy' : 'File deleted',
                status: isApproval ? 'approval_required' : 'completed'
              });
            } else if (type === 'command_started') {
              addAct({
                type: 'PROCESS',
                title: `Executing: ${eventData.command}`,
                status: 'running'
              });
            } else if (type === 'command_completed') {
              const code = eventData.exit_code;
              addAct({
                type: 'PROCESS_RESULT',
                title: `Command Completed (Exit ${code})`,
                detail: eventData.stdout ? `stdout: ${eventData.stdout.trim()}` : (eventData.stderr ? `stderr: ${eventData.stderr.trim()}` : undefined),
                status: code === 0 ? 'completed' : 'failed'
              });
              // Append command execution observation directly
              const cmdObs: ExecutionObs = {
                tool: 'run_command',
                action: 'RUN_COMMAND',
                command: eventData.command,
                stdout: eventData.stdout || '',
                stderr: eventData.stderr || '',
                exit_code: eventData.exit_code ?? 0,
                duration: eventData.duration || 0,
                success: code === 0
              };
              rd.observations = [...rd.observations, cmdObs];
            } else if (type === 'server_started' || type === 'preview_started') {
              const url = eventData?.url || eventData?.preview_url || `http://localhost:${eventData?.port || 5500}`;
              setPreviewInfo({
                status: 'running',
                url: url,
                main_file: eventData?.target || eventData?.filename || 'ecommerce.html'
              });
              addAct({
                type: 'PROCESS',
                title: `Application Server Running at ${url}`,
                detail: `Port ${eventData?.port || 5500} | PID ${eventData?.pid || 'managed'}`,
                status: 'completed'
              });
            } else if (type === 'server_stopped' || type === 'preview_stopped') {
              setPreviewInfo({ status: 'stopped' });
              addAct({
                type: 'PROCESS',
                title: 'Application Server Stopped',
                status: 'completed'
              });
            } else if (type === 'observation_created') {
              if (eventData && typeof eventData === 'object') {
                rd.observations = [...rd.observations, eventData];
              }
            } else if (type === 'validation_result') {
              rd.validationResult = eventData;
              addAct({
                type: 'VALIDATION',
                title: eventData.valid ? `PASS: ${eventData.reason}` : `FAIL: ${eventData.reason}`,
                status: eventData.valid ? 'completed' : 'failed'
              });
            } else if (type === 'run_completed') {
              isFinished = true;
              evtSource.close();
              rd.status = 'completed';
              setActiveRunStatus('completed');
              fetch(`http://localhost:8000/api/runs/${newRunId}`)
                .then(r => r.json())
                .then(finalData => {
                  setMessages(mPrev => mPrev.map(m => {
                    if (m.id !== asstMsgId || !m.runData) return m;
                    const finalState = finalData.state || {};
                    const mergedObs = [...(m.runData.observations || []), ...(finalState.observations || [])];
                    // Deduplicate observations by command/action/summary
                    const uniqueObs: ExecutionObs[] = [];
                    const seen = new Set();
                    for (const o of mergedObs) {
                      const key = `${o.action || o.tool}_${o.command || o.target}_${o.stdout}_${o.stderr}`;
                      if (!seen.has(key)) {
                        seen.add(key);
                        uniqueObs.push(o);
                      }
                    }
                    return {
                      ...m,
                      runData: {
                        ...m.runData,
                        status: 'completed',
                        finalResult: finalState,
                        artifacts: finalState.artifacts || m.runData.artifacts,
                        observations: uniqueObs.length > 0 ? uniqueObs : m.runData.observations
                      }
                    };
                  }));
                })
                .catch(err => console.error(err));
            } else if (type === 'run_failed') {
              isFinished = true;
              evtSource.close();
              rd.status = 'failed';
              setActiveRunStatus('failed');
              const safeNode = node || eventData?.node || 'execution';
              const safeMsg = eventData?.message || eventData?.error || 'Run failed unexpectedly.';
              rd.errorInfo = {
                node: safeNode,
                message: safeMsg,
                error_type: eventData?.error_type || 'ExecutionError'
              };
              addAct({
                type: 'ERROR',
                title: `${safeNode.toUpperCase()} FAILED: ${safeMsg}`,
                status: 'failed'
              });
            }

            rd.activityStream = newStream;
            return { ...msg, runData: rd };
          }));
        } catch (err) {
          console.error("Error parsing SSE frame:", err);
        }
      };
      
      evtSource.onerror = (err) => {
        evtSource.close();
        if (isFinished) {
          return;
        }
        setMessages(prev => prev.map(msg => {
          if (msg.id !== asstMsgId || !msg.runData) return msg;
          if (msg.runData.status === 'completed' || msg.runData.status === 'failed') {
            return msg;
          }
          setActiveRunStatus('error');
          return {
            ...msg,
            runData: {
              ...msg.runData,
              status: 'error',
              errorInfo: {
                node: 'connection',
                message: 'Lost connection to backend execution stream.',
                error_type: 'SSEConnectionError'
              }
            }
          };
        }));
      };
      
    } catch (err: any) {
      setActiveRunStatus('error');
      alert(err.message || 'Error connecting to backend.');
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
  }, [inputVal, activeRunStatus, conversationId]);

  const toggleSwitch = (key: 'web' | 'kb' | 'tools') => {
    setSwitches(prev => ({ ...prev, [key]: !prev[key] }));
  };

  const createNewConversation = () => {
    setConversationId(null);
    setMessages([]);
    setActiveRunId(null);
    setActiveRunStatus('idle');
    setInputVal('');
    setView('conversation');
  };

  const setSelectedObsForRun = (asstMsgId: string, index: number) => {
    setMessages(prev => prev.map(m => {
      if (m.id !== asstMsgId || !m.runData) return m;
      return {
        ...m,
        runData: {
          ...m.runData,
          selectedObsIndex: index
        }
      };
    }));
  };

  // Helper to extract active relevant files from messages
  const currentRelevantFiles = Array.from(new Set(
    messages.flatMap(m => m.runData?.relevantFiles || [])
  ));

  // Helper to extract active artifacts from messages
  const currentArtifacts = messages.flatMap(m => m.runData?.artifacts || []);

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
              <span>New Conversation</span>
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
                {conversationId && (
                  <span className="text-fra-yellow font-bold text-[9px] uppercase font-mono">{conversationId}</span>
                )}
              </div>
              <div className="space-y-0.5 mb-2">
                <div className="flex items-center space-x-1.5 text-neutral-300 font-mono text-[11px] px-1 py-1 font-bold">
                  <span className="text-fra-yellow">{"//"}</span><span>{workspace}</span>
                </div>
                <div className="pl-4 space-y-0.5">
                  <div className="text-neutral-400 hover:text-white px-2 py-1 text-[10px] font-mono break-all truncate" title={workspaceRoot}>
                    {workspaceRoot}
                  </div>
                  {currentRelevantFiles.length > 0 && (
                    <div className="pt-2 border-t border-neutral-800">
                      <div className="text-[9px] text-neutral-500 font-bold uppercase mb-1">Active Files</div>
                      {currentRelevantFiles.map(f => (
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
                <button className="w-full flex items-center space-x-2 text-neutral-300 hover:text-white px-2 py-1.5 hover:bg-neutral-900 rounded cursor-pointer" onClick={() => setView('terminal')}>
                  <span>[TERM]</span> <span>Integrated Terminal</span>
                </button>
                <button className="w-full flex items-center justify-between text-neutral-300 hover:text-white px-2 py-1.5 hover:bg-neutral-900 rounded cursor-pointer" onClick={() => setView('runs')}>
                  <span className="flex items-center gap-2"><span>[RUNS]</span> Active Runs</span>
                  <span className="bg-neutral-800 text-neutral-300 px-1 rounded text-[10px]">{messages.filter(m => m.role === 'assistant').length} Runs</span>
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
          {previewInfo.status === 'running' && (
            <div className="bg-neutral-950 text-white p-2 px-4 border-b-2 border-fra-black flex items-center justify-between font-mono text-xs flex-shrink-0 z-30">
              <div className="flex items-center space-x-3 truncate">
                <span className="bg-fra-green text-black font-extrabold px-1.5 py-0.5 text-[9px] uppercase border border-black animate-pulse">● RUNNING</span>
                <span className="font-bold text-fra-yellow">APPLICATION: {previewInfo.main_file || 'Web Application'}</span>
                <span className="text-neutral-400 font-normal truncate hidden md:inline">URL: {previewInfo.url}</span>
              </div>
              <div className="flex items-center space-x-2">
                {previewInfo.url && (
                  <a href={previewInfo.url} target="_blank" rel="noopener noreferrer" className="bg-fra-yellow text-black font-bold px-2.5 py-1 text-[10px] border border-black hover:bg-yellow-400 text-decoration-none">
                    [ Open Preview ]
                  </a>
                )}
                <button onClick={stopPreviewServer} className="bg-red-500 text-white font-bold px-2.5 py-1 text-[10px] border border-black hover:bg-red-600">
                  [ Stop ]
                </button>
              </div>
            </div>
          )}

          {view === 'terminal' && (
            <div className="flex-1 flex overflow-hidden bg-neutral-950 text-white p-4 flex-col font-mono">
              <div className="flex items-center justify-between border-b border-neutral-800 pb-3 mb-3 flex-shrink-0">
                <div className="flex items-center space-x-3">
                  <h1 className="text-xl font-extrabold text-fra-yellow font-sans tracking-tight">INTEGRATED FRAIDAY TERMINAL</h1>
                  <span className="bg-neutral-800 text-neutral-300 text-[10px] px-2 py-0.5 font-bold border border-neutral-700">Controlled Execution Sandbox</span>
                </div>
                <button className="bg-neutral-800 hover:bg-neutral-700 text-white text-xs px-2.5 py-1 font-bold border border-neutral-600" onClick={() => setTerminalLogs([])}>
                  Clear Output
                </button>
              </div>

              <div className="flex-1 overflow-y-auto bg-black border border-neutral-800 p-4 space-y-4 text-xs font-mono mb-3 shadow-inner">
                {terminalLogs.length === 0 ? (
                  <div className="text-neutral-500 italic space-y-2">
                    <p className="text-fra-yellow font-bold">&gt; Fraiday Workspace Terminal / Execution Runner</p>
                    <p>Enter any CLI command below (e.g. &quot;python hello.py&quot;, &quot;node hello.js&quot;, &quot;javac Hello.java&quot;) or run generated artifacts directly from the Files/Artifacts inspector.</p>
                    <p className="text-[10px] text-neutral-600">All commands execute within workspace root sandbox with full command policy & safety verification.</p>
                  </div>
                ) : (
                  terminalLogs.map((log, idx) => (
                    <div key={idx} className="border-l-2 border-fra-yellow pl-3 py-1 bg-neutral-900/50 p-2">
                      <div className="flex items-center justify-between text-neutral-400 font-bold mb-1">
                        <span className="text-white">&gt; {log.command}</span>
                        {log.exit_code !== undefined && (
                          <span className={log.exit_code === 0 ? "text-fra-green font-bold text-[10px]" : "text-red-400 font-bold text-[10px]"}>
                            EXIT CODE: {log.exit_code} {log.duration ? `(${log.duration}s)` : ""}
                          </span>
                        )}
                      </div>
                      {log.stdout && (
                        <pre className="text-neutral-200 whitespace-pre-wrap font-mono text-[11px] leading-relaxed mb-1">{log.stdout}</pre>
                      )}
                      {log.stderr && (
                        <pre className="text-red-300 whitespace-pre-wrap font-mono text-[11px] leading-relaxed border-t border-neutral-800 pt-1 mt-1">{log.stderr}</pre>
                      )}
                    </div>
                  ))
                )}
              </div>

              <div className="flex items-center space-x-2 bg-neutral-900 border border-neutral-700 p-2 flex-shrink-0">
                <span className="text-fra-yellow font-bold text-sm pl-1">&gt;</span>
                <input
                  type="text"
                  className="flex-1 bg-transparent text-white font-mono text-xs focus:outline-none placeholder-neutral-500"
                  placeholder="Type command to execute in workspace (e.g. python hello.py)..."
                  value={terminalInput}
                  onChange={(e) => setTerminalInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault();
                      handleRunCommand();
                    }
                  }}
                />
                <button
                  disabled={terminalRunning}
                  className={`px-4 py-1.5 text-xs font-bold border border-black ${terminalRunning ? 'bg-neutral-600 text-neutral-400 cursor-not-allowed' : 'bg-fra-yellow text-black hover:bg-yellow-400'}`}
                  onClick={() => handleRunCommand()}
                >
                  {terminalRunning ? 'Running...' : 'Run'}
                </button>
              </div>
            </div>
          )}

          {view === 'conversation' && (
            <div className="flex-1 flex overflow-hidden">
              {/* Chat Stream */}
              <section className="flex-1 flex flex-col border-r-2 border-fra-black overflow-hidden bg-fra-cream">
                
                <div className="p-4 border-b-2 border-fra-black bg-fra-cream flex-shrink-0">
                  <div className="flex items-center justify-between mb-1.5">
                    <div className="flex items-center space-x-2 text-[11px] text-neutral-600 font-mono">
                      <span className="font-bold text-neutral-800">Fraiday</span>
                      <span>&gt;</span>
                      <span className="text-black font-semibold">Active Conversation</span>
                    </div>
                    {conversationId && <div className="text-[9px] font-bold bg-fra-yellow border border-black px-1.5 py-0.5 font-mono">CONV: {conversationId}</div>}
                  </div>
                </div>

                {/* CHRONOLOGICAL CONVERSATION VIEWPORT */}
                <div ref={chatScrollRef} className="flex-1 overflow-y-auto p-4 space-y-6">
                  {messages.length === 0 ? (
                    <div className="flex flex-col items-center justify-center h-full text-center p-8 font-mono">
                      <div className="w-12 h-12 bg-black text-white font-black text-xl flex items-center justify-center mb-3 shadow-brutal">F_</div>
                      <h2 className="text-lg font-bold text-black font-sans uppercase tracking-tight mb-1">Fraiday Autonomous Execution Agent</h2>
                      <p className="text-xs text-neutral-600 max-w-md">Submit any high-level objective. Fraiday will research, generate executable plans, invoke real workspace tools, observe subprocess outputs, and validate results autonomously.</p>
                    </div>
                  ) : (
                    messages.map((msg) => {
                      if (msg.role === 'user') {
                        return (
                          <div key={msg.id} className="flex items-start justify-end max-w-2xl ml-auto">
                            <div className="bg-white border-2 border-fra-black p-3 shadow-brutal text-sm text-black font-mono">
                              <div className="text-[9px] font-bold text-neutral-400 uppercase mb-1">USER INSTRUCTION</div>
                              {msg.content}
                            </div>
                          </div>
                        );
                      }

                      const rd = msg.runData;
                      if (!rd) return null;

                      // Extract observations for output inspection.
                      // Only include genuine command-execution observations (RUN_COMMAND).
                      // Do NOT include LIST_DIRECTORY/READ_FILE even though they have exit_code defined.
                      const allObs = rd.observations || [];
                      const procObs = allObs.filter(o =>
                        o.action === 'RUN_COMMAND' ||
                        o.tool === 'run_command' ||
                        (o.command && o.action !== 'LIST_DIRECTORY' && o.action !== 'READ_FILE' && o.action !== 'CREATE_FILE' && o.action !== 'UPDATE_FILE')
                      );
                      const displayObsList = procObs.length > 0 ? procObs : allObs;
                      const selectedObsIndex = Math.min(rd.selectedObsIndex || 0, Math.max(0, displayObsList.length - 1));
                      const activeObs = displayObsList[selectedObsIndex] || (allObs.length > 0 ? allObs[0] : null);

                      return (
                        <div key={msg.id} className="flex items-start max-w-3xl">
                          <div className="w-8 h-8 rounded bg-black flex-shrink-0 mr-3 flex items-center justify-center text-white font-bold text-sm">F_</div>
                          <div className="flex-1">
                            <div className="bg-fra-cream-card border-2 border-fra-black shadow-brutal">
                              
                              <div className="flex items-center justify-between p-3 border-b-2 border-fra-black bg-white">
                                <div className="flex items-center space-x-2">
                                  <span className="font-bold text-[11px] uppercase tracking-wider font-mono">Execution Status</span>
                                  <span className="text-[9px] font-mono text-neutral-500">ID: {rd.runId}</span>
                                </div>
                                {rd.status === 'running' || rd.status === 'starting' ? (
                                    <span className="bg-fra-yellow px-2 py-0.5 text-[10px] font-bold border border-black animate-pulse">[RUNNING]</span>
                                ) : rd.status === 'completed' ? (
                                    <span className="bg-fra-green text-white px-2 py-0.5 text-[10px] font-bold border border-black">[COMPLETED]</span>
                                ) : (
                                    <span className="bg-red-500 text-white px-2 py-0.5 text-[10px] font-bold border border-black">[FAILED]</span>
                                )}
                              </div>

                              <div className="p-4 space-y-5">
                                
                                {/* Execution Graph Progress */}
                                <div className="border-2 border-fra-black bg-white p-3 shadow-brutal-sm">
                                  <div className="font-bold text-[11px] uppercase tracking-wider mb-3 font-mono">Execution Progress</div>
                                  <div className="flex flex-wrap items-center gap-2 text-[10px] font-mono">
                                    {['orchestrator', 'researcher', 'executor', 'validator', 'recovery'].map((node, i, arr) => (
                                      <React.Fragment key={node}>
                                        <div className={`flex-1 min-w-[100px] border-2 border-fra-black p-2 shadow-brutal-sm ${rd.nodes[node] === 'running' ? 'bg-fra-yellow' : 'bg-white'}`}>
                                          <div className={`flex items-center space-x-1 font-bold ${rd.nodes[node] === 'completed' ? 'text-fra-green' : 'text-fra-black'}`}>
                                            {rd.nodes[node] === 'completed' ? <span>[OK]</span> : rd.nodes[node] === 'running' ? <span className="animate-pulse">[*]</span> : <span>[-]</span>}
                                            <span className="capitalize">{node}</span>
                                          </div>
                                        </div>
                                        {i < arr.length - 1 && <div className="font-bold text-neutral-400">-&gt;</div>}
                                      </React.Fragment>
                                    ))}
                                  </div>
                                </div>

                                {/* AGENT ACTIVITY STREAM */}
                                <div className="border-2 border-fra-black bg-white p-3 shadow-brutal-sm">
                                  <div className="flex items-center justify-between mb-2">
                                    <span className="font-bold text-[11px] uppercase tracking-wider font-mono">Agent Activity Stream</span>
                                    <span className="text-[9px] font-mono bg-neutral-200 px-1 border border-neutral-300">{rd.activityStream.length} Events</span>
                                  </div>
                                  {rd.activityStream.length === 0 ? (
                                    <div className="text-xs text-neutral-500 italic font-mono">Waiting for activity...</div>
                                  ) : (
                                    <div className="space-y-2 font-mono text-xs max-h-64 overflow-y-auto pr-1">
                                      {rd.activityStream.map((act) => (
                                        <div key={act.id} className="border-l-2 border-fra-black pl-2 py-0.5">
                                          <div className="flex items-center justify-between">
                                            <div className="flex items-center space-x-2">
                                              <span className={`text-[9px] font-black px-1 border border-black ${
                                                act.status === 'approval_required' ? 'bg-orange-400 text-black' :
                                                act.status === 'completed' ? 'bg-fra-green text-white' :
                                                act.status === 'failed' ? 'bg-red-500 text-white' :
                                                'bg-fra-yellow text-black animate-pulse'
                                              }`}>
                                                {act.type}
                                              </span>
                                              <span className="font-bold text-neutral-900">{act.title}</span>
                                            </div>
                                            <span className="text-[9px] text-neutral-400">{act.timestamp}</span>
                                          </div>
                                          {act.detail && (
                                            <div className="text-[10px] text-neutral-600 pl-1 mt-0.5 bg-neutral-50 p-1 border border-neutral-200 break-all">
                                              {act.detail}
                                            </div>
                                          )}
                                        </div>
                                      ))}
                                    </div>
                                  )}
                                </div>

                                {/* WORK PLAN */}
                                <div className="border-2 border-fra-black bg-white p-3 shadow-brutal-sm">
                                  <div className="font-bold text-[11px] uppercase tracking-wider mb-3 font-mono">Work Plan</div>
                                  {rd.planSteps.length === 0 ? (
                                    <div className="text-xs text-neutral-500 italic font-mono">Waiting for orchestrator...</div>
                                  ) : (
                                    <div className="space-y-2.5 font-mono text-[11px]">
                                      {rd.planSteps.map(step => (
                                        <div key={step.id} className="border-b border-neutral-100 pb-1.5 flex items-start justify-between">
                                          <div className="flex items-start space-x-2">
                                            <span className={`font-bold ${
                                              step.status === 'completed' ? 'text-fra-green' :
                                              step.status === 'running' ? 'text-fra-amber animate-spin' :
                                              'text-neutral-400'
                                            }`}>
                                              {step.status === 'completed' ? '[x]' : step.status === 'running' ? '[*]' : '[-]'}
                                            </span>
                                            <div>
                                              <div className={`font-bold ${step.status === 'pending' ? 'text-neutral-500' : 'text-black'}`}>
                                                {step.description}
                                              </div>
                                              {step.action && <div className="text-[9px] text-neutral-400 uppercase tracking-wider">Action: {step.action}</div>}
                                            </div>
                                          </div>
                                          <span className="text-[9px] text-neutral-500 uppercase font-mono px-1 border border-neutral-300">{step.agent}</span>
                                        </div>
                                      ))}
                                    </div>
                                  )}
                                </div>

                                {/* Validation Result */}
                                {rd.validationResult && (
                                  <div className={`border-2 border-fra-black p-3 shadow-brutal-sm ${
                                    rd.validationResult.status === 'approval_required' ? 'bg-orange-50 border-orange-600' :
                                    rd.validationResult.valid ? 'bg-green-50' : 'bg-red-50'
                                  }`}>
                                    <div className="font-bold text-[11px] uppercase tracking-wider mb-1 font-mono">Validation Result</div>
                                    <div className={`text-xs font-mono font-bold ${
                                      rd.validationResult.status === 'approval_required' ? 'text-orange-700' :
                                      rd.validationResult.valid ? 'text-fra-green' : 'text-red-600'
                                    }`}>
                                      {rd.validationResult.status === 'approval_required' ? 'APPROVAL REQUIRED: ' : (rd.validationResult.valid ? 'PASS: ' : 'FAIL: ')}
                                      {rd.validationResult.reason}
                                    </div>
                                  </div>
                                )}

                                {/* Error Details */}
                                {rd.errorInfo && (
                                  <div className="border-2 border-fra-black bg-red-100 text-red-900 p-3 shadow-brutal-sm font-mono">
                                    <div className="font-black text-xs uppercase tracking-wider text-red-700">
                                      {(rd.errorInfo.node || "RUNNER").toUpperCase()} FAILED
                                    </div>
                                    <div className="text-xs font-bold mt-1 text-black">
                                      {rd.errorInfo.message}
                                    </div>
                                    {rd.errorInfo.error_type && (
                                      <div className="text-[9px] text-neutral-600 mt-1 uppercase">
                                        Error Type: {rd.errorInfo.error_type}
                                      </div>
                                    )}
                                  </div>
                                )}

                                {/* WORKSPACE EXECUTION OUTPUT INSPECTION PANEL */}
                                {activeObs ? (
                                  <div className="border-2 border-fra-black bg-black text-white p-3 shadow-brutal text-xs font-mono overflow-x-auto">
                                    <div className="flex items-center justify-between border-b border-neutral-800 pb-2 mb-2">
                                      <div className="font-bold text-fra-yellow uppercase tracking-wider text-[10px]">
                                        {procObs.length > 0 ? "WORKSPACE EXECUTION STDOUT" : "WORKSPACE OBSERVATION"} [{activeObs.command ? activeObs.command : (activeObs.action || activeObs.tool || "output")}]
                                      </div>
                                      {displayObsList.length > 1 && (
                                        <div className="flex items-center space-x-1">
                                          <span className="text-[9px] text-neutral-400 font-bold uppercase mr-1">Outputs:</span>
                                          {displayObsList.map((obsItem, oIdx) => (
                                            <button
                                              key={oIdx}
                                              className={`px-1.5 py-0.5 text-[9px] font-bold border ${
                                                selectedObsIndex === oIdx ? 'bg-fra-yellow text-black border-black' : 'bg-neutral-800 text-neutral-300 border-neutral-700 hover:bg-neutral-700'
                                              }`}
                                              onClick={() => setSelectedObsForRun(msg.id, oIdx)}
                                            >
                                              #{oIdx + 1} {obsItem.command ? obsItem.command.split(' ')[0] : (obsItem.action || obsItem.tool || 'obs')}
                                            </button>
                                          ))}
                                        </div>
                                      )}
                                    </div>

                                    {/* Stdout display — real subprocess output takes priority */}
                                    <pre className="mb-3 text-neutral-200 whitespace-pre-wrap font-mono text-[11px] leading-relaxed">
                                      {activeObs.stdout && activeObs.stdout.trim()
                                        ? activeObs.stdout
                                        : activeObs.action === 'LIST_DIRECTORY' && (activeObs as any).entries?.length > 0
                                          ? `Directory listing (${(activeObs as any).entries.length} items):\n` + (activeObs as any).entries.map((e: string) => `  ${e}`).join('\n')
                                          : activeObs.action === 'READ_FILE' && activeObs.summary
                                            ? activeObs.summary
                                            : activeObs.action === 'CREATE_FILE' || activeObs.action === 'UPDATE_FILE'
                                              ? activeObs.summary || 'File written successfully.'
                                              : activeObs.summary || activeObs.detail || '(no output captured)'}
                                    </pre>
                                    
                                    {/* Stderr display if present */}
                                    {activeObs.stderr && activeObs.stderr.trim() !== '' && (
                                      <div className="mb-3 border-t border-neutral-800 pt-2">
                                        <div className="font-bold text-red-400 uppercase tracking-wider mb-1 text-[10px]">STDERR</div>
                                        <pre className="text-red-200 whitespace-pre-wrap font-mono text-[11px] leading-relaxed">{activeObs.stderr}</pre>
                                      </div>
                                    )}

                                    <div className="font-bold text-neutral-400 text-[10px] uppercase border-t border-neutral-800 pt-1.5 flex justify-between">
                                      <span>EXIT CODE: {activeObs.exit_code ?? 0}</span>
                                      <span>DURATION: {activeObs.duration || 0}s</span>
                                    </div>
                                  </div>
                                ) : (
                                  <div className="border-2 border-fra-black bg-neutral-900 text-neutral-400 p-3 shadow-brutal text-xs font-mono italic">
                                    No command outputs or observations recorded yet.
                                  </div>
                                )}

                              </div>
                            </div>
                          </div>
                        </div>
                      );
                    })
                  )}
                </div>

                {/* BottomPromptDock */}
                <div className="p-3 border-t-2 border-fra-black bg-fra-cream flex-shrink-0">
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
                          disabled={activeRunStatus === 'starting' || activeRunStatus === 'running'}
                          className={`px-4 py-1.5 text-xs font-bold border-2 border-black flex items-center space-x-1.5 shadow-brutal-sm ${activeRunStatus === 'starting' || activeRunStatus === 'running' ? 'bg-neutral-400 text-neutral-600 cursor-not-allowed' : 'bg-black text-white hover:bg-neutral-800'}`}
                          onClick={startRun}
                        >
                          <span>{activeRunStatus === 'starting' || activeRunStatus === 'running' ? 'Running...' : 'Send'}</span><span>-&gt;</span>
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
                        <button className="border-2 border-fra-black bg-white px-2.5 py-1 font-bold flex items-center space-x-1.5 shadow-brutal-sm hover:bg-neutral-100" onClick={() => { setModelMenuOpen(!modelMenuOpen); setModeMenuOpen(false); }}>
                          <span>Active Model</span><span className="font-bold text-black bg-fra-yellow px-1 border border-black">{model}</span><span className="text-[8px]">v</span>
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
              <aside className="w-80 bg-fra-cream flex flex-col overflow-y-auto select-none font-mono">
                <div className="grid grid-cols-4 border-b-2 border-fra-black text-[11px] font-bold text-center">
                  <button className="py-2.5 bg-fra-yellow border-r-2 border-fra-black font-extrabold text-black">Context</button>
                  <button className="py-2.5 bg-neutral-200 border-r-2 border-fra-black hover:bg-fra-yellow" onClick={() => setView('agents')}>Agents</button>
                  <button className="py-2.5 bg-neutral-200 border-r-2 border-fra-black hover:bg-fra-yellow" onClick={() => alert('Files in workspace: ' + workspaceRoot)}>Files</button>
                  <button className="py-2.5 bg-neutral-200 hover:bg-fra-yellow" onClick={() => alert('Artifacts: ' + (currentArtifacts.length || 0))}>Artifacts</button>
                </div>
                <div className="p-4 space-y-5 flex-1">
                  
                  {/* CONTEXT PANEL */}
                  <div className="border-2 border-fra-black bg-fra-cream-card p-3 shadow-brutal">
                    <div className="font-bold text-[11px] uppercase tracking-wider mb-2">RUN CONTEXT</div>
                    <div className="space-y-1.5 text-[10px]">
                      <div className="flex justify-between border-b border-neutral-200 pb-1">
                        <span className="text-neutral-600">WORKSPACE</span>
                        <span className="font-bold text-black">{workspace}</span>
                      </div>
                      <div className="flex justify-between border-b border-neutral-200 pb-1">
                        <span className="text-neutral-600">CONVERSATION ID</span>
                        <span className="font-bold text-fra-yellow">{conversationId || 'New Session'}</span>
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
                        {currentRelevantFiles.length === 0 ? (
                          <span className="text-neutral-400 italic">None accessed yet</span>
                        ) : (
                          <div className="space-y-0.5">
                            {currentRelevantFiles.map(f => (
                              <div key={f} className="text-black font-bold bg-white px-1 border border-neutral-300 truncate">
                                {f}
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* ARTIFACTS PANEL */}
                  <div className="border-2 border-fra-black bg-fra-cream-card p-3 shadow-brutal">
                    <div className="font-bold text-[11px] uppercase tracking-wider mb-2">RUN ARTIFACTS</div>
                    {currentArtifacts.length === 0 ? (
                      <div className="text-[10px] text-neutral-400 italic">No artifacts generated yet.</div>
                    ) : (
                      <div className="space-y-1.5 text-[10px]">
                        {currentArtifacts.map((art, idx) => {
                          const p = art.path || "";
                          const isHtml = p.endsWith(".html") || p.endsWith(".htm");
                          const isPy = p.endsWith(".py");
                          const isJs = p.endsWith(".js");
                          const isJava = p.endsWith(".java");

                          return (
                            <div key={idx} className="flex flex-col gap-1 border border-black bg-white p-2">
                              <div className="flex items-center justify-between">
                                <span className="font-bold truncate max-w-[140px]">{p}</span>
                                <span className="text-[8px] uppercase font-bold bg-fra-yellow px-1 border border-black">{art.operation}</span>
                              </div>
                              <div className="flex items-center justify-end gap-1 pt-1 border-t border-neutral-100">
                                {isHtml && (
                                  <button
                                    className="bg-fra-yellow text-black font-bold px-2 py-0.5 text-[9px] border border-black hover:bg-yellow-400"
                                    onClick={() => startPreviewServer(p)}
                                  >
                                    [ Run Application / Preview ]
                                  </button>
                                )}
                                {isPy && (
                                  <button
                                    className="bg-black text-white font-bold px-2 py-0.5 text-[9px] border border-black hover:bg-neutral-800"
                                    onClick={() => handleRunCommand(`python ${p}`)}
                                  >
                                    [ Run Python ]
                                  </button>
                                )}
                                {isJs && (
                                  <button
                                    className="bg-black text-white font-bold px-2 py-0.5 text-[9px] border border-black hover:bg-neutral-800"
                                    onClick={() => handleRunCommand(`node ${p}`)}
                                  >
                                    [ Run JS ]
                                  </button>
                                )}
                                {isJava && (
                                  <button
                                    className="bg-black text-white font-bold px-2 py-0.5 text-[9px] border border-black hover:bg-neutral-800"
                                    onClick={() => handleRunCommand(`javac ${p} && java ${p.replace('.java', '')}`)}
                                  >
                                    [ Run Java ]
                                  </button>
                                )}
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                  
                  {/* WORKSPACE RUNTIME PANEL */}
                  <div className="border-2 border-fra-black bg-fra-cream-card p-3 shadow-brutal">
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

                  <div className="border-2 border-fra-black bg-fra-cream-card p-3 shadow-brutal">
                    <div className="font-bold text-[11px] uppercase tracking-wider mb-2">QUICK ACTIONS</div>
                    <div className="grid grid-cols-2 gap-2 text-[11px]">
                      <button className="border-2 border-fra-black bg-fra-cream-card p-2 font-bold shadow-brutal-sm hover:bg-fra-yellow flex items-center justify-center space-x-1" onClick={() => setView('runs')}>
                        <span>View Runs</span>
                      </button>
                      <button className="border-2 border-fra-black bg-fra-cream-card p-2 font-bold shadow-brutal-sm hover:bg-fra-yellow flex items-center justify-center space-x-1" onClick={() => alert('Files in: ' + workspaceRoot)}>
                        <span>Open Root</span>
                      </button>
                    </div>
                  </div>
                </div>
              </aside>
            </div>
          )}

          {view === 'runs' && (
            <div className="flex-1 flex overflow-hidden bg-fra-cream p-4 flex-col font-mono">
              <h1 className="text-3xl font-extrabold font-sans mb-4">RUNS</h1>
              <div className="border-2 border-fra-black bg-white p-4 shadow-brutal mb-4">
                <div className="text-xs text-neutral-600 mb-2 font-bold uppercase">Active Conversation Runs ({messages.filter(m => m.role === 'assistant').length})</div>
                {messages.filter(m => m.role === 'assistant').length > 0 ? (
                  <div className="space-y-2">
                    {messages.filter(m => m.role === 'assistant').map((m, idx) => (
                      <div key={m.id} className="p-2 border border-black bg-fra-yellow flex justify-between items-center text-xs">
                        <span className="font-bold"># {idx + 1} | Run: {m.runData?.runId} | {m.runData?.objective}</span>
                        <span className="font-black bg-black text-white px-2 py-0.5">{m.runData?.status.toUpperCase()}</span>
                      </div>
                    ))}
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
    </>
  );
}
