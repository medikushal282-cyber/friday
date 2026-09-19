export type UserStatus = 'active' | 'pending_verification' | 'disabled';

export interface User {
  id: string;
  name: string;
  email: string;
  password_hash: string;
  email_verified: number | boolean;
  created_at: string | Date;
  updated_at: string | Date;
  last_login_at?: string | Date | null;
  status: UserStatus;
}

export type NewUser = Omit<User, 'created_at' | 'updated_at' | 'last_login_at'> & {
  last_login_at?: string | Date | null;
};

export interface EmailVerificationToken {
  id: string;
  user_id: string;
  token_hash: string;
  expires_at: string | Date;
  used_at?: string | Date | null;
  created_at?: string | Date;
}

export interface PasswordResetToken {
  id: string;
  user_id: string;
  token_hash: string;
  expires_at: string | Date;
  used_at?: string | Date | null;
  created_at?: string | Date;
}

export interface Session {
  id: string;
  user_id: string;
  session_token_hash: string;
  expires_at: string | Date;
  created_at?: string | Date;
  last_seen_at?: string | Date;
  revoked_at?: string | Date | null;
}

export type AuthEventType =
  | 'REGISTER_SUCCESS'
  | 'REGISTER_FAILURE'
  | 'EMAIL_VERIFICATION_SENT'
  | 'EMAIL_VERIFIED'
  | 'EMAIL_VERIFICATION_FAILED'
  | 'LOGIN_SUCCESS'
  | 'LOGIN_FAILURE'
  | 'LOGOUT'
  | 'PASSWORD_RESET_REQUESTED'
  | 'PASSWORD_RESET_SUCCESS'
  | 'PASSWORD_RESET_FAILURE'
  | 'SESSION_EXPIRED'
  | 'ACCOUNT_LOCKED'
  | 'ACCOUNT_UNLOCKED';

export interface AuthEvent {
  id: string;
  user_id?: string | null;
  event_type: AuthEventType;
  success: number | boolean;
  ip_address?: string | null;
  user_agent?: string | null;
  metadata?: Record<string, any> | null;
  created_at?: string | Date;
}

export interface SafeUser {
  id: string;
  name: string;
  email: string;
  emailVerified: boolean;
  createdAt: string;
  lastLoginAt?: string | null;
  status: UserStatus;
}
