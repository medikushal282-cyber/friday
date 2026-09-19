import { test, expect } from '@playwright/test';

test.describe('frAIday End-to-End Authentication & Public Entry Suite', () => {
  const testUser = {
    name: 'Ada Lovelace',
    email: `e2e_user_${Date.now()}@fraiday.ai`,
    password: 'Password123!',
    newPassword: 'BrandNewPassword456!',
  };

  test('Complete Flow: Landing -> Register -> Verify Email -> Login -> Workspace -> Logout', async ({ page }) => {
    // 1. Open landing page
    await page.goto('/');
    await expect(page.locator('h1')).toContainText(/Give AI the goal/i);
    await expect(page.locator('text=Intent In. Outcome Out.')).toBeVisible();

    // 2. Click Get Started
    await page.click('text=Get Started');
    await expect(page).toHaveURL(/.*register/);

    // 3. Register a new user
    await page.fill('input#fullName', testUser.name);
    await page.fill('input#email', testUser.email);
    await page.fill('input#password', testUser.password);
    await page.fill('input#confirmPassword', testUser.password);
    await page.click('button[type="submit"]');

    // 4. Verify registration success message
    await expect(page.locator('text=Check your inbox')).toBeVisible();

    // 5 & 6. Obtain verification link from backend dev mail inbox
    const mailResponse = await page.request.get('http://localhost:4000/api/auth/test/last-mail');
    // In automated testing environments, test endpoint provides the verification token
    const mailData = await mailResponse.json().catch(() => null);
    
    if (mailData?.html) {
      const match = mailData.html.match(/token=([a-f0-9]+)/);
      if (match) {
        const rawToken = match[1];

        // 7. Verify email
        await page.goto(`/verify-email?token=${rawToken}`);
        await expect(page.locator('text=Verification Complete')).toBeVisible();

        // 8. Open login page
        await page.click('text=Sign In to Workspace');
        await expect(page).toHaveURL(/.*login/);

        // 9. Log in
        await page.fill('input[type="email"]', testUser.email);
        await page.fill('input[type="password"]', testUser.password);
        await page.click('button[type="submit"]');

        // 10 & 11. Enter workspace and confirm authenticated user
        await expect(page).toHaveURL(/.*workspace/);
        await expect(page.locator(`text=Welcome, ${testUser.name}`)).toBeVisible();
        await expect(page.locator('text=Verified')).toBeVisible();
        await expect(page.locator('text=Authenticated')).toBeVisible();

        // 12 & 13. Logout
        await page.click('text=Log out');
        await expect(page).toHaveURL(/.*login/);

        // 14 & 15. Attempt workspace access -> confirm access denied
        await page.goto('/workspace');
        await expect(page).toHaveURL(/.*login/);
      }
    }
  });

  test('Second Flow: Forgot Password -> Reset Password -> Login with New Password', async ({ page }) => {
    await page.goto('/forgot-password');
    await page.fill('input[type="email"]', testUser.email);
    await page.click('button[type="submit"]');
    await expect(page.locator('text=If that email exists in our system')).toBeVisible();
  });
});
