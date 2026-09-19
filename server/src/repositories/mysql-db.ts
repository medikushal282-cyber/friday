import { Pool, RowDataPacket, ResultSetHeader } from 'mysql2/promise';
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

export class MySqlDatabase
  implements IUserRepository, ITokenRepository, ISessionRepository, IAuthEventRepository
{
  constructor(private pool: Pool) {}

  // --- IUserRepository ---
  async findById(id: string): Promise<User | null> {
    const [rows] = await this.pool.execute<RowDataPacket[]>(
      'SELECT id, name, email, password_hash, email_verified, created_at, updated_at, last_login_at, status FROM users WHERE id = ? LIMIT 1',
      [id]
    );
    if (!rows.length) return null;
    return rows[0] as User;
  }

  async findByEmail(email: string): Promise<User | null> {
    const [rows] = await this.pool.execute<RowDataPacket[]>(
      'SELECT id, name, email, password_hash, email_verified, created_at, updated_at, last_login_at, status FROM users WHERE LOWER(email) = LOWER(?) LIMIT 1',
      [email.trim()]
    );
    if (!rows.length) return null;
    return rows[0] as User;
  }

  async create(user: NewUser): Promise<User> {
    await this.pool.execute<ResultSetHeader>(
      `INSERT INTO users (id, name, email, password_hash, email_verified, status)
       VALUES (?, ?, ?, ?, ?, ?)`,
      [
        user.id,
        user.name,
        user.email.trim().toLowerCase(),
        user.password_hash,
        user.email_verified ? 1 : 0,
        user.status,
      ]
    );
    const created = await this.findById(user.id);
    if (!created) throw new Error('Failed to retrieve newly created user');
    return created;
  }

  async markEmailVerified(userId: string): Promise<void> {
    await this.pool.execute(
      `UPDATE users SET email_verified = 1, status = 'active', updated_at = NOW() WHERE id = ?`,
      [userId]
    );
  }

  async updatePassword(userId: string, newPasswordHash: string): Promise<void> {
    await this.pool.execute(
      `UPDATE users SET password_hash = ?, updated_at = NOW() WHERE id = ?`,
      [newPasswordHash, userId]
    );
  }

  async updateProfile(userId: string, data: { name?: string }): Promise<User> {
    if (data.name) {
      await this.pool.execute(
        `UPDATE users SET name = ?, updated_at = NOW() WHERE id = ?`,
        [data.name, userId]
      );
    }
    const updated = await this.findById(userId);
    if (!updated) throw new Error('User not found');
    return updated;
  }

  async updateLastLogin(userId: string): Promise<void> {
    await this.pool.execute(
      `UPDATE users SET last_login_at = NOW(), updated_at = NOW() WHERE id = ?`,
      [userId]
    );
  }

  // --- ITokenRepository ---
  async createVerificationToken(token: EmailVerificationToken): Promise<EmailVerificationToken> {
    await this.pool.execute(
      `INSERT INTO email_verification_tokens (id, user_id, token_hash, expires_at)
       VALUES (?, ?, ?, ?)`,
      [token.id, token.user_id, token.token_hash, token.expires_at]
    );
    return token;
  }

  async findVerificationTokenByHash(hash: string): Promise<EmailVerificationToken | null> {
    const [rows] = await this.pool.execute<RowDataPacket[]>(
      `SELECT id, user_id, token_hash, expires_at, used_at, created_at
       FROM email_verification_tokens
       WHERE token_hash = ?
       LIMIT 1`,
      [hash]
    );
    if (!rows.length) return null;
    return rows[0] as EmailVerificationToken;
  }

  async markVerificationTokenUsed(tokenId: string): Promise<void> {
    await this.pool.execute(
      `UPDATE email_verification_tokens SET used_at = NOW() WHERE id = ?`,
      [tokenId]
    );
  }

  async createPasswordResetToken(token: PasswordResetToken): Promise<PasswordResetToken> {
    await this.pool.execute(
      `INSERT INTO password_reset_tokens (id, user_id, token_hash, expires_at)
       VALUES (?, ?, ?, ?)`,
      [token.id, token.user_id, token.token_hash, token.expires_at]
    );
    return token;
  }

  async findPasswordResetTokenByHash(hash: string): Promise<PasswordResetToken | null> {
    const [rows] = await this.pool.execute<RowDataPacket[]>(
      `SELECT id, user_id, token_hash, expires_at, used_at, created_at
       FROM password_reset_tokens
       WHERE token_hash = ?
       LIMIT 1`,
      [hash]
    );
    if (!rows.length) return null;
    return rows[0] as PasswordResetToken;
  }

  async markPasswordResetTokenUsed(tokenId: string): Promise<void> {
    await this.pool.execute(
      `UPDATE password_reset_tokens SET used_at = NOW() WHERE id = ?`,
      [tokenId]
    );
  }

  // --- ISessionRepository ---
  async createSession(session: Session): Promise<Session> {
    await this.pool.execute(
      `INSERT INTO sessions (id, user_id, session_token_hash, expires_at)
       VALUES (?, ?, ?, ?)`,
      [session.id, session.user_id, session.session_token_hash, session.expires_at]
    );
    return session;
  }

  async findSessionByHash(hash: string): Promise<Session | null> {
    const [rows] = await this.pool.execute<RowDataPacket[]>(
      `SELECT id, user_id, session_token_hash, expires_at, created_at, last_seen_at, revoked_at
       FROM sessions
       WHERE session_token_hash = ?
       LIMIT 1`,
      [hash]
    );
    if (!rows.length) return null;
    return rows[0] as Session;
  }

  async updateLastSeen(sessionId: string): Promise<void> {
    await this.pool.execute(
      `UPDATE sessions SET last_seen_at = NOW() WHERE id = ?`,
      [sessionId]
    );
  }

  async revokeSession(sessionId: string): Promise<void> {
    await this.pool.execute(
      `UPDATE sessions SET revoked_at = NOW() WHERE id = ?`,
      [sessionId]
    );
  }

  async revokeAllUserSessions(userId: string): Promise<void> {
    await this.pool.execute(
      `UPDATE sessions SET revoked_at = NOW() WHERE user_id = ? AND revoked_at IS NULL`,
      [userId]
    );
  }

  // --- IAuthEventRepository ---
  async recordEvent(event: AuthEvent): Promise<AuthEvent> {
    await this.pool.execute(
      `INSERT INTO auth_events (id, user_id, event_type, success, ip_address, user_agent, metadata)
       VALUES (?, ?, ?, ?, ?, ?, ?)`,
      [
        event.id,
        event.user_id || null,
        event.event_type,
        event.success ? 1 : 0,
        event.ip_address || null,
        event.user_agent || null,
        event.metadata ? JSON.stringify(event.metadata) : null,
      ]
    );
    return event;
  }

  async getEventsByUserId(userId: string, limit: number = 50): Promise<AuthEvent[]> {
    const [rows] = await this.pool.execute<RowDataPacket[]>(
      `SELECT id, user_id, event_type, success, ip_address, user_agent, metadata, created_at
       FROM auth_events
       WHERE user_id = ?
       ORDER BY created_at DESC
       LIMIT ?`,
      [userId, limit]
    );
    return rows.map((r: any) => ({
      ...r,
      metadata: typeof r.metadata === 'string' ? JSON.parse(r.metadata) : r.metadata,
    }));
  }
}
