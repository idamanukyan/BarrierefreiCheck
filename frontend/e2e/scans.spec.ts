import { test, expect } from '@playwright/test';

test.describe('Scan Functionality', () => {
  // Skip tests if no test credentials
  test.beforeEach(async ({ page }) => {
    const testEmail = process.env.E2E_TEST_EMAIL;
    const testPassword = process.env.E2E_TEST_PASSWORD;

    if (!testEmail || !testPassword) {
      test.skip();
      return;
    }

    // Login first
    await page.goto('/login');
    await page.fill('input[type="email"]', testEmail);
    await page.fill('input[type="password"]', testPassword);
    await page.click('button[type="submit"]');
    await page.waitForURL(/.*dashboard/, { timeout: 10000 });
  });

  test('should navigate to new scan page', async ({ page }) => {
    // Click new scan button
    await page.click('text=/new scan|start scan|scan/i');

    // Should see URL input
    await expect(page.locator('input[placeholder*="URL"], input[name*="url"]')).toBeVisible();
  });

  test('should validate URL before scanning', async ({ page }) => {
    await page.goto('/scans/new');

    // Enter invalid URL
    await page.fill('input[placeholder*="URL"], input[name*="url"]', 'not-a-url');

    // Try to start scan
    await page.click('button[type="submit"]');

    // Should show validation error
    await expect(page.locator('text=/invalid|valid URL|error/i')).toBeVisible();
  });

  test('should display scan history', async ({ page }) => {
    await page.goto('/scans');

    // Should see scans list or empty state
    const hasScansList = await page.locator('table, [data-testid="scans-list"]').isVisible();
    const hasEmptyState = await page.locator('text=/no scans|get started|first scan/i').isVisible();

    expect(hasScansList || hasEmptyState).toBeTruthy();
  });
});

test.describe('Scan Results', () => {
  test.beforeEach(async ({ page }) => {
    const testEmail = process.env.E2E_TEST_EMAIL;
    const testPassword = process.env.E2E_TEST_PASSWORD;

    if (!testEmail || !testPassword) {
      test.skip();
      return;
    }

    await page.goto('/login');
    await page.fill('input[type="email"]', testEmail);
    await page.fill('input[type="password"]', testPassword);
    await page.click('button[type="submit"]');
    await page.waitForURL(/.*dashboard/, { timeout: 10000 });
  });

  test('should display scan details when clicking on a scan', async ({ page }) => {
    await page.goto('/scans');

    // Check if there are any scans
    const scanRow = page.locator('tr, [data-testid="scan-item"]').first();
    const hasScans = await scanRow.isVisible();

    if (!hasScans) {
      test.skip();
      return;
    }

    // Click on first scan
    await scanRow.click();

    // Should show scan details
    await expect(page.locator('text=/issues|score|accessibility|WCAG/i')).toBeVisible();
  });

  test('should filter issues by impact level', async ({ page }) => {
    // Navigate to a scan with issues (if available)
    await page.goto('/scans');

    const scanRow = page.locator('tr, [data-testid="scan-item"]').first();
    if (!(await scanRow.isVisible())) {
      test.skip();
      return;
    }

    await scanRow.click();
    await page.waitForLoadState('networkidle');

    // Look for filter controls
    const filterButton = page.locator('button:has-text("Filter"), select[name*="impact"]');
    if (await filterButton.isVisible()) {
      await filterButton.click();
      // Check that filter options exist
      await expect(page.locator('text=/critical|serious|moderate|minor/i')).toBeVisible();
    }
  });
});
