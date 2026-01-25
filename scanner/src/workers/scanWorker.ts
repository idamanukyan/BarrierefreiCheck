/**
 * Scan Worker
 *
 * Processes accessibility scan jobs from the queue.
 * Handles crawling, axe-core testing, and result aggregation.
 */

import { Worker, Job } from 'bullmq';
import { Page } from 'puppeteer';
import { BrowserManager, getBrowserManager, closeBrowserManager } from '../utils/browser.js';
import { logger } from '../utils/logger.js';
import { validateUrl } from '../utils/url.js';
import { Crawler, CrawlOptions } from '../crawler/crawler.js';
import { AxeRunner, getAxeRunner } from '../axe/runner.js';
import { captureHighlightedScreenshot } from '../utils/screenshot.js';
import {
  SCAN_QUEUE,
  ScanJobData,
  JobProgress,
  getRedisConnection,
} from './queue.js';
import { PageScanResult, AccessibilityIssue, ScanSummary } from '../axe/types.js';

export interface ScanResult {
  scanId: string;
  baseUrl: string;
  pages: PageScanResult[];
  summary: ScanSummary;
  errors: string[];
}

/**
 * Process a single page for accessibility issues
 */
async function scanPage(
  page: Page,
  url: string,
  scanId: string,
  captureScreenshots: boolean,
  axeRunner: AxeRunner
): Promise<PageScanResult> {
  logger.debug(`Scanning page: ${url}`);

  try {
    // Navigate to the page
    await page.goto(url, {
      waitUntil: 'networkidle2',
      timeout: 30000,
    });

    // Wait for page to settle
    await page.waitForTimeout(1000);

    // Run axe-core analysis
    const result = await axeRunner.analyze(page, url);

    // Capture screenshots for violations if enabled
    if (captureScreenshots && result.issues.length > 0) {
      const screenshotDir = `./screenshots/${scanId}`;

      for (let i = 0; i < Math.min(result.issues.length, 20); i++) {
        const issue = result.issues[i];
        try {
          const screenshotResult = await captureHighlightedScreenshot(
            page,
            issue.element.selector,
            scanId,
            issue.ruleId,
            i,
            { outputDir: screenshotDir }
          );

          if (screenshotResult.success && screenshotResult.filePath) {
            issue.screenshotPath = screenshotResult.filePath;
          }
        } catch (error) {
          // Continue even if screenshot fails
          logger.debug(`Screenshot failed for issue ${i}: ${error}`);
        }
      }
    }

    return result;
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : 'Unknown error';
    logger.error(`Error scanning page ${url}: ${errorMessage}`);

    return {
      url,
      title: '',
      scanTime: 0,
      score: 0,
      issues: [],
      passedRules: 0,
      failedRules: 0,
      incompleteRules: 0,
      inapplicableRules: 0,
      timestamp: new Date(),
      error: errorMessage,
    };
  }
}

/**
 * Calculate scan summary from page results
 */
function calculateSummary(
  scanId: string,
  baseUrl: string,
  pages: PageScanResult[],
  scanDuration: number
): ScanSummary {
  const allIssues = pages.flatMap((p) => p.issues);

  const issuesByImpact = {
    critical: 0,
    serious: 0,
    moderate: 0,
    minor: 0,
  };

  const issuesByWcagLevel = {
    A: 0,
    AA: 0,
    AAA: 0,
  };

  for (const issue of allIssues) {
    // Count by impact
    issuesByImpact[issue.impact]++;

    // Count by WCAG level
    issuesByWcagLevel[issue.wcagLevel]++;
  }

  // Calculate overall score (weighted average)
  const totalScore = pages.reduce((sum, p) => sum + p.score, 0);
  const overallScore = pages.length > 0 ? totalScore / pages.length : 0;

  return {
    scanId,
    baseUrl,
    totalPages: pages.length,
    totalIssues: allIssues.length,
    issuesByImpact,
    issuesByWcagLevel,
    overallScore: Math.round(overallScore * 10) / 10,
    scanDuration,
    completedAt: new Date(),
  };
}

/**
 * Process a scan job
 */
