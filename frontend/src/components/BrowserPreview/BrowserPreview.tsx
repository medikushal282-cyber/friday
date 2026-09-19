"use client";

import React, { useState, useRef } from 'react';

interface BrowserPreviewProps {
  url: string;
  isOpen: boolean;
  onClose: () => void;
  title?: string;
}

export const BrowserPreview: React.FC<BrowserPreviewProps> = ({
  url,
  isOpen,
  onClose,
  title = "frAIday Live Browser Preview"
}) => {
  const [deviceMode, setDeviceMode] = useState<'desktop' | 'tablet' | 'mobile'>('desktop');
  const [iframeKey, setIframeKey] = useState<number>(1);
  const [currentUrl, setCurrentUrl] = useState<string>(url);
  const [inputUrl, setInputUrl] = useState<string>(url);
  const iframeRef = useRef<HTMLIFrameElement | null>(null);

  React.useEffect(() => {
    setCurrentUrl(url);
    setInputUrl(url);
  }, [url]);

  if (!isOpen) return null;

  const handleNavigate = (e: React.FormEvent) => {
    e.preventDefault();
    let dest = inputUrl.trim();
    if (!dest) return;
    if (!dest.startsWith('http://') && !dest.startsWith('https://')) {
      dest = `http://localhost:8000/api/preview/${dest}`;
    }
    setCurrentUrl(dest);
    setInputUrl(dest);
    setIframeKey(prev => prev + 1);
  };

  const handleReload = () => {
    setIframeKey(prev => prev + 1);
  };

  const handleOpenNewTab = () => {
    window.open(currentUrl, '_blank', 'noopener,noreferrer');
  };

  const getContainerWidth = () => {
    switch (deviceMode) {
      case 'mobile':
        return 'max-w-[390px]';
      case 'tablet':
        return 'max-w-[768px]';
      default:
        return 'w-full';
    }
  };

  return (
    <div className="border-2 border-fra-black bg-white shadow-brutal flex flex-col h-[560px] mb-4 overflow-hidden select-none">
      {/* Browser Chrome Header */}
      <div className="bg-[#0A0A0A] text-white px-3 py-2 border-b-2 border-black flex items-center justify-between gap-3">
        {/* Left Window Controls & Title */}
        <div className="flex items-center space-x-2">
          <div className="flex items-center space-x-1.5 mr-1">
            <span className="w-2.5 h-2.5 rounded-full bg-red-500 inline-block"></span>
            <span className="w-2.5 h-2.5 rounded-full bg-yellow-500 inline-block"></span>
            <span className="w-2.5 h-2.5 rounded-full bg-green-500 inline-block"></span>
          </div>
          <span className="font-mono font-bold text-[11px] text-neutral-300 hidden sm:inline">
            {title}
          </span>
        </div>

        {/* Center URL Address Bar */}
        <form onSubmit={handleNavigate} className="flex-1 max-w-xl mx-auto flex items-center bg-[#171717] border border-neutral-700 px-2 py-1 rounded text-xs font-mono text-neutral-200">
          <span className="text-neutral-500 mr-1.5 text-[10px]">🔒</span>
          <input
            type="text"
            value={inputUrl}
            onChange={(e) => setInputUrl(e.target.value)}
            className="flex-1 bg-transparent text-[11px] text-fra-yellow focus:outline-none font-mono"
            placeholder="Type file name (e.g. index.html, main.py) or URL..."
          />
          <button type="submit" className="text-[10px] text-neutral-400 hover:text-white ml-1 px-1 font-bold">
            GO
          </button>
          <div className="flex items-center space-x-1.5 ml-2 border-l border-neutral-800 pl-2">
            <span className="w-2 h-2 rounded-full bg-fra-green animate-pulse" title="Live Auto-Sync Active"></span>
            <span className="text-[9px] text-fra-green font-bold uppercase hidden md:inline">SYNC</span>
          </div>
        </form>

        {/* Right Action Tools */}
        <div className="flex items-center space-x-1.5 text-xs font-mono">
          {/* Reload Button */}
          <button
            onClick={handleReload}
            className="border border-neutral-700 bg-neutral-900 hover:bg-neutral-800 text-white px-2 py-0.5 text-[11px] flex items-center gap-1"
            title="Reload Frame"
          >
            <span>↻</span>
          </button>

          {/* Device Switcher */}
          <div className="hidden lg:flex items-center border border-neutral-700 bg-neutral-900 text-[10px]">
            <button
              onClick={() => setDeviceMode('desktop')}
              className={`px-1.5 py-0.5 ${deviceMode === 'desktop' ? 'bg-fra-yellow text-black font-bold' : 'text-neutral-400'}`}
              title="Desktop View"
            >
              Desktop
            </button>
            <button
              onClick={() => setDeviceMode('tablet')}
              className={`px-1.5 py-0.5 ${deviceMode === 'tablet' ? 'bg-fra-yellow text-black font-bold' : 'text-neutral-400'}`}
              title="Tablet View"
            >
              Tablet
            </button>
            <button
              onClick={() => setDeviceMode('mobile')}
              className={`px-1.5 py-0.5 ${deviceMode === 'mobile' ? 'bg-fra-yellow text-black font-bold' : 'text-neutral-400'}`}
              title="Mobile View"
            >
              Mobile
            </button>
          </div>

          {/* Open in New Browser Tab Button */}
          <button
            onClick={handleOpenNewTab}
            className="border-2 border-black bg-fra-yellow text-black font-bold text-[10px] px-2.5 py-1 flex items-center space-x-1 shadow-brutal-sm hover:bg-yellow-400 uppercase tracking-wider"
          >
            <span>Open in Tab</span>
            <span>↗</span>
          </button>

          {/* Close Dock Button */}
          <button
            onClick={onClose}
            className="text-neutral-400 hover:text-white px-1.5 text-sm font-bold"
            title="Close Preview"
          >
            ✕
          </button>
        </div>
      </div>

      {/* Frame Container */}
      <div className="flex-1 bg-neutral-100 flex items-center justify-center overflow-hidden p-2">
        <div className={`h-full ${getContainerWidth()} mx-auto transition-all duration-300 border-2 border-neutral-300 bg-white shadow-md flex flex-col overflow-hidden`}>
          <iframe
            key={iframeKey}
            ref={iframeRef}
            src={currentUrl}
            title="Live Preview"
            className="w-full h-full border-0"
            sandbox="allow-scripts allow-same-origin allow-forms allow-modals allow-popups"
          />
        </div>
      </div>
    </div>
  );
};

export default BrowserPreview;
