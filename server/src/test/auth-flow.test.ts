import { describe, it, expect, beforeEach } from 'vitest';
import request from 'supertest';
import { createApp } from '../app.js';
import { InMemoryDatabase } from '../repositories/in-memory-db.js';
import { MailService } from '../mail/mail.service.js';
import { AuthAuditService } from '../services/audit.service.js';
import { AuthService } from '../services/auth.service.js';

describe('frAIday Authentication System Integration Suite (Milestones 3 - 11)', () => {
  let inMemDb: InMemoryDatabase;
  let mailService: MailService;
  let auditService: AuthAuditService;
  let authService: AuthService;
  let app: any;

  beforeEach(() => {
    process.env.SKIP_EMAIL_VERIFICATION = 'false';
    inMemDb = new InMemoryDatabase();
    mailService = new MailService(true);
    auditService = new AuthAuditService(inMemDb);
    authService = new AuthService(inMemDb, inMemDb, inMemDb, auditService, mailService);
    app = createApp({ authService });
  });

  describe('Milestone 3: Registration', () => {
    it('successfully registers a user with secure password hash and sends verification email', async () => {
      const res = await request(app)
        .post('/api/auth/register')
        .send({
          name: 'Ada Lovelace',
          email: 'ada@fraiday.ai',
          password: 'Password123!',
          confirmPassword: 'Password123!',
        });

      expect(res.status).toBe(201);
      expect(res.body.success).toBe(true);
      expect(res.body.user).toBeDefined();
      expect(res.body.user.email).toBe('ada@fraiday.ai');
      expect(res.body.user.emailVerified).toBe(false);

      // SECURITY: password hash must NEVER be in response
      expect(res.body.user).not.toHaveProperty('password');
      expect(res.body.user).not.toHaveProperty('password_hash');

      // Database assertion: stored password is an authentic bcrypt hash
      const stored = await inMemDb.findByEmail('ada@fraiday.ai');
      expect(stored?.password_hash).toMatch(/^\$2[aby]\$\d+\$/);

      // Email service assertion: verification email was generated
      expect(mailService.sentMails.length).toBe(1);
      const email = mailService.getLastSentMail();
      expect(email?.to).toBe('ada@fraiday.ai');
      expect(email?.subject).toBe('Verify your frAIday account');
      expect(email?.html).toContain('/verify-email?token=');
    });

    it('rejects duplicate email registration with 409 conflict', async () => {
      await request(app)
        .post('/api/auth/register')
        .send({
          name: 'Ada First',
          email: 'duplicate@fraiday.ai',
          password: 'Password123!',
          confirmPassword: 'Password123!',
        });

      const res = await request(app)
        .post('/api/auth/register')
        .send({
          name: 'Ada Second',
          email: 'duplicate@fraiday.ai',
          password: 'Password123!',
          confirmPassword: 'Password123!',
        });

      expect(res.status).toBe(409);
      expect(res.body.success).toBe(false);
      expect(res.body.error.code).toBe('EMAIL_CONFLICT');
    });

    it('rejects invalid email, weak passwords, and mismatched passwords', async () => {
      // Invalid email
      let res = await request(app)
        .post('/api/auth/register')
        .send({
          name: 'User',
          email: 'not-an-email',
          password: 'Password123!',
          confirmPassword: 'Password123!',
        });
      expect(res.status).toBe(400);

      // Weak password (no special char)
      res = await request(app)
        .post('/api/auth/register')
        .send({
          name: 'User',
          email: 'weak@fraiday.ai',
          password: 'password123',
          confirmPassword: 'password123',
        });
      expect(res.status).toBe(400);

      // Password mismatch
      res = await request(app)
        .post('/api/auth/register')
        .send({
          name: 'User',
          email: 'mismatch@fraiday.ai',
          password: 'Password123!',
          confirmPassword: 'DifferentPassword123!',
        });
      expect(res.status).toBe(400);
      expect(res.body.error.message).toMatch(/passwords do not match/i);
    });
  });

  describe('Milestone 4 & 5: Email Verification', () => {
    it('verifies account with valid token and rejects subsequent token reuse', async () => {
      // 1. Register user
      await request(app)
        .post('/api/auth/register')
        .send({
          name: 'Alan Turing',
          email: 'alan@fraiday.ai',
          password: 'Password123!',
          confirmPassword: 'Password123!',
        });

      const sentEmail = mailService.getLastSentMail();
      const tokenMatch = sentEmail?.html.match(/token=([a-f0-9]+)/);
      expect(tokenMatch).not.toBeNull();
      const rawToken = tokenMatch![1];

      // 2. Verify email
      const verifyRes = await request(app)
        .get(`/api/auth/verify-email?token=${rawToken}`);

      expect(verifyRes.status).toBe(200);
      expect(verifyRes.body.success).toBe(true);
      expect(verifyRes.body.user.emailVerified).toBe(true);

      // Check DB
      const userInDb = await inMemDb.findByEmail('alan@fraiday.ai');
      expect(userInDb?.email_verified).toBe(1);
      expect(userInDb?.status).toBe('active');

      // 3. Attempt token reuse
      const reuseRes = await request(app)
        .get(`/api/auth/verify-email?token=${rawToken}`);

      expect(reuseRes.status).toBe(400);
      expect(reuseRes.body.error.message).toMatch(/already been used/i);
    });

    it('rejects invalid and expired tokens', async () => {
      const res = await request(app)
        .get('/api/auth/verify-email?token=invalidnonexistenttoken1234567890');

      expect(res.status).toBe(400);
      expect(res.body.error.message).toMatch(/invalid or expired/i);
    });
  });

  describe('Milestone 6: Login & Session Management', () => {
    beforeEach(async () => {
      // Create and verify a test user
      await request(app)
        .post('/api/auth/register')
        .send({
          name: 'Verified User',
          email: 'verified@fraiday.ai',
          password: 'Password123!',
          confirmPassword: 'Password123!',
        });

      const token = mailService.getLastSentMail()!.html.match(/token=([a-f0-9]+)/)![1];
      await request(app).get(`/api/auth/verify-email?token=${token}`);
    });

    it('authenticates verified user and sets HTTP-only session cookie', async () => {
      const res = await request(app)
        .post('/api/auth/login')
        .send({
          email: 'verified@fraiday.ai',
          password: 'Password123!',
        });

      expect(res.status).toBe(200);
      expect(res.body.success).toBe(true);
      expect(res.body.user.email).toBe('verified@fraiday.ai');
      expect(res.body.token).toBeDefined();

      // Check cookie header
      const cookies = res.headers['set-cookie'];
      expect(cookies).toBeDefined();
      expect(cookies[0]).toMatch(/fraiday_session=/);
      expect(cookies[0]).toMatch(/HttpOnly/i);
    });

    it('blocks unverified accounts from logging in', async () => {
      await request(app)
        .post('/api/auth/register')
        .send({
          name: 'Unverified',
          email: 'unverified@fraiday.ai',
          password: 'Password123!',
          confirmPassword: 'Password123!',
        });

      const res = await request(app)
        .post('/api/auth/login')
        .send({
          email: 'unverified@fraiday.ai',
          password: 'Password123!',
        });

      expect(res.status).toBe(403);
      expect(res.body.error.code).toBe('EMAIL_UNVERIFIED');
    });

    it('enforces anti-enumeration for unknown accounts and wrong passwords', async () => {
      // Wrong password
      const res1 = await request(app)
        .post('/api/auth/login')
        .send({
          email: 'verified@fraiday.ai',
          password: 'WrongPassword999!',
        });
      expect(res1.status).toBe(401);
      expect(res1.body.error.message).toBe('Invalid email or password.');

      // Unknown account
      const res2 = await request(app)
        .post('/api/auth/login')
        .send({
          email: 'ghost@fraiday.ai',
          password: 'Password123!',
        });
      expect(res2.status).toBe(401);
      expect(res2.body.error.message).toBe('Invalid email or password.');
    });
  });

  describe('Milestone 7: Logout & Session Invalidation', () => {
    it('logs out and revokes active session', async () => {
      // Register & Verify
      await request(app).post('/api/auth/register').send({
        name: 'Logout Test',
        email: 'logout@fraiday.ai',
        password: 'Password123!',
        confirmPassword: 'Password123!',
      });
      const token = mailService.getLastSentMail()!.html.match(/token=([a-f0-9]+)/)![1];
      await request(app).get(`/api/auth/verify-email?token=${token}`);

      // Login
      const loginRes = await request(app).post('/api/auth/login').send({
        email: 'logout@fraiday.ai',
        password: 'Password123!',
      });
      const sessionCookie = loginRes.headers['set-cookie'];

      // Access protected endpoint with cookie
      const meRes = await request(app).get('/api/auth/me').set('Cookie', sessionCookie);
      expect(meRes.status).toBe(200);

      // Logout
      const logoutRes = await request(app).post('/api/auth/logout').set('Cookie', sessionCookie);
      expect(logoutRes.status).toBe(200);

      // Subsequent access must fail
      const afterLogoutRes = await request(app).get('/api/auth/me').set('Cookie', sessionCookie);
      expect(afterLogoutRes.status).toBe(401);
    });
  });

  describe('Milestone 8: Audit Logging', () => {
    it('records audit events with zero sensitive credentials or passwords', async () => {
      await request(app).post('/api/auth/register').send({
        name: 'Audit User',
        email: 'audit@fraiday.ai',
        password: 'Password123!',
        confirmPassword: 'Password123!',
      });

      const events = inMemDb.authEvents;
      expect(events.length).toBeGreaterThanOrEqual(1);

      for (const event of events) {
        expect(event).not.toHaveProperty('password');
        expect(event).not.toHaveProperty('password_hash');
        if (event.metadata) {
          expect(event.metadata).not.toHaveProperty('password');
          expect(event.metadata).not.toHaveProperty('token');
        }
      }
    });
  });

  describe('Milestone 9: Password Reset', () => {
    it('requests password reset, sends email, and resets password successfully', async () => {
      // Register & Verify
      await request(app).post('/api/auth/register').send({
        name: 'Reset User',
        email: 'reset@fraiday.ai',
        password: 'OldPassword123!',
        confirmPassword: 'OldPassword123!',
      });
      const verifyToken = mailService.getLastSentMail()!.html.match(/token=([a-f0-9]+)/)![1];
      await request(app).get(`/api/auth/verify-email?token=${verifyToken}`);

      // Login to get an active session
      const loginRes = await request(app).post('/api/auth/login').send({
        email: 'reset@fraiday.ai',
        password: 'OldPassword123!',
      });
      const oldSessionCookie = loginRes.headers['set-cookie'];

      // Request password reset
      const forgotRes = await request(app).post('/api/auth/forgot-password').send({
        email: 'reset@fraiday.ai',
      });
      expect(forgotRes.status).toBe(200);

      // Check reset email
      const resetEmail = mailService.getLastSentMail();
      expect(resetEmail?.subject).toBe('Reset your frAIday password');
      const resetToken = resetEmail?.html.match(/token=([a-f0-9]+)/)![1];

      // Perform password reset
      const resetRes = await request(app).post('/api/auth/reset-password').send({
        token: resetToken,
        password: 'NewPassword999!',
        confirmPassword: 'NewPassword999!',
      });
      expect(resetRes.status).toBe(200);

      // Assert old session was revoked for security
      const oldSessionCheck = await request(app).get('/api/auth/me').set('Cookie', oldSessionCookie);
      expect(oldSessionCheck.status).toBe(401);

      // Old password fails
      const oldLogin = await request(app).post('/api/auth/login').send({
        email: 'reset@fraiday.ai',
        password: 'OldPassword123!',
      });
      expect(oldLogin.status).toBe(401);

      // New password succeeds
      const newLogin = await request(app).post('/api/auth/login').send({
        email: 'reset@fraiday.ai',
        password: 'NewPassword999!',
      });
      expect(newLogin.status).toBe(200);
    });

    it('returns generic response for unknown emails on password reset request', async () => {
      const res = await request(app).post('/api/auth/forgot-password').send({
        email: 'nonexistent@fraiday.ai',
      });
      expect(res.status).toBe(200);
      expect(res.body.message).toMatch(/if that email exists/i);
    });
  });

  describe('Milestone 10: Protected Workspace Route & User Profile', () => {
    it('allows access to workspace status only for verified authenticated users', async () => {
      // Unauthenticated
      const unauth = await request(app).get('/api/auth/workspace/status');
      expect(unauth.status).toBe(401);

      // Register & Verify
      await request(app).post('/api/auth/register').send({
        name: 'Workspace Tester',
        email: 'ws@fraiday.ai',
        password: 'Password123!',
        confirmPassword: 'Password123!',
      });
      const token = mailService.getLastSentMail()!.html.match(/token=([a-f0-9]+)/)![1];
      await request(app).get(`/api/auth/verify-email?token=${token}`);

      const loginRes = await request(app).post('/api/auth/login').send({
        email: 'ws@fraiday.ai',
        password: 'Password123!',
      });
      const cookie = loginRes.headers['set-cookie'];

      // Authenticated + Verified
      const authRes = await request(app).get('/api/auth/workspace/status').set('Cookie', cookie);
      expect(authRes.status).toBe(200);
      expect(authRes.body.data.workspace).toBe('frAIday AI-Native Execution Engine');
    });

    it('updates user profile name and changes password via settings', async () => {
      // Register & Verify
      await request(app).post('/api/auth/register').send({
        name: 'Original Name',
        email: 'profile@fraiday.ai',
        password: 'Password123!',
        confirmPassword: 'Password123!',
      });
      const token = mailService.getLastSentMail()!.html.match(/token=([a-f0-9]+)/)![1];
      await request(app).get(`/api/auth/verify-email?token=${token}`);

      const loginRes = await request(app).post('/api/auth/login').send({
        email: 'profile@fraiday.ai',
        password: 'Password123!',
      });
      const cookie = loginRes.headers['set-cookie'];

      // Update name
      const updateRes = await request(app)
        .patch('/api/auth/profile')
        .set('Cookie', cookie)
        .send({ name: 'Updated Name' });
      expect(updateRes.status).toBe(200);
      expect(updateRes.body.user.name).toBe('Updated Name');

      // Change password
      const changeRes = await request(app)
        .post('/api/auth/change-password')
        .set('Cookie', cookie)
        .send({
          currentPassword: 'Password123!',
          newPassword: 'BrandNewPassword789!',
          confirmPassword: 'BrandNewPassword789!',
        });
      expect(changeRes.status).toBe(200);
    });
  });
});
