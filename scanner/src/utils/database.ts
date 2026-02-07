/**
 * Database Service
 *
 * PostgreSQL client for persisting scan results.
 */

import { Pool, PoolClient } from 'pg';
import { logger } from './logger.js';
import { PageScanResult, AccessibilityIssue, ScanSummary } from '../axe/types.js';

// Database connection pool
let pool: Pool | null = null;

/**
 * Get database connection pool
 */
export function getPool(): Pool {
  if (!pool) {
    const connectionString = process.env.DATABASE_URL ||
      'postgresql://accesscheck:accesscheck_dev@localhost:5432/accessibilitychecker';

    pool = new Pool({
      connectionString,
      max: 10,
      idleTimeoutMillis: 30000,
      connectionTimeoutMillis: 5000,
    });

    pool.on('error', (err) => {
      logger.error('Unexpected database pool error:', err);
    });

    pool.on('connect', () => {
      logger.debug('New database connection established');
    });

    logger.info('Database pool initialized');
  }

  return pool;
}

/**
 * Close database pool
 */
export async function closePool(): Promise<void> {
  if (pool) {
    await pool.end();
    pool = null;
    logger.info('Database pool closed');
  }
}

/**
 * Update scan status
 */
export async function updateScanStatus(
  scanId: string,
  status: string,
  errorMessage?: string
): Promise<void> {
  const client = await getPool().connect();
  try {
    const now = new Date().toISOString();

    if (status === 'scanning' || status === 'crawling') {
      await client.query(
        `UPDATE scans SET status = $1, started_at = COALESCE(started_at, $2) WHERE id = $3`,
        [status, now, scanId]
      );
    } else if (status === 'completed' || status === 'failed' || status === 'cancelled') {
      await client.query(
        `UPDATE scans SET status = $1, completed_at = $2, error_message = $3 WHERE id = $4`,
        [status, now, errorMessage || null, scanId]
      );
    } else {
      await client.query(
        `UPDATE scans SET status = $1 WHERE id = $2`,
        [status, scanId]
      );
    }

    logger.debug(`Scan ${scanId} status updated to ${status}`);
  } finally {
    client.release();
  }
}

/**
 * Update scan progress
 */
export async function updateScanProgress(
  scanId: string,
  stage: string,
  current: number,
  total: number
): Promise<void> {
  const client = await getPool().connect();
  try {
    await client.query(
      `UPDATE scans SET
        progress_stage = $1,
        progress_current = $2,
        progress_total = $3
       WHERE id = $4`,
      [stage, current, total, scanId]
    );
  } finally {
    client.release();
  }
}

/**
 * Persist scan results to database
 */
export async function persistScanResults(
  scanId: string,
  pages: PageScanResult[],
  summary: ScanSummary
): Promise<void> {
  const client = await getPool().connect();

  try {
    await client.query('BEGIN');

    // Update scan summary
    await client.query(
      `UPDATE scans SET
        status = 'completed',
        completed_at = NOW(),
        score = $1,
        pages_scanned = $2,
        issues_count = $3,
        issues_critical = $4,
        issues_serious = $5,
        issues_moderate = $6,
        issues_minor = $7,
        progress_stage = 'complete',
        progress_current = $2,
        progress_total = $2
       WHERE id = $8`,
      [
        summary.overallScore,
        summary.totalPages,
        summary.totalIssues,
        summary.issuesByImpact.critical,
        summary.issuesByImpact.serious,
        summary.issuesByImpact.moderate,
        summary.issuesByImpact.minor,
        scanId,
      ]
    );

    // Insert pages and issues
    for (const pageResult of pages) {
      // Insert page
      const pageInsertResult = await client.query(
        `INSERT INTO pages (
          scan_id, url, title, depth, score, issues_count,
          passed_rules, failed_rules, incomplete_rules,
          load_time_ms, scan_time_ms, error, scanned_at
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
        RETURNING id`,
        [
          scanId,
          pageResult.url,
          pageResult.title || null,
          0, // depth - could be passed from crawler
          pageResult.score,
          pageResult.issues.length,
          pageResult.passedRules,
          pageResult.failedRules,
          pageResult.incompleteRules,
          null, // load_time_ms - could be tracked
          pageResult.scanTime,
          pageResult.error || null,
          pageResult.timestamp,
        ]
      );

      const pageId = pageInsertResult.rows[0].id;

      // Insert issues for this page
      for (const issue of pageResult.issues) {
        await client.query(
          `INSERT INTO issues (
            page_id, rule_id, impact, wcag_criteria, wcag_level,
            bfsg_reference, title_de, description_de, fix_suggestion_de,
            element_selector, element_html, element_xpath,
            help_url, screenshot_path
          ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)`,
          [
            pageId,
            issue.ruleId,
            issue.impact,
            issue.wcagCriteria || [],
            issue.wcagLevel,
            issue.bfsgReference || null,
            issue.titleDe,
            issue.descriptionDe || null,
            issue.fixSuggestionDe || null,
            issue.element?.selector || null,
            issue.element?.html || null,
            issue.element?.xpath || null,
            issue.helpUrl || null,
            issue.screenshotPath || null,
          ]
        );
      }
    }

    await client.query('COMMIT');
    logger.info(`Scan results persisted: ${scanId} - ${pages.length} pages, ${summary.totalIssues} issues`);

  } catch (error) {
    await client.query('ROLLBACK');
    logger.error(`Failed to persist scan results for ${scanId}:`, error);
    throw error;
  } finally {
    client.release();
  }
}

/**
 * Mark scan as failed
 */
export async function markScanFailed(
  scanId: string,
  errorMessage: string
): Promise<void> {
  const client = await getPool().connect();
  try {
    await client.query(
      `UPDATE scans SET
        status = 'failed',
        completed_at = NOW(),
        error_message = $1
       WHERE id = $2`,
      [errorMessage, scanId]
    );
    logger.info(`Scan marked as failed: ${scanId}`);
  } finally {
    client.release();
  }
}
