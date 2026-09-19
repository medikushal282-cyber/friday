import React, { useState } from 'react';

interface ArtifactViewerProps {
  filename: string;
  content: string;
  diff?: string;
  previousContent?: string;
  operation?: 'created' | 'updated' | 'read' | 'deleted';
  onRun?: (filename: string) => void;
  onContinue?: () => void;
}

export const ArtifactViewer: React.FC<ArtifactViewerProps> = ({
  filename,
  content,
  diff,
  previousContent,
  operation = 'created',
  onRun,
  onContinue
}) => {
  const [viewMode, setViewMode] = useState<'code' | 'diff'>(diff ? 'diff' : 'code');
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  const lines = content.split('\n');

  return (
    <div className="border-2 border-fra-black bg-white shadow-brutal my-3 font-mono text-xs select-none">
      {/* Header bar */}
      <div className="flex items-center justify-between px-3 py-2 border-b-2 border-fra-black bg-neutral-100">
        <div className="flex items-center space-x-2">
          <span className="font-extrabold text-neutral-900">{filename}</span>
          <span className="text-[9px] uppercase px-1.5 py-0.5 font-bold border border-black">
            {operation}
          </span>
          {diff && (
            <span className="text-[10px] text-neutral-600 bg-white px-1.5 py-0.5 border border-neutral-300">
              {diff}
            </span>
          )}
        </div>

        <div className="flex items-center space-x-1.5">
          {diff && (
            <button
              onClick={() => setViewMode(viewMode === 'code' ? 'diff' : 'code')}
              className="px-2 py-0.5 text-[10px] font-bold border border-black shadow-brutal-sm"
            >
              {viewMode === 'diff' ? 'Show Code' : 'Show Diff'}
            </button>
          )}

          <button
            onClick={handleCopy}
            className="px-2 py-0.5 text-[10px] font-bold border border-black bg-white hover:bg-neutral-50 shadow-brutal-sm"
          >
            {copied ? 'Copied!' : 'Copy'}
          </button>

          {onRun && filename.endsWith('.py') && (
            <button
              onClick={() => onRun(filename)}
              className="px-2 py-0.5 text-[10px] font-bold border border-black bg-fra-green text-white hover:bg-green-700 shadow-brutal-sm"
            >
              Run Script
            </button>
          )}

          {onContinue && (
            <button
              onClick={onContinue}
              className="px-2 py-0.5 text-[10px] font-bold border border-black bg-black text-white hover:bg-neutral-800 shadow-brutal-sm"
            >
              Continue Working
            </button>
          )}
        </div>
      </div>

      {/* Code body */}
      <div className="p-3 bg-neutral-950 text-neutral-100 overflow-x-auto max-h-72">
        {viewMode === 'diff' && previousContent ? (
          <div className="font-mono text-[11px] leading-relaxed">
            {previousContent.split('\n').map((l, idx) => (
              <div key={'old-' + idx} className="text-red-400 bg-red-950/40 px-1">
                - {l}
              </div>
            ))}
            {lines.map((l, idx) => (
              <div key={'new-' + idx} className="text-emerald-400 bg-emerald-950/40 px-1">
                + {l}
              </div>
            ))}
          </div>
        ) : (
          <table className="w-full text-left font-mono text-[11px] leading-relaxed">
            <tbody>
              {lines.map((line, idx) => (
                <tr key={idx} className="hover:bg-neutral-900">
                  <td className="text-neutral-600 select-none pr-3 text-right w-8">{idx + 1}</td>
                  <td className="text-neutral-200 whitespace-pre">{line}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
};
