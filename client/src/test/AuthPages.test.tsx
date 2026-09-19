import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { RegisterPage } from '../pages/RegisterPage';
import { LoginPage } from '../pages/LoginPage';
import { VerifyEmailPage } from '../pages/VerifyEmailPage';
import { AuthProvider } from '../stores/AuthContext';
import { describe, it, expect } from 'vitest';

describe('Frontend Authentication UI Components', () => {
  it('renders registration form and password requirements checklist', () => {
    render(
      <AuthProvider>
        <BrowserRouter>
          <RegisterPage />
        </BrowserRouter>
      </AuthProvider>
    );

    expect(screen.getByText(/Create frAIday Account/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/full name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/work email/i)).toBeInTheDocument();
    expect(screen.getByText(/At least 8 characters/i)).toBeInTheDocument();
    expect(screen.getByText(/At least 1 numeric digit/i)).toBeInTheDocument();
    expect(screen.getByText(/At least 1 special character/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /register/i })).toBeInTheDocument();
  });

  it('renders login form with anti-enumeration hints and forgot password link', () => {
    render(
      <AuthProvider>
        <BrowserRouter>
          <LoginPage />
        </BrowserRouter>
      </AuthProvider>
    );

    expect(screen.getByText(/Sign in to frAIday/i)).toBeInTheDocument();
    expect(screen.getByText(/Forgot password/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /authenticate/i })).toBeInTheDocument();

    // Verify top-left frAIday brand icon returns to home page '/'
    const homeLink = screen.getByRole('link', { name: /return to fraiday home page/i });
    expect(homeLink).toBeInTheDocument();
    expect(homeLink).toHaveAttribute('href', '/');
  });

  it('renders email verification initial validating state', () => {
    render(
      <AuthProvider>
        <BrowserRouter>
          <VerifyEmailPage />
        </BrowserRouter>
      </AuthProvider>
    );

    expect(screen.getByText(/Email Verification/i)).toBeInTheDocument();
  });
});
