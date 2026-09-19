import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../stores/AuthContext';
import { User, ShieldCheck, Calendar, Clock, Lock, CheckCircle2, AlertCircle, Loader2, LogOut, ArrowLeft } from 'lucide-react';

export const AccountSettingsPage: React.FC = () => {
  const { user, logout, updateProfile, changePassword } = useAuth();
  const navigate = useNavigate();

  // Name state
  const [name, setName] = useState(user?.name || '');
  const [nameSuccess, setNameSuccess] = useState<string | null>(null);
  const [nameError, setNameError] = useState<string | null>(null);
  const [isUpdatingName, setIsUpdatingName] = useState(false);

  // Password state
  const [passwordForm, setPasswordForm] = useState({
    currentPassword: '',
    newPassword: '',
    confirmPassword: '',
  });
  const [passwordSuccess, setPasswordSuccess] = useState<string | null>(null);
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [isUpdatingPassword, setIsUpdatingPassword] = useState(false);

  const handleUpdateName = async (e: React.FormEvent) => {
    e.preventDefault();
    setNameSuccess(null);
    setNameError(null);

    if (!name.trim() || name.trim().length < 2) {
      setNameError('Name must be at least 2 characters.');
      return;
    }

    setIsUpdatingName(true);
    try {
      await updateProfile(name);
      setNameSuccess('Profile name updated successfully.');
    } catch (err: any) {
      setNameError(err.message || 'Failed to update name.');
    } finally {
      setIsUpdatingName(false);
    }
  };

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setPasswordSuccess(null);
    setPasswordError(null);

    if (passwordForm.newPassword !== passwordForm.confirmPassword) {
      setPasswordError('New passwords do not match.');
      return;
    }

    if (passwordForm.newPassword.length < 8) {
      setPasswordError('New password must be at least 8 characters.');
      return;
    }

    setIsUpdatingPassword(true);
    try {
      await changePassword({
        currentPassword: passwordForm.currentPassword,
        newPassword: passwordForm.newPassword,
        confirmPassword: passwordForm.confirmPassword,
      });
      setPasswordSuccess('Password updated successfully. Other active sessions were revoked.');
      setPasswordForm({ currentPassword: '', newPassword: '', confirmPassword: '' });
    } catch (err: any) {
      setPasswordError(err.message || 'Failed to update password.');
    } finally {
      setIsUpdatingPassword(false);
    }
  };

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  return (
    <div className="min-h-screen bg-fra-cream text-black flex flex-col font-sans select-none">
      {/* Top Header */}
      <header className="h-14 border-b-2 border-fra-black bg-fra-cream flex items-center justify-between px-4 z-30 fixed top-0 left-0 right-0">
        <div className="flex items-center space-x-3">
          <Link to="/" className="flex items-center">
            <span className="font-extrabold text-2xl tracking-tighter bg-black text-white px-2 py-0.5 mr-1 hover:bg-fra-yellow hover:text-black transition-colors">
              FRAIDAY_
            </span>
          </Link>
          <span className="font-mono text-xs font-bold text-neutral-600 hidden sm:inline">
            // ACCOUNT_SETTINGS
          </span>
        </div>

        <div className="flex items-center space-x-3 font-mono">
          <Link
            to="/workspace"
            className="flex items-center space-x-1.5 border-2 border-black bg-white px-2.5 py-1 text-xs font-bold shadow-brutal hover:bg-fra-yellow transition-colors"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>WORKSPACE</span>
          </Link>
          <button
            onClick={handleLogout}
            className="border-2 border-black bg-fra-red text-white px-2.5 py-1 text-xs font-bold shadow-brutal hover:bg-red-600 transition-colors flex items-center gap-1"
          >
            <LogOut className="w-3.5 h-3.5" />
            <span>SIGN OUT</span>
          </button>
        </div>
      </header>

      {/* Main Container */}
      <main className="flex-1 max-w-4xl w-full mx-auto px-4 pt-20 pb-16 tech-grid-cream font-mono">
        {/* Header Title */}
        <div className="border-2 border-black bg-fra-cream-card p-5 shadow-brutal-lg mb-6">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-mono font-black uppercase bg-black text-white px-2 py-0.5">
              [SECURITY_MANAGEMENT]
            </span>
            <span className="text-[9px] font-mono font-bold text-neutral-600">
              OPERATOR PROFILE
            </span>
          </div>
          <h1 className="text-2xl font-black tracking-tight text-black mt-2 uppercase">
            Account &amp; Security Credentials
          </h1>
          <p className="text-xs text-neutral-700 mt-1">
            Maintain your verified identity, display parameters, and cryptographic access keys.
          </p>
        </div>

        {/* Identity Overview Cards */}
        <div className="border-2 border-black bg-white p-5 shadow-brutal mb-6">
          <h2 className="text-xs font-extrabold uppercase text-neutral-500 mb-3">[OPERATOR_METADATA]</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
            <div className="p-3 border-2 border-black bg-fra-cream-card flex items-center gap-3">
              <User className="w-5 h-5 text-black shrink-0" />
              <div>
                <span className="text-[9px] text-neutral-500 uppercase block font-bold">OPERATOR NAME</span>
                <span className="text-black font-extrabold">{user?.name}</span>
              </div>
            </div>

            <div className="p-3 border-2 border-black bg-fra-cream-card flex items-center gap-3">
              <ShieldCheck className="w-5 h-5 text-green-700 shrink-0" />
              <div>
                <span className="text-[9px] text-neutral-500 uppercase block font-bold">EMAIL REGISTER</span>
                <span className="text-black font-extrabold">{user?.email}</span>{' '}
                <span className="text-[9px] px-1 py-0.5 bg-black text-white font-bold ml-1">
                  VERIFIED
                </span>
              </div>
            </div>

            <div className="p-3 border-2 border-black bg-fra-cream-card flex items-center gap-3">
              <Calendar className="w-5 h-5 text-black shrink-0" />
              <div>
                <span className="text-[9px] text-neutral-500 uppercase block font-bold">REGISTRATION DATE</span>
                <span className="text-black font-bold">
                  {user?.createdAt ? new Date(user.createdAt).toLocaleDateString() : 'Active'}
                </span>
              </div>
            </div>

            <div className="p-3 border-2 border-black bg-fra-cream-card flex items-center gap-3">
              <Clock className="w-5 h-5 text-black shrink-0" />
              <div>
                <span className="text-[9px] text-neutral-500 uppercase block font-bold">LAST LOGIN EVENT</span>
                <span className="text-black font-bold">
                  {user?.lastLoginAt ? new Date(user.lastLoginAt).toLocaleString() : 'Current Session'}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Update Name Card */}
        <div className="border-2 border-black bg-white p-5 shadow-brutal mb-6">
          <h2 className="text-xs font-extrabold uppercase text-neutral-500 mb-2">[UPDATE_NAME]</h2>
          <p className="text-xs text-neutral-700 mb-3">Your display name appears in the autonomous execution audit stream.</p>

          {nameSuccess && (
            <div className="mb-3 p-2.5 border-2 border-black bg-green-100 text-xs text-black font-bold flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-green-700" />
              <span>{nameSuccess}</span>
            </div>
          )}
          {nameError && (
            <div className="mb-3 p-2.5 border-2 border-black bg-red-100 text-xs text-black font-bold flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-red-600" />
              <span>{nameError}</span>
            </div>
          )}

          <form onSubmit={handleUpdateName} className="max-w-md space-y-3">
            <div>
              <label htmlFor="accountName" className="block text-[11px] font-bold uppercase text-black mb-1">
                Full Name
              </label>
              <input
                id="accountName"
                name="name"
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full border-2 border-black bg-white px-3 py-2 text-xs font-mono shadow-brutal-sm focus:outline-none focus:bg-fra-cream"
              />
            </div>
            <button
              type="submit"
              disabled={isUpdatingName}
              className="px-4 py-2 border-2 border-black bg-fra-yellow text-black font-extrabold text-xs shadow-brutal hover:bg-fra-yellow-hover uppercase disabled:opacity-50"
            >
              {isUpdatingName ? 'SAVING...' : 'SAVE NAME'}
            </button>
          </form>
        </div>

        {/* Change Password Card */}
        <div className="border-2 border-black bg-white p-5 shadow-brutal mb-6">
          <h2 className="text-xs font-extrabold uppercase text-neutral-500 mb-2">[CHANGE_PASSWORD]</h2>
          <p className="text-xs text-neutral-700 mb-3">Changing password will invalidate all other active sessions across devices.</p>

          {passwordSuccess && (
            <div className="mb-3 p-2.5 border-2 border-black bg-green-100 text-xs text-black font-bold flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-green-700" />
              <span>{passwordSuccess}</span>
            </div>
          )}
          {passwordError && (
            <div className="mb-3 p-2.5 border-2 border-black bg-red-100 text-xs text-black font-bold flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-red-600" />
              <span>{passwordError}</span>
            </div>
          )}

          <form onSubmit={handleChangePassword} className="max-w-md space-y-3">
            <div>
              <label htmlFor="currPass" className="block text-[11px] font-bold uppercase text-black mb-1">
                Current Password
              </label>
              <div className="relative">
                <Lock className="w-4 h-4 text-neutral-500 absolute left-3 top-2.5" />
                <input
                  id="currPass"
                  name="currentPassword"
                  type="password"
                  required
                  value={passwordForm.currentPassword}
                  onChange={(e) => setPasswordForm({ ...passwordForm, currentPassword: e.target.value })}
                  placeholder="••••••••••••"
                  className="w-full border-2 border-black bg-white pl-9 pr-3 py-2 text-xs font-mono shadow-brutal-sm focus:outline-none focus:bg-fra-cream"
                />
              </div>
            </div>

            <div>
              <label htmlFor="newPass" className="block text-[11px] font-bold uppercase text-black mb-1">
                New Password
              </label>
              <div className="relative">
                <Lock className="w-4 h-4 text-neutral-500 absolute left-3 top-2.5" />
                <input
                  id="newPass"
                  name="newPassword"
                  type="password"
                  required
                  value={passwordForm.newPassword}
                  onChange={(e) => setPasswordForm({ ...passwordForm, newPassword: e.target.value })}
                  placeholder="••••••••••••"
                  className="w-full border-2 border-black bg-white pl-9 pr-3 py-2 text-xs font-mono shadow-brutal-sm focus:outline-none focus:bg-fra-cream"
                />
              </div>
            </div>

            <div>
              <label htmlFor="confirmNewPass" className="block text-[11px] font-bold uppercase text-black mb-1">
                Confirm New Password
              </label>
              <div className="relative">
                <Lock className="w-4 h-4 text-neutral-500 absolute left-3 top-2.5" />
                <input
                  id="confirmNewPass"
                  name="confirmPassword"
                  type="password"
                  required
                  value={passwordForm.confirmPassword}
                  onChange={(e) => setPasswordForm({ ...passwordForm, confirmPassword: e.target.value })}
                  placeholder="••••••••••••"
                  className="w-full border-2 border-black bg-white pl-9 pr-3 py-2 text-xs font-mono shadow-brutal-sm focus:outline-none focus:bg-fra-cream"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={isUpdatingPassword}
              className="px-4 py-2 border-2 border-black bg-fra-yellow text-black font-extrabold text-xs shadow-brutal hover:bg-fra-yellow-hover uppercase disabled:opacity-50 flex items-center gap-1.5"
            >
              {isUpdatingPassword ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  UPDATING...
                </>
              ) : (
                'UPDATE PASSWORD'
              )}
            </button>
          </form>
        </div>

        {/* Terminate Session Button */}
        <div className="border-2 border-black bg-fra-cream-card p-5 shadow-brutal flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h3 className="text-xs font-black uppercase text-black">Sign Out From Current Device</h3>
            <p className="text-xs text-neutral-600 mt-0.5">Revokes active session token and wipes local HTTP-only cookie.</p>
          </div>
          <button
            onClick={handleLogout}
            className="px-4 py-2 border-2 border-black bg-fra-red text-white font-extrabold text-xs shadow-brutal hover:bg-red-600 uppercase"
          >
            END SESSION
          </button>
        </div>
      </main>
    </div>
  );
};
