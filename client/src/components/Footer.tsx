import React from 'react';
import { Github } from 'lucide-react';
import { Link } from 'react-router-dom';

export const Footer: React.FC = () => {
  return (
    <footer className="border-t-2 border-black bg-fra-sidebar text-white py-12 px-4 sm:px-6 lg:px-8 text-xs font-mono select-none">
      <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-6">
        <div className="flex items-center gap-3">
          <span className="font-extrabold text-xl tracking-tighter bg-black text-white px-2 py-0.5 border border-neutral-700">
            FRAIDAY_
          </span>
          <div className="text-neutral-400 font-bold">
            AI-NATIVE AUTONOMOUS WORKSPACE CORE
          </div>
        </div>

        {/* Links */}
        <div className="flex flex-wrap items-center justify-center gap-6 font-bold uppercase text-[11px]">
          <a href="#workflow" className="hover:text-fra-yellow hover:underline underline-offset-4">
            [01] Product
          </a>
          <a href="#preview" className="hover:text-fra-yellow hover:underline underline-offset-4">
            [02] Workspace
          </a>
          <a href="#capabilities" className="hover:text-fra-yellow hover:underline underline-offset-4">
            [03] Capabilities
          </a>
          <a href="#security" className="hover:text-fra-yellow hover:underline underline-offset-4">
            [04] Security
          </a>
          <a
            href="https://github.com/medikushal282-cyber/friday"
            target="_blank"
            rel="noreferrer"
            className="hover:text-fra-yellow hover:underline underline-offset-4 flex items-center gap-1"
          >
            <Github className="w-3.5 h-3.5" />
            GitHub
          </a>
          <Link to="/privacy" className="hover:text-fra-yellow hover:underline underline-offset-4">
            Privacy
          </Link>
          <Link to="/terms" className="hover:text-fra-yellow hover:underline underline-offset-4">
            Terms
          </Link>
        </div>

        <div className="text-neutral-500 text-center md:text-right font-bold text-[10px]">
          &copy; {new Date().getFullYear()} FRAIDAY &bull; ENGINEERED FOR AUTONOMY
        </div>
      </div>
    </footer>
  );
};
