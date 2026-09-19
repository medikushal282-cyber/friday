import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, Terminal, ShieldCheck } from 'lucide-react';
import { Navbar } from '../components/Navbar';
import { WorkflowVisualizer } from '../components/WorkflowVisualizer';
import { WorkspacePreview } from '../components/WorkspacePreview';
import { CapabilityGrid } from '../components/CapabilityGrid';
import { InteractiveOutcomes } from '../components/InteractiveOutcomes';
import { SecuritySection } from '../components/SecuritySection';
import { Footer } from '../components/Footer';

interface LandingPageProps {
  isAuthenticated?: boolean;
  userName?: string;
  onLogout?: () => void;
}

export const LandingPage: React.FC<LandingPageProps> = ({ isAuthenticated, userName, onLogout }) => {
  return (
    <div className="min-h-screen bg-fra-cream text-black flex flex-col font-sans select-none selection:bg-fra-yellow selection:text-black">
      <Navbar isAuthenticated={isAuthenticated} userName={userName} onLogout={onLogout} />

      {/* Hero Section */}
      <section className="relative pt-28 pb-20 px-4 sm:px-6 lg:px-8 overflow-hidden tech-grid-cream">
        <div className="max-w-5xl mx-auto text-center relative z-10">
          {/* Badge */}
          <div className="inline-flex items-center gap-2 px-3 py-1 border-2 border-black bg-white shadow-brutal text-xs font-mono font-bold mb-6">
            <span className="w-2 h-2 rounded-full bg-fra-green animate-ping" />
            <span className="uppercase">frAIday :: Autonomous Agent Architecture</span>
          </div>

          {/* Headline */}
          <h1 className="text-4xl sm:text-6xl lg:text-7xl font-black tracking-tight text-black max-w-4xl mx-auto leading-[1.05] uppercase">
            Give AI the goal.{' '}
            <span className="bg-fra-yellow px-2 border-2 border-black shadow-brutal inline-block mt-2">
              Let it execute the work.
            </span>
          </h1>

          {/* Tagline & Supporting text */}
          <p className="mt-6 text-xl sm:text-2xl font-black tracking-tight text-neutral-900 max-w-2xl mx-auto font-mono">
            Intent In. Outcome Out.
          </p>
          <p className="mt-2 text-sm sm:text-base font-mono text-neutral-700 max-w-2xl mx-auto leading-relaxed">
            Turn high-level intent into autonomous execution. frAIday plans the work, researches context, executes sandboxed tools, self-heals failures, and validates outcomes.
          </p>

          {/* CTAs */}
          <div className="mt-8 flex flex-col sm:flex-row items-center justify-center gap-4 font-mono">
            <Link
              to="/register"
              className="w-full sm:w-auto px-8 py-3.5 border-2 border-black bg-fra-yellow text-black font-black text-sm shadow-brutal-lg hover:bg-black hover:text-fra-yellow hover:-translate-y-0.5 transition-all flex items-center justify-center gap-2 uppercase tracking-wider"
            >
              <span>Get Started</span>
              <ArrowRight className="w-4 h-4" />
            </Link>
            <a
              href="#workflow"
              className="w-full sm:w-auto px-7 py-3.5 border-2 border-black bg-white text-black font-extrabold text-sm shadow-brutal hover:bg-neutral-100 hover:-translate-y-0.5 transition-all flex items-center justify-center gap-2 uppercase"
            >
              <Terminal className="w-4 h-4" />
              <span>See How It Works</span>
            </a>
          </div>

          {/* Trust Indicators */}
          <div className="mt-12 flex flex-wrap items-center justify-center gap-4 text-[11px] font-mono font-bold text-black">
            <span className="flex items-center gap-1.5 border-2 border-black bg-white px-3 py-1.5 shadow-brutal-sm">
              <ShieldCheck className="w-3.5 h-3.5 text-green-700 stroke-[2.5]" />
              SANDBOXED CONTAINERS
            </span>
            <span className="border-2 border-black bg-white px-3 py-1.5 shadow-brutal-sm">
              DETERMINISTIC DAGs
            </span>
            <span className="border-2 border-black bg-white px-3 py-1.5 shadow-brutal-sm">
              HUMAN-IN-THE-LOOP GATES
            </span>
            <span className="border-2 border-black bg-white px-3 py-1.5 shadow-brutal-sm">
              ZERO DATA LEAKAGE
            </span>
          </div>
        </div>
      </section>

      {/* Autonomous Workflow Section */}
      <section id="workflow">
        <WorkflowVisualizer />
      </section>

      {/* Realistic Product Workspace Preview */}
      <WorkspacePreview />

      {/* Capability Section */}
      <CapabilityGrid />

      {/* Interactive Outcomes Section */}
      <InteractiveOutcomes />

      {/* Security Section */}
      <SecuritySection />

      {/* Final Call to Action */}
      <section className="py-20 px-4 sm:px-6 lg:px-8 border-t-2 border-black bg-fra-yellow text-center font-mono">
        <div className="max-w-3xl mx-auto border-2 border-black bg-white p-8 sm:p-12 shadow-brutal-xl">
          <span className="text-xs font-mono font-black uppercase bg-black text-white px-3 py-1 shadow-brutal-sm inline-block">
            [READY_TO_BUILD]
          </span>
          <h2 className="text-3xl sm:text-4xl font-black mt-4 text-black tracking-tight uppercase font-sans">
            Start building with frAIday.
          </h2>
          <p className="text-xs sm:text-sm text-neutral-600 mt-2 max-w-xl mx-auto leading-relaxed">
            Experience the new standard in autonomous task execution. From raw idea to production artifacts.
          </p>
          <div className="mt-8 flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link
              to="/register"
              className="w-full sm:w-auto px-8 py-3.5 border-2 border-black bg-fra-yellow text-black font-black text-sm shadow-brutal hover:bg-black hover:text-fra-yellow transition-all flex items-center justify-center gap-2 uppercase tracking-wider"
            >
              <span>Create Account</span>
              <ArrowRight className="w-4 h-4" />
            </Link>
            <Link
              to="/login"
              className="w-full sm:w-auto px-7 py-3.5 border-2 border-black bg-white text-black font-extrabold text-sm shadow-brutal hover:bg-neutral-100 transition-all uppercase"
            >
              Sign In to Workspace
            </Link>
          </div>
        </div>
      </section>

      <Footer />
    </div>
  );
};
