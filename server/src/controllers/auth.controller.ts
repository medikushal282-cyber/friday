import { Request, Response } from 'express';
import { AuthService } from '../services/auth.service.js';
import {
  registerSchema,
  loginSchema,
  verifyEmailSchema,
  forgotPasswordSchema,
  resetPasswordSchema,
  changePasswordSchema,
} from '../utils/validators.js';
import { AuthenticatedRequest } from '../middleware/auth.middleware.js';

export class AuthController {
  constructor(private authService: AuthService) {}

  private getClientInfo(req: Request) {
    const ip =
      (req.headers['x-forwarded-for'] as string)?.split(',')[0].trim() ||
      req.socket.remoteAddress ||
      'unknown';
    const userAgent = req.headers['user-agent'] || 'unknown';
    return { ip, userAgent };
  }

  private setSessionCookie(res: Response, sessionToken: string, expiresAt: Date) {
    const cookieName = process.env.SESSION_COOKIE_NAME || 'fraiday_session';
    const isProduction = process.env.NODE_ENV === 'production';

    res.cookie(cookieName, sessionToken, {
      httpOnly: true,
      secure: isProduction,
      sameSite: 'lax',
      expires: expiresAt,
      path: '/',
    });
  }

  private clearSessionCookie(res: Response) {
    const cookieName = process.env.SESSION_COOKIE_NAME || 'fraiday_session';
    const isProduction = process.env.NODE_ENV === 'production';

    res.clearCookie(cookieName, {
      httpOnly: true,
      secure: isProduction,
      sameSite: 'lax',
      path: '/',
    });
  }

  register = async (req: Request, res: Response) => {
    try {
      const parsed = registerSchema.safeParse(req.body);
      if (!parsed.success) {
        return res.status(400).json({
          success: false,
          error: {
            code: 'VALIDATION_ERROR',
            message: parsed.error.errors[0]?.message || 'Invalid input data',
            details: parsed.error.flatten().fieldErrors,
          },
        });
      }

      const { ip, userAgent } = this.getClientInfo(req);
      const result = await this.authService.register({
        name: parsed.data.name,
        email: parsed.data.email,
        password: parsed.data.password,
        ip,
        userAgent,
      });

      if (result.sessionToken && (result as any).expiresAt) {
        this.setSessionCookie(res, result.sessionToken, (result as any).expiresAt);
      }

      return res.status(201).json({
        success: true,
        message: result.message,
        user: result.user,
        sessionToken: result.sessionToken,
        devVerificationUrl: result.devVerificationUrl,
        previewUrl: (result as any).previewUrl,
      });
    } catch (err: any) {
      const isConflict = err.message?.includes('already exists');
      return res.status(isConflict ? 409 : 500).json({
        success: false,
        error: {
          code: isConflict ? 'EMAIL_CONFLICT' : 'REGISTRATION_FAILED',
          message: err.message || 'Registration failed',
        },
      });
    }
  };

  verifyEmail = async (req: Request, res: Response) => {
    try {
      const token = (req.query.token as string) || req.body?.token;
      const parsed = verifyEmailSchema.safeParse({ token });
      if (!parsed.success) {
        return res.status(400).json({
          success: false,
          error: {
            code: 'INVALID_TOKEN',
            message: 'Invalid or missing verification token.',
          },
        });
      }

      const { ip, userAgent } = this.getClientInfo(req);
      const result = await this.authService.verifyEmail(parsed.data.token, ip, userAgent);

      return res.json({
        success: true,
        message: result.message,
        user: result.user,
      });
    } catch (err: any) {
      return res.status(400).json({
        success: false,
        error: {
          code: 'VERIFICATION_FAILED',
          message: err.message || 'Verification failed',
        },
      });
    }
  };

  resendVerification = async (req: Request, res: Response) => {
    try {
      const { email } = req.body;
      if (!email || typeof email !== 'string') {
        return res.status(400).json({
          success: false,
          error: { code: 'INVALID_EMAIL', message: 'Email address is required.' },
        });
      }

      const { ip, userAgent } = this.getClientInfo(req);
      const result = await this.authService.resendVerification(email, ip, userAgent);

      return res.json({
        success: true,
        message: result.message,
      });
    } catch (err: any) {
      return res.status(500).json({
        success: false,
        error: { code: 'SERVER_ERROR', message: 'Unable to process verification resend request.' },
      });
    }
  };

