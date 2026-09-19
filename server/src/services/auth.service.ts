import crypto from 'crypto';
import {
  IUserRepository,
  ITokenRepository,
  ISessionRepository,
} from '../repositories/interfaces.js';
import { AuthAuditService } from './audit.service.js';
import { MailService } from '../mail/mail.service.js';
import {
  hashPassword,
  verifyPassword,
  generateSecureToken,
  hashToken,
  sanitizeUser,
} from '../auth/security.js';
import { SafeUser } from '../types/index.js';

export interface RegisterInput {
  name: string;
  email: string;
  password: string;
  ip?: string;
  userAgent?: string;
}

export interface LoginInput {
  email: string;
  password: string;
  ip?: string;
  userAgent?: string;
}

export class AuthService {
  constructor(
    private userRepo: IUserRepository,
    private tokenRepo: ITokenRepository,
    private sessionRepo: ISessionRepository,
    private auditService: AuthAuditService,
    private mailService: MailService
  ) {}

  async register(input: RegisterInput): Promise<{ user: SafeUser; message: string }> {
    const existing = await this.userRepo.findByEmail(input.email);
    if (existing) {
      await this.auditService.recordRegistration(
        null,
        false,
        input.ip,
        input.userAgent,
        'email_already_registered'
      );
      throw new Error('An account with this email address already exists');
    }

    const password_hash = await hashPassword(input.password);
    const userId = crypto.randomUUID();

    const skipVerification = process.env.SKIP_EMAIL_VERIFICATION === 'true';

    const user = await this.userRepo.create({
      id: userId,
      name: input.name.trim(),
      email: input.email.trim().toLowerCase(),
      password_hash,
      email_verified: skipVerification ? 1 : 0,
      status: skipVerification ? 'active' : 'pending_verification',
    });

    let devVerificationUrl: string | undefined;
    let lastMail: any;

    if (!skipVerification) {
      // Generate email verification token
      const rawToken = generateSecureToken();
      const token_hash = hashToken(rawToken);
      const expiresAt = new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString();

      await this.tokenRepo.createVerificationToken({
        id: crypto.randomUUID(),
        user_id: user.id,
        token_hash,
        expires_at: expiresAt,
      });

      // Send verification email
      devVerificationUrl = await this.mailService.sendVerificationEmail(user.email, user.name, rawToken);
      lastMail = this.mailService.getLastSentMail();
      await this.auditService.recordEmailVerificationSent(user.id, input.ip, input.userAgent);
    }

    let sessionToken: string | undefined;
    let expiresAtDate: Date | undefined;

    if (skipVerification) {
      const rawSessionToken = generateSecureToken();
      const session_token_hash = hashToken(rawSessionToken);
      const maxAgeMs = Number(process.env.SESSION_MAX_AGE_MS) || 7 * 24 * 60 * 60 * 1000;
      expiresAtDate = new Date(Date.now() + maxAgeMs);

      await this.sessionRepo.createSession({
        id: crypto.randomUUID(),
        user_id: user.id,
        session_token_hash,
        expires_at: expiresAtDate.toISOString(),
      });
      sessionToken = rawSessionToken;
      await this.userRepo.updateLastLogin(user.id);
    }

    await this.auditService.recordRegistration(user.id, true, input.ip, input.userAgent);

    return {
      user: sanitizeUser(user),
      message: skipVerification
        ? 'Account created and verified successfully. Welcome to frAIday!'
        : 'Registration successful. Please check your inbox to verify your account.',
      sessionToken,
      expiresAt: expiresAtDate,
      devVerificationUrl,
      previewUrl: lastMail?.previewUrl || undefined,
    };
  }

