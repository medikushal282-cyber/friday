import React from 'react';
import { Terminal, ShieldAlert, CheckCircle2, RefreshCw, Cpu, Layers, GitBranch, ArrowUpRight } from 'lucide-react';

export const WorkspacePreview: React.FC = () => {
  return (
    <section id="preview" className="py-16 px-4 sm:px-6 lg:px-8 bg-fra-cream tech-grid-cream">
      <div className="max-w-6xl mx-auto">
        <div className="flex flex-col sm:flex-row sm:items-end justify-between mb-8 pb-4 border-b-2 border-black">
          <div>
            <span className="text-xs font-mono font-bold uppercase bg-black text-white px-3 py-1 shadow-brutal-sm">
              [LIVE_ENGINE_PREVIEW]
            </span>
            <h2 className="text-2xl sm:text-3xl font-black mt-3 text-black tracking-tight uppercase">
              AI-Native Autonomous Workspace
            </h2>
            <p className="text-xs sm:text-sm font-mono text-neutral-700 mt-1">
              Deterministic task DAGs, tool dispatchers, sandboxed sub-agents, and explicit human gates.
            </p>
          </div>
          <div className="mt-4 sm:mt-0 flex items-center gap-2 text-xs font-mono font-bold text-neutral-800 border-2 border-black bg-white px-3 py-1.5 shadow-brutal">
            <span className="inline-block w-2.5 h-2.5 rounded-full bg-fra-green border border-black animate-ping" />
            <span className="text-black uppercase">CORE ACTIVE</span>
            <span>|</span>
            <span className="text-neutral-600">DAG: 7/8 PASS</span>
          </div>
        </div>

        {/* Realistic Neo-Brutalist Technical Workspace Shell */}
        <div className="border-2 border-black bg-white shadow-brutal-xl overflow-hidden">
          {/* Workspace Titlebar */}
          <div className="bg-black text-white px-4 py-2.5 border-b-2 border-black flex items-center justify-between text-xs font-mono select-none">
            <div className="flex items-center gap-3">
              <span className="bg-fra-yellow text-black font-black px-1.5 py-0.5 text-[10px]">
                FRAIDAY_SYS
              </span>
              <span className="text-neutral-400 font-bold hidden sm:inline">
                // ROOT: C:\Projects\Fraiday\core-v0.1
              </span>
            </div>
            <div className="flex items-center gap-3 text-[11px] font-bold">
              <span className="flex items-center gap-1 text-fra-yellow">
                <GitBranch className="w-3.5 h-3.5" />
                feat/autonomous-core
              </span>
              <span className="bg-neutral-800 text-white px-2 py-0.5 border border-neutral-700">
                #88219-RUN
              </span>
            </div>
          </div>

          {/* Main Layout Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-12 min-h-[460px]">
            {/* Left Column: Objective & DAG Steps (5 cols) */}
            <div className="lg:col-span-5 border-b-2 lg:border-b-0 lg:border-r-2 border-black p-4 bg-fra-cream flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between mb-3">
                  <span className="text-[11px] font-mono font-bold uppercase tracking-wider flex items-center gap-1.5 text-black">
                    <Layers className="w-3.5 h-3.5" />
                    Objective Spec
                  </span>
                  <span className="text-[10px] font-mono font-extrabold bg-green-200 border border-black text-black px-2 py-0.5">
                    VALIDATED
                  </span>
                </div>

                <div className="p-3 border-2 border-black bg-white shadow-brutal-sm mb-4">
                  <p className="text-xs font-mono text-neutral-900 leading-relaxed font-bold">
                    "Build an optimized data transformer pipeline that processes university metrics, reconciles anomalies, and generates an interactive report."
                  </p>
                </div>

                {/* Execution Plan DAG */}
                <div className="space-y-1.5 font-mono">
                  <span className="text-[10px] uppercase font-bold text-neutral-600 block mb-1">
                    Execution DAG (Directed Acyclic Graph)
                  </span>

                  {[
                    { title: 'Recon & Schema Introspection', status: 'done', time: '1.2s' },
                    { title: 'CSV Anomaly Sanitization', status: 'done', time: '3.4s' },
                    { title: 'Data Transformation Engine', status: 'done', time: '4.8s' },
                    { title: 'Automated Regression Suite', status: 'done', time: '2.1s' },
                    { title: 'Deploy Interactive Dashboard', status: 'running', time: 'Active' },
                    { title: 'Produce Final Audit Report', status: 'pending', time: 'Queued' },
                  ].map((step, idx) => (
                    <div
                      key={idx}
                      className={`flex items-center justify-between p-2 border-2 border-black text-xs ${
                        step.status === 'done'
                          ? 'bg-white shadow-brutal-sm text-black font-bold'
                          : step.status === 'running'
                          ? 'bg-fra-yellow shadow-brutal text-black font-extrabold'
                          : 'bg-fra-cream text-neutral-500'
                      }`}
                    >
                      <div className="flex items-center gap-2">
                        {step.status === 'done' && <CheckCircle2 className="w-3.5 h-3.5 text-green-700 shrink-0 stroke-[3]" />}
                        {step.status === 'running' && <RefreshCw className="w-3.5 h-3.5 text-black animate-spin shrink-0 stroke-[3]" />}
                        {step.status === 'pending' && <span className="w-3.5 h-3.5 border-2 border-black shrink-0 inline-block bg-neutral-200" />}
                        <span className="truncate">{step.title}</span>
                      </div>
                      <span className="text-[10px] text-neutral-600 shrink-0 ml-2 font-mono">{step.time}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Status footer */}
              <div className="mt-4 pt-3 border-t-2 border-black flex items-center justify-between text-[11px] font-mono font-bold text-black">
                <span className="flex items-center gap-1.5">
                  <Cpu className="w-3.5 h-3.5" />
                  Active Sub-Agents: 3
                </span>
                <span className="bg-black text-white px-2 py-0.5">RAM: 312MB</span>
              </div>
            </div>

            {/* Right Column: Live Terminal Stream & Human Gate (7 cols) */}
            <div className="lg:col-span-7 p-4 bg-white flex flex-col justify-between">
              {/* Terminal Log Stream */}
              <div>
                <div className="flex items-center justify-between mb-3 font-mono">
                  <span className="text-[11px] font-bold uppercase tracking-wider flex items-center gap-1.5 text-black">
                    <Terminal className="w-3.5 h-3.5" />
                    Runtime Activity Stream (SSE)
                  </span>
                  <span className="text-[10px] bg-neutral-100 border border-black px-2 py-0.5 font-bold">
                    LIVE_FEED
                  </span>
                </div>

                <div className="border-2 border-black bg-black p-3 font-mono text-xs text-white space-y-1.5 max-h-[220px] overflow-y-auto dark-scroll shadow-inner">
                  <div className="text-neutral-400 text-[11px]">[10:24:02.114] INITIALIZING autonomous runtime context...</div>
                  <div className="text-fra-green text-[11px] font-bold">[10:24:03.450] PLAN_GRAPH resolved: 6 execution nodes mapped</div>
                  <div className="text-fra-yellow text-[11px] font-bold">[10:24:04.012] TOOL_DISPATCH: python_runner -&gt; verify_result.py</div>
                  <div className="text-neutral-200 text-[11px]">[10:24:06.189] OUTPUT: 1,420 rows ingested, 0 unhandled nulls</div>
                  <div className="text-amber-400 text-[11px] font-bold">[10:24:08.330] INVARIANT_CHECK: Recovery heuristic applied to invalid date token</div>
                  <div className="text-fra-green text-[11px] font-bold">[10:24:10.902] TESTS: 14/14 automated assertions passed in 210ms</div>
                  <div className="text-fra-yellow text-[11px] font-extrabold">[10:24:12.441] TOOL_INVOKE: serve_dashboard.py --port=3000</div>
                </div>
              </div>

              {/* Realistic Human-in-the-loop Approval Gate */}
              <div className="mt-4 p-4 border-2 border-black bg-fra-yellow shadow-brutal flex flex-col sm:flex-row sm:items-center justify-between gap-4 font-mono">
                <div className="flex items-start gap-3">
                  <div className="p-1.5 border-2 border-black bg-black text-fra-yellow shrink-0">
                    <ShieldAlert className="w-5 h-5" />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-black uppercase text-black">
                        Human Approval Required
                      </span>
                      <span className="text-[9px] font-black bg-black text-white px-1.5 py-0.5">
                        GATE
                      </span>
                    </div>
                    <p className="text-xs text-black/90 mt-1 leading-snug">
                      Target action involves binding port 3000 and writing compiled HTML report to production output.
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  <button className="px-3 py-1.5 border-2 border-black bg-white text-black font-bold text-xs shadow-brutal-sm hover:bg-neutral-100 uppercase">
                    Diff
                  </button>
                  <button className="px-3.5 py-1.5 border-2 border-black bg-black text-white font-extrabold text-xs shadow-brutal hover:bg-neutral-800 transition-colors flex items-center gap-1 uppercase">
                    <span>Approve</span>
                    <ArrowUpRight className="w-3.5 h-3.5 text-fra-yellow" />
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
