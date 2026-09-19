import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { LandingPage } from '../pages/LandingPage';
import { describe, it, expect } from 'vitest';

describe('Milestone 1: frAIday Landing Page', () => {
  it('renders brand identity and primary headline', () => {
    render(
      <BrowserRouter>
        <LandingPage />
      </BrowserRouter>
    );

    expect(screen.getAllByText(/frAIday/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/Give AI the goal/i)).toBeInTheDocument();
    expect(screen.getByText(/Let it execute the work/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Intent In. Outcome Out./i).length).toBeGreaterThan(0);
  });

  it('renders core pipeline workflow steps', () => {
    render(
      <BrowserRouter>
        <LandingPage />
      </BrowserRouter>
    );

    expect(screen.getAllByText(/Intent In/i).length).toBeGreaterThan(0);
    expect(screen.getByText('Plan')).toBeInTheDocument();
    expect(screen.getByText('Research')).toBeInTheDocument();
    expect(screen.getByText('Execute')).toBeInTheDocument();
    expect(screen.getByText('Validate')).toBeInTheDocument();
    expect(screen.getByText('Deliver')).toBeInTheDocument();
  });

  it('renders navigation CTAs and links', () => {
    render(
      <BrowserRouter>
        <LandingPage />
      </BrowserRouter>
    );

    // CTAs
    const getStartedButtons = screen.getAllByRole('link', { name: /get started/i });
    expect(getStartedButtons.length).toBeGreaterThan(0);

    const loginButtons = screen.getAllByRole('link', { name: /log in/i });
    expect(loginButtons.length).toBeGreaterThan(0);

    // Section Links
    expect(screen.getByRole('link', { name: /see how it works/i })).toBeInTheDocument();
  });

  it('renders realistic workspace preview and security guardrails', () => {
    render(
      <BrowserRouter>
        <LandingPage />
      </BrowserRouter>
    );

    expect(screen.getAllByText(/AI-Native Autonomous Workspace/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/Human Approval Required/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Sandboxed Execution/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/Immutable Audit Trails/i)).toBeInTheDocument();
  });
});
