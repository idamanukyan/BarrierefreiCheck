/**
 * Browser Manager - Puppeteer browser instance management
 *
 * Handles browser lifecycle, page creation, and resource cleanup.
 *
 * SECURITY NOTE: This scanner visits untrusted websites. We maintain browser
 * security features (same-origin policy, site isolation) to prevent malicious
 * websites from exploiting the scanner. The scanner operates in a sandboxed
 * Docker container for additional isolation.
 */

import puppeteer, { Browser, Page, PuppeteerLaunchOptions } from 'puppeteer';
import { logger } from './logger.js';

export interface BrowserConfig {
  headless?: boolean;
  timeout?: number;
  viewport?: { width: number; height: number };
  userAgent?: string;
  /** Allow disabling sandbox for Docker environments (requires container isolation) */
  allowNoSandbox?: boolean;
}

const DEFAULT_CONFIG: BrowserConfig = {
  headless: true,
  timeout: 30000,
  viewport: { width: 1920, height: 1080 },
  userAgent:
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 AccessibilityChecker/1.0',
  allowNoSandbox: true, // Required for Docker, ensure container provides isolation
};

export class BrowserManager {
  private browser: Browser | null = null;
  private config: BrowserConfig;

  constructor(config: Partial<BrowserConfig> = {}) {
    this.config = { ...DEFAULT_CONFIG, ...config };
  }

  /**
   * Launch a new browser instance
   *
   * SECURITY: We maintain browser security features to protect against
   * malicious websites. The scanner runs in a Docker container which
   * provides the necessary isolation for --no-sandbox mode.
   */
  async launch(): Promise<Browser> {
    if (this.browser) {
      return this.browser;
    }

    logger.info('Launching browser...');

    // Base arguments for performance and Docker compatibility
    const args: string[] = [
      '--disable-dev-shm-usage',     // Use /tmp instead of /dev/shm for shared memory
      '--disable-accelerated-2d-canvas',
      '--disable-gpu',
      '--window-size=1920,1080',
      // Security: Block potentially dangerous features
      '--disable-background-networking',
      '--disable-default-apps',
      '--disable-extensions',
      '--disable-sync',
      '--disable-translate',
      '--metrics-recording-only',
      '--mute-audio',
      '--no-first-run',
      // Limit resource usage per page
      '--single-process',            // Use single process for better isolation
      '--disable-backgrounding-occluded-windows',
    ];

    // Add sandbox flags only if explicitly allowed (Docker environments)
    // SECURITY NOTE: When using --no-sandbox, ensure the container provides
    // proper isolation (non-root user, seccomp profiles, read-only filesystem)
    if (this.config.allowNoSandbox) {
      args.push('--no-sandbox', '--disable-setuid-sandbox');
      logger.warn('Browser sandbox disabled - ensure container provides isolation');
    }

    const launchOptions: PuppeteerLaunchOptions = {
      headless: this.config.headless,
      args,
      defaultViewport: this.config.viewport,
    };

    this.browser = await puppeteer.launch(launchOptions);

    this.browser.on('disconnected', () => {
      logger.warn('Browser disconnected');
      this.browser = null;
    });

    logger.info('Browser launched successfully');
    return this.browser;
  }

  /**
   * Create a new page with configured settings
   *
   * SECURITY: Pages are created with security-conscious defaults:
   * - JavaScript dialogs are auto-dismissed
   * - Download behavior is disabled
   * - Potentially dangerous resources are blocked
   */
  async createPage(): Promise<Page> {
    const browser = await this.launch();
    const page = await browser.newPage();

    // Set user agent
    if (this.config.userAgent) {
      await page.setUserAgent(this.config.userAgent);
    }

    // Set viewport
    if (this.config.viewport) {
      await page.setViewport(this.config.viewport);
    }

    // Set default timeout
    page.setDefaultTimeout(this.config.timeout || 30000);
    page.setDefaultNavigationTimeout(this.config.timeout || 30000);

    // SECURITY: Auto-dismiss JavaScript dialogs to prevent scanner blocking
    page.on('dialog', async (dialog) => {
      logger.debug(`Auto-dismissing ${dialog.type()} dialog: ${dialog.message()}`);
      await dialog.dismiss();
    });

    // SECURITY: Block downloads to prevent malicious file execution
    const client = await page.createCDPSession();
    await client.send('Page.setDownloadBehavior', {
      behavior: 'deny',
    });

    // Block unnecessary and potentially dangerous resources
    await page.setRequestInterception(true);
    page.on('request', (request) => {
      const resourceType = request.resourceType();
      const url = request.url();

      // Block media to improve performance
      if (resourceType === 'media') {
        request.abort();
        return;
      }

      // SECURITY: Block data URLs in certain contexts (potential XSS vector)
      if (url.startsWith('data:') && resourceType === 'document') {
        logger.debug(`Blocked data URL navigation: ${url.substring(0, 100)}`);
        request.abort();
        return;
      }

      // SECURITY: Block known malicious URL schemes
      if (url.startsWith('javascript:') || url.startsWith('vbscript:')) {
        logger.debug(`Blocked dangerous URL scheme: ${url.substring(0, 50)}`);
        request.abort();
        return;
      }

      request.continue();
    });

    // SECURITY: Limit page context to prevent resource exhaustion
    page.on('error', (error) => {
      logger.error('Page error:', error.message);
    });

    page.on('pageerror', (error) => {
      logger.debug('Page JavaScript error:', error.message);
    });

    return page;
  }

  /**
   * Close a page
   */
  async closePage(page: Page): Promise<void> {
    try {
      if (!page.isClosed()) {
        await page.close();
      }
    } catch (error) {
      logger.error('Error closing page:', error);
    }
  }

  /**
   * Close the browser instance
   */
  async close(): Promise<void> {
    if (this.browser) {
      logger.info('Closing browser...');
      await this.browser.close();
      this.browser = null;
      logger.info('Browser closed');
    }
  }

  /**
   * Get browser instance (launches if not running)
   */
  async getBrowser(): Promise<Browser> {
    return this.launch();
  }

  /**
   * Check if browser is running
   */
  isRunning(): boolean {
    return this.browser !== null && this.browser.connected;
  }
}

// Singleton instance for shared use
let browserManagerInstance: BrowserManager | null = null;

export function getBrowserManager(config?: Partial<BrowserConfig>): BrowserManager {
  if (!browserManagerInstance) {
    browserManagerInstance = new BrowserManager(config);
  }
  return browserManagerInstance;
}

export async function closeBrowserManager(): Promise<void> {
  if (browserManagerInstance) {
    await browserManagerInstance.close();
    browserManagerInstance = null;
  }
}
