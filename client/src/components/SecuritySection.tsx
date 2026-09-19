import React from 'react';
import { Shield, Box, UserCheck, FileKey, Lock } from 'lucide-react';

export const SecuritySection: React.FC = () => {
  return (
    <section id="security" className="py-20 px-4 sm:px-6 lg:px-8 border-t-2 border-black bg-fra-sidebar text-white">
      <div className="max-w-6xl mx-auto">
        <div className="text-center mb-14">
          <span className="text-xs font-mono font-black uppercase bg-fra-yellow text-black px-3 py-1 shadow-brutal-sm inline-flex items-center gap-1.5 mx-auto">
            <Shield className="w-3.5 h-3.5 text-black" />
            [ENTERPRISE_GUARDRAILS]
          </span>
          <h2 className="text-3xl sm:text-4xl font-black mt-3 text-white tracking-tight uppercase font-sans">
            Uncompromised Security by Default
          </h2>
          <p className="text-xs sm:text-sm font-mono text-neutral-400 mt-2 max-w-xl mx-auto">
            Autonomy without guardrails is a liability. Every frAIday execution step is isolated, audited, and strictly permissioned.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
          <div className="p-6 border-2 border-neutral-700 bg-neutral-900 shadow-brutal hover:border-fra-yellow hover:-translate-y-1 transition-all group">
            <div className="w-10 h-10 border-2 border-neutral-700 bg-black text-fra-yellow flex items-center justify-center mb-4 shadow-brutal-sm group-hover:border-fra-yellow transition-colors">
              <Box className="w-4 h-4" />
            </div>
            <h3 className="text-sm font-black text-white uppercase font-sans">Sandboxed Execution</h3>
            <p className="text-xs font-mono text-neutral-400 mt-2 leading-relaxed">
              All code compilation and command execution are strictly containerized with isolated disk and memory limits.
            </p>
          </div>

          <div className="p-6 border-2 border-neutral-700 bg-neutral-900 shadow-brutal hover:border-fra-yellow hover:-translate-y-1 transition-all group">
            <div className="w-10 h-10 border-2 border-neutral-700 bg-black text-fra-yellow flex items-center justify-center mb-4 shadow-brutal-sm group-hover:border-fra-yellow transition-colors">
              <UserCheck className="w-4 h-4" />
            </div>
            <h3 className="text-sm font-black text-white uppercase font-sans">Human Approval Gates</h3>
            <p className="text-xs font-mono text-neutral-400 mt-2 leading-relaxed">
              Destructive shell commands, external API pushes, and production writes require explicit one-click operator approval.
            </p>
          </div>

          <div className="p-6 border-2 border-neutral-700 bg-neutral-900 shadow-brutal hover:border-fra-yellow hover:-translate-y-1 transition-all group">
            <div className="w-10 h-10 border-2 border-neutral-700 bg-black text-fra-yellow flex items-center justify-center mb-4 shadow-brutal-sm group-hover:border-fra-yellow transition-colors">
              <FileKey className="w-4 h-4" />
            </div>
            <h3 className="text-sm font-black text-white uppercase font-sans">Immutable Audit Trails</h3>
            <p className="text-xs font-mono text-neutral-400 mt-2 leading-relaxed">
              Every authentication event, command invocation, and plan adjustment is logged with cryptographic request identifiers.
            </p>
          </div>

          <div className="p-6 border-2 border-neutral-700 bg-neutral-900 shadow-brutal hover:border-fra-yellow hover:-translate-y-1 transition-all group">
            <div className="w-10 h-10 border-2 border-neutral-700 bg-black text-fra-yellow flex items-center justify-center mb-4 shadow-brutal-sm group-hover:border-fra-yellow transition-colors">
              <Lock className="w-4 h-4" />
            </div>
            <h3 className="text-sm font-black text-white uppercase font-sans">Secure Authentication</h3>
            <p className="text-xs font-mono text-neutral-400 mt-2 leading-relaxed">
              Bcrypt password hashing, SHA-256 token hashing, HTTP-only secure cookie sessions, and zero secret logging.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
};
