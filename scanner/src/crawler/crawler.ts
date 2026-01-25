/**
 * Website Crawler
 *
 * Crawls websites to discover pages for accessibility testing.
 * Respects robots.txt and implements rate limiting.
 */

import { Page } from 'puppeteer';
import { BrowserManager, getBrowserManager } from '../utils/browser.js';
import { logger } from '../utils/logger.js';
import {
  validateUrl,
  normalizeUrl,
  getDomain,
  isSameDomain,
  shouldSkipUrl,
  extractLinks,
  ParsedUrl,
} from '../utils/url.js';
import { RobotsChecker, getRobotsChecker } from './robots.js';

export interface CrawlOptions {
  maxPages: number;
  maxDepth: number;
  sameDomainOnly: boolean;
  respectRobotsTxt: boolean;
  crawlDelay: number; // milliseconds between requests
  timeout: number; // page load timeout
  waitForSelector?: string;
  waitTime?: number; // additional wait time after page load
}

export interface CrawledPage {
  url: string;
  title: string;
  depth: number;
  links: string[];
  loadTime: number;
  statusCode?: number;
  error?: string;
}

export interface CrawlResult {
  baseUrl: string;
  domain: string;
  pages: CrawledPage[];
  totalPages: number;
  crawlTime: number;
  errors: string[];
}

const DEFAULT_OPTIONS: CrawlOptions = {
  maxPages: 100,
  maxDepth: 5,
  sameDomainOnly: true,
  respectRobotsTxt: true,
  crawlDelay: 500,
  timeout: 30000,
  waitTime: 1000,
};

export class Crawler {
  private browserManager: BrowserManager;
  private robotsChecker: RobotsChecker;
  private options: CrawlOptions;
  private visited: Set<string> = new Set();
  private queue: Array<{ url: string; depth: number }> = [];
  private pages: CrawledPage[] = [];
  private errors: string[] = [];
  private isRunning: boolean = false;
  private shouldStop: boolean = false;

  constructor(options: Partial<CrawlOptions> = {}) {
    this.options = { ...DEFAULT_OPTIONS, ...options };
    this.browserManager = getBrowserManager();
    this.robotsChecker = getRobotsChecker();
  }

  /**
   * Start crawling from a given URL
   */
  async crawl(startUrl: string): Promise<CrawlResult> {
    const startTime = Date.now();

    // Reset state
    this.visited.clear();
    this.queue = [];
    this.pages = [];
    this.errors = [];
    this.isRunning = true;
    this.shouldStop = false;

    // Validate start URL
    const validation = validateUrl(startUrl);
    if (!validation.valid || !validation.url) {
      return {
        baseUrl: startUrl,
        domain: '',
        pages: [],
        totalPages: 0,
        crawlTime: Date.now() - startTime,
        errors: [validation.error || 'Invalid URL'],
      };
    }

    const baseUrl = validation.url.normalized;
    const domain = validation.url.domain;

    logger.info(`Starting crawl of ${baseUrl} (max ${this.options.maxPages} pages)`);

    // Add start URL to queue
    this.queue.push({ url: baseUrl, depth: 0 });

    // Create a page for crawling
    let page: Page | null = null;

    try {
      page = await this.browserManager.createPage();

      // Process queue
      while (this.queue.length > 0 && !this.shouldStop) {
        // Check if we've reached the page limit
        if (this.pages.length >= this.options.maxPages) {
          logger.info(`Reached page limit of ${this.options.maxPages}`);
          break;
        }

        const item = this.queue.shift();
        if (!item) continue;

        const { url, depth } = item;

        // Skip if already visited
        if (this.visited.has(url)) {
          continue;
        }

        // Skip if max depth exceeded
        if (depth > this.options.maxDepth) {
          continue;
        }

        // Check robots.txt
        if (this.options.respectRobotsTxt) {
          const allowed = await this.robotsChecker.isAllowed(url);
          if (!allowed) {
            logger.debug(`Skipping ${url} - disallowed by robots.txt`);
            continue;
          }
        }

        // Mark as visited
        this.visited.add(url);

        // Crawl the page
        const crawledPage = await this.crawlPage(page, url, depth);

        if (crawledPage) {
          this.pages.push(crawledPage);

          // Add discovered links to queue
          for (const link of crawledPage.links) {
            if (!this.visited.has(link) && !this.queue.some((q) => q.url === link)) {
              this.queue.push({ url: link, depth: depth + 1 });
            }
          }

          logger.info(
            `Crawled ${this.pages.length}/${this.options.maxPages}: ${url} ` +
              `(${crawledPage.links.length} links found)`
          );
        }

        // Apply crawl delay
        if (this.options.crawlDelay > 0 && this.queue.length > 0) {
          await this.delay(this.options.crawlDelay);
        }
      }
    } finally {
      if (page) {
        await this.browserManager.closePage(page);
      }
      this.isRunning = false;
    }

    const crawlTime = Date.now() - startTime;

    logger.info(
      `Crawl completed: ${this.pages.length} pages in ${(crawlTime / 1000).toFixed(2)}s`
    );

    return {
      baseUrl,
      domain,
      pages: this.pages,
      totalPages: this.pages.length,
      crawlTime,
      errors: this.errors,
    };
  }

