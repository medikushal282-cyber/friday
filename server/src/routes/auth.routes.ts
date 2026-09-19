import { Router } from 'express';
import { AuthController } from '../controllers/auth.controller.js';
import { createAuthMiddleware, requireVerifiedEmail } from '../middleware/auth.middleware.js';
import { authLimiter } from '../middleware/rate-limiter.js';
import { AuthService } from '../services/auth.service.js';
import { MailService } from '../mail/mail.service.js';

export function createAuthRouter(authService: AuthService, mailService?: MailService): Router {
  const router = Router();
  const controller = new AuthController(authService);
  const requireAuth = createAuthMiddleware(authService);

  // Public / Rate-limited
  router.post('/register', authLimiter, controller.register);
  router.get('/verify-email', controller.verifyEmail);
  router.post('/resend-verification', authLimiter, controller.resendVerification);
  router.post('/login', authLimiter, controller.login);
  router.post('/forgot-password', authLimiter, controller.forgotPassword);
  router.post('/reset-password', authLimiter, controller.resetPassword);

  // Authenticated
  router.get('/me', requireAuth, controller.getCurrentUser);
  router.post('/logout', requireAuth, controller.logout);
  router.post('/change-password', requireAuth, controller.changePassword);
  router.patch('/profile', requireAuth, controller.updateProfile);

  // Protected workspace verification check
  router.get('/workspace/status', requireAuth, requireVerifiedEmail, (req, res) => {
    res.json({
      success: true,
      data: {
        workspace: 'frAIday AI-Native Execution Engine',
        status: 'ready',
        authenticated: true,
        emailVerified: true,
      },
    });
  });

  // Development/Test inspection endpoint for automated test runner
  if (process.env.NODE_ENV !== 'production' && mailService) {
    router.get('/test/last-mail', (req, res) => {
      const last = mailService.getLastSentMail();
      res.json(last || { message: 'No emails recorded in mock transport.' });
    });
  }

  return router;
}
