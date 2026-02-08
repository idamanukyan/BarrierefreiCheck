/**
 * Screenshot Utility
 *
 * Captures screenshots of elements and pages for accessibility reports.
 */

import { Page, ElementHandle } from 'puppeteer';
import { logger } from './logger.js';
import * as path from 'path';
import * as fs from 'fs/promises';

// UUID v4 regex pattern for validation
const UUID_REGEX = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

/**
 * Validate that a scanId is a valid UUID to prevent path traversal attacks
 */
function validateScanId(scanId: string): boolean {
  return UUID_REGEX.test(scanId);
}

/**
 * Sanitize a string for use in filenames
 * Removes any characters that could be used for path traversal
 */
function sanitizeForFilename(input: string): string {
  // Remove any path separators and special characters
  return input.replace(/[^a-zA-Z0-9_-]/g, '_').substring(0, 100);
}

export interface ScreenshotOptions {
  outputDir: string;
  fullPage?: boolean;
  quality?: number;
  type?: 'png' | 'jpeg' | 'webp';
  padding?: number; // Padding around element
}

export interface ElementScreenshotResult {
  success: boolean;
  filePath?: string;
  error?: string;
}

const DEFAULT_OPTIONS: ScreenshotOptions = {
  outputDir: './screenshots',
  fullPage: false,
  quality: 80,
  type: 'png',
  padding: 10,
};

/**
 * Ensure output directory exists
 */
async function ensureDir(dir: string): Promise<void> {
  try {
    await fs.mkdir(dir, { recursive: true });
  } catch (error) {
    // Directory might already exist
  }
}

/**
 * Build a safe screenshot directory path for a scan
 * Validates scanId and returns an absolute path within the allowed directory
 */
export function getSafeScreenshotDir(baseDir: string, scanId: string): string {
  if (!validateScanId(scanId)) {
    throw new Error(`Invalid scanId format: ${scanId}`);
  }

  // Use path.resolve to get absolute path and ensure it's within baseDir
  const safePath = path.resolve(baseDir, scanId);

  // Verify the resolved path is still within the base directory
  const resolvedBase = path.resolve(baseDir);
  if (!safePath.startsWith(resolvedBase)) {
    throw new Error('Path traversal attempt detected');
  }

  return safePath;
}

/**
 * Generate a unique filename for screenshot
 * Validates scanId and sanitizes ruleId to prevent path traversal
 */
function generateFilename(
  scanId: string,
  ruleId: string,
  index: number,
  type: string
): string {
  // Validate scanId is a valid UUID
  if (!validateScanId(scanId)) {
    throw new Error(`Invalid scanId format: ${scanId}`);
  }

  // Sanitize ruleId to prevent any path traversal
  const safeRuleId = sanitizeForFilename(ruleId);
  const timestamp = Date.now();

  return `${scanId}_${safeRuleId}_${index}_${timestamp}.${type}`;
}

/**
 * Capture screenshot of a specific element
 */
export async function captureElementScreenshot(
  page: Page,
  selector: string,
  scanId: string,
  ruleId: string,
  index: number,
  options: Partial<ScreenshotOptions> = {}
): Promise<ElementScreenshotResult> {
  const config = { ...DEFAULT_OPTIONS, ...options };

  // Validate scanId to prevent path traversal attacks
  if (!validateScanId(scanId)) {
    logger.error(`Invalid scanId format rejected: ${scanId}`);
    return {
      success: false,
      error: 'Invalid scanId format',
    };
  }

  try {
    await ensureDir(config.outputDir);

    // Find the element
    const element = await page.$(selector);

    if (!element) {
      logger.debug(`Element not found for screenshot: ${selector}`);
      return {
        success: false,
        error: `Element not found: ${selector}`,
      };
    }

    // Get element bounding box
    const boundingBox = await element.boundingBox();

    if (!boundingBox) {
      logger.debug(`Cannot get bounding box for: ${selector}`);
      return {
        success: false,
        error: `Cannot get bounding box for: ${selector}`,
      };
    }

    // Scroll element into view
    await element.scrollIntoView();
    await page.waitForTimeout(200); // Wait for scroll

    // Calculate clip area with padding
    const padding = config.padding || 0;
    const viewport = page.viewport();
    const pageWidth = viewport?.width || 1920;
    const pageHeight = viewport?.height || 1080;

    const clip = {
      x: Math.max(0, boundingBox.x - padding),
      y: Math.max(0, boundingBox.y - padding),
      width: Math.min(boundingBox.width + padding * 2, pageWidth - boundingBox.x + padding),
      height: Math.min(boundingBox.height + padding * 2, pageHeight - boundingBox.y + padding),
    };

    // Generate filename
    const filename = generateFilename(scanId, ruleId, index, config.type || 'png');
    const filePath = path.join(config.outputDir, filename);

    // Take screenshot
    await page.screenshot({
      path: filePath,
      type: config.type,
      quality: config.type === 'png' ? undefined : config.quality,
      clip,
    });

    logger.debug(`Screenshot captured: ${filePath}`);

    return {
      success: true,
      filePath: filename,
    };
  } catch (error) {
    const errorMessage =
      error instanceof Error ? error.message : 'Unknown error';
    logger.error(`Screenshot capture failed: ${errorMessage}`);

    return {
      success: false,
      error: errorMessage,
    };
  }
}

