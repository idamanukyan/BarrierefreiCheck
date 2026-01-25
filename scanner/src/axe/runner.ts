/**
 * axe-core Runner
 *
 * Executes axe-core accessibility tests on web pages using Puppeteer.
 */

import { Page } from 'puppeteer';
import { createRequire } from 'module';
import { logger } from '../utils/logger.js';
import {
  AxeResults,
  PageScanResult,
  AccessibilityIssue,
  ImpactLevel,
} from './types.js';
import { getTranslation, extractWcagCriteria, extractWcagLevel } from './translator.js';

const require = createRequire(import.meta.url);

export interface AxeRunnerConfig {
  runOnly?: string[];
  rules?: Record<string, { enabled: boolean }>;
  resultTypes?: ('violations' | 'passes' | 'incomplete' | 'inapplicable')[];
  timeout?: number;
}

const DEFAULT_CONFIG: AxeRunnerConfig = {
  runOnly: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'best-practice'],
  resultTypes: ['violations', 'passes', 'incomplete', 'inapplicable'],
  timeout: 30000,
};

export class AxeRunner {
  private config: AxeRunnerConfig;
  private axeSource: string;

  constructor(config: Partial<AxeRunnerConfig> = {}) {
    this.config = { ...DEFAULT_CONFIG, ...config };

    // Load axe-core source
    const axeCorePath = require.resolve('axe-core');
    this.axeSource = require('fs').readFileSync(axeCorePath, 'utf8');
  }

  /**
   * Run axe-core on a page
   */
  async analyze(page: Page, url?: string): Promise<PageScanResult> {
    const startTime = Date.now();
    const pageUrl = url || page.url();

    logger.debug(`Running axe-core analysis on ${pageUrl}`);

    try {
      // Inject axe-core into the page
      await page.evaluate(this.axeSource);

      // Configure and run axe
      const results: AxeResults = await page.evaluate(
        async (config) => {
          // @ts-expect-error axe is injected globally
          const axe = window.axe;

          const options: Record<string, unknown> = {};

          if (config.runOnly && config.runOnly.length > 0) {
            options.runOnly = {
              type: 'tag',
              values: config.runOnly,
            };
          }

          if (config.rules) {
            options.rules = config.rules;
          }

          if (config.resultTypes) {
            options.resultTypes = config.resultTypes;
          }

          return await axe.run(document, options);
        },
        this.config as Record<string, unknown>
      );

      // Get page title
      const title = await page.title();

      // Process results
      const issues = this.processViolations(results, pageUrl);
      const score = this.calculateScore(results);
      const scanTime = Date.now() - startTime;

      logger.info(
        `axe-core analysis completed for ${pageUrl}: ` +
          `${issues.length} issues, score: ${score.toFixed(1)}%`
      );

      return {
        url: pageUrl,
        title,
        scanTime,
        score,
        issues,
        passedRules: results.passes?.length || 0,
        failedRules: results.violations?.length || 0,
        incompleteRules: results.incomplete?.length || 0,
        inapplicableRules: results.inapplicable?.length || 0,
        timestamp: new Date(),
      };
    } catch (error) {
      const errorMessage =
        error instanceof Error ? error.message : 'Unknown error';
      logger.error(`axe-core analysis failed for ${pageUrl}: ${errorMessage}`);

      return {
        url: pageUrl,
        title: '',
        scanTime: Date.now() - startTime,
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
   * Process violations into our issue format with German translations
   */
  private processViolations(
    results: AxeResults,
    pageUrl: string
  ): AccessibilityIssue[] {
    const issues: AccessibilityIssue[] = [];

    if (!results.violations) {
      return issues;
    }

    for (const violation of results.violations) {
      const translation = getTranslation(violation.id);
      const wcagCriteria = extractWcagCriteria(violation.tags);
      const wcagLevel = extractWcagLevel(violation.tags);

      for (const node of violation.nodes) {
        const issue: AccessibilityIssue = {
          id: `${violation.id}-${issues.length}`,
          ruleId: violation.id,
          impact: (violation.impact as ImpactLevel) || 'moderate',
          wcagCriteria: translation?.wcagCriteria || wcagCriteria,
          wcagLevel: translation?.wcagLevel || wcagLevel,
          bfsgReference: translation?.bfsgReference,
          titleDe: translation?.titleDe || violation.help,
          descriptionDe: translation?.descriptionDe || violation.description,
          fixSuggestionDe:
            translation?.fixDe || node.failureSummary || 'Fix this issue',
          helpUrl: violation.helpUrl,
          element: {
            selector: node.target.join(' > '),
            html: node.html,
          },
          pageUrl,
          createdAt: new Date(),
        };

        issues.push(issue);
      }
    }

    return issues;
  }

  /**
   * Calculate compliance score
   * Weighted by impact: critical=3, serious=2, moderate=1, minor=0.5
   */
  private calculateScore(results: AxeResults): number {
    const violations = results.violations || [];
    const passes = results.passes || [];

    if (violations.length === 0 && passes.length === 0) {
      return 100;
    }

    // Count weighted violations
    let weightedViolations = 0;
    for (const violation of violations) {
      const weight = this.getImpactWeight(violation.impact as ImpactLevel);
      weightedViolations += violation.nodes.length * weight;
    }

    // Count total rules (passed + failed)
    const totalRules = passes.length + violations.length;

    if (totalRules === 0) {
      return 100;
    }

    // Calculate score: higher weight = lower score
    // Base score starts at 100, reduced by weighted violations
    const maxPenalty = totalRules * 3; // Max possible penalty (all critical)
    const score = Math.max(
      0,
      100 - (weightedViolations / maxPenalty) * 100
    );

    return Math.round(score * 10) / 10;
  }

  /**
   * Get weight for impact level
   */
  private getImpactWeight(impact: ImpactLevel | undefined): number {
    switch (impact) {
      case 'critical':
        return 3;
      case 'serious':
        return 2;
      case 'moderate':
        return 1;
      case 'minor':
        return 0.5;
      default:
        return 1;
    }
  }
}

// Singleton instance
let axeRunnerInstance: AxeRunner | null = null;

export function getAxeRunner(config?: Partial<AxeRunnerConfig>): AxeRunner {
  if (!axeRunnerInstance) {
    axeRunnerInstance = new AxeRunner(config);
  }
  return axeRunnerInstance;
}
