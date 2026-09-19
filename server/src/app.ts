import express, { Express, Request, Response, NextFunction } from 'express';
import helmet from 'helmet';
import cors from 'cors';
import cookieParser from 'cookie-parser';
import crypto from 'crypto';
import { AuthService } from './services/auth.service.js';
import { MailService } from './mail/mail.service.js';
import { createAuthRouter } from './routes/auth.routes.js';
import { generalLimiter } from './middleware/rate-limiter.js';

export interface AppDependencies {
  authService: AuthService;
  mailService?: MailService;
}

export function createApp(deps: AppDependencies): Express {
  const app = express();

  // Request ID middleware for structured observability
  app.use((req: Request, res: Response, next: NextFunction) => {
    const requestId = (req.headers['x-request-id'] as string) || crypto.randomUUID();
    res.setHeader('x-request-id', requestId);
    (req as any).requestId = requestId;
    next();
  });

  // Security Headers
  app.use(
    helmet({
      contentSecurityPolicy: false,
      crossOriginEmbedderPolicy: false,
    })
  );

  // CORS
  const appUrl = process.env.APP_URL || 'http://localhost:5173';
  app.use(
    cors({
      origin: [appUrl, 'http://localhost:3000', 'http://127.0.0.1:5173'],
      credentials: true,
      methods: ['GET', 'POST', 'PATCH', 'DELETE', 'OPTIONS'],
      allowedHeaders: ['Content-Type', 'Authorization', 'x-request-id'],
    })
  );

  app.use(cookieParser());
  app.use(express.json({ limit: '100kb' }));
  app.use(generalLimiter);

  // Health endpoint
  app.get('/health', (req: Request, res: Response) => {
    res.json({
      status: 'healthy',
      service: 'fraiday-auth-service',
      timestamp: new Date().toISOString(),
      requestId: (req as any).requestId,
    });
  });

  // API Routes
  app.use('/api/auth', createAuthRouter(deps.authService, deps.mailService));

  // 404 handler
  app.use((req: Request, res: Response) => {
    res.status(404).json({
      success: false,
      error: {
        code: 'NOT_FOUND',
        message: `Endpoint ${req.method} ${req.path} not found.`,
      },
    });
  });

  // Global Error Handler
  app.use((err: any, req: Request, res: Response, next: NextFunction) => {
    res.status(500).json({
      success: false,
      error: {
        code: 'INTERNAL_SERVER_ERROR',
        message: 'An unexpected error occurred.',
        requestId: (req as any).requestId,
      },
    });
  });

  return app;
}
