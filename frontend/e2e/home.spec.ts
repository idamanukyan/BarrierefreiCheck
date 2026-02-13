import { test, expect } from '@playwright/test';

test.describe('Homepage', () => {
  test('should load homepage successfully', async ({ page }) => {
    await page.goto('/');

    // Should have main heading
    await expect(page.locator('h1')).toBeVisible();

    // Should have navigation
    await expect(page.locator('nav, header')).toBeVisible();
  });

  test('should have working navigation links', async ({ page }) => {
    await page.goto('/');

    // Check for login link
    const loginLink = page.locator('a[href*="login"], button:has-text("Login")');
    await expect(loginLink).toBeVisible();

    // Check for register link
    const registerLink = page.locator('a[href*="register"], button:has-text("Register")');
    await expect(registerLink).toBeVisible();
  });

  test('should be responsive on mobile', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/');

    // Page should still be functional
    await expect(page.locator('h1')).toBeVisible();

    // Check for mobile menu or hamburger
    const mobileMenu = page.locator('[aria-label*="menu"], button:has-text("Menu"), .hamburger');
    const desktopNav = page.locator('nav:visible');

    // Either mobile menu or desktop nav should be visible
    const hasMobileMenu = await mobileMenu.isVisible();
    const hasDesktopNav = await desktopNav.isVisible();

    expect(hasMobileMenu || hasDesktopNav).toBeTruthy();
  });

  test('should support language switching if available', async ({ page }) => {
    await page.goto('/');

    // Look for language switcher
    const langSwitcher = page.locator('button:has-text("DE"), button:has-text("EN"), [aria-label*="language"]');

    if (await langSwitcher.isVisible()) {
      // Click to switch language
      await langSwitcher.click();

      // Should have language options
      await expect(page.locator('text=/Deutsch|English|DE|EN/')).toBeVisible();
    }
  });
});

test.describe('Accessibility', () => {
  test('homepage should not have obvious accessibility issues', async ({ page }) => {
    await page.goto('/');

    // Check for basic accessibility requirements

    // All images should have alt text
    const imagesWithoutAlt = await page.locator('img:not([alt])').count();
    expect(imagesWithoutAlt).toBe(0);

    // Page should have a main landmark
    const mainLandmark = page.locator('main, [role="main"]');
    await expect(mainLandmark).toBeVisible();

    // Page should have a heading structure
    const h1 = page.locator('h1');
    await expect(h1).toBeVisible();

    // Links should have accessible text
    const emptyLinks = await page.locator('a:not(:has-text(*)):not([aria-label])').count();
    expect(emptyLinks).toBe(0);
  });

  test('forms should have labels', async ({ page }) => {
    await page.goto('/login');

    // All form inputs should have associated labels
    const inputs = page.locator('input:not([type="hidden"]):not([type="submit"])');
    const inputCount = await inputs.count();

    for (let i = 0; i < inputCount; i++) {
      const input = inputs.nth(i);
      const id = await input.getAttribute('id');
      const ariaLabel = await input.getAttribute('aria-label');
      const ariaLabelledby = await input.getAttribute('aria-labelledby');
      const placeholder = await input.getAttribute('placeholder');

      // Input should have some form of labeling
      const hasLabel = id ? (await page.locator(`label[for="${id}"]`).count()) > 0 : false;
      const hasAccessibleName = ariaLabel || ariaLabelledby || placeholder || hasLabel;

      expect(hasAccessibleName).toBeTruthy();
    }
  });

  test('should have sufficient color contrast (visual check)', async ({ page }) => {
    await page.goto('/');

    // Take a screenshot for visual inspection
    // In a full setup, you'd use axe-playwright or similar
    await page.screenshot({ path: 'playwright-report/homepage-contrast.png' });
  });
});

test.describe('Performance', () => {
  test('homepage should load within acceptable time', async ({ page }) => {
    const startTime = Date.now();

    await page.goto('/', { waitUntil: 'domcontentloaded' });

    const loadTime = Date.now() - startTime;

    // Page should load in under 3 seconds
    expect(loadTime).toBeLessThan(3000);
  });

  test('should not have console errors', async ({ page }) => {
    const errors: string[] = [];

    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        errors.push(msg.text());
      }
    });

    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Filter out known acceptable errors (e.g., favicon 404)
    const criticalErrors = errors.filter(
      (e) => !e.includes('favicon') && !e.includes('404')
    );

    expect(criticalErrors).toHaveLength(0);
  });
});
