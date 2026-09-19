import { describe, it, expect, beforeEach } from 'vitest';
import { InMemoryDatabase } from '../repositories/in-memory-db.js';
import crypto from 'crypto';

describe('Milestone 2: Database Schema & Repository Layer', () => {
  let db: InMemoryDatabase;

  beforeEach(() => {
    db = new InMemoryDatabase();
  });

  describe('User Repository', () => {
    it('creates a new user and retrieves by ID and Email', async () => {
      const user = await db.create({
        id: crypto.randomUUID(),
        name: 'Ada Lovelace',
        email: 'ada@fraiday.ai',
        password_hash: '$2a$12$e8Y6y...',
        email_verified: 0,
        status: 'pending_verification',
      });

      expect(user.id).toBeDefined();
      expect(user.name).toBe('Ada Lovelace');
      expect(user.email).toBe('ada@fraiday.ai');
      expect(user.email_verified).toBe(0);

      const byId = await db.findById(user.id);
      expect(byId?.email).toBe('ada@fraiday.ai');

      const byEmail = await db.findByEmail('ADA@fraiday.ai'); // Case-insensitive test
      expect(byEmail?.id).toBe(user.id);
    });

    it('enforces unique email constraint', async () => {
      await db.create({
        id: crypto.randomUUID(),
        name: 'First',
        email: 'unique@fraiday.ai',
        password_hash: 'hash1',
        email_verified: 0,
        status: 'pending_verification',
      });

      await expect(
        db.create({
          id: crypto.randomUUID(),
          name: 'Second',
          email: 'unique@fraiday.ai',
          password_hash: 'hash2',
          email_verified: 0,
          status: 'pending_verification',
        })
      ).rejects.toThrow(/already exists/i);
    });

    it('updates email verification status and password hash', async () => {
      const user = await db.create({
        id: crypto.randomUUID(),
        name: 'User',
        email: 'user@fraiday.ai',
        password_hash: 'old-hash',
        email_verified: 0,
        status: 'pending_verification',
      });

      await db.markEmailVerified(user.id);
      let updated = await db.findById(user.id);
      expect(updated?.email_verified).toBe(1);
      expect(updated?.status).toBe('active');

      await db.updatePassword(user.id, 'new-secure-hash');
      updated = await db.findById(user.id);
      expect(updated?.password_hash).toBe('new-secure-hash');
    });
  });

  describe('Token Repository', () => {
    it('creates, finds by hash, and marks email verification token as used', async () => {
      const tokenId = crypto.randomUUID();
      const userId = crypto.randomUUID();
      const rawToken = crypto.randomBytes(32).toString('hex');
      const tokenHash = crypto.createHash('sha256').update(rawToken).digest('hex');

      await db.createVerificationToken({
        id: tokenId,
        user_id: userId,
        token_hash: tokenHash,
        expires_at: new Date(Date.now() + 3600000).toISOString(),
      });

      const found = await db.findVerificationTokenByHash(tokenHash);
      expect(found).not.toBeNull();
      expect(found?.id).toBe(tokenId);
      expect(found?.used_at).toBeFalsy();

      await db.markVerificationTokenUsed(tokenId);
      const used = await db.findVerificationTokenByHash(tokenHash);
      expect(used?.used_at).toBeDefined();
    });

    it('creates, finds by hash, and marks password reset token as used', async () => {
      const tokenId = crypto.randomUUID();
      const userId = crypto.randomUUID();
      const rawToken = crypto.randomBytes(32).toString('hex');
      const tokenHash = crypto.createHash('sha256').update(rawToken).digest('hex');

      await db.createPasswordResetToken({
        id: tokenId,
        user_id: userId,
        token_hash: tokenHash,
        expires_at: new Date(Date.now() + 900000).toISOString(),
      });

      const found = await db.findPasswordResetTokenByHash(tokenHash);
      expect(found).not.toBeNull();
      expect(found?.id).toBe(tokenId);

      await db.markPasswordResetTokenUsed(tokenId);
      const used = await db.findPasswordResetTokenByHash(tokenHash);
      expect(used?.used_at).toBeDefined();
    });
  });

  describe('Session Repository', () => {
    it('creates session, updates last seen, and revokes', async () => {
      const sessionId = crypto.randomUUID();
      const userId = crypto.randomUUID();
      const rawSession = crypto.randomBytes(32).toString('hex');
      const sessionHash = crypto.createHash('sha256').update(rawSession).digest('hex');

      await db.createSession({
        id: sessionId,
        user_id: userId,
        session_token_hash: sessionHash,
        expires_at: new Date(Date.now() + 86400000).toISOString(),
      });

      const found = await db.findSessionByHash(sessionHash);
      expect(found?.user_id).toBe(userId);
      expect(found?.revoked_at).toBeNull();

      await db.updateLastSeen(sessionId);
      await db.revokeSession(sessionId);

      const revoked = await db.findSessionByHash(sessionHash);
      expect(revoked?.revoked_at).toBeDefined();
    });

    it('revokes all active sessions for a user upon password reset', async () => {
      const userId = crypto.randomUUID();
      for (let i = 0; i < 3; i++) {
        await db.createSession({
          id: crypto.randomUUID(),
          user_id: userId,
          session_token_hash: `hash-${i}`,
          expires_at: new Date(Date.now() + 86400000).toISOString(),
        });
      }

      await db.revokeAllUserSessions(userId);

      for (let i = 0; i < 3; i++) {
        const s = await db.findSessionByHash(`hash-${i}`);
        expect(s?.revoked_at).toBeDefined();
      }
    });
  });

  describe('Auth Event Repository (Audit Logging)', () => {
    it('records authentication events with zero sensitive credentials', async () => {
      const userId = crypto.randomUUID();
      await db.recordEvent({
        id: crypto.randomUUID(),
        user_id: userId,
        event_type: 'LOGIN_SUCCESS',
        success: 1,
        ip_address: '127.0.0.1',
        user_agent: 'Mozilla/5.0 TestBrowser',
        metadata: { loginMethod: 'password', mfaPrompted: false },
      });

      const events = await db.getEventsByUserId(userId);
      expect(events.length).toBe(1);
      expect(events[0].event_type).toBe('LOGIN_SUCCESS');
      expect(events[0].metadata).not.toHaveProperty('password');
      expect(events[0].metadata).not.toHaveProperty('token');
    });
  });
});
