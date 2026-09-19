import React from 'react';
import { GitFork, BookOpen, Terminal, CheckCircle, ShieldCheck, HeartHandshake } from 'lucide-react';

const capabilities = [
  {
    title: 'Autonomous Planning',
    desc: 'Deconstructs goals into isolated dependency DAGs. Re-evaluates milestones dynamically as runtime feedback evolves.',
    icon: GitFork,
    badge: 'DAG ENGINE',
  },
  {
    title: 'Deep Research & Recon',
    desc: 'Autonomously inspects codebases, filesystems, and live external APIs to uncover required context before execution.',
    icon: BookOpen,
    badge: 'CONTEXT AWARE',
  },
  {
    title: 'Sandboxed Execution',
    desc: 'Runs compilers, scripts, database queries, and shell operations within isolated containers and deterministic environments.',
    icon: Terminal,
    badge: 'CONTAINERIZED',
  },
  {
    title: 'Multi-Level Validation',
    desc: 'Asserts correctness using unit tests, syntax linters, schema checks, and functional invariants prior to committing changes.',
    icon: CheckCircle,
    badge: 'ZERO GUESSWORK',
  },
  {
    title: 'Self-Healing Recovery',
    desc: 'Detects compiler errors, runtime exceptions, and deadlock conditions automatically, applying targeted heuristic remedies.',
    icon: ShieldCheck,
    badge: 'RESILIENT',
  },
  {
    title: 'Human-in-the-Loop Control',
    desc: 'Sensitive boundaries, deployment actions, and data mutations pause execution until authorized by explicit human approval.',
    icon: HeartHandshake,
    badge: 'SAFETY FIRST',
  },
];

export const CapabilityGrid: React.FC = () => {
  return (
    <section id="capabilities" className="py-20 px-4 sm:px-6 lg:px-8 border-y-2 border-black bg-white">
      <div className="max-w-6xl mx-auto">
        <div className="text-center mb-14">
          <span className="text-xs font-mono font-black uppercase bg-black text-white px-3 py-1 shadow-brutal-sm inline-block">
            [CORE_PRIMITIVES]
          </span>
          <h2 className="text-3xl sm:text-4xl font-black mt-3 text-black tracking-tight uppercase font-sans">
            Engineered for Rigorous Autonomy
          </h2>
          <p className="text-xs sm:text-sm font-mono text-neutral-600 mt-2 max-w-2xl mx-auto">
            frAIday does not stop at text suggestions. It executes the full software and systems development lifecycle.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {capabilities.map((item, idx) => {
            const Icon = item.icon;
            return (
              <div
                key={idx}
                className="p-6 border-2 border-black bg-fra-cream shadow-brutal hover:bg-fra-yellow hover:shadow-brutal-lg hover:-translate-y-1 transition-all flex flex-col justify-between group"
              >
                <div>
                  <div className="flex items-center justify-between mb-4">
                    <div className="w-10 h-10 border-2 border-black bg-white group-hover:bg-black group-hover:text-fra-yellow text-black flex items-center justify-center shadow-brutal-sm transition-colors">
                      <Icon className="w-5 h-5" />
                    </div>
                    <span className="text-[10px] font-mono font-black bg-black text-white px-2 py-0.5 uppercase">
                      {item.badge}
                    </span>
                  </div>
                  <h3 className="text-base font-black text-black uppercase font-sans">
                    {item.title}
                  </h3>
                  <p className="text-xs font-mono text-neutral-800 mt-2 leading-relaxed">
                    {item.desc}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
};
