import { test, expect } from '@playwright/test';

test.describe('Authentication', () => {
  test.beforeEach(async ({ page }) => {
    // Start from the home page
    await page.goto('/');
  });

  test('should display login page', async ({ page }) => {
    await page.click('text=Login');

    // Should be on login page
    await expect(page).toHaveURL(/.*login/);

    // Should have email and password fields
    await expect(page.locator('input[type="email"]')).toBeVisible();
    await expect(page.locator('input[type="password"]')).toBeVisible();

    // Should have login button
    await expect(page.locator('button[type="submit"]')).toBeVisible();
  });

  test('should display registration page', async ({ page }) => {
    await page.click('text=Register');

    // Should be on register page
    await expect(page).toHaveURL(/.*register/);

    // Should have required fields
    await expect(page.locator('input[type="email"]')).toBeVisible();
    await expect(page.locator('input[type="password"]')).toBeVisible();
  });

  test('should show error for invalid login', async ({ page }) => {
    await page.goto('/login');

    // Enter invalid credentials
    await page.fill('input[type="email"]', 'invalid@example.com');
    await page.fill('input[type="password"]', 'wrongpassword');

    // Submit form
    await page.click('button[type="submit"]');

    // Should show error message
    await expect(page.locator('text=/incorrect|invalid|error/i')).toBeVisible({ timeout: 5000 });
  });

  test('should enforce password requirements on registration', async ({ page }) => {
    await page.goto('/register');

    // Fill with weak password
    await page.fill('input[type="email"]', 'test@example.com');
    await page.fill('input[type="password"]', 'weak');

    // Try to submit
    await page.click('button[type="submit"]');

    // Should show validation error
    await expect(page.locator('text=/password|characters|requirements/i')).toBeVisible({ timeout: 5000 });
  });
});

test.describe('Authenticated User', () => {
  // Helper to log in before tests
  test.beforeEach(async ({ page }) => {
    // This would use a test account or mock authentication
    // For now, we'll skip if we can't authenticate
    await page.goto('/login');

    // Use environment variables for test credentials
    const testEmail = process.env.E2E_TEST_EMAIL;
    const testPassword = process.env.E2E_TEST_PASSWORD;

    if (!testEmail || !testPassword) {
      test.skip();
      return;
    }

    await page.fill('input[type="email"]', testEmail);
    await page.fill('input[type="password"]', testPassword);
    await page.click('button[type="submit"]');

    // Wait for redirect to dashboard
    await page.waitForURL(/.*dashboard/, { timeout: 10000 });
  });

  test('should display dashboard after login', async ({ page }) => {
    // Should see dashboard elements
    await expect(page.locator('text=/dashboard|scans|overview/i')).toBeVisible();
  });

  test('should be able to logout', async ({ page }) => {
    // Find and click logout
    await page.click('text=/logout|sign out/i');

    // Should redirect to home or login
    await expect(page).toHaveURL(/\/(login)?$/);
  });
});