async function processScanJob(job: Job<ScanJobData>): Promise<ScanResult> {
  const { scanId, url, crawl, maxPages, options = {} } = job.data;
  const startTime = Date.now();
  const errors: string[] = [];

  logger.info(`Processing scan job: ${scanId} for ${url}`);

  // Validate URL
  const validation = validateUrl(url);
  if (!validation.valid || !validation.url) {
    throw new Error(validation.error || 'Invalid URL');
  }

  const baseUrl = validation.url.normalized;
  const browserManager = getBrowserManager();
  const axeRunner = getAxeRunner();
  const pages: PageScanResult[] = [];

  // Update progress: starting
  await job.updateProgress({
    stage: 'crawling',
    pagesScanned: 0,
    totalPages: crawl ? maxPages : 1,
    currentUrl: baseUrl,
    issuesFound: 0,
  } as JobProgress);

  let page: Page | null = null;

  try {
    page = await browserManager.createPage();

    if (crawl && maxPages > 1) {
      // Multi-page crawl and scan
      const crawlOptions: Partial<CrawlOptions> = {
        maxPages,
        respectRobotsTxt: options.respectRobotsTxt !== false,
        waitTime: options.waitTime || 1000,
      };

      const crawler = new Crawler(crawlOptions);
      const crawlResult = await crawler.crawl(baseUrl);

      errors.push(...crawlResult.errors);

      // Update progress: scanning
      await job.updateProgress({
        stage: 'scanning',
        pagesScanned: 0,
        totalPages: crawlResult.pages.length,
        currentUrl: baseUrl,
        issuesFound: 0,
      } as JobProgress);

      // Scan each crawled page
      let issuesFound = 0;
      for (let i = 0; i < crawlResult.pages.length; i++) {
        const crawledPage = crawlResult.pages[i];

        if (crawledPage.error) {
          // Skip pages with crawl errors
          continue;
        }

        const pageResult = await scanPage(
          page,
          crawledPage.url,
          scanId,
          options.captureScreenshots !== false,
          axeRunner
        );

        pages.push(pageResult);
        issuesFound += pageResult.issues.length;

        // Update progress
        await job.updateProgress({
          stage: 'scanning',
          pagesScanned: i + 1,
          totalPages: crawlResult.pages.length,
          currentUrl: crawledPage.url,
          issuesFound,
        } as JobProgress);

        // Log progress
        if ((i + 1) % 10 === 0) {
          logger.info(
            `Scan progress: ${i + 1}/${crawlResult.pages.length} pages, ${issuesFound} issues`
          );
        }
      }
    } else {
      // Single page scan
      await job.updateProgress({
        stage: 'scanning',
        pagesScanned: 0,
        totalPages: 1,
        currentUrl: baseUrl,
        issuesFound: 0,
      } as JobProgress);

      const pageResult = await scanPage(
        page,
        baseUrl,
        scanId,
        options.captureScreenshots !== false,
        axeRunner
      );

      pages.push(pageResult);

      await job.updateProgress({
        stage: 'processing',
        pagesScanned: 1,
        totalPages: 1,
        currentUrl: baseUrl,
        issuesFound: pageResult.issues.length,
      } as JobProgress);
    }
  } finally {
    if (page) {
      await browserManager.closePage(page);
    }
  }

  // Calculate summary
  const scanDuration = Date.now() - startTime;
  const summary = calculateSummary(scanId, baseUrl, pages, scanDuration);

  // Final progress update
  await job.updateProgress({
    stage: 'complete',
    pagesScanned: pages.length,
    totalPages: pages.length,
    issuesFound: summary.totalIssues,
  } as JobProgress);

  logger.info(
    `Scan completed: ${scanId} - ${pages.length} pages, ${summary.totalIssues} issues, ` +
      `score: ${summary.overallScore}%, duration: ${(scanDuration / 1000).toFixed(2)}s`
  );

  return {
    scanId,
    baseUrl,
    pages,
    summary,
    errors,
  };
}

/**
 * Create and start the scan worker
 */
export function createScanWorker(concurrency: number = 2): Worker<ScanJobData, ScanResult> {
  const worker = new Worker<ScanJobData, ScanResult>(
    SCAN_QUEUE,
    processScanJob,
    {
      connection: getRedisConnection(),
      concurrency,
      limiter: {
        max: 10,
        duration: 1000,
      },
    }
  );

  // Worker event handlers
  worker.on('completed', (job, result) => {
    logger.info(
      `Job ${job.id} completed: ${result.summary.totalPages} pages, ` +
        `${result.summary.totalIssues} issues`
    );
  });

  worker.on('failed', (job, err) => {
    logger.error(`Job ${job?.id} failed:`, err);
  });

  worker.on('progress', (job, progress) => {
    const p = progress as JobProgress;
    logger.debug(
      `Job ${job.id} progress: ${p.stage} - ${p.pagesScanned}/${p.totalPages}`
    );
  });

  worker.on('error', (err) => {
    logger.error('Worker error:', err);
  });

  logger.info(`Scan worker started with concurrency: ${concurrency}`);

  return worker;
}

/**
 * Graceful shutdown handler
 */
export async function shutdownWorker(worker: Worker): Promise<void> {
  logger.info('Shutting down scan worker...');

  await worker.close();
  await closeBrowserManager();

  logger.info('Scan worker shut down complete');
}
