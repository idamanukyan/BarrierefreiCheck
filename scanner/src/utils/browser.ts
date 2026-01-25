/**
 * Browser Manager - Puppeteer browser instance management
 *
 * Handles browser lifecycle, page creation, and resource cleanup.
 */

import puppeteer, { Browser, Page, PuppeteerLaunchOptions } from 'puppeteer';
import { logger } from './logger.js';

export interface BrowserConfig {
  headless?: boolean;
  timeout?: number;
  viewport?: { width: number; height: number };
  userAgent?: string;
}

const DEFAULT_CONFIG: BrowserConfig = {
  headless: true,
  timeout: 30000,
  viewport: { width: 1920, height: 1080 },
  userAgent:
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 AccessibilityChecker/1.0',
};

export class BrowserManager {
  private browser: Browser | null = null;
  private config: BrowserConfig;

  constructor(config: Partial<BrowserConfig> = {}) {
    this.config = { ...DEFAULT_CONFIG, ...config };
  }

  /**
   * Launch a new browser instance
   */
  async launch(): Promise<Browser> {
    if (this.browser) {
      return this.browser;
    }

    logger.info('Launching browser...');

    const launchOptions: PuppeteerLaunchOptions = {
      headless: this.config.headless,
      args: [
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-dev-shm-usage',
        '--disable-accelerated-2d-canvas',
        '--disable-gpu',
        '--window-size=1920,1080',
        '--disable-web-security',
        '--disable-features=IsolateOrigins,site-per-process',
      ],
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

    // Block unnecessary resources for faster loading
    await page.setRequestInterception(true);
    page.on('request', (request) => {
      const resourceType = request.resourceType();
      // Allow all resources for accurate accessibility testing
      // but could block 'media', 'font' if needed for performance
      if (resourceType === 'media') {
        request.abort();
      } else {
        request.continue();
      }
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
