import bcrypt from 'bcryptjs';
import crypto from 'crypto';
import { User, SafeUser } from '../types/index.js';

const BCRYPT_SALT_ROUNDS = 12;

export async function hashPassword(password: string): Promise<string> {
  return bcrypt.hash(password, BCRYPT_SALT_ROUNDS);
}

export async function verifyPassword(password: string, hash: string): Promise<boolean> {
  return bcrypt.compare(password, hash);
}

export function generateSecureToken(): string {
  return crypto.randomBytes(32).toString('hex');
}

export function hashToken(token: string): string {
  return crypto.createHash('sha256').update(token.trim()).digest('hex');
}

export function sanitizeUser(user: User): SafeUser {
  return {
    id: user.id,
    name: user.name,
    email: user.email,
    emailVerified: Boolean(user.email_verified),
    createdAt: typeof user.created_at === 'string' ? user.created_at : user.created_at.toISOString(),
    lastLoginAt: user.last_login_at
      ? typeof user.last_login_at === 'string'
        ? user.last_login_at
        : user.last_login_at.toISOString()
      : null,
    status: user.status,
  };
}
