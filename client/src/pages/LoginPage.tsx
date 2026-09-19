import React, { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { AuthLayout } from '../layouts/AuthLayout';
import { useAuth } from '../stores/AuthContext';
import { Mail, Lock, AlertCircle, ArrowRight, Loader2, CheckCircle2 } from 'lucide-react';
import { apiRequest } from '../services/api';

export const LoginPage: React.FC = () => {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const from = (location.state as any)?.from?.pathname || '/workspace';

  const [formData, setFormData] = useState({
    email: '',
    password: '',
    rememberMe: true,
  });

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isUnverified, setIsUnverified] = useState(false);
  const [resendStatus, setResendStatus] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);
    setIsUnverified(false);
    setResendStatus(null);

    if (!formData.email || !formData.password) {
      setErrorMessage('Please provide both email and password.');
      return;
    }

    setIsSubmitting(true);
    try {
      await login({
        email: formData.email,
        password: formData.password,
      });
      navigate(from, { replace: true });
    } catch (err: any) {
      if (err.code === 'EMAIL_UNVERIFIED') {
        setIsUnverified(true);
        setErrorMessage('Your account email has not been verified yet.');
      } else {
        setErrorMessage(err.message || 'Invalid email or password.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleResend = async () => {
    try {
      await apiRequest('/auth/resend-verification', {
        method: 'POST',
        body: JSON.stringify({ email: formData.email }),
      });
      setResendStatus('A new verification email has been dispatched to your inbox.');
    } catch {
      setResendStatus('Failed to resend verification email. Please try again.');
    }
  };

  return (
    <AuthLayout
      title="Sign in to frAIday"
      subtitle="Enter your verified credentials to access the execution workspace."
    >
      {errorMessage && (
        <div className="mb-4 p-3 border-2 border-black bg-red-100 text-xs text-black font-mono shadow-brutal-sm flex items-start gap-2">
          <AlertCircle className="w-4 h-4 text-red-600 shrink-0 mt-0.5" />
          <div className="flex-1">
            <span className="font-bold">{errorMessage}</span>
            {isUnverified && (
              <div className="mt-2">
                <button
                  type="button"
                  onClick={handleResend}
                  className="text-[11px] font-mono underline font-bold text-black hover:bg-fra-yellow px-1"
                >
                  Resend verification email &rarr;
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {resendStatus && (
        <div className="mb-4 p-3 border-2 border-black bg-green-100 text-xs text-black font-mono shadow-brutal-sm flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-green-700 shrink-0" />
          <span className="font-bold">{resendStatus}</span>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Email */}
        <div>
          <label htmlFor="loginEmail" className="block text-[11px] font-mono font-bold uppercase text-black mb-1">
            Email Address
          </label>
          <div className="relative">
            <Mail className="w-4 h-4 text-neutral-500 absolute left-3 top-3" />
            <input
              id="loginEmail"
              name="email"
              type="email"
              required
              value={formData.email}
              onChange={(e) => setFormData({ ...formData, email: e.target.value })}
              placeholder="developer@company.com"
              className="w-full border-2 border-black bg-white pl-9 pr-3 py-2.5 text-xs font-mono text-black placeholder-neutral-400 shadow-brutal-sm focus:outline-none focus:bg-yellow-50/70 focus:border-black transition-colors"
            />
          </div>
        </div>

        {/* Password */}
        <div>
          <div className="flex items-center justify-between mb-1">
            <label htmlFor="loginPassword" className="block text-[11px] font-mono font-bold uppercase text-black">
              Password
            </label>
            <Link
              to="/forgot-password"
              className="text-[11px] font-mono font-bold text-neutral-600 hover:text-black hover:underline"
            >
              Forgot password?
            </Link>
          </div>
          <div className="relative">
            <Lock className="w-4 h-4 text-neutral-500 absolute left-3 top-3" />
            <input
              id="loginPassword"
              name="password"
              type="password"
              required
              value={formData.password}
              onChange={(e) => setFormData({ ...formData, password: e.target.value })}
              placeholder="••••••••••••"
              className="w-full border-2 border-black bg-white pl-9 pr-3 py-2.5 text-xs font-mono text-black placeholder-neutral-400 shadow-brutal-sm focus:outline-none focus:bg-yellow-50/70 focus:border-black transition-colors"
            />
          </div>
        </div>

        {/* Remember me */}
        <div className="flex items-center gap-2 pt-1 font-mono">
          <input
            type="checkbox"
            id="remember"
            checked={formData.rememberMe}
            onChange={(e) => setFormData({ ...formData, rememberMe: e.target.checked })}
            className="w-4 h-4 border-2 border-black rounded-none text-black focus:ring-0 cursor-pointer accent-black"
          />
          <label htmlFor="remember" className="text-[11px] text-neutral-700 cursor-pointer select-none">
            Remember session for 7 days
          </label>
        </div>

        {/* Submit button */}
        <button
          type="submit"
          disabled={isSubmitting}
          className="w-full mt-2 py-3 border-2 border-black bg-fra-yellow text-black font-black text-xs shadow-brutal hover:bg-black hover:text-fra-yellow transition-all flex items-center justify-center gap-2 uppercase tracking-wider disabled:opacity-50"
        >
          {isSubmitting ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              AUTHENTICATING...
            </>
          ) : (
            <>
              <span>AUTHENTICATE &amp; ENTER</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </>
          )}
        </button>
      </form>

      <div className="mt-5 pt-3 border-t-2 border-black text-center text-xs font-mono text-neutral-700">
        Don't have an account yet?{' '}
        <Link to="/register" className="text-black font-black underline hover:bg-fra-yellow px-1">
          CREATE ACCOUNT
        </Link>
      </div>
    </AuthLayout>
  );
};
