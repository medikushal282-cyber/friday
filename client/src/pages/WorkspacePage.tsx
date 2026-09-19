import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../stores/AuthContext';
import { ShieldCheck, CheckCircle2, Cpu, Settings, LogOut, Terminal, ArrowUpRight, Play } from 'lucide-react';
import LatticeLoader from '../components/LatticeLoader';

export const WorkspacePage: React.FC = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  return (
    <div className="min-h-screen bg-fra-cream text-black flex flex-col font-sans select-none">
      {/* Top Header - Exact Agent Core Aesthetic */}
      <header className="h-14 border-b-2 border-fra-black bg-fra-cream flex items-center justify-between px-3 flex-shrink-0 z-30 select-none">
        <div className="flex items-center space-x-4">
          <Link to="/" className="flex items-center group">
            <span className="font-extrabold text-2xl tracking-tighter bg-black text-white px-2 py-0.5 mr-1 group-hover:bg-fra-yellow group-hover:text-black transition-colors">
              FRAIDAY_
            </span>
          </Link>
          <div className="border-l-2 border-fra-black pl-3 text-[9px] leading-tight font-mono font-bold tracking-tight text-neutral-800 hidden md:block">
            AUTHENTICATED OPERATOR: <span className="text-black font-extrabold">{user?.name || 'Verified Operator'}</span><br />
            SECURITY PERIMETER: <span className="text-fra-green font-extrabold">SESSION ACTIVE &bull; VERIFIED</span> | AUTH: <span className="text-black font-extrabold">256-BIT HASHED</span>
          </div>
        </div>

        <nav className="hidden lg:flex items-center space-x-6 text-[11px] font-mono font-semibold">
          <span className="underline underline-offset-4 decoration-2 font-bold cursor-pointer">Workspace</span>
          <Link to="/settings/account" className="hover:underline underline-offset-4 decoration-2">Account Settings</Link>
          <a href="http://localhost:3000" target="_blank" rel="noreferrer" className="hover:underline underline-offset-4 decoration-2 flex items-center gap-1">
            <span>Agent Core</span>
            <ArrowUpRight className="w-3 h-3" />
          </a>
        </nav>

        <div className="flex items-center space-x-3">
          <Link
            to="/settings/account"
            className="flex items-center space-x-2 border-2 border-fra-black bg-fra-cream-card px-2.5 py-1 text-[11px] font-bold shadow-brutal hover:bg-fra-yellow transition-colors font-mono"
          >
            <span className="text-xs font-black">[USER]</span>
            <div className="flex flex-col text-left leading-none">
              <span className="text-[8px] font-mono uppercase text-neutral-500 font-bold">OPERATOR</span>
              <span className="truncate max-w-[100px]">{user?.name}</span>
            </div>
          </Link>
          <button
            onClick={handleLogout}
            className="border-2 border-fra-black bg-fra-red text-white px-2.5 py-1 text-[11px] font-bold shadow-brutal hover:bg-red-600 transition-colors font-mono flex items-center gap-1"
          >
            <LogOut className="w-3 h-3" />
            <span>EXIT</span>
          </button>
        </div>
      </header>

      {/* Main Split Layout */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left Dark Sidebar - Mirroring Agent Core */}
        <aside className="w-64 bg-fra-sidebar text-white border-r-2 border-fra-black flex flex-col justify-between flex-shrink-0 select-none z-20">
          <div className="overflow-y-auto dark-scroll p-3 flex-1">
            <a
              href="http://localhost:3000"
              target="_blank"
              rel="noreferrer"
              className="w-full bg-fra-yellow text-fra-black font-extrabold text-[12px] py-2 px-3 border-2 border-black flex items-center justify-center space-x-2 shadow-brutal hover:bg-fra-yellow-hover transition-all mb-4"
            >
              <span className="text-base leading-none font-black">+</span>
              <span>Launch Execution DAG</span>
            </a>

            <div className="space-y-1 mb-5 text-[11px] font-mono">
              <div className="flex items-center space-x-2 text-white bg-neutral-900 px-2 py-1.5 rounded cursor-pointer font-bold">
                <span className="text-fra-yellow">[AUTH]</span>
                <span>Protected Workspace</span>
              </div>
              <Link
                to="/settings/account"
                className="flex items-center space-x-2 text-neutral-400 hover:text-white px-2 py-1.5 rounded cursor-pointer hover:bg-neutral-900 transition-colors"
              >
                <span className="font-bold text-neutral-500">[CONF]</span>
                <span>Security &amp; Credentials</span>
              </Link>
            </div>

            <div className="mb-5 border-t border-neutral-800 pt-3">
              <div className="flex items-center justify-between text-neutral-400 font-mono text-[10px] uppercase font-bold tracking-wider mb-2 px-1">
                <span>Identity Context</span>
              </div>
              <div className="p-2 border border-neutral-800 bg-[#121212] space-y-1 text-[10px] font-mono">
                <div className="text-neutral-400">ID: {user?.id.slice(0, 8)}...</div>
                <div className="text-neutral-400 truncate">EMAIL: {user?.email}</div>
                <div className="text-fra-green font-bold">[STATUS: EMAIL_VERIFIED]</div>
              </div>
            </div>

            <div className="mb-4 pt-3 border-t border-neutral-800">
              <div className="text-neutral-500 font-mono text-[10px] uppercase font-bold tracking-wider mb-2 px-1">
                Security Controls
              </div>
              <div className="space-y-1 text-[11px] font-mono">
                <div className="px-2 py-1 text-neutral-400 text-[10px]">
                  &bull; HTTP-Only Cookie Active<br />
                  &bull; 256-Bit Session Hash<br />
                  &bull; Zero Plaintext Storage
                </div>
              </div>
            </div>
          </div>

          <div className="p-3 border-t border-neutral-800 text-[9px] font-mono text-neutral-500">
            FRAIDAY AI-NATIVE HUB &bull; ONLINE
          </div>
        </aside>

        {/* Right Main Content Panel */}
        <main className="flex-1 bg-fra-cream p-6 overflow-y-auto font-sans">
          <div className="max-w-4xl mx-auto space-y-6">
            {/* Operator Greeting Header */}
            <div className="border-2 border-black bg-fra-cream-card p-5 shadow-brutal-lg flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div>
                <span className="text-[10px] font-mono font-black uppercase bg-black text-white px-2 py-0.5">
                  [OPERATOR_VERIFIED]
                </span>
                <h1 className="text-2xl font-black tracking-tight text-black mt-2">
                  Welcome to frAIday, {user?.name}
                </h1>
                <p className="text-xs font-mono text-neutral-700 mt-1">
                  You have successfully passed the security gate. Your authenticated session is active and monitored.
                </p>
              </div>

              <div className="flex items-center gap-2">
                <Link
                  to="/settings/account"
                  className="px-3 py-2 border-2 border-black bg-white text-black font-mono font-bold text-xs shadow-brutal hover:bg-fra-yellow transition-colors flex items-center gap-1.5"
                >
                  <Settings className="w-3.5 h-3.5" />
                  <span>SETTINGS</span>
                </Link>
                <button
                  onClick={handleLogout}
                  className="px-3 py-2 border-2 border-black bg-fra-red text-white font-mono font-bold text-xs shadow-brutal hover:bg-red-600 transition-colors flex items-center gap-1.5"
                >
                  <LogOut className="w-3.5 h-3.5" />
                  <span>SIGN OUT</span>
                </button>
              </div>
            </div>

            {/* Three Status Diagnostic Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="border-2 border-black bg-white p-4 shadow-brutal">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[9px] font-mono font-bold uppercase text-neutral-500">AUTH_STATUS</span>
                  <ShieldCheck className="w-4 h-4 text-green-600" />
                </div>
                <div className="text-base font-extrabold text-black font-mono flex items-center gap-1">
                  <CheckCircle2 className="w-4 h-4 text-green-600" />
                  <span>VERIFIED</span>
                </div>
                <p className="text-[11px] font-mono text-neutral-600 mt-1">
                  Email verification cryptographic challenge resolved.
                </p>
              </div>

              <div className="border-2 border-black bg-white p-4 shadow-brutal">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[9px] font-mono font-bold uppercase text-neutral-500">SESSION_STATE</span>
                  <Terminal className="w-4 h-4 text-black" />
                </div>
                <div className="text-base font-extrabold text-black font-mono flex items-center gap-1">
                  <CheckCircle2 className="w-4 h-4 text-green-600" />
                  <span>ACTIVE_TOKEN</span>
                </div>
                <p className="text-[11px] font-mono text-neutral-600 mt-1">
                  Server-side session mapped in MySQL database.
                </p>
              </div>

              <div className="border-2 border-black bg-white p-4 shadow-brutal">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[9px] font-mono font-bold uppercase text-neutral-500">AGENT_CORE_DISPATCH</span>
                  <Cpu className="w-4 h-4 text-black" />
                </div>
                <div className="text-base font-extrabold text-black font-mono flex items-center gap-1">
                  <span className="w-2 h-2 rounded-full bg-green-500 animate-ping mr-1" />
                  <span>DISPATCH_READY</span>
                </div>
                <p className="text-[11px] font-mono text-neutral-600 mt-1">
                  Next.js + Python autonomous runtime listening on :3000/:8000.
                </p>
                <div className="mt-3 pt-2.5 border-t border-neutral-200">
                  <LatticeLoader
                    status="working"
                    label="Core Active"
                    pattern="orbit"
                    grid={3}
                    shape="round"
                    cellSize={5}
                    gap={2}
                    fontSize={11}
                    step={90}
                    idleOpacity={0.2}
                    showTimer={true}
                  />
                </div>
              </div>
            </div>

            {/* Launch Agent Core Canvas Banner */}
            <div className="border-2 border-black bg-fra-yellow p-6 shadow-brutal-lg">
              <div className="flex items-start justify-between">
                <div>
                  <span className="text-[10px] font-mono font-black uppercase bg-black text-white px-2 py-0.5">
                    [INTEGRATION_BRIDGE]
                  </span>
                  <h2 className="text-xl font-black text-black mt-2">
                    Enter the Autonomous Execution Core
                  </h2>
                  <p className="text-xs font-mono text-black/80 mt-1 max-w-xl leading-relaxed">
                    Launch the live agent execution stream. Dispatch objectives, watch the dynamic DAG generation, inspect tool executions, and authorize security gates.
                  </p>
                </div>
                <div className="w-10 h-10 border-2 border-black bg-white flex items-center justify-center shadow-brutal hidden sm:flex">
                  <Play className="w-5 h-5 text-black" />
                </div>
              </div>

              <div className="mt-5 flex flex-wrap gap-3 font-mono">
                <a
                  href="http://localhost:3000"
                  target="_blank"
                  rel="noreferrer"
                  className="border-2 border-black bg-black text-white font-extrabold text-xs px-4 py-2.5 shadow-brutal hover:bg-neutral-800 transition-colors flex items-center gap-2 uppercase tracking-wider"
                >
                  <span>Open Agent Core Interface</span>
                  <ArrowUpRight className="w-4 h-4" />
                </a>
                <Link
                  to="/settings/account"
                  className="border-2 border-black bg-white text-black font-bold text-xs px-4 py-2.5 shadow-brutal hover:bg-fra-cream transition-colors uppercase"
                >
                  Account Settings
                </Link>
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
};