/**
 * Capture full page screenshot
 */
export async function captureFullPageScreenshot(
  page: Page,
  scanId: string,
  pageIndex: number,
  options: Partial<ScreenshotOptions> = {}
): Promise<ElementScreenshotResult> {
  const config = { ...DEFAULT_OPTIONS, ...options };

  // Validate scanId to prevent path traversal attacks
  if (!validateScanId(scanId)) {
    logger.error(`Invalid scanId format rejected: ${scanId}`);
    return {
      success: false,
      error: 'Invalid scanId format',
    };
  }

  try {
    await ensureDir(config.outputDir);

    const filename = `${scanId}_fullpage_${pageIndex}_${Date.now()}.${config.type}`;
    const filePath = path.join(config.outputDir, filename);

    await page.screenshot({
      path: filePath,
      fullPage: true,
      type: config.type,
      quality: config.type === 'png' ? undefined : config.quality,
    });

    logger.debug(`Full page screenshot captured: ${filePath}`);

    return {
      success: true,
      filePath: filename,
    };
  } catch (error) {
    const errorMessage =
      error instanceof Error ? error.message : 'Unknown error';
    logger.error(`Full page screenshot failed: ${errorMessage}`);

    return {
      success: false,
      error: errorMessage,
    };
  }
}

/**
 * Capture screenshots for multiple issues
 */
export async function captureIssueScreenshots(
  page: Page,
  issues: Array<{ selector: string; ruleId: string }>,
  scanId: string,
  options: Partial<ScreenshotOptions> = {}
): Promise<Map<string, ElementScreenshotResult>> {
  const results = new Map<string, ElementScreenshotResult>();

  for (let i = 0; i < issues.length; i++) {
    const issue = issues[i];
    const result = await captureElementScreenshot(
      page,
      issue.selector,
      scanId,
      issue.ruleId,
      i,
      options
    );

    results.set(`${issue.ruleId}-${i}`, result);

    // Small delay between screenshots
    await page.waitForTimeout(100);
  }

  return results;
}

/**
 * Highlight element before screenshot (adds visual indicator)
 */
export async function highlightElement(
  page: Page,
  selector: string,
  color: string = '#ff0000'
): Promise<void> {
  try {
    await page.evaluate(
      (sel, col) => {
        const element = document.querySelector(sel);
        if (element) {
          const el = element as HTMLElement;
          el.style.outline = `3px solid ${col}`;
          el.style.outlineOffset = '2px';
        }
      },
      selector,
      color
    );
  } catch {
    // Ignore errors - element might not exist
  }
}

/**
 * Remove element highlight
 */
export async function removeHighlight(
  page: Page,
  selector: string
): Promise<void> {
  try {
    await page.evaluate((sel) => {
      const element = document.querySelector(sel);
      if (element) {
        const el = element as HTMLElement;
        el.style.outline = '';
        el.style.outlineOffset = '';
      }
    }, selector);
  } catch {
    // Ignore errors
  }
}

/**
 * Capture screenshot with highlight
 */
export async function captureHighlightedScreenshot(
  page: Page,
  selector: string,
  scanId: string,
  ruleId: string,
  index: number,
  options: Partial<ScreenshotOptions> = {}
): Promise<ElementScreenshotResult> {
  // Add highlight
  await highlightElement(page, selector, '#e53e3e');

  // Wait for highlight to render
  await page.waitForTimeout(100);

  // Capture screenshot
  const result = await captureElementScreenshot(
    page,
    selector,
    scanId,
    ruleId,
    index,
    options
  );

  // Remove highlight
  await removeHighlight(page, selector);

  return result;
}