  login = async (req: Request, res: Response) => {
    try {
      const parsed = loginSchema.safeParse(req.body);
      if (!parsed.success) {
        return res.status(400).json({
          success: false,
          error: {
            code: 'VALIDATION_ERROR',
            message: 'Please provide both email and password.',
          },
        });
      }

      const { ip, userAgent } = this.getClientInfo(req);
      const { sessionToken, user, expiresAt } = await this.authService.login({
        email: parsed.data.email,
        password: parsed.data.password,
        ip,
        userAgent,
      });

      this.setSessionCookie(res, sessionToken, expiresAt);

      return res.json({
        success: true,
        message: 'Login successful.',
        user,
        token: sessionToken, // also returned for API clients/tests
      });
    } catch (err: any) {
      if (err.code === 'EMAIL_UNVERIFIED') {
        return res.status(403).json({
          success: false,
          error: {
            code: 'EMAIL_UNVERIFIED',
            message: err.message,
          },
        });
      }
      return res.status(401).json({
        success: false,
        error: {
          code: 'INVALID_CREDENTIALS',
          message: err.message || 'Invalid email or password.',
        },
      });
    }
  };

  logout = async (req: AuthenticatedRequest, res: Response) => {
    try {
      const sessionToken = req.sessionToken;
      const { ip, userAgent } = this.getClientInfo(req);

      await this.authService.logout(sessionToken, ip, userAgent);
      this.clearSessionCookie(res);

      return res.json({
        success: true,
        message: 'Logged out successfully.',
      });
    } catch (err: any) {
      this.clearSessionCookie(res);
      return res.json({
        success: true,
        message: 'Logged out.',
      });
    }
  };

  getCurrentUser = async (req: AuthenticatedRequest, res: Response) => {
    if (!req.user) {
      return res.status(401).json({
        success: false,
        error: {
          code: 'UNAUTHORIZED',
          message: 'Not authenticated.',
        },
      });
    }

    return res.json({
      success: true,
      user: req.user,
    });
  };

  forgotPassword = async (req: Request, res: Response) => {
    try {
      const parsed = forgotPasswordSchema.safeParse(req.body);
      if (!parsed.success) {
        return res.status(400).json({
          success: false,
          error: { code: 'INVALID_EMAIL', message: 'Valid email address is required.' },
        });
      }

      const { ip, userAgent } = this.getClientInfo(req);
      const result = await this.authService.requestPasswordReset(parsed.data.email, ip, userAgent);

      return res.json({
        success: true,
        message: result.message,
      });
    } catch (err: any) {
      return res.status(500).json({
        success: false,
        error: { code: 'REQUEST_FAILED', message: 'Unable to process password reset request.' },
      });
    }
  };

  resetPassword = async (req: Request, res: Response) => {
    try {
      const parsed = resetPasswordSchema.safeParse(req.body);
      if (!parsed.success) {
        return res.status(400).json({
          success: false,
          error: {
            code: 'VALIDATION_ERROR',
            message: parsed.error.errors[0]?.message || 'Invalid reset data.',
          },
        });
      }

      const { ip, userAgent } = this.getClientInfo(req);
      const result = await this.authService.resetPassword(
        parsed.data.token,
        parsed.data.password,
        ip,
        userAgent
      );

      this.clearSessionCookie(res);

      return res.json({
        success: true,
        message: result.message,
      });
    } catch (err: any) {
      return res.status(400).json({
        success: false,
        error: {
          code: 'RESET_FAILED',
          message: err.message || 'Password reset failed.',
        },
      });
    }
  };

  changePassword = async (req: AuthenticatedRequest, res: Response) => {
    try {
      const parsed = changePasswordSchema.safeParse(req.body);
      if (!parsed.success) {
        return res.status(400).json({
          success: false,
          error: {
            code: 'VALIDATION_ERROR',
            message: parsed.error.errors[0]?.message || 'Invalid password change request.',
          },
        });
      }

      const { ip, userAgent } = this.getClientInfo(req);
      const result = await this.authService.changePassword(
        req.user!.id,
        parsed.data.currentPassword,
        parsed.data.newPassword,
        ip,
        userAgent
      );

      return res.json({
        success: true,
        message: result.message,
      });
    } catch (err: any) {
      return res.status(400).json({
        success: false,
        error: {
          code: 'CHANGE_PASSWORD_FAILED',
          message: err.message || 'Unable to update password.',
        },
      });
    }
  };

  updateProfile = async (req: AuthenticatedRequest, res: Response) => {
    try {
      const { name } = req.body;
      if (!name || typeof name !== 'string' || name.trim().length < 2) {
        return res.status(400).json({
          success: false,
          error: { code: 'INVALID_NAME', message: 'Name must be at least 2 characters.' },
        });
      }

      const updated = await this.authService.updateProfile(req.user!.id, name);
      return res.json({
        success: true,
        user: updated,
        message: 'Profile updated successfully.',
      });
    } catch (err: any) {
      return res.status(500).json({
        success: false,
        error: { code: 'UPDATE_FAILED', message: 'Unable to update profile.' },
      });
    }
  };
}
