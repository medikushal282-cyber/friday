import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../stores/AuthContext';
import { Terminal } from 'lucide-react';

interface ProtectedRouteProps {
  children: React.ReactNode;
  requireVerified?: boolean;
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({
  children,
  requireVerified = true,
}) => {
  const { user, isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="min-h-screen bg-[#08090d] flex items-center justify-center font-mono text-zinc-400">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 rounded border border-blue-500/40 bg-blue-500/10 flex items-center justify-center text-blue-400 animate-pulse">
            <Terminal className="w-4 h-4" />
          </div>
          <span className="text-xs text-zinc-400">Authenticating session...</span>
        </div>
      </div>
    );
  }

  if (!isAuthenticated || !user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (requireVerified && !user.emailVerified) {
    return (
      <div className="min-h-screen bg-[#08090d] text-zinc-100 flex items-center justify-center p-4">
        <div className="max-w-md w-full p-6 rounded-xl border border-amber-500/40 bg-amber-950/20 text-center">
          <h2 className="text-lg font-bold text-amber-300 mb-2">Email Verification Required</h2>
          <p className="text-xs text-zinc-300 mb-4 leading-relaxed">
            Your account ({user.email}) must be verified before entering the autonomous workspace. Please click the link sent to your inbox.
          </p>
          <a
            href="/"
            className="inline-block px-4 py-2 rounded text-xs font-semibold bg-zinc-800 text-zinc-200 hover:bg-zinc-700 transition-colors"
          >
            Return to Home
          </a>
        </div>
      </div>
    );
  }

  return <>{children}</>;
};
