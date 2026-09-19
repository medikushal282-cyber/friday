import React from 'react';
import { Link } from 'react-router-dom';
import { Shield, ArrowLeft, Terminal, Lock } from 'lucide-react';

interface AuthLayoutProps {
  children: React.ReactNode;
  title: string;
  subtitle: string;
}

export const AuthLayout: React.FC<AuthLayoutProps> = ({ children, title, subtitle }) => {
  return (
    <div className="min-h-screen bg-fra-cream text-black flex flex-col justify-between tech-grid-cream select-none font-sans">
      {/* Top Header Bar (matches Workspace TopHeader exactly) */}
      <header className="h-14 border-b-2 border-black bg-fra-cream flex items-center justify-between px-4 sm:px-6 flex-shrink-0 z-30">
        <div className="flex items-center space-x-3">
          <Link
            to="/"
            id="fraiday-logo-link"
            aria-label="Return to frAIday home page"
            title="Return to Home Page"
            className="flex items-center space-x-2 group cursor-pointer focus:outline-none"
          >
            {/* frAIday Brand Icon */}
            <div className="w-8 h-8 border-2 border-black bg-fra-yellow text-black flex items-center justify-center font-mono font-black text-xs shadow-brutal-sm group-hover:bg-black group-hover:text-fra-yellow transition-all">
              <Terminal className="w-4 h-4 stroke-[2.5]" />
            </div>
            <span className="font-extrabold text-2xl tracking-tighter bg-black text-white px-2 py-0.5 group-hover:bg-fra-yellow group-hover:text-black transition-colors">
              FRAIDAY_
            </span>
          </Link>
          <div className="border-l-2 border-black pl-3 text-[9px] leading-tight font-mono font-bold tracking-tight text-neutral-800 hidden sm:block">
            AUTONOMOUS WORKSPACE AUTHENTICATION GATEWAY<br />
            STATUS: <span className="text-fra-green font-extrabold">AUTH PERIMETER READY</span>
          </div>
        </div>

        <Link
          to="/"
          id="portal-home-link"
          aria-label="Back to home page"
          className="text-xs font-mono font-bold text-black hover:text-black flex items-center gap-1.5 border-2 border-black bg-white px-3 py-1.5 shadow-brutal hover:bg-fra-yellow hover:-translate-y-0.5 transition-all"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>PORTAL_HOME</span>
        </Link>
      </header>

      {/* Main Neo-Brutalist Form Card (Engineered Workspace Window) */}
      <main className="w-full max-w-md mx-auto my-10 px-4">
        <div className="border-2 border-black bg-white shadow-brutal-xl overflow-hidden">
          {/* Workspace-style Window Header Bar */}
          <div className="bg-black text-white px-4 py-2.5 border-b-2 border-black flex items-center justify-between font-mono text-xs select-none">
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-fra-yellow border border-black inline-block" />
              <span className="bg-fra-yellow text-black font-black px-1.5 py-0.5 text-[10px]">
                FRAIDAY_AUTH
              </span>
              <span className="text-neutral-400 font-bold hidden sm:inline">
                // PERIMETER_GATE
              </span>
            </div>
            <div className="flex items-center gap-2 text-[10px] font-bold">
              <span className="flex items-center gap-1.5 text-fra-green">
                <span className="w-1.5 h-1.5 rounded-full bg-fra-green animate-ping" />
                TLS 1.3 SECURE
              </span>
            </div>
          </div>

          {/* Card Body in pure white */}
          <div className="p-6 sm:p-8 bg-white">
            <div className="mb-6 pb-4 border-b-2 border-black">
              <div className="flex items-center justify-between mb-2">
                <span className="text-[10px] font-mono font-black uppercase bg-black text-white px-2 py-0.5">
                  [SECURITY_CLEARANCE]
                </span>
                <span className="text-[9px] font-mono font-bold text-neutral-500">
                  SHA-256 &bull; BCRYPT-12
                </span>
              </div>
              <h1 className="text-2xl sm:text-3xl font-black tracking-tight text-black uppercase font-sans">
                {title}
              </h1>
              <p className="text-xs font-mono text-neutral-600 mt-1.5 leading-relaxed">
                {subtitle}
              </p>
            </div>

            {children}
          </div>

          {/* Technical Sub-bar (Deep Obsidian Footer) */}
          <div className="border-t-2 border-black bg-fra-sidebar text-neutral-300 px-4 py-2.5 font-mono text-[10px] flex items-center justify-between font-bold">
            <div className="flex items-center gap-1.5 text-fra-yellow">
              <Shield className="w-3.5 h-3.5" />
              <span>ZERO PLAINTEXT LOGGING</span>
            </div>
            <div className="flex items-center gap-1 text-neutral-400">
              <Lock className="w-3 h-3 text-fra-green" />
              <span>STRICT SESSION COOKIE</span>
            </div>
          </div>
        </div>
      </main>

      {/* Footer matching Workspace */}
      <footer className="h-10 border-t-2 border-black bg-fra-cream flex items-center justify-center px-4 text-center text-[10px] font-mono font-bold text-neutral-700 flex-shrink-0">
        FRAIDAY &copy; {new Date().getFullYear()} &bull; DETERMINISTIC AUTONOMOUS EXECUTION HUB &bull; HIGH CONTRAST RUNTIME
      </footer>
    </div>
  );
};
