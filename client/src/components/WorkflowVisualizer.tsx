import React, { useState, useEffect } from 'react';
import { Sparkles, Compass, Search, Play, CheckCircle2, PackageCheck } from 'lucide-react';

interface WorkflowStep {
  id: string;
  name: string;
  desc: string;
  icon: React.ElementType;
  tag: string;
}

const steps: WorkflowStep[] = [
  {
    id: 'intent',
    name: 'Intent In',
    desc: 'High-level objective parsed into unambiguous target state',
    icon: Sparkles,
    tag: 'INPUT',
  },
  {
    id: 'plan',
    name: 'Plan',
    desc: 'Dynamic DAG generation with dependency isolation',
    icon: Compass,
    tag: 'DAG_GRAPH',
  },
  {
    id: 'research',
    name: 'Research',
    desc: 'Deep autonomous inspection, documentation and context gathering',
    icon: Search,
    tag: 'RAG_RECON',
  },
  {
    id: 'execute',
    name: 'Execute',
    desc: 'Sandboxed code synthesis, terminal operations and tool calls',
    icon: Play,
    tag: 'RUNNER',
  },
  {
    id: 'validate',
    name: 'Validate',
    desc: 'Automated test suite execution and invariant verification',
    icon: CheckCircle2,
    tag: 'ASSERT',
  },
  {
    id: 'deliver',
    name: 'Deliver',
    desc: 'Production-ready outcome, artifacts, and interactive interfaces',
    icon: PackageCheck,
    tag: 'DEPLOY',
  },
];

export const WorkflowVisualizer: React.FC = () => {
  const [activeStep, setActiveStep] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setActiveStep((prev) => (prev + 1) % steps.length);
    }, 2800);
    return () => clearInterval(timer);
  }, []);

  return (
    <div className="w-full py-20 px-4 sm:px-6 lg:px-8 bg-fra-sidebar text-white border-y-2 border-black">
      <div className="max-w-6xl mx-auto">
        <div className="text-center mb-12">
          <span className="text-xs font-mono font-black uppercase bg-fra-yellow text-black px-3 py-1 shadow-brutal-sm inline-block">
            [PIPELINE_ARCHITECTURE]
          </span>
          <h2 className="text-3xl sm:text-4xl font-black mt-3 text-white tracking-tight uppercase font-sans">
            How frAIday Executes Intent
          </h2>
          <p className="text-xs sm:text-sm font-mono text-neutral-400 mt-2 max-w-xl mx-auto">
            From abstract goal to verified delivery — each stage is observable, sandboxed, and resilient.
          </p>
        </div>

        {/* Steps Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-6 gap-3">
          {steps.map((step, idx) => {
            const Icon = step.icon;
            const isActive = activeStep === idx;
            const isCompleted = activeStep > idx;

            return (
              <div
                key={step.id}
                onClick={() => setActiveStep(idx)}
                className={`cursor-pointer transition-all duration-200 border-2 p-4 text-left flex flex-col justify-between min-h-[170px] ${
                  isActive
                    ? 'bg-fra-yellow text-black border-white shadow-brutal-lg -translate-y-1 font-bold'
                    : isCompleted
                    ? 'bg-neutral-900 border-neutral-700 text-neutral-200 shadow-brutal hover:border-neutral-500'
                    : 'bg-fra-sidebar-card border-neutral-800 text-neutral-400 shadow-brutal hover:border-fra-yellow hover:text-neutral-200'
                }`}
              >
                <div className="flex items-center justify-between font-mono">
                  <span className={`text-[10px] px-1.5 py-0.5 border font-black ${
                    isActive
                      ? 'bg-black text-white border-black'
                      : isCompleted
                      ? 'bg-neutral-800 text-neutral-300 border-neutral-700'
                      : 'bg-neutral-950 text-neutral-500 border-neutral-800'
                  }`}>
                    0{idx + 1}
                  </span>
                  <span className={`text-[9px] font-bold uppercase ${
                    isActive ? 'text-black' : 'text-neutral-500'
                  }`}>
                    [{step.tag}]
                  </span>
                </div>

                <div className="my-2">
                  <div className={`w-8 h-8 border-2 flex items-center justify-center mb-2 shadow-brutal-sm ${
                    isActive
                      ? 'bg-black text-fra-yellow border-black'
                      : 'bg-neutral-900 text-white border-neutral-700'
                  }`}>
                    <Icon className="w-4 h-4" />
                  </div>
                  <h3 className={`text-sm font-black tracking-tight uppercase ${
                    isActive ? 'text-black' : 'text-white'
                  }`}>
                    {step.name}
                  </h3>
                </div>

                <p className={`text-[11px] font-mono line-clamp-3 leading-snug ${
                  isActive ? 'text-neutral-900 font-semibold' : 'text-neutral-400'
                }`}>
                  {step.desc}
                </p>
              </div>
            );
          })}
        </div>

        {/* Status Bar */}
        <div className="mt-8 p-3 border-2 border-neutral-700 bg-black text-white shadow-brutal flex flex-wrap items-center justify-between gap-3 text-xs font-mono">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 bg-fra-green rounded-full animate-ping inline-block" />
            <span className="font-bold text-neutral-400">ACTIVE STAGE:</span>
            <span className="bg-fra-yellow text-black px-2 py-0.5 font-black uppercase">
              {steps[activeStep].name}
            </span>
          </div>
          <div className="text-neutral-400 text-[11px] font-bold">
            STAGE {activeStep + 1} / {steps.length} &bull; DETERMINISTIC RECOVERY GUARANTEED
          </div>
        </div>
      </div>
    </div>
  );
};
