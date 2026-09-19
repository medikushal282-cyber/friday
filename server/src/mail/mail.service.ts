import nodemailer from 'nodemailer';
import dotenv from 'dotenv';

dotenv.config();

export interface EmailMessage {
  to: string;
  subject: string;
  html: string;
  text: string;
  previewUrl?: string | null;
  messageId?: string;
  deliveryMode: 'smtp' | 'ethereal' | 'mock';
  sentAt: string;
}

export class MailService {
  private transporter: nodemailer.Transporter | null = null;
  private etherealTransporter: nodemailer.Transporter | null = null;
  private etherealReadyPromise: Promise<void> | null = null;
  public sentMails: EmailMessage[] = [];
  private useMock: boolean;
  private appUrl: string;

  constructor(useMock?: boolean) {
    const isTest = process.env.NODE_ENV === 'test';

    this.useMock =
      useMock !== undefined
        ? useMock
        : isTest ||
          process.env.USE_MOCK_MAIL === 'true' ||
          (!process.env.SMTP_HOST && !process.env.SMTP_SERVICE) ||
          Boolean(process.env.SMTP_HOST?.includes('example.com'));

    this.appUrl = process.env.APP_URL || 'http://localhost:5173';

    if (isTest) {
      // In automated testing, skip network calls to ensure sub-second test execution
      return;
    }

    if (!this.useMock && (process.env.SMTP_HOST || process.env.SMTP_SERVICE)) {
      console.log('[frAIday Mail] Configuring fast pooled SMTP transporter...');
      const transportOptions: any = {
        pool: true,
        maxConnections: 5,
        maxMessages: 100,
        rateDelta: 1000,
        rateLimit: 5,
        connectionTimeout: 5000,
        greetingTimeout: 5000,
        socketTimeout: 10000,
      };

      if (process.env.SMTP_SERVICE) {
        transportOptions.service = process.env.SMTP_SERVICE;
      } else {
        transportOptions.host = process.env.SMTP_HOST;
        transportOptions.port = Number(process.env.SMTP_PORT) || 587;
        transportOptions.secure = process.env.SMTP_SECURE === 'true';
      }

      transportOptions.auth = {
        user: process.env.SMTP_USER,
        pass: process.env.SMTP_PASSWORD,
      };

      this.transporter = nodemailer.createTransport(transportOptions);

      // Verify connection in the background so it does not block startup
      this.transporter.verify().then(() => {
        console.log('[frAIday Mail] Fast pooled SMTP connection verified successfully.');
      }).catch((err) => {
        console.warn('[frAIday Mail] Fast SMTP verification warning (will attempt on dispatch):', err.message);
      });
    } else {
      console.log('[frAIday Mail] Initializing Fast Ethereal SMTP account for instant webmail previews...');
      this.etherealReadyPromise = nodemailer.createTestAccount()
        .then((account) => {
          this.etherealTransporter = nodemailer.createTransport({
            host: account.smtp.host,
            port: account.smtp.port,
            secure: account.smtp.secure,
            pool: true,
            auth: {
              user: account.user,
              pass: account.pass,
            },
          });
          console.log(`[frAIday Mail] Fast Ethereal SMTP active (user: ${account.user}). Live inbox previews enabled.`);
        })
        .catch((err) => {
          console.warn('[frAIday Mail] Ethereal initialization note (using local mock):', err.message);
        });
    }
  }

  public clearSentMails(): void {
    this.sentMails = [];
  }

  public getLastSentMail(): EmailMessage | undefined {
    return this.sentMails[this.sentMails.length - 1];
  }