  async verifyEmail(
    rawToken: string,
    ip?: string,
    userAgent?: string
  ): Promise<{ message: string; user: SafeUser }> {
    const token_hash = hashToken(rawToken);
    const tokenRecord = await this.tokenRepo.findVerificationTokenByHash(token_hash);

    if (!tokenRecord) {
      await this.auditService.recordEmailVerification(null, false, ip, userAgent, 'token_not_found');
      throw new Error('Invalid or expired verification link');
    }

    if (tokenRecord.used_at) {
      await this.auditService.recordEmailVerification(
        tokenRecord.user_id,
        false,
        ip,
        userAgent,
        'token_already_used'
      );
      throw new Error('This verification link has already been used');
    }

    const expiryTime = new Date(tokenRecord.expires_at).getTime();
    if (Date.now() > expiryTime) {
      await this.auditService.recordEmailVerification(
        tokenRecord.user_id,
        false,
        ip,
        userAgent,
        'token_expired'
      );
      throw new Error('This verification link has expired. Please request a new one');
    }

    const user = await this.userRepo.findById(tokenRecord.user_id);
    if (!user) {
      throw new Error('User associated with this token no longer exists');
    }

    await this.userRepo.markEmailVerified(user.id);
    await this.tokenRepo.markVerificationTokenUsed(tokenRecord.id);
    await this.auditService.recordEmailVerification(user.id, true, ip, userAgent);

    const updatedUser = await this.userRepo.findById(user.id);
    return {
      message: 'Your email address has been verified successfully.',
      user: sanitizeUser(updatedUser || user),
    };
  }

  async resendVerification(email: string, ip?: string, userAgent?: string): Promise<{ message: string }> {
    const user = await this.userRepo.findByEmail(email);
    // Anti-enumeration: always return success
    if (!user || user.email_verified) {
      return { message: 'If an unverified account exists with that email, a verification link has been sent.' };
    }

    const rawToken = generateSecureToken();
    const token_hash = hashToken(rawToken);
    const expiresAt = new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString();

    await this.tokenRepo.createVerificationToken({
      id: crypto.randomUUID(),
      user_id: user.id,
      token_hash,
      expires_at: expiresAt,
    });

    await this.mailService.sendVerificationEmail(user.email, user.name, rawToken);
    await this.auditService.recordEmailVerificationSent(user.id, ip, userAgent);

    return { message: 'If an unverified account exists with that email, a verification link has been sent.' };
  }

  async login(
    input: LoginInput
  ): Promise<{ sessionToken: string; user: SafeUser; expiresAt: Date }> {
    const user = await this.userRepo.findByEmail(input.email);

    // Anti-enumeration failure
    if (!user) {
      await this.auditService.recordLogin(null, false, input.ip, input.userAgent, 'user_not_found');
      throw new Error('Invalid email or password.');
    }

    const isMatch = await verifyPassword(input.password, user.password_hash);
    if (!isMatch) {
      await this.auditService.recordLogin(user.id, false, input.ip, input.userAgent, 'invalid_password');
      throw new Error('Invalid email or password.');
    }

    if (user.status === 'disabled') {
      await this.auditService.recordLogin(user.id, false, input.ip, input.userAgent, 'account_disabled');
      throw new Error('This account has been disabled. Please contact support.');
    }

    const skipVerification = process.env.SKIP_EMAIL_VERIFICATION === 'true';

    if (!skipVerification && !user.email_verified) {
      await this.auditService.recordLogin(user.id, false, input.ip, input.userAgent, 'email_unverified');
      const error = new Error('Please verify your email address before logging in.');
      (error as any).code = 'EMAIL_UNVERIFIED';
      throw error;
    } else if (skipVerification && !user.email_verified) {
      await this.userRepo.markEmailVerified(user.id);
      user.email_verified = 1;
      user.status = 'active';
    }

    // Create session
    const rawSessionToken = generateSecureToken();
    const session_token_hash = hashToken(rawSessionToken);
    const maxAgeMs = Number(process.env.SESSION_MAX_AGE_MS) || 7 * 24 * 60 * 60 * 1000;
    const expiresAt = new Date(Date.now() + maxAgeMs);

    await this.sessionRepo.createSession({
      id: crypto.randomUUID(),
      user_id: user.id,
      session_token_hash,
      expires_at: expiresAt.toISOString(),
    });

    await this.userRepo.updateLastLogin(user.id);
    await this.auditService.recordLogin(user.id, true, input.ip, input.userAgent);

    const updatedUser = await this.userRepo.findById(user.id);

    return {
      sessionToken: rawSessionToken,
      user: sanitizeUser(updatedUser || user),
      expiresAt,
    };
  }

  async logout(sessionToken?: string, ip?: string, userAgent?: string): Promise<void> {
    if (!sessionToken) return;
    const session_token_hash = hashToken(sessionToken);
    const session = await this.sessionRepo.findSessionByHash(session_token_hash);
    if (session) {
      await this.sessionRepo.revokeSession(session.id);
      await this.auditService.recordLogout(session.user_id, ip, userAgent);
    }
  }

