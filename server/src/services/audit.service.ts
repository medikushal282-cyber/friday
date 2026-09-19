import crypto from 'crypto';
import { IAuthEventRepository } from '../repositories/interfaces.js';
import { AuthEventType, AuthEvent } from '../types/index.js';

export class AuthAuditService {
  constructor(private eventRepo: IAuthEventRepository) {}

  private async log(
    eventType: AuthEventType,
    success: boolean,
    userId?: string | null,
    ip?: string | null,
    userAgent?: string | null,
    metadata?: Record<string, any>
  ): Promise<AuthEvent> {
    // Security check: strip any accidentally passed sensitive keys
    const sanitizedMetadata: Record<string, any> = {};
    if (metadata) {
      for (const [key, val] of Object.entries(metadata)) {
        const lower = key.toLowerCase();
        if (
          lower.includes('password') ||
          lower.includes('token') ||
          lower.includes('secret') ||
          lower.includes('credential')
        ) {
          continue; // strictly omitted from audit log
        }
        sanitizedMetadata[key] = val;
      }
    }

    return this.eventRepo.recordEvent({
      id: crypto.randomUUID(),
      user_id: userId || null,
      event_type: eventType,
      success,
      ip_address: ip || null,
      user_agent: userAgent || null,
      metadata: Object.keys(sanitizedMetadata).length ? sanitizedMetadata : null,
      created_at: new Date().toISOString(),
    });
  }

  async recordRegistration(
    userId: string | null,
    success: boolean,
    ip?: string | null,
    userAgent?: string | null,
    errorReason?: string
  ) {
    return this.log(
      success ? 'REGISTER_SUCCESS' : 'REGISTER_FAILURE',
      success,
      userId,
      ip,
      userAgent,
      errorReason ? { reason: errorReason } : undefined
    );
  }

  async recordEmailVerificationSent(userId: string, ip?: string | null, userAgent?: string | null) {
    return this.log('EMAIL_VERIFICATION_SENT', true, userId, ip, userAgent);
  }

  async recordEmailVerification(
    userId: string | null,
    success: boolean,
    ip?: string | null,
    userAgent?: string | null,
    errorReason?: string
  ) {
    return this.log(
      success ? 'EMAIL_VERIFIED' : 'EMAIL_VERIFICATION_FAILED',
      success,
      userId,
      ip,
      userAgent,
      errorReason ? { reason: errorReason } : undefined
    );
  }

  async recordLogin(
    userId: string | null,
    success: boolean,
    ip?: string | null,
    userAgent?: string | null,
    errorReason?: string
  ) {
    return this.log(
      success ? 'LOGIN_SUCCESS' : 'LOGIN_FAILURE',
      success,
      userId,
      ip,
      userAgent,
      errorReason ? { reason: errorReason } : undefined
    );
  }

  async recordLogout(userId: string | null, ip?: string | null, userAgent?: string | null) {
    return this.log('LOGOUT', true, userId, ip, userAgent);
  }

  async recordPasswordResetRequested(userId: string | null, ip?: string | null, userAgent?: string | null) {
    return this.log('PASSWORD_RESET_REQUESTED', true, userId, ip, userAgent);
  }

  async recordPasswordReset(
    userId: string | null,
    success: boolean,
    ip?: string | null,
    userAgent?: string | null,
    errorReason?: string
  ) {
    return this.log(
      success ? 'PASSWORD_RESET_SUCCESS' : 'PASSWORD_RESET_FAILURE',
      success,
      userId,
      ip,
      userAgent,
      errorReason ? { reason: errorReason } : undefined
    );
  }
}
