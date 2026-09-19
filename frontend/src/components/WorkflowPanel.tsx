import React from 'react';

interface WorkflowStep {
  id: string;
  description: string;
  agent: string;
  action: string;
  target?: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'blocked' | 'waiting_for_approval';
  reason?: string;
  result?: any;
}

interface WorkflowPanelProps {
  steps: WorkflowStep[];
  selectedStepId: string | null;
  onSelectStep: (stepId: string) => void;
  approvalRequired?: boolean;
  approvalRequest?: any;
  onApprove?: () => void;
  onReject?: () => void;
}

export const WorkflowPanel: React.FC<WorkflowPanelProps> = ({
  steps,
  selectedStepId,
  onSelectStep,
  approvalRequired,
  approvalRequest,
  onApprove,
  onReject
}) => {
  return (
    <div className="flex flex-col h-full bg-fra-cream text-black font-mono select-none">
      <div className="p-3 border-b-2 border-fra-black bg-white flex items-center justify-between">
        <span className="font-extrabold text-xs uppercase tracking-wider">Dynamic Workflow</span>
        <span className="text-[10px] bg-fra-yellow px-1.5 py-0.5 border border-black font-bold">
          {steps.filter(s => s.status === 'completed').length}/{steps.length} Steps
        </span>
      </div>

      {approvalRequired && approvalRequest && (
        <div className="m-3 p-3 border-2 border-red-600 bg-red-50 shadow-brutal animate-pulse">
          <div className="flex items-center justify-between mb-1">
            <span className="font-black text-xs text-red-700 uppercase">[ APPROVAL REQUIRED ]</span>
          </div>
          <p className="text-[11px] font-bold text-neutral-800 mb-1">
            Action: <span className="underline">{approvalRequest.tool?.toUpperCase()}</span> on <span className="font-extrabold">{approvalRequest.path}</span>
          </p>
          <p className="text-[10px] text-neutral-600 mb-2">{approvalRequest.reason || 'This destructive operation requires explicit user authorization.'}</p>
          <div className="flex items-center space-x-2">
            <button
              onClick={onReject}
              className="flex-1 py-1 text-[11px] font-bold border-2 border-black bg-white hover:bg-neutral-100 shadow-brutal-sm"
            >
              Reject
            </button>
            <button
              onClick={onApprove}
              className="flex-1 py-1 text-[11px] font-bold border-2 border-black bg-red-600 text-white hover:bg-red-700 shadow-brutal-sm"
            >
              Approve
            </button>
          </div>
        </div>
      )}

      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {steps.length === 0 ? (
          <div className="text-neutral-500 italic text-[11px] text-center p-4">
            Workflow will appear once the objective is analyzed...
          </div>
        ) : (
          steps.map((step) => {
            const isSelected = selectedStepId === step.id;
            const isCompleted = step.status === 'completed';
            const isRunning = step.status === 'running';
            const isFailed = step.status === 'failed';
            const isBlocked = step.status === 'blocked' || step.status === 'waiting_for_approval';

            return (
              <div
                key={step.id}
                onClick={() => onSelectStep(step.id)}
                className={`border-2 border-fra-black p-2 cursor-pointer transition-all shadow-brutal-sm ${
                  isSelected ? 'bg-fra-yellow border-black font-bold' :
                  isRunning ? 'bg-amber-50 border-amber-500 animate-pulse' :
                  isCompleted ? 'bg-white hover:bg-neutral-50' :
                  isFailed ? 'bg-red-50 border-red-500' :
                  'bg-neutral-50 hover:bg-white text-neutral-600'
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center space-x-1.5">
                    <span className={`text-[10px] font-black ${
                      isCompleted ? 'text-fra-green' :
                      isRunning ? 'text-amber-600' :
                      isFailed ? 'text-red-600' :
                      isBlocked ? 'text-orange-600' :
                      'text-neutral-400'
                    }`}>
                      {isCompleted ? '[✓]' : isRunning ? '[●]' : isFailed ? '[✗]' : isBlocked ? '[!]' : '[○]'}
                    </span>
                    <span className="text-[11px] font-bold text-neutral-900 line-clamp-1">{step.description}</span>
                  </div>
                  <span className="text-[9px] uppercase px-1 border border-neutral-300 bg-neutral-100 text-neutral-600 font-bold">
                    {step.agent}
                  </span>
                </div>

                <div className="flex items-center justify-between text-[9px] text-neutral-500 pl-4">
                  <span>Action: {step.action}</span>
                  {step.target && <span className="truncate max-w-[120px]">{step.target}</span>}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
