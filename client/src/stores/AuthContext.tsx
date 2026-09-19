import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { User, AuthResponse } from '../types';
import { apiRequest } from '../services/api';

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  clearError: () => void;
  login: (data: { email: string; password: string }) => Promise<void>;
  register: (data: {
    name: string;
    email: string;
    password: string;
    confirmPassword: string;
  }) => Promise<{ message: string; devVerificationUrl?: string; previewUrl?: string; user?: User }>;
  logout: () => Promise<void>;
  verifyEmail: (token: string) => Promise<User>;
  resendVerification: (email: string) => Promise<string>;
  forgotPassword: (email: string) => Promise<string>;
  resetPassword: (data: { token: string; password: string; confirmPassword: string }) => Promise<string>;
  updateProfile: (name: string) => Promise<void>;
  changePassword: (data: { currentPassword: string; newPassword: string; confirmPassword: string }) => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const clearError = () => setError(null);

  const refreshUser = useCallback(async () => {
    try {
      const res = await apiRequest<{ success: boolean; user: User }>('/auth/me');
      setUser(res.user);
    } catch {
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshUser();
  }, [refreshUser]);

  const login = async (data: { email: string; password: string }) => {
    setError(null);
    setIsLoading(true);
    try {
      const res = await apiRequest<{ success: boolean; user: User }>('/auth/login', {
        method: 'POST',
        body: JSON.stringify(data),
      });
      setUser(res.user);
    } catch (err: any) {
      setError(err.message || 'Login failed');
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  const register = async (data: { name: string; email: string; password: string; confirmPassword: string }) => {
    setError(null);
    try {
      const res = await apiRequest<AuthResponse>('/auth/register', {
        method: 'POST',
        body: JSON.stringify(data),
      });
      if (res.user && (res.user.emailVerified || res.sessionToken)) {
        setUser(res.user);
      }
      return {
        message: res.message || 'Account created successfully.',
        devVerificationUrl: res.devVerificationUrl,
        previewUrl: res.previewUrl,
        user: res.user,
      };
    } catch (err: any) {
      setError(err.message || 'Registration failed');
      throw err;
    }
  };

  const logout = async () => {
    try {
      await apiRequest('/auth/logout', { method: 'POST' });
    } finally {
      setUser(null);
    }
  };

  const verifyEmail = async (token: string) => {
    setError(null);
    try {
      const res = await apiRequest<{ success: boolean; message: string; user: User }>(
        `/auth/verify-email?token=${encodeURIComponent(token)}`
      );
      if (user && user.id === res.user.id) {
        setUser(res.user);
      }
      return res.user;
    } catch (err: any) {
      setError(err.message || 'Email verification failed');
      throw err;
    }
  };

  const resendVerification = async (email: string) => {
    setError(null);
    try {
      const res = await apiRequest<{ success: boolean; message: string }>('/auth/resend-verification', {
        method: 'POST',
        body: JSON.stringify({ email }),
      });
      return res.message;
    } catch (err: any) {
      setError(err.message || 'Failed to resend verification email');
      throw err;
    }
  };

  const forgotPassword = async (email: string) => {
    setError(null);
    try {
      const res = await apiRequest<{ success: boolean; message: string }>('/auth/forgot-password', {
        method: 'POST',
        body: JSON.stringify({ email }),
      });
      return res.message;
    } catch (err: any) {
      setError(err.message || 'Unable to request password reset');
      throw err;
    }
  };

  const resetPassword = async (data: { token: string; password: string; confirmPassword: string }) => {
    setError(null);
    try {
      const res = await apiRequest<{ success: boolean; message: string }>('/auth/reset-password', {
        method: 'POST',
        body: JSON.stringify(data),
      });
      return res.message;
    } catch (err: any) {
      setError(err.message || 'Unable to reset password');
      throw err;
    }
  };

  const updateProfile = async (name: string) => {
    setError(null);
    try {
      const res = await apiRequest<{ success: boolean; user: User }>('/auth/profile', {
        method: 'PATCH',
        body: JSON.stringify({ name }),
      });
      setUser(res.user);
    } catch (err: any) {
      setError(err.message || 'Unable to update profile');
      throw err;
    }
  };

  const changePassword = async (data: { currentPassword: string; newPassword: string; confirmPassword: string }) => {
    setError(null);
    try {
      await apiRequest<{ success: boolean; message: string }>('/auth/change-password', {
        method: 'POST',
        body: JSON.stringify(data),
      });
    } catch (err: any) {
      setError(err.message || 'Unable to change password');
      throw err;
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user && user.emailVerified,
        isLoading,
        error,
        clearError,
        login,
        register,
        logout,
        verifyEmail,
        resendVerification,
        forgotPassword,
        resetPassword,
        updateProfile,
        changePassword,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
