import dotenv from 'dotenv';
import { createApp } from './app.js';
import { InMemoryDatabase } from './repositories/in-memory-db.js';
import { MySqlDatabase } from './repositories/mysql-db.js';
import { getMySqlPool } from './database/mysql-pool.js';
import { MailService } from './mail/mail.service.js';
import { AuthAuditService } from './services/audit.service.js';
import { AuthService } from './services/auth.service.js';
import { hashPassword } from './auth/security.js';
import crypto from 'crypto';

dotenv.config();

const port = Number(process.env.PORT) || 4000;
const useInMemory = process.env.USE_TEST_DB === 'true' || !process.env.DATABASE_PASSWORD;

let userRepo: any;
let tokenRepo: any;
let sessionRepo: any;
let auditRepo: any;

if (useInMemory) {
  console.log('[frAIday Auth] Running with in-memory repository layer (Development/Test Mode).');
  const inMem = new InMemoryDatabase();
  userRepo = inMem;
  tokenRepo = inMem;
  sessionRepo = inMem;
  auditRepo = inMem;
} else {
  console.log('[frAIday Auth] Connecting to MySQL database...');
  const pool = getMySqlPool();
  const mysqlDb = new MySqlDatabase(pool);
  userRepo = mysqlDb;
  tokenRepo = mysqlDb;
  sessionRepo = mysqlDb;
  auditRepo = mysqlDb;
}

const mailService = new MailService();
const auditService = new AuthAuditService(auditRepo);
const authService = new AuthService(userRepo, tokenRepo, sessionRepo, auditService, mailService);

// Pre-seed a verified demo operator for immediate testing
async function seedDemoUser() {
  try {
    const existing = await userRepo.findByEmail('operator@fraiday.ai');
    if (!existing) {
      const passwordHash = await hashPassword('Password123!');
      await userRepo.create({
        id: crypto.randomUUID(),
        name: 'Ada Lovelace',
        email: 'operator@fraiday.ai',
        password_hash: passwordHash,
        email_verified: 1,
        status: 'active',
      });
      console.log('[frAIday Auth] Seeded verified demo operator: operator@fraiday.ai / Password123!');
    }
  } catch (err) {
    console.warn('[frAIday Auth] Note on demo seed:', err);
  }
}

seedDemoUser();

const app = createApp({ authService, mailService });

app.listen(port, () => {
  console.log(`[frAIday Auth] Server running on http://localhost:${port}`);
  console.log(`[frAIday Auth] Health check at http://localhost:${port}/health`);
  console.log(`[frAIday Auth] Test inbox endpoint at http://localhost:${port}/api/auth/test/last-mail`);
});
