export interface User {
  id: string;
  name: string;
  email: string;
  emailVerified: boolean;
  createdAt: string;
  lastLoginAt?: string | null;
  status: 'active' | 'pending_verification' | 'disabled';
}

export interface AuthResponse {
  success: boolean;
  message?: string;
  user?: User;
  sessionToken?: string;
  devVerificationUrl?: string;
  previewUrl?: string;
  error?: {
    code: string;
    message: string;
    details?: Record<string, string[]>;
  };
}

export interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
}
