# frAIday Authentication API Specification

Base URL: `/api/auth`

All API responses follow consistent JSON formats:
- **Success**: `{ "success": true, "message": "...", ... }`
- **Error**: `{ "success": false, "error": { "code": "...", "message": "..." } }`

---

## Public Endpoints

### 1. Register
- **Endpoint**: `POST /register`
- **Rate Limit**: Yes (15 req / 15 min)
- **Request Body**:
  ```json
  {
    "name": "Ada Lovelace",
    "email": "ada@fraiday.ai",
    "password": "Password123!",
    "confirmPassword": "Password123!"
  }
  ```
- **Response (201 Created)**:
  ```json
  {
    "success": true,
    "message": "Registration successful. Please check your inbox to verify your account.",
    "user": {
      "id": "uuid",
      "name": "Ada Lovelace",
      "email": "ada@fraiday.ai",
      "emailVerified": false,
      "createdAt": "ISO-8601",
      "status": "pending_verification"
    }
  }
  ```

### 2. Verify Email
- **Endpoint**: `GET /verify-email?token=<RAW_TOKEN>`
- **Rate Limit**: Yes
- **Response (200 OK)**:
  ```json
  {
    "success": true,
    "message": "Your email address has been verified successfully.",
    "user": {
      "id": "uuid",
      "emailVerified": true,
      "status": "active"
    }
  }
  ```

### 3. Resend Verification Link
- **Endpoint**: `POST /resend-verification`
- **Request Body**: `{ "email": "ada@fraiday.ai" }`
- **Response (200 OK)**:
  ```json
  {
    "success": true,
    "message": "If an unverified account exists with that email, a verification link has been sent."
  }
  ```

### 4. Login
- **Endpoint**: `POST /login`
- **Rate Limit**: Yes
- **Request Body**:
  ```json
  {
    "email": "ada@fraiday.ai",
    "password": "Password123!"
  }
  ```
- **Sets Cookie**: `fraiday_session=<TOKEN>; HttpOnly; SameSite=Lax`
- **Response (200 OK)**:
  ```json
  {
    "success": true,
    "message": "Login successful.",
    "user": {
      "id": "uuid",
      "name": "Ada Lovelace",
      "email": "ada@fraiday.ai",
      "emailVerified": true
    }
  }
  ```

### 5. Forgot Password
- **Endpoint**: `POST /forgot-password`
- **Request Body**: `{ "email": "ada@fraiday.ai" }`
- **Response (200 OK - Anti-Enumeration)**:
  ```json
  {
    "success": true,
    "message": "If that email exists in our system, a password reset link has been sent."
  }
  ```

### 6. Reset Password
- **Endpoint**: `POST /reset-password`
- **Request Body**:
  ```json
  {
    "token": "raw-token-from-link",
    "password": "NewSecurePassword456!",
    "confirmPassword": "NewSecurePassword456!"
  }
  ```
- **Response (200 OK)**:
  ```json
  {
    "success": true,
    "message": "Password has been reset successfully. Please log in with your new password."
  }
  ```

---

## Authenticated Endpoints (Requires `fraiday_session` Cookie)

### 7. Get Current User Profile
- **Endpoint**: `GET /me`
- **Response (200 OK)**:
  ```json
  {
    "success": true,
    "user": {
      "id": "uuid",
      "name": "Ada Lovelace",
      "email": "ada@fraiday.ai",
      "emailVerified": true,
      "createdAt": "ISO-8601",
      "lastLoginAt": "ISO-8601",
      "status": "active"
    }
  }
  ```

### 8. Logout
- **Endpoint**: `POST /logout`
- **Clears Cookie**: `fraiday_session`
- **Response (200 OK)**:
  ```json
  {
    "success": true,
    "message": "Logged out successfully."
  }
  ```

### 9. Update Profile Name
- **Endpoint**: `PATCH /profile`
- **Request Body**: `{ "name": "Ada Augusta King" }`
- **Response (200 OK)**:
  ```json
  {
    "success": true,
    "user": { ... },
    "message": "Profile updated successfully."
  }
  ```

### 10. Change Password
- **Endpoint**: `POST /change-password`
- **Request Body**:
  ```json
  {
    "currentPassword": "CurrentPassword123!",
    "newPassword": "NewSecurePassword789!",
    "confirmPassword": "NewSecurePassword789!"
  }
  ```
- **Response (200 OK)**:
  ```json
  {
    "success": true,
    "message": "Password updated successfully."
  }
  ```

### 11. Workspace Status Check
- **Endpoint**: `GET /workspace/status`
- **Guards**: `requireAuth` + `requireVerifiedEmail`
- **Response (200 OK)**:
  ```json
  {
    "success": true,
    "data": {
      "workspace": "frAIday AI-Native Execution Engine",
      "status": "ready",
      "authenticated": true,
      "emailVerified": true
    }
  }
  ```
