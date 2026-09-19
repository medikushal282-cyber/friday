import React, { useEffect, useState, useRef } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { AuthLayout } from '../layouts/AuthLayout';
import { useAuth } from '../stores/AuthContext';
import { CheckCircle2, AlertTriangle, Loader2, ArrowRight, Mail, RefreshCw } from 'lucide-react';
import { User } from '../types';

export const VerifyEmailPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token');
  const { verifyEmail, resendVerification } = useAuth();

  const [status, setStatus] = useState<'verifying' | 'success' | 'error'>('verifying');
  const [message, setMessage] = useState<string>('Validating cryptographic token against security register...');
  const [verifiedUser, setVerifiedUser] = useState<User | null>(null);

  // Resend state
  const [resendEmailInput, setResendEmailInput] = useState('');
  const [resendStatus, setResendStatus] = useState<'idle' | 'sending' | 'sent' | 'error'>('idle');
  const [resendMessage, setResendMessage] = useState<string | null>(null);

  const hasExecutedRef = useRef(false);

  useEffect(() => {
    if (!token) {
      setStatus('error');
      setMessage('No verification token was provided in the URL link.');
      return;
    }

    if (hasExecutedRef.current) return;
    hasExecutedRef.current = true;

    const runVerification = async () => {
      try {
        const user = await verifyEmail(token);
        setVerifiedUser(user);
        setStatus('success');
        setMessage('Your email address has been verified and registered in the security core.');
      } catch (err: any) {
        setStatus('error');
        setMessage(err.message || 'Verification link is invalid, expired, or has already been used.');
      }
    };

    runVerification();
  }, [token, verifyEmail]);

  const handleResend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!resendEmailInput.trim()) return;

    setResendStatus('sending');
    setResendMessage(null);
    try {
      const msg = await resendVerification(resendEmailInput.trim());
      setResendStatus('sent');
      setResendMessage(msg || 'A fresh verification link has been dispatched.');
    } catch (err: any) {
      setResendStatus('error');
      setResendMessage(err.message || 'Failed to dispatch new verification link.');
    }
  };

  return (
    <AuthLayout
      title="Email Verification"
      subtitle="Confirming account ownership for frAIday autonomous execution."
    >
      <div className="py-6 text-center space-y-4 font-mono">
        {status === 'verifying' && (
          <div className="flex flex-col items-center gap-3 py-4">
            <div className="w-12 h-12 border-2 border-black bg-white flex items-center justify-center shadow-brutal">
              <Loader2 className="w-6 h-6 text-black animate-spin" />
            </div>
            <p className="text-xs text-neutral-800">{message}</p>
          </div>
        )}

        {status === 'success' && (
          <div className="space-y-4">
            <div className="w-12 h-12 border-2 border-black bg-fra-yellow text-black flex items-center justify-center mx-auto shadow-brutal">
              <CheckCircle2 className="w-6 h-6" />
            </div>
            <div>
              <div className="inline-block px-2 py-0.5 border-2 border-black bg-green-200 text-black text-[10px] font-bold uppercase mb-2 shadow-brutal-sm">
                [SECURITY STATUS: VERIFIED]
              </div>
              <h2 className="text-sm font-black uppercase text-black">Verification Complete</h2>
              <p className="text-xs text-neutral-700 mt-1">{message}</p>
              {verifiedUser && (
                <p className="text-xs font-bold text-black mt-2 bg-yellow-100 p-2 border-2 border-black inline-block">
                  Operator: {verifiedUser.email}
                </p>
              )}
            </div>
            <div className="pt-2">
              <Link
                to="/login"
                className="inline-flex items-center justify-center gap-2 w-full py-3 border-2 border-black bg-fra-yellow text-black font-black text-xs shadow-brutal hover:bg-black hover:text-fra-yellow transition-colors uppercase tracking-wider"
              >
                <span>Sign In to Workspace</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </div>
          </div>
        )}

        {status === 'error' && (
          <div className="space-y-4 text-left">
            <div className="text-center">
              <div className="w-12 h-12 border-2 border-black bg-red-100 text-red-600 flex items-center justify-center mx-auto shadow-brutal mb-3">
                <AlertTriangle className="w-6 h-6" />
              </div>
              <h2 className="text-sm font-black uppercase text-red-600">Verification Failed</h2>
              <p className="text-xs text-neutral-800 mt-1">{message}</p>
            </div>

            {/* Resend Verification Form */}
            <div className="p-3.5 border-2 border-black bg-neutral-50 shadow-brutal-sm space-y-3">
              <div className="flex items-center gap-2 text-xs font-bold text-black uppercase">
                <RefreshCw className="w-3.5 h-3.5" />
                <span>Request a Fresh Verification Link</span>
              </div>
              <p className="text-[11px] text-neutral-600">
                If your link expired or was invalid, enter your registered email below to receive a new link.
              </p>

              {resendStatus === 'sent' ? (
                <div className="p-2.5 border-2 border-black bg-green-100 text-black text-xs space-y-1">
                  <div className="font-bold">✓ Verification Link Dispatched</div>
                  <p className="text-[11px] text-neutral-700">{resendMessage}</p>
                  <p className="text-[10px] text-neutral-600 mt-1">
                    Check your inbox or console output, or visit{' '}
                    <a
                      href="http://localhost:4000/api/auth/test/last-mail"
                      target="_blank"
                      rel="noreferrer"
                      className="underline font-bold"
                    >
                      /api/auth/test/last-mail
                    </a>
                  </p>
                </div>
              ) : (
                <form onSubmit={handleResend} className="space-y-2">
                  <div className="relative">
                    <Mail className="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-500" />
                    <input
                      type="email"
                      required
                      placeholder="operator@fraiday.ai"
                      value={resendEmailInput}
                      onChange={(e) => setResendEmailInput(e.target.value)}
                      className="w-full pl-8 pr-3 py-2 border-2 border-black text-xs font-mono bg-white shadow-brutal-sm focus:outline-none focus:bg-yellow-50/70 focus:border-black transition-colors"
                    />
                  </div>
                  {resendStatus === 'error' && (
                    <p className="text-[11px] text-red-600 font-bold">{resendMessage}</p>
                  )}
                  <button
                    type="submit"
                    disabled={resendStatus === 'sending'}
                    className="w-full py-2.5 border-2 border-black bg-fra-yellow text-black font-black text-xs shadow-brutal hover:bg-black hover:text-fra-yellow transition-colors uppercase disabled:opacity-50"
                  >
                    {resendStatus === 'sending' ? 'Dispatching...' : 'Resend Verification Link'}
                  </button>
                </form>
              )}
            </div>

            <div className="pt-2 flex flex-col gap-2 text-center">
              <Link
                to="/login"
                className="inline-flex items-center justify-center gap-2 w-full py-2 border-2 border-black bg-white text-black font-bold text-xs shadow-brutal hover:bg-neutral-100 transition-colors uppercase"
              >
                Return to Sign In
              </Link>
              <Link
                to="/register"
                className="text-xs text-neutral-600 hover:text-black hover:underline"
              >
                Need to create a new account?
              </Link>
            </div>
          </div>
        )}
      </div>
    </AuthLayout>
  );
};
