import { Request, Response, NextFunction } from 'express';
import { AuthService } from '../services/auth.service.js';
import { SafeUser } from '../types/index.js';

export interface AuthenticatedRequest extends Request {
  user?: SafeUser;
  sessionToken?: string;
}

export function createAuthMiddleware(authService: AuthService) {
  const cookieName = process.env.SESSION_COOKIE_NAME || 'fraiday_session';

  return async (req: AuthenticatedRequest, res: Response, next: NextFunction) => {
    try {
      const sessionToken =
        req.cookies?.[cookieName] ||
        (req.headers.authorization?.startsWith('Bearer ')
          ? req.headers.authorization.substring(7)
          : undefined);

      if (!sessionToken) {
        return res.status(401).json({
          success: false,
          error: {
            code: 'UNAUTHORIZED',
            message: 'Authentication required to access this resource.',
          },
        });
      }

      const user = await authService.getCurrentUser(sessionToken);
      if (!user) {
        return res.status(401).json({
          success: false,
          error: {
            code: 'SESSION_INVALID',
            message: 'Your session has expired or is invalid. Please log in again.',
          },
        });
      }

      req.user = user;
      req.sessionToken = sessionToken;
      next();
    } catch (err) {
      return res.status(500).json({
        success: false,
        error: {
          code: 'INTERNAL_ERROR',
          message: 'An internal error occurred while validating your session.',
        },
      });
    }
  };
}

export function requireVerifiedEmail(
  req: AuthenticatedRequest,
  res: Response,
  next: NextFunction
) {
  if (process.env.SKIP_EMAIL_VERIFICATION === 'true') {
    return next();
  }
  if (!req.user?.emailVerified) {
    return res.status(403).json({
      success: false,
      error: {
        code: 'EMAIL_NOT_VERIFIED',
        message: 'You must verify your email address to access this resource.',
      },
    });
  }
  next();
}