  /**
   * Crawl a single page
   */
  private async crawlPage(
    page: Page,
    url: string,
    depth: number
  ): Promise<CrawledPage | null> {
    const startTime = Date.now();

    try {
      // Navigate to the page
      const response = await page.goto(url, {
        waitUntil: 'networkidle2',
        timeout: this.options.timeout,
      });

      const statusCode = response?.status();

      // Check for error status codes
      if (statusCode && statusCode >= 400) {
        const error = `HTTP ${statusCode} for ${url}`;
        this.errors.push(error);
        logger.warn(error);
        return null;
      }

      // Wait for additional time if specified
      if (this.options.waitTime && this.options.waitTime > 0) {
        await this.delay(this.options.waitTime);
      }

      // Wait for specific selector if specified
      if (this.options.waitForSelector) {
        try {
          await page.waitForSelector(this.options.waitForSelector, {
            timeout: 5000,
          });
        } catch {
          // Selector not found, continue anyway
        }
      }

      // Extract page information
      const { title, links } = await page.evaluate(() => {
        // Get page title
        const pageTitle = document.title || '';

        // Get all links
        const anchors = Array.from(document.querySelectorAll('a[href]'));
        const hrefs = anchors
          .map((a) => a.getAttribute('href'))
          .filter((href): href is string => href !== null && href !== '');

        return { title: pageTitle, links: hrefs };
      });

      // Filter and normalize links
      const normalizedLinks = this.options.sameDomainOnly
        ? extractLinks(url, links, true)
        : extractLinks(url, links, false);

      const loadTime = Date.now() - startTime;

      return {
        url,
        title,
        depth,
        links: normalizedLinks,
        loadTime,
        statusCode,
      };
    } catch (error) {
      const errorMessage =
        error instanceof Error ? error.message : 'Unknown error';
      const errorLog = `Error crawling ${url}: ${errorMessage}`;
      this.errors.push(errorLog);
      logger.error(errorLog);

      return {
        url,
        title: '',
        depth,
        links: [],
        loadTime: Date.now() - startTime,
        error: errorMessage,
      };
    }
  }

  /**
   * Stop the crawl
   */
  stop(): void {
    this.shouldStop = true;
    logger.info('Crawl stop requested');
  }

  /**
   * Check if crawl is currently running
   */
  isActive(): boolean {
    return this.isRunning;
  }

  /**
   * Get current progress
   */
  getProgress(): { visited: number; queued: number; total: number } {
    return {
      visited: this.pages.length,
      queued: this.queue.length,
      total: this.options.maxPages,
    };
  }

  /**
   * Delay helper
   */
  private delay(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }
}

/**
 * Crawl a single page without full site crawl
 */
export async function crawlSinglePage(url: string): Promise<CrawledPage | null> {
  const crawler = new Crawler({ maxPages: 1, maxDepth: 0 });
  const result = await crawler.crawl(url);
  return result.pages[0] || null;
}
