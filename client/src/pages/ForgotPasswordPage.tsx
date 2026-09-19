import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { AuthLayout } from '../layouts/AuthLayout';
import { useAuth } from '../stores/AuthContext';
import { Mail, ArrowRight, AlertCircle, CheckCircle2, Loader2 } from 'lucide-react';

export const ForgotPasswordPage: React.FC = () => {
  const { forgotPassword } = useAuth();
  const [email, setEmail] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);

    if (!email.trim()) {
      setErrorMessage('Please enter your email address.');
      return;
    }

    setIsSubmitting(true);
    try {
      const msg = await forgotPassword(email);
      setStatusMessage(msg);
    } catch (err: any) {
      setErrorMessage(err.message || 'Unable to process reset request.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <AuthLayout
      title="Reset Password"
      subtitle="Enter your email to receive a single-use, 15-minute password reset link."
    >
      {errorMessage && (
        <div className="mb-4 p-3 border-2 border-black bg-red-100 text-xs text-black font-mono shadow-brutal-sm flex items-start gap-2">
          <AlertCircle className="w-4 h-4 text-red-600 shrink-0 mt-0.5" />
          <span>{errorMessage}</span>
        </div>
      )}

      {statusMessage ? (
        <div className="text-center py-4 space-y-4 font-mono">
          <div className="w-12 h-12 border-2 border-black bg-fra-yellow text-black flex items-center justify-center mx-auto shadow-brutal">
            <CheckCircle2 className="w-6 h-6" />
          </div>
          <p className="text-xs text-neutral-800 leading-relaxed">{statusMessage}</p>
          <div className="pt-2">
            <Link
              to="/login"
              className="inline-block w-full py-2 border-2 border-black bg-white text-black font-bold text-xs shadow-brutal hover:bg-fra-yellow transition-colors uppercase"
            >
              RETURN TO LOG IN &rarr;
            </Link>
          </div>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="resetEmail" className="block text-[11px] font-mono font-bold uppercase text-black mb-1">
              Account Email
            </label>
            <div className="relative">
              <Mail className="w-4 h-4 text-neutral-500 absolute left-3 top-3" />
              <input
                id="resetEmail"
                name="email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="developer@company.com"
                className="w-full border-2 border-black bg-white pl-9 pr-3 py-2.5 text-xs font-mono text-black placeholder-neutral-400 shadow-brutal-sm focus:outline-none focus:bg-yellow-50/70 focus:border-black transition-colors"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full mt-2 py-3 border-2 border-black bg-fra-yellow text-black font-black text-xs shadow-brutal hover:bg-black hover:text-fra-yellow transition-all flex items-center justify-center gap-2 uppercase tracking-wider disabled:opacity-50 font-mono"
          >
            {isSubmitting ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                DISPATCHING LINK...
              </>
            ) : (
              <>
                <span>SEND RESET LINK</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </>
            )}
          </button>

          <div className="mt-4 text-center">
            <Link to="/login" className="text-xs font-mono text-neutral-600 hover:text-black hover:underline">
              Remember your password? Sign in
            </Link>
          </div>
        </form>
      )}
    </AuthLayout>
  );
};
