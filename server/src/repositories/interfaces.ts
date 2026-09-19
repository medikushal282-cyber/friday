import { User, NewUser, EmailVerificationToken, PasswordResetToken, Session, AuthEvent } from '../types/index.js';

export interface IUserRepository {
  findById(id: string): Promise<User | null>;
  findByEmail(email: string): Promise<User | null>;
  create(user: NewUser): Promise<User>;
  markEmailVerified(userId: string): Promise<void>;
  updatePassword(userId: string, newPasswordHash: string): Promise<void>;
  updateProfile(userId: string, data: { name?: string }): Promise<User>;
  updateLastLogin(userId: string): Promise<void>;
}

export interface ITokenRepository {
  createVerificationToken(token: EmailVerificationToken): Promise<EmailVerificationToken>;
  findVerificationTokenByHash(hash: string): Promise<EmailVerificationToken | null>;
  markVerificationTokenUsed(tokenId: string): Promise<void>;

  createPasswordResetToken(token: PasswordResetToken): Promise<PasswordResetToken>;
  findPasswordResetTokenByHash(hash: string): Promise<PasswordResetToken | null>;
  markPasswordResetTokenUsed(tokenId: string): Promise<void>;
}

export interface ISessionRepository {
  createSession(session: Session): Promise<Session>;
  findSessionByHash(hash: string): Promise<Session | null>;
  updateLastSeen(sessionId: string): Promise<void>;
  revokeSession(sessionId: string): Promise<void>;
  revokeAllUserSessions(userId: string): Promise<void>;
}

export interface IAuthEventRepository {
  recordEvent(event: AuthEvent): Promise<AuthEvent>;
  getEventsByUserId(userId: string, limit?: number): Promise<AuthEvent[]>;
}