  async getCurrentUser(sessionToken?: string): Promise<SafeUser | null> {
    if (!sessionToken) return null;
    const session_token_hash = hashToken(sessionToken);
    const session = await this.sessionRepo.findSessionByHash(session_token_hash);

    if (!session || session.revoked_at) {
      return null;
    }

    const expiryTime = new Date(session.expires_at).getTime();
    if (Date.now() > expiryTime) {
      return null;
    }

    await this.sessionRepo.updateLastSeen(session.id);
    const user = await this.userRepo.findById(session.user_id);
    if (!user || user.status === 'disabled') {
      return null;
    }

    return sanitizeUser(user);
  }

  async requestPasswordReset(email: string, ip?: string, userAgent?: string): Promise<{ message: string }> {
    const user = await this.userRepo.findByEmail(email);

    // Anti-enumeration: always return generic message
    const genericMessage = 'If that email exists in our system, a password reset link has been sent.';
    if (!user) {
      return { message: genericMessage };
    }

    const rawToken = generateSecureToken();
    const token_hash = hashToken(rawToken);
    const expiresAt = new Date(Date.now() + 15 * 60 * 1000).toISOString(); // 15 mins

    await this.tokenRepo.createPasswordResetToken({
      id: crypto.randomUUID(),
      user_id: user.id,
      token_hash,
      expires_at: expiresAt,
    });

    await this.mailService.sendPasswordResetEmail(user.email, user.name, rawToken);
    await this.auditService.recordPasswordResetRequested(user.id, ip, userAgent);

    return { message: genericMessage };
  }

  async resetPassword(
    rawToken: string,
    newPassword: string,
    ip?: string,
    userAgent?: string
  ): Promise<{ message: string }> {
    const token_hash = hashToken(rawToken);
    const tokenRecord = await this.tokenRepo.findPasswordResetTokenByHash(token_hash);

    if (!tokenRecord) {
      await this.auditService.recordPasswordReset(null, false, ip, userAgent, 'token_not_found');
      throw new Error('Invalid or expired password reset link');
    }

    if (tokenRecord.used_at) {
      await this.auditService.recordPasswordReset(
        tokenRecord.user_id,
        false,
        ip,
        userAgent,
        'token_already_used'
      );
      throw new Error('This password reset link has already been used');
    }

    const expiryTime = new Date(tokenRecord.expires_at).getTime();
    if (Date.now() > expiryTime) {
      await this.auditService.recordPasswordReset(
        tokenRecord.user_id,
        false,
        ip,
        userAgent,
        'token_expired'
      );
      throw new Error('This password reset link has expired');
    }

    const newPasswordHash = await hashPassword(newPassword);

    await this.userRepo.updatePassword(tokenRecord.user_id, newPasswordHash);
    await this.tokenRepo.markPasswordResetTokenUsed(tokenRecord.id);

    // Revoke all existing sessions for security
    await this.sessionRepo.revokeAllUserSessions(tokenRecord.user_id);

    await this.auditService.recordPasswordReset(tokenRecord.user_id, true, ip, userAgent);

    return { message: 'Password has been reset successfully. Please log in with your new password.' };
  }

  async changePassword(
    userId: string,
    currentPassword: string,
    newPassword: string,
    ip?: string,
    userAgent?: string
  ): Promise<{ message: string }> {
    const user = await this.userRepo.findById(userId);
    if (!user) {
      throw new Error('User not found');
    }

    const isMatch = await verifyPassword(currentPassword, user.password_hash);
    if (!isMatch) {
      throw new Error('Current password is incorrect');
    }

    const newPasswordHash = await hashPassword(newPassword);
    await this.userRepo.updatePassword(userId, newPasswordHash);

    // Invalidate other sessions
    await this.sessionRepo.revokeAllUserSessions(userId);

    await this.auditService.recordPasswordReset(userId, true, ip, userAgent);

    return { message: 'Password updated successfully.' };
  }

  async updateProfile(userId: string, name: string): Promise<SafeUser> {
    const updated = await this.userRepo.updateProfile(userId, { name: name.trim() });
    return sanitizeUser(updated);
  }
}
