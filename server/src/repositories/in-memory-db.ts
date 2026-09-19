import {
  User,
  NewUser,
  EmailVerificationToken,
  PasswordResetToken,
  Session,
  AuthEvent,
} from '../types/index.js';
import {
  IUserRepository,
  ITokenRepository,
  ISessionRepository,
  IAuthEventRepository,
} from './interfaces.js';

export class InMemoryDatabase
  implements IUserRepository, ITokenRepository, ISessionRepository, IAuthEventRepository
{
  public users: Map<string, User> = new Map();
  public verificationTokens: Map<string, EmailVerificationToken> = new Map();
  public resetTokens: Map<string, PasswordResetToken> = new Map();
  public sessions: Map<string, Session> = new Map();
  public authEvents: AuthEvent[] = [];

  public clear(): void {
    this.users.clear();
    this.verificationTokens.clear();
    this.resetTokens.clear();
    this.sessions.clear();
    this.authEvents = [];
  }

  // --- IUserRepository ---
  async findById(id: string): Promise<User | null> {
    const user = this.users.get(id);
    return user ? { ...user } : null;
  }

  async findByEmail(email: string): Promise<User | null> {
    const normalized = email.trim().toLowerCase();
    for (const user of this.users.values()) {
      if (user.email.toLowerCase() === normalized) {
        return { ...user };
      }
    }
    return null;
  }

  async create(newUser: NewUser): Promise<User> {
    const existing = await this.findByEmail(newUser.email);
    if (existing) {
      const err = new Error(`User with email ${newUser.email} already exists`);
      (err as any).code = 'ER_DUP_ENTRY';
      throw err;
    }

    const now = new Date().toISOString();
    const user: User = {
      ...newUser,
      created_at: now,
      updated_at: now,
      last_login_at: null,
    };
    this.users.set(user.id, user);
    return { ...user };
  }

  async markEmailVerified(userId: string): Promise<void> {
    const user = this.users.get(userId);
    if (user) {
      user.email_verified = 1;
      user.status = 'active';
      user.updated_at = new Date().toISOString();
      this.users.set(userId, user);
    }
  }

  async updatePassword(userId: string, newPasswordHash: string): Promise<void> {
    const user = this.users.get(userId);
    if (user) {
      user.password_hash = newPasswordHash;
      user.updated_at = new Date().toISOString();
      this.users.set(userId, user);
    }
  }

  async updateProfile(userId: string, data: { name?: string }): Promise<User> {
    const user = this.users.get(userId);
    if (!user) {
      throw new Error('User not found');
    }
    if (data.name) {
      user.name = data.name;
      user.updated_at = new Date().toISOString();
      this.users.set(userId, user);
    }
    return { ...user };
  }

  async updateLastLogin(userId: string): Promise<void> {
    const user = this.users.get(userId);
    if (user) {
      user.last_login_at = new Date().toISOString();
      this.users.set(userId, user);
    }
  }

  // --- ITokenRepository ---
  async createVerificationToken(token: EmailVerificationToken): Promise<EmailVerificationToken> {
    const record = {
      ...token,
      created_at: token.created_at || new Date().toISOString(),
    };
    this.verificationTokens.set(record.id, record);
    return { ...record };
  }

  async findVerificationTokenByHash(hash: string): Promise<EmailVerificationToken | null> {
    for (const token of this.verificationTokens.values()) {
      if (token.token_hash === hash) {
        return { ...token };
      }
    }
    return null;
  }

  async markVerificationTokenUsed(tokenId: string): Promise<void> {
    const token = this.verificationTokens.get(tokenId);
    if (token) {
      token.used_at = new Date().toISOString();
      this.verificationTokens.set(tokenId, token);
    }
  }

  async createPasswordResetToken(token: PasswordResetToken): Promise<PasswordResetToken> {
    const record = {
      ...token,
      created_at: token.created_at || new Date().toISOString(),
    };
    this.resetTokens.set(record.id, record);
    return { ...record };
  }

  async findPasswordResetTokenByHash(hash: string): Promise<PasswordResetToken | null> {
    for (const token of this.resetTokens.values()) {
      if (token.token_hash === hash) {
        return { ...token };
      }
    }
    return null;
  }

  async markPasswordResetTokenUsed(tokenId: string): Promise<void> {
    const token = this.resetTokens.get(tokenId);
    if (token) {
      token.used_at = new Date().toISOString();
      this.resetTokens.set(tokenId, token);
    }
  }

  // --- ISessionRepository ---
  async createSession(session: Session): Promise<Session> {
    const record: Session = {
      ...session,
      created_at: session.created_at || new Date().toISOString(),
      last_seen_at: session.last_seen_at || new Date().toISOString(),
      revoked_at: null,
    };
    this.sessions.set(record.id, record);
    return { ...record };
  }

  async findSessionByHash(hash: string): Promise<Session | null> {
    for (const session of this.sessions.values()) {
      if (session.session_token_hash === hash) {
        return { ...session };
      }
    }
    return null;
  }

  async updateLastSeen(sessionId: string): Promise<void> {
    const session = this.sessions.get(sessionId);
    if (session) {
      session.last_seen_at = new Date().toISOString();
      this.sessions.set(sessionId, session);
    }
  }

  async revokeSession(sessionId: string): Promise<void> {
    const session = this.sessions.get(sessionId);
    if (session) {
      session.revoked_at = new Date().toISOString();
      this.sessions.set(sessionId, session);
    }
  }

  async revokeAllUserSessions(userId: string): Promise<void> {
    const now = new Date().toISOString();
    for (const [id, session] of this.sessions.entries()) {
      if (session.user_id === userId && !session.revoked_at) {
        session.revoked_at = now;
        this.sessions.set(id, session);
      }
    }
  }

  // --- IAuthEventRepository ---
  async recordEvent(event: AuthEvent): Promise<AuthEvent> {
    const record: AuthEvent = {
      ...event,
      created_at: event.created_at || new Date().toISOString(),
    };
    this.authEvents.push(record);
    return { ...record };
  }

  async getEventsByUserId(userId: string, limit: number = 50): Promise<AuthEvent[]> {
    return this.authEvents
      .filter((e) => e.user_id === userId)
      .slice(-limit);
  }
}
