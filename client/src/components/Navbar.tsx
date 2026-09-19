import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { ArrowRight, Menu, X, Shield, Terminal } from 'lucide-react';

interface NavbarProps {
  isAuthenticated?: boolean;
  userName?: string;
  onLogout?: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({ isAuthenticated, userName, onLogout }) => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const location = useLocation();

  const isAuthPage = ['/login', '/register', '/forgot-password', '/reset-password'].includes(location.pathname);

  return (
    <header className="h-14 border-b-2 border-black bg-fra-cream flex items-center justify-between px-4 z-40 select-none fixed top-0 left-0 right-0">
      {/* Brand & Technical Metadata */}
      <div className="flex items-center space-x-4">
        <Link to="/" className="flex items-center space-x-2 group">
          <div className="w-8 h-8 border-2 border-black bg-fra-yellow text-black flex items-center justify-center font-mono font-black text-xs shadow-brutal-sm group-hover:bg-black group-hover:text-fra-yellow transition-all">
            <Terminal className="w-4 h-4 stroke-[2.5]" />
          </div>
          <span className="font-extrabold text-2xl tracking-tighter bg-black text-white px-2 py-0.5 mr-1 group-hover:bg-fra-yellow group-hover:text-black transition-colors">
            FRAIDAY_
          </span>
        </Link>
        <div className="border-l-2 border-black pl-3 text-[9px] leading-tight font-mono font-bold tracking-tight text-neutral-800 hidden md:block">
          INTENT IN. OUTCOME OUT.<br />
          AUTONOMOUS WORKSPACE CORE &bull; <span className="text-black font-extrabold">v0.1</span>
        </div>
      </div>

      {/* Center Navigation */}
      {!isAuthPage && (
        <nav className="hidden lg:flex items-center space-x-6 text-[11px] font-mono font-bold uppercase tracking-wider">
          <a href="#workflow" className="hover:underline underline-offset-4 decoration-2">
            [01] How it Works
          </a>
          <a href="#preview" className="hover:underline underline-offset-4 decoration-2">
            [02] Workspace
          </a>
          <a href="#capabilities" className="hover:underline underline-offset-4 decoration-2">
            [03] Capabilities
          </a>
          <a href="#outcomes" className="hover:underline underline-offset-4 decoration-2">
            [04] Outcomes
          </a>
          <a href="#security" className="hover:underline underline-offset-4 decoration-2 flex items-center gap-1">
            <Shield className="w-3.5 h-3.5" />
            Security
          </a>
        </nav>
      )}

      {/* Right Controls */}
      <div className="hidden md:flex items-center space-x-3">
        {isAuthenticated ? (
          <div className="flex items-center space-x-2">
            <Link
              to="/workspace"
              className="flex items-center space-x-1.5 border-2 border-black bg-white px-3 py-1 text-[11px] font-bold shadow-brutal hover:bg-fra-yellow transition-colors font-mono"
            >
              <span className="text-xs font-black text-black">[WS]</span>
              <span>{userName || 'User'}</span>
            </Link>
            <Link
              to="/settings/account"
              className="border-2 border-black bg-white px-3 py-1 text-[11px] font-bold shadow-brutal hover:bg-neutral-100 transition-colors font-mono"
            >
              Settings
            </Link>
            {onLogout && (
              <button
                onClick={onLogout}
                className="border-2 border-black bg-fra-red text-white px-3 py-1 text-[11px] font-bold shadow-brutal hover:bg-red-600 transition-colors font-mono"
              >
                Log out
              </button>
            )}
          </div>
        ) : (
          <div className="flex items-center space-x-3">
            <Link
              to="/login"
              className="border-2 border-black bg-white px-3.5 py-1.5 text-[11px] font-mono font-bold shadow-brutal hover:bg-neutral-100 hover:-translate-y-0.5 transition-all"
            >
              LOG IN
            </Link>
            <Link
              to="/register"
              className="bg-fra-yellow text-black font-black text-[12px] py-1.5 px-4 border-2 border-black flex items-center space-x-1.5 shadow-brutal hover:bg-black hover:text-fra-yellow hover:-translate-y-0.5 transition-all font-mono"
            >
              <span>GET STARTED</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        )}
      </div>

      {/* Mobile Menu Button */}
      <div className="md:hidden flex items-center">
        <button
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          className="border-2 border-black bg-fra-cream-card p-1 shadow-brutal"
          aria-label="Toggle Navigation"
        >
          {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>
      </div>

      {/* Mobile Drawer */}
      {mobileMenuOpen && (
        <div className="md:hidden absolute top-14 left-0 right-0 border-b-2 border-black bg-fra-cream p-4 space-y-3 shadow-brutal-lg font-mono text-xs">
          <a
            href="#workflow"
            onClick={() => setMobileMenuOpen(false)}
            className="block font-bold py-1 hover:underline"
          >
            [01] How it Works
          </a>
          <a
            href="#preview"
            onClick={() => setMobileMenuOpen(false)}
            className="block font-bold py-1 hover:underline"
          >
            [02] Workspace
          </a>
          <a
            href="#capabilities"
            onClick={() => setMobileMenuOpen(false)}
            className="block font-bold py-1 hover:underline"
          >
            [03] Capabilities
          </a>
          <a
            href="#security"
            onClick={() => setMobileMenuOpen(false)}
            className="block font-bold py-1 hover:underline"
          >
            [04] Security
          </a>
          <div className="pt-2 border-t-2 border-black flex flex-col gap-2">
            {isAuthenticated ? (
              <>
                <Link
                  to="/workspace"
                  onClick={() => setMobileMenuOpen(false)}
                  className="w-full text-center py-2 bg-fra-yellow border-2 border-black font-bold shadow-brutal"
                >
                  Workspace
                </Link>
                <Link
                  to="/settings/account"
                  onClick={() => setMobileMenuOpen(false)}
                  className="w-full text-center py-2 bg-white border-2 border-black font-bold shadow-brutal"
                >
                  Account Settings
                </Link>
              </>
            ) : (
              <>
                <Link
                  to="/login"
                  onClick={() => setMobileMenuOpen(false)}
                  className="w-full text-center py-2 bg-white border-2 border-black font-bold shadow-brutal"
                >
                  Log in
                </Link>
                <Link
                  to="/register"
                  onClick={() => setMobileMenuOpen(false)}
                  className="w-full text-center py-2 bg-fra-yellow border-2 border-black font-bold shadow-brutal"
                >
                  Get Started
                </Link>
              </>
            )}
          </div>
        </div>
      )}
    </header>
  );
};
