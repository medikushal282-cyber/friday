import React from 'react';
import { Layout, Server, BarChart3, FileText, Code2, Database } from 'lucide-react';

const outcomes = [
  {
    title: 'Full-Stack Applications',
    desc: 'Functional React, Next.js, or Vue frontends paired with robust backend services.',
    icon: Layout,
    sample: 'Deployable Web App',
  },
  {
    title: 'Production REST & GraphQL APIs',
    desc: 'Contract-tested endpoints with schema validation, auth middleware, and swagger docs.',
    icon: Server,
    sample: 'FastAPI / Express Microservice',
  },
  {
    title: 'Interactive Dashboards',
    desc: 'Dynamic data visualization web components with real-time analytics and controls.',
    icon: BarChart3,
    sample: 'Metrics & BI Panel',
  },
  {
    title: 'Technical Audits & Reports',
    desc: 'Comprehensive HTML/Markdown deliverables with verifiable execution traces and diffs.',
    icon: FileText,
    sample: 'Executive Architecture Report',
  },
  {
    title: 'Tested Code Modules',
    desc: 'Clean, documented source code bundled with full unit and integration test coverage.',
    icon: Code2,
    sample: 'Algorithmic Package',
  },
  {
    title: 'Data Transformation Pipelines',
    desc: 'ETL routines that ingest unstructured files, sanitize schemas, and output clean datasets.',
    icon: Database,
    sample: 'ETL Pipeline & SQL Models',
  },
];

export const InteractiveOutcomes: React.FC = () => {
  return (
    <section id="outcomes" className="py-20 px-4 sm:px-6 lg:px-8 border-t-2 border-black bg-fra-cream tech-grid-cream">
      <div className="max-w-6xl mx-auto">
        <div className="text-center mb-14">
          <span className="text-xs font-mono font-bold uppercase bg-black text-white px-3 py-1 shadow-brutal-sm">
            [DELIVERABLES]
          </span>
          <h2 className="text-3xl sm:text-4xl font-black mt-3 text-black tracking-tight uppercase">
            More Than Just Chat Responses
          </h2>
          <p className="text-xs sm:text-sm font-mono text-neutral-700 mt-2 max-w-xl mx-auto">
            frAIday compiles, tests, and serves actual software artifacts directly into your environment.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {outcomes.map((item, idx) => {
            const Icon = item.icon;
            return (
              <div
                key={idx}
                className="p-6 border-2 border-black bg-white shadow-brutal hover:-translate-y-1 hover:shadow-brutal-xl transition-all flex flex-col justify-between group"
              >
                <div>
                  <div className="flex items-center justify-between mb-4">
                    <div className="w-10 h-10 border-2 border-black bg-fra-yellow text-black flex items-center justify-center shadow-brutal-sm group-hover:bg-black group-hover:text-fra-yellow transition-colors">
                      <Icon className="w-5 h-5" />
                    </div>
                    <span className="text-[10px] font-mono font-bold px-2 py-0.5 border border-black bg-neutral-100 text-black shadow-brutal-sm">
                      {item.sample}
                    </span>
                  </div>
                  <h3 className="text-sm font-black text-black uppercase mb-1.5 font-sans">
                    {item.title}
                  </h3>
                  <p className="text-xs font-mono text-neutral-700 leading-relaxed">
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
