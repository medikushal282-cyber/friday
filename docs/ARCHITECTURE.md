# frAIday Authentication & Entry System — Architecture Overview

## 1. System Vision & Context

**frAIday** is an AI-native workspace where users provide a high-level objective and an autonomous agent orchestrates planning, research, execution, failure recovery, human approvals, and outcome delivery.

This public entry and authentication system forms the secure, verifiable perimeter that gates entry to the autonomous execution workspace.

---

## 2. High-Level Architecture Diagram

```
                             PUBLIC INTERNET
                                    │
                                    ▼
       ┌─────────────────────────────────────────────────────────┐
       │                frAIday Public Entry Client              │
       │           (React 18 + TypeScript + Vite + Tailwind)     │
       │                                                         │
       │  • Premium Technical Landing Page                       │
       │  • Autonomous Pipeline Visualizer                       │
       │  • Conceptual Workspace Preview & Human Approval Gate   │
       │  • Registration, Login, Email Verification UI           │
       │  • Password Reset & Self-Service Account Management     │
       └────────────────────────────┬────────────────────────────┘
                                    │
                         HTTP/HTTPS │ SameSite Strict/Lax
                    Credentials     │ HTTP-Only Cookie
                                    ▼
       ┌─────────────────────────────────────────────────────────┐
       │             frAIday Express Security Gateway            │
       │               (Node.js + Express + TypeScript)          │
       │                                                         │
       │  • Helmet (CSP, HSTS, Secure Headers)                   │
       │  • CORS with credential validation                      │
       │  • express-rate-limit (authLimiter, generalLimiter)     │
       │  • Zod Payload Validation & Sanitization                │
       │  • Request ID Tracing (x-request-id)                    │
       │  • Cookie Parser & Session Token Extractor              │
       └────────────────────────────┬────────────────────────────┘
                                    │
                                    ▼
       ┌─────────────────────────────────────────────────────────┐
       │                   Domain Service Layer                  │
       │                                                         │
       │  • AuthService (Register, Login, Session, Reset)        │
       │  • AuthAuditService (Zero-Secret Event Logger)          │
       │  • MailService (Nodemailer SMTP + Dev Mock Transport)   │
       │  • Security Engine (Bcrypt-12, SHA-256 Token Hashes)    │
       └────────────────────────────┬────────────────────────────┘
                                    │
                                    ▼
       ┌─────────────────────────────────────────────────────────┐
       │                 Database Repository Layer               │
       │                                                         │
       │  • IUserRepository, ISessionRepository                  │
       │  • ITokenRepository, IAuthEventRepository               │
       │  • Parameterized Raw SQL Queries (MySQL 8.0+)           │
       │  • In-Memory Test Driver (100% Deterministic CI/Dev)    │
       └────────────────────────────┬────────────────────────────┘
                                    │
                                    ▼
                      ┌───────────────────────────┐
                      │    Relational Database    │
                      │   - users                 │
                      │   - sessions              │
                      │   - email_verification... │
                      │   - password_reset_tokens │
                      │   - auth_events           │
                      └───────────────────────────┘
```

---

## 3. Data Flow & Authentication Lifecycle

### 3.1 Registration & Email Verification
1. **User submits** `name`, `email`, `password`, `confirmPassword`.
2. **Client-side & Server-side** independently validate password complexity (8+ chars, 1 number, 1 special char).
3. **Password hashed** using bcrypt (`saltRounds=12`).
4. **User created** in `users` table with `status='pending_verification'` and `email_verified=0`.
5. **Token generated**: 256 bits of cryptographically secure entropy (`crypto.randomBytes(32)`).
6. **Token stored**: Only the **SHA-256 hash** of the token is saved in `email_verification_tokens` with a 24-hour expiration.
7. **Email dispatched**: MailService sends email with clickable link containing the raw token.
8. **Verification**: User clicks link &rarr; Server hashes token &rarr; matches hash &rarr; activates account &rarr; marks token used &rarr; logs `EMAIL_VERIFIED`.

### 3.2 Login & Session Management
1. **User inputs** `email` and `password`.
2. **Server validates** credentials using `bcrypt.compare` against `password_hash`.
3. **Anti-Enumeration**: Consistent generic message `Invalid email or password.` returned for both unknown accounts and incorrect passwords.
4. **Verification Guard**: Unverified accounts are refused with an `EMAIL_UNVERIFIED` challenge.
5. **Session Created**: Cryptographic 256-bit session token generated; only its SHA-256 hash is stored in `sessions`.
6. **Cookie Set**: `fraiday_session` issued as `HttpOnly`, `Secure` (production), `SameSite=Lax`, with 7-day expiration.
7. **Audit Record**: `LOGIN_SUCCESS` recorded in `auth_events`.

### 3.3 Password Reset & Session Invalidation
1. **Forgot password requested**: Always returns generic success message so account existence is not disclosed.
2. **Reset token generated**: 15-minute lifespan, SHA-256 hash stored in `password_reset_tokens`.
3. **Password update**: Hashes new password, updates `users`, marks token `used_at = NOW()`, and **immediately revokes all active user sessions** to protect against compromised credentials.
