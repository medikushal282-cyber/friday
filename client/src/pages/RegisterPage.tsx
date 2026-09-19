import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { AuthLayout } from '../layouts/AuthLayout';
import { useAuth } from '../stores/AuthContext';
import { Mail, Lock, User, Check, AlertCircle, ArrowRight, Loader2 } from 'lucide-react';

export const RegisterPage: React.FC = () => {
  const { register } = useAuth();
  const navigate = useNavigate();

  const [formData, setFormData] = useState({
    name: '',
    email: '',
    password: '',
    confirmPassword: '',
    acceptTerms: true,
  });

  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [isAutoVerified, setIsAutoVerified] = useState(false);
  const [devVerificationUrl, setDevVerificationUrl] = useState<string | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [serverError, setServerError] = useState<string | null>(null);

  const hasMinLength = formData.password.length >= 8;
  const hasNumber = /[0-9]/.test(formData.password);
  const hasSpecial = /[^a-zA-Z0-9]/.test(formData.password);
  const passwordsMatch = Boolean(formData.password) && formData.password === formData.confirmPassword;

  const validate = () => {
    const errs: Record<string, string> = {};
    if (!formData.name.trim() || formData.name.trim().length < 2) {
      errs.name = 'Full name must be at least 2 characters.';
    }
    if (!formData.email.trim() || !formData.email.includes('@')) {
      errs.email = 'Please enter a valid email address.';
    }
    if (!hasMinLength || !hasNumber || !hasSpecial) {
      errs.password = 'Password does not meet the security requirements.';
    }
    if (formData.password !== formData.confirmPassword) {
      errs.confirmPassword = 'Passwords do not match.';
    }
    if (!formData.acceptTerms) {
      errs.acceptTerms = 'You must accept the security policy.';
    }
    setErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setServerError(null);

    if (!validate()) return;

    setIsSubmitting(true);
    try {
      const result = await register({
        name: formData.name,
        email: formData.email,
        password: formData.password,
        confirmPassword: formData.confirmPassword,
      });
      setSuccessMessage(result.message);
      if (result.user?.emailVerified || result.user?.status === 'active') {
        setIsAutoVerified(true);
        setTimeout(() => {
          navigate('/workspace');
        }, 1200);
      }
      if (result.devVerificationUrl) {
        setDevVerificationUrl(result.devVerificationUrl);
      }
      if (result.previewUrl) {
        setPreviewUrl(result.previewUrl);
      }
    } catch (err: any) {
      setServerError(err.message || 'Registration failed. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isAutoVerified) {
    return (
      <AuthLayout
        title="Account Active & Ready"
        subtitle="Email evaluation has been skipped. Your operator account has full workspace access."
      >
        <div className="text-center py-6 space-y-4 font-mono">
          <div className="w-14 h-14 border-2 border-black bg-fra-yellow text-black flex items-center justify-center mx-auto shadow-brutal">
            <Check className="w-8 h-8" />
          </div>
          <div>
            <div className="inline-block px-2.5 py-1 border-2 border-black bg-green-200 text-black text-xs font-black uppercase mb-2 shadow-brutal-sm">
              [VERIFICATION SKIPPED &bull; INSTANT ACTIVE]
            </div>
            <h2 className="text-sm font-black uppercase text-black">Welcome, {formData.name}!</h2>
            <p className="text-xs text-neutral-700 mt-1">
              Operator identity registered: <span className="font-bold text-black">{formData.email}</span>.
              Zero verification delay required.
            </p>
          </div>
          <div className="pt-3">
            <Link
              to="/workspace"
              className="inline-flex items-center justify-center gap-2 w-full py-3 border-2 border-black bg-fra-yellow text-black font-extrabold text-xs shadow-brutal hover:bg-black hover:text-white transition-all uppercase tracking-wider"
            >
              <span>Enter Autonomous Workspace Now</span>
              <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        </div>
      </AuthLayout>
    );
  }

  if (successMessage) {
    return (
      <AuthLayout
        title="Check your inbox"
        subtitle="A verification challenge has been dispatched to confirm your identity."
      >
        <div className="text-center py-4 space-y-4 font-mono">
          <div className="w-12 h-12 border-2 border-black bg-fra-yellow text-black flex items-center justify-center mx-auto shadow-brutal">
            <Mail className="w-6 h-6" />
          </div>
          <p className="text-xs text-neutral-800 leading-relaxed">
            Confirmation link sent to:{' '}
            <span className="font-extrabold text-black bg-yellow-200 px-1">{formData.email}</span>.
            Valid for 24 hours.
          </p>

          {devVerificationUrl ? (
            <div className="p-3 border-2 border-black bg-yellow-50 text-left space-y-2.5 shadow-brutal-sm">
              <div className="text-[11px] font-bold text-black flex items-center gap-1.5">
                <span className="inline-block w-2 h-2 bg-yellow-500 rounded-full animate-ping"></span>
                [FAST SMTP ACTIVE &bull; VERIFY IMMEDIATELY]
              </div>
              <p className="text-[11px] text-neutral-700">
                A verification link was securely generated and dispatched. You can verify instantly:
              </p>
              <a
                href={devVerificationUrl}
                className="block text-center py-2 px-3 border-2 border-black bg-fra-yellow text-black font-extrabold text-xs shadow-brutal hover:bg-black hover:text-white transition-all uppercase"
              >
                ⚡ Verify Account Now (1-Click) &rarr;
              </a>
              {previewUrl && (
                <a
                  href={previewUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="block text-center py-2 px-3 border-2 border-black bg-white text-black font-extrabold text-xs shadow-brutal hover:bg-neutral-100 transition-all uppercase"
                >
                  ✉️ Open Webmail Preview (Ethereal) &rarr;
                </a>
              )}
              <div className="text-[10px] text-neutral-500 break-all">
                Direct URL: <a href={devVerificationUrl} className="underline text-blue-700">{devVerificationUrl}</a>
              </div>
            </div>
          ) : (
            <div className="p-3 border-2 border-black bg-white text-[11px] text-neutral-700 shadow-brutal-sm">
              [NOTICE] Check spam folder if message does not appear in 60 seconds.
            </div>
          )}

          <div className="p-3 border-2 border-dashed border-neutral-400 bg-neutral-50 text-left text-[11px] text-neutral-600 space-y-1">
            <div className="font-bold text-neutral-800">Need real emails in your inbox?</div>
            <div>
              Set <code>USE_MOCK_MAIL=false</code> and configure <code>SMTP_HOST</code>, <code>SMTP_USER</code>, <code>SMTP_PASSWORD</code> in <code>server/.env</code>.
            </div>
            <div>
              View last dispatched mail API:{' '}
              <a
                href="http://localhost:4000/api/auth/test/last-mail"
                target="_blank"
                rel="noreferrer"
                className="underline font-bold text-black hover:text-blue-600"
              >
                /api/auth/test/last-mail
              </a>
            </div>
          </div>

          <div className="pt-2">
            <Link
              to="/login"
              className="inline-block w-full py-2 border-2 border-black bg-fra-yellow text-black font-bold text-xs shadow-brutal hover:bg-fra-yellow-hover transition-colors"
            >
              PROCEED TO LOG IN &rarr;
            </Link>
          </div>
        </div>
      </AuthLayout>
    );
  }

  return (
    <AuthLayout
      title="Create frAIday Account"
      subtitle="Gain entry to the AI-native workspace for autonomous execution."
    >
      {serverError && (
        <div className="mb-4 p-3 border-2 border-black bg-red-100 text-xs text-black font-mono shadow-brutal-sm flex items-start gap-2">
          <AlertCircle className="w-4 h-4 text-red-600 shrink-0 mt-0.5" />
          <span>{serverError}</span>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-3.5">
        {/* Full Name */}
        <div>
          <label htmlFor="fullName" className="block text-[11px] font-mono font-bold uppercase text-black mb-1">
            Full Name
          </label>
          <div className="relative">
            <User className="w-4 h-4 text-neutral-500 absolute left-3 top-3" />
            <input
              id="fullName"
              name="fullName"
              type="text"
              required
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              placeholder="Ada Lovelace"
              className="w-full border-2 border-black bg-white pl-9 pr-3 py-2.5 text-xs font-mono text-black placeholder-neutral-400 shadow-brutal-sm focus:outline-none focus:bg-yellow-50/70 focus:border-black transition-colors"
            />
          </div>
          {errors.name && <p className="text-[11px] font-mono font-bold text-red-600 mt-1">{errors.name}</p>}
        </div>

        {/* Email */}
        <div>
          <label htmlFor="email" className="block text-[11px] font-mono font-bold uppercase text-black mb-1">
            Work Email
          </label>
          <div className="relative">
            <Mail className="w-4 h-4 text-neutral-500 absolute left-3 top-3" />
            <input
              id="email"
              name="email"
              type="email"
              required
              value={formData.email}
              onChange={(e) => setFormData({ ...formData, email: e.target.value })}
              placeholder="developer@company.com"
              className="w-full border-2 border-black bg-white pl-9 pr-3 py-2.5 text-xs font-mono text-black placeholder-neutral-400 shadow-brutal-sm focus:outline-none focus:bg-yellow-50/70 focus:border-black transition-colors"
            />
          </div>
          {errors.email && <p className="text-[11px] font-mono font-bold text-red-600 mt-1">{errors.email}</p>}
        </div>

        {/* Password */}
        <div>
          <label htmlFor="password" className="block text-[11px] font-mono font-bold uppercase text-black mb-1">
            Password
          </label>
          <div className="relative">
            <Lock className="w-4 h-4 text-neutral-500 absolute left-3 top-3" />
            <input
              id="password"
              name="password"
              type="password"
              required
              value={formData.password}
              onChange={(e) => setFormData({ ...formData, password: e.target.value })}
              placeholder="••••••••••••"
              className="w-full border-2 border-black bg-white pl-9 pr-3 py-2.5 text-xs font-mono text-black placeholder-neutral-400 shadow-brutal-sm focus:outline-none focus:bg-yellow-50/70 focus:border-black transition-colors"
            />
          </div>

          {/* Requirements Checklist in Brutalist Badges */}
          <div className="mt-2.5 p-2.5 border-2 border-black bg-neutral-50 space-y-1.5 text-[10px] font-mono shadow-brutal-sm">
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
          {errors.password && <p className="text-[11px] font-mono font-bold text-red-600 mt-1">{errors.password}</p>}
        </div>

        {/* Confirm Password */}
        <div>
          <label htmlFor="confirmPassword" className="block text-[11px] font-mono font-bold uppercase text-black mb-1">
            Confirm Password
          </label>
          <div className="relative">
            <Lock className="w-4 h-4 text-neutral-500 absolute left-3 top-3" />
            <input
              id="confirmPassword"
              name="confirmPassword"
              type="password"
              required
              value={formData.confirmPassword}
              onChange={(e) => setFormData({ ...formData, confirmPassword: e.target.value })}
              placeholder="••••••••••••"
              className="w-full border-2 border-black bg-white pl-9 pr-3 py-2.5 text-xs font-mono text-black placeholder-neutral-400 shadow-brutal-sm focus:outline-none focus:bg-yellow-50/70 focus:border-black transition-colors"
            />
          </div>
          {formData.confirmPassword && (
            <div className={`mt-1.5 text-[10px] font-mono font-bold flex items-center gap-1.5 ${passwordsMatch ? 'text-black bg-green-200 border border-black px-1.5 py-0.5 inline-block' : 'text-red-700 bg-red-100 border border-red-400 px-1.5 py-0.5 inline-block'}`}>
              <Check className="w-3 h-3 stroke-[3]" />
              <span>{passwordsMatch ? 'Passwords match' : 'Passwords do not match'}</span>
            </div>
          )}
          {errors.confirmPassword && <p className="text-[11px] font-mono font-bold text-red-600 mt-1">{errors.confirmPassword}</p>}
        </div>

        {/* Terms */}
        <div className="flex items-center gap-2 pt-1 font-mono">
          <input
            type="checkbox"
            id="terms"
            checked={formData.acceptTerms}
            onChange={(e) => setFormData({ ...formData, acceptTerms: e.target.checked })}
            className="w-4 h-4 border-2 border-black rounded-none text-black focus:ring-0 cursor-pointer accent-black"
          />
          <label htmlFor="terms" className="text-[11px] text-neutral-700 cursor-pointer select-none">
            I agree to the <span className="font-bold underline text-black">Terms of Service</span> and Security Policy.
          </label>
        </div>
        {errors.acceptTerms && <p className="text-[11px] font-mono font-bold text-red-600">{errors.acceptTerms}</p>}

        {/* Submit button */}
        <button
          type="submit"
          disabled={isSubmitting}
          className="w-full mt-2 py-3 border-2 border-black bg-fra-yellow text-black font-black text-xs shadow-brutal hover:bg-black hover:text-fra-yellow transition-all flex items-center justify-center gap-2 uppercase tracking-wider disabled:opacity-50"
        >
          {isSubmitting ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              CREATING ACCOUNT...
            </>
          ) : (
            <>
              <span>REGISTER &amp; PROCEED</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </>
          )}
        </button>
      </form>

      <div className="mt-5 pt-3 border-t-2 border-black text-center text-xs font-mono text-neutral-700">
        Already have an account?{' '}
        <Link to="/login" className="text-black font-black underline hover:bg-fra-yellow px-1">
          SIGN IN
        </Link>
      </div>
    </AuthLayout>
  );
};