  async sendVerificationEmail(to: string, name: string, rawToken: string): Promise<string> {
    const verifyUrl = `${this.appUrl}/verify-email?token=${encodeURIComponent(rawToken)}`;

    const subject = 'Verify your frAIday account';
    const html = `
      <!DOCTYPE html>
      <html>
      <head>
        <meta charset="utf-8">
        <style>
          body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #F5F2EA; color: #000000; padding: 24px; }
          .container { max-width: 560px; margin: 0 auto; background-color: #FAF8F3; border: 2px solid #000000; padding: 32px; box-shadow: 4px 4px 0px #000000; }
          .logo { font-family: monospace; font-size: 20px; font-weight: bold; background: #000; color: #fff; display: inline-block; padding: 2px 8px; margin-bottom: 24px; }
          h1 { font-size: 20px; font-weight: 800; color: #000000; margin-bottom: 16px; text-transform: uppercase; }
          p { font-size: 14px; line-height: 1.6; color: #262626; margin-bottom: 20px; }
          .btn { display: inline-block; background-color: #FFE600; color: #000000; text-decoration: none; padding: 12px 28px; border: 2px solid #000; font-weight: 800; font-size: 14px; margin-bottom: 24px; box-shadow: 2px 2px 0px #000; text-transform: uppercase; }
          .notice { font-size: 11px; font-family: monospace; color: #525252; border-top: 2px solid #000; padding-top: 16px; margin-top: 24px; }
        </style>
      </head>
      <body>
        <div class="container">
          <div class="logo">FRAIDAY_</div>
          <h1>Verify your frAIday account</h1>
          <p>Hello ${name},</p>
          <p>Welcome to frAIday — the AI-native workspace for autonomous execution. To secure your account and access the autonomous workspace, please confirm your email address.</p>
          <a href="${verifyUrl}" class="btn">Verify Account</a>
          <p>This verification link expires in 24 hours and can only be used once.</p>
          <div class="notice">
            If you did not create an account on frAIday, you can safely disregard this message. No password or sensitive credentials are ever included in this email.
          </div>
        </div>
      </body>
      </html>
    `;

    const text = `Welcome to frAIday, ${name}!\n\nPlease verify your account by visiting the link below:\n${verifyUrl}\n\nThis link expires in 24 hours.\nIf you did not sign up, please ignore this email.`;

    let previewUrl: string | null = null;
    let messageId: string | undefined;
    let deliveryMode: 'smtp' | 'ethereal' | 'mock' = 'mock';

    // 1. If configured with real fast SMTP
    if (this.transporter) {
      try {
        const info = await this.transporter.sendMail({
          from: process.env.SMTP_FROM || '"frAIday Security" <no-reply@fraiday.ai>',
          to,
          subject,
          html,
          text,
        });
        deliveryMode = 'smtp';
        messageId = info.messageId;
      } catch (err: any) {
        console.error('[frAIday Mail] Real SMTP send error (falling back to fast mock/preview):', err.message);
      }
    }

    // 2. If Ethereal test transporter is active
    if (deliveryMode === 'mock') {
      if (this.etherealReadyPromise) {
        try {
          await this.etherealReadyPromise;
        } catch {
          // ignore
        }
      }
      if (this.etherealTransporter) {
        try {
          const info = await this.etherealTransporter.sendMail({
            from: '"frAIday Security" <no-reply@fraiday.ai>',
            to,
            subject,
            html,
            text,
          });
          deliveryMode = 'ethereal';
          messageId = info.messageId;
          previewUrl = nodemailer.getTestMessageUrl(info) || null;
        } catch (err: any) {
          console.warn('[frAIday Mail] Ethereal delivery error:', err.message);
        }
      }
    }

    const message: EmailMessage = {
      to,
      subject,
      html,
      text,
      previewUrl,
      messageId,
      deliveryMode,
      sentAt: new Date().toISOString(),
    };
    this.sentMails.push(message);

    console.log('\n============================================================');
    console.log(`[frAIday Mail] VERIFICATION EMAIL DISPATCHED (${deliveryMode.toUpperCase()} FAST MODE)`);
    console.log(`[frAIday Mail] RECIPIENT: ${to}`);
    console.log(`[frAIday Mail] DIRECT VERIFY LINK: ${verifyUrl}`);
    if (previewUrl) {
      console.log(`[frAIday Mail] ✉️ LIVE WEB INBOX PREVIEW: ${previewUrl}`);
    }
    console.log('============================================================\n');

    return verifyUrl;
  }

