import React, { useState } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { AuthLayout } from '../layouts/AuthLayout';
import { useAuth } from '../stores/AuthContext';
import { Lock, Check, AlertCircle, CheckCircle2, ArrowRight, Loader2 } from 'lucide-react';

export const ResetPasswordPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token');
  const { resetPassword } = useAuth();

  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const hasMinLength = password.length >= 8;
  const hasNumber = /[0-9]/.test(password);
  const hasSpecial = /[^a-zA-Z0-9]/.test(password);
  const passwordsMatch = Boolean(password) && password === confirmPassword;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);

    if (!token) {
      setErrorMessage('Missing password reset token in the link.');
      return;
    }
    if (!hasMinLength || !hasNumber || !hasSpecial) {
      setErrorMessage('Password does not satisfy the security requirements.');
      return;
    }
    if (password !== confirmPassword) {
      setErrorMessage('Passwords do not match.');
      return;
    }

    setIsSubmitting(true);
    try {
      const msg = await resetPassword({ token, password, confirmPassword });
      setSuccessMessage(msg);
    } catch (err: any) {
      setErrorMessage(err.message || 'Password reset failed. The link may have expired or already been used.');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!token) {
    return (
      <AuthLayout title="Reset Password" subtitle="Invalid request.">
        <div className="text-center py-4 space-y-4 font-mono">
          <p className="text-xs text-red-600 font-bold">No reset token was found in the URL.</p>
          <Link
            to="/forgot-password"
            className="inline-block px-4 py-2 border-2 border-black bg-fra-yellow text-black font-bold text-xs shadow-brutal hover:bg-fra-yellow-hover uppercase"
          >
            Request a New Link
          </Link>
        </div>
      </AuthLayout>
    );
  }

  return (
    <AuthLayout
      title="Create New Password"
      subtitle="Choose a secure password. All previous active sessions will be terminated."
    >
      {errorMessage && (
        <div className="mb-4 p-3 border-2 border-black bg-red-100 text-xs text-black font-mono shadow-brutal-sm flex items-start gap-2">
          <AlertCircle className="w-4 h-4 text-red-600 shrink-0 mt-0.5" />
          <span>{errorMessage}</span>
        </div>
      )}

      {successMessage ? (
        <div className="text-center py-4 space-y-4 font-mono">
          <div className="w-12 h-12 border-2 border-black bg-fra-yellow text-black flex items-center justify-center mx-auto shadow-brutal">
            <CheckCircle2 className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-sm font-black uppercase text-black">Password Reset Complete</h2>
            <p className="text-xs text-neutral-700 mt-1">{successMessage}</p>
          </div>
          <div className="pt-2">
            <Link
              to="/login"
              className="inline-flex items-center justify-center gap-2 w-full py-2.5 border-2 border-black bg-fra-yellow text-black font-extrabold text-xs shadow-brutal hover:bg-fra-yellow-hover transition-colors uppercase tracking-wider"
            >
              <span>Sign In with New Password</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-4 font-mono">
          <div>
            <label htmlFor="newPassword" className="block text-[11px] font-bold uppercase text-black mb-1">
              New Password
            </label>
            <div className="relative">
              <Lock className="w-4 h-4 text-neutral-500 absolute left-3 top-3" />
              <input
                id="newPassword"
                name="password"
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••••"
                className="w-full border-2 border-black bg-white pl-9 pr-3 py-2.5 text-xs font-mono text-black placeholder-neutral-400 shadow-brutal-sm focus:outline-none focus:bg-yellow-50/70 focus:border-black transition-colors"
              />
            </div>
            <div className="mt-2.5 p-2.5 border-2 border-black bg-neutral-50 space-y-1.5 text-[10px] shadow-brutal-sm">
              <div className={`flex items-center gap-1.5 font-bold ${hasMinLength ? 'text-black bg-green-200 border border-black px-1.5 py-0.5' : 'text-neutral-500 px-1.5 py-0.5'}`}>
                <Check className="w-3 h-3 stroke-[3]" />
                <span>At least 8 characters</span>
              </div>
              <div className={`flex items-center gap-1.5 font-bold ${hasNumber ? 'text-black bg-green-200 border border-black px-1.5 py-0.5' : 'text-neutral-500 px-1.5 py-0.5'}`}>
                <Check className="w-3 h-3 stroke-[3]" />
                <span>At least 1 numeric digit</span>
              </div>
              <div className={`flex items-center gap-1.5 font-bold ${hasSpecial ? 'text-black bg-green-200 border border-black px-1.5 py-0.5' : 'text-neutral-500 px-1.5 py-0.5'}`}>
                <Check className="w-3 h-3 stroke-[3]" />
                <span>At least 1 special character</span>
              </div>
            </div>
          </div>

          <div>
            <label htmlFor="confirmNewPassword" className="block text-[11px] font-bold uppercase text-black mb-1">
              Confirm New Password
            </label>
            <div className="relative">
              <Lock className="w-4 h-4 text-neutral-500 absolute left-3 top-3" />
              <input
                id="confirmNewPassword"
                name="confirmPassword"
                type="password"
                required
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="••••••••••••"
                className="w-full border-2 border-black bg-white pl-9 pr-3 py-2.5 text-xs font-mono text-black placeholder-neutral-400 shadow-brutal-sm focus:outline-none focus:bg-yellow-50/70 focus:border-black transition-colors"
              />
            </div>
            {confirmPassword && (
              <div className={`mt-1.5 text-[10px] font-bold flex items-center gap-1.5 ${passwordsMatch ? 'text-black bg-green-200 border border-black px-1.5 py-0.5 inline-block' : 'text-red-700 bg-red-100 border border-red-400 px-1.5 py-0.5 inline-block'}`}>
                <Check className="w-3 h-3 stroke-[3]" />
                <span>{passwordsMatch ? 'Passwords match' : 'Passwords do not match'}</span>
              </div>
            )}
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full mt-2 py-3 border-2 border-black bg-fra-yellow text-black font-black text-xs shadow-brutal hover:bg-black hover:text-fra-yellow transition-all flex items-center justify-center gap-2 uppercase tracking-wider disabled:opacity-50"
          >
            {isSubmitting ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                UPDATING PASSWORD...
              </>
            ) : (
              <>
                <span>UPDATE PASSWORD &amp; REVOKE SESSIONS</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </>
            )}
          </button>
        </form>
      )}
    </AuthLayout>
  );
};