  async sendPasswordResetEmail(to: string, name: string, rawToken: string): Promise<string> {
    const resetUrl = `${this.appUrl}/reset-password?token=${encodeURIComponent(rawToken)}`;

    const subject = 'Reset your frAIday password';
    const html = `
      <!DOCTYPE html>
      <html>
      <head>
        <meta charset="utf-8">
        <style>
          body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #F5F2EA; color: #000000; padding: 24px; }
          .container { max-width: 560px; margin: 0 auto; background-color: #FAF8F3; border: 2px solid #000000; padding: 32px; box-shadow: 4px 4px 0px #000000; }
          .logo { font-family: monospace; font-size: 20px; font-weight: bold; background: #000; color: #fff; display: inline-block; padding: 2px 8px; margin-bottom: 24px; }
          h1 { font-size: 20px; font-weight: 800; color: #000000; margin-bottom: 16px; text-transform: uppercase; }
          p { font-size: 14px; line-height: 1.6; color: #262626; margin-bottom: 20px; }
          .btn { display: inline-block; background-color: #FFE600; color: #000000; text-decoration: none; padding: 12px 28px; border: 2px solid #000; font-weight: 800; font-size: 14px; margin-bottom: 24px; box-shadow: 2px 2px 0px #000; text-transform: uppercase; }
          .notice { font-size: 11px; font-family: monospace; color: #525252; border-top: 2px solid #000; padding-top: 16px; margin-top: 24px; }
        </style>
      </head>
      <body>
        <div class="container">
          <div class="logo">FRAIDAY_</div>
          <h1>Password Reset Request</h1>
          <p>Hello ${name},</p>
          <p>We received a request to reset your password for frAIday. Click the button below to choose a new password.</p>
          <a href="${resetUrl}" class="btn">Reset Password</a>
          <p>This reset link expires in 15 minutes and can only be used once. After reset, all existing active sessions will be revoked for security.</p>
          <div class="notice">
            If you did not request this password reset, please ignore this email. Your password remains safe and unchanged.
          </div>
        </div>
      </body>
      </html>
    `;

    const text = `Hello ${name},\n\nA password reset was requested for your frAIday account. Visit the link below to set a new password:\n${resetUrl}\n\nThis link expires in 15 minutes.\nIf you did not request this, please ignore this email.`;

    let previewUrl: string | null = null;
    let messageId: string | undefined;
    let deliveryMode: 'smtp' | 'ethereal' | 'mock' = 'mock';

    if (this.transporter) {
      try {
        const info = await this.transporter.sendMail({
          from: process.env.SMTP_FROM || '"frAIday Security" <no-reply@fraiday.ai>',
          to,
          subject,
          html,
          text,
        });
        deliveryMode = 'smtp';
        messageId = info.messageId;
      } catch (err: any) {
        console.error('[frAIday Mail] Real SMTP send error (falling back to fast mock/preview):', err.message);
      }
    }

    if (deliveryMode === 'mock') {
      if (this.etherealReadyPromise) {
        try {
          await this.etherealReadyPromise;
        } catch {
          // ignore
        }
      }
      if (this.etherealTransporter) {
        try {
          const info = await this.etherealTransporter.sendMail({
            from: '"frAIday Security" <no-reply@fraiday.ai>',
            to,
            subject,
            html,
            text,
          });
          deliveryMode = 'ethereal';
          messageId = info.messageId;
          previewUrl = nodemailer.getTestMessageUrl(info) || null;
        } catch (err: any) {
          console.warn('[frAIday Mail] Ethereal delivery error:', err.message);
        }
      }
    }

    const message: EmailMessage = {
      to,
      subject,
      html,
      text,
      previewUrl,
      messageId,
      deliveryMode,
      sentAt: new Date().toISOString(),
    };
    this.sentMails.push(message);

    console.log('\n============================================================');
    console.log(`[frAIday Mail] PASSWORD RESET EMAIL DISPATCHED (${deliveryMode.toUpperCase()} FAST MODE)`);
    console.log(`[frAIday Mail] RECIPIENT: ${to}`);
    console.log(`[frAIday Mail] DIRECT RESET LINK: ${resetUrl}`);
    if (previewUrl) {
      console.log(`[frAIday Mail] ✉️ LIVE WEB INBOX PREVIEW: ${previewUrl}`);
    }
    console.log('============================================================\n');

    return resetUrl;
  }
}
