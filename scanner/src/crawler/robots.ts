/**
 * Robots.txt Parser
 *
 * Handles fetching and parsing robots.txt files to respect
 * crawling rules set by website owners.
 */

import robotsParser from 'robots-parser';
import { logger } from '../utils/logger.js';

export interface RobotsConfig {
  userAgent: string;
  timeout: number;
}

const DEFAULT_CONFIG: RobotsConfig = {
  userAgent: 'AccessibilityChecker',
  timeout: 10000,
};

export class RobotsChecker {
  private cache: Map<string, ReturnType<typeof robotsParser>> = new Map();
  private config: RobotsConfig;

  constructor(config: Partial<RobotsConfig> = {}) {
    this.config = { ...DEFAULT_CONFIG, ...config };
  }

  /**
   * Fetch and parse robots.txt for a given URL
   */
  async fetchRobots(baseUrl: string): Promise<ReturnType<typeof robotsParser> | null> {
    try {
      const url = new URL(baseUrl);
      const robotsUrl = `${url.protocol}//${url.host}/robots.txt`;

      // Check cache first
      if (this.cache.has(url.host)) {
        return this.cache.get(url.host) || null;
      }

      logger.debug(`Fetching robots.txt from ${robotsUrl}`);

      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), this.config.timeout);

      const response = await fetch(robotsUrl, {
        signal: controller.signal,
        headers: {
          'User-Agent': this.config.userAgent,
        },
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        // No robots.txt found - allow all
        logger.debug(`No robots.txt found at ${robotsUrl} (status: ${response.status})`);
        const emptyRobots = robotsParser(robotsUrl, '');
        this.cache.set(url.host, emptyRobots);
        return emptyRobots;
      }

      const robotsTxt = await response.text();
      const robots = robotsParser(robotsUrl, robotsTxt);

      // Cache the result
      this.cache.set(url.host, robots);

      logger.debug(`Successfully parsed robots.txt for ${url.host}`);
      return robots;
    } catch (error) {
      if (error instanceof Error && error.name === 'AbortError') {
        logger.warn(`Timeout fetching robots.txt for ${baseUrl}`);
      } else {
        logger.warn(`Error fetching robots.txt for ${baseUrl}:`, error);
      }
      // On error, allow crawling (fail open)
      return null;
    }
  }

  /**
   * Check if a URL is allowed to be crawled
   */
  async isAllowed(url: string): Promise<boolean> {
    try {
      const robots = await this.fetchRobots(url);

      if (!robots) {
        // If we couldn't fetch robots.txt, allow crawling
        return true;
      }

      const allowed = robots.isAllowed(url, this.config.userAgent);

      if (!allowed) {
        logger.debug(`URL disallowed by robots.txt: ${url}`);
      }

      return allowed !== false; // robots-parser returns undefined for no match
    } catch (error) {
      logger.warn(`Error checking robots.txt for ${url}:`, error);
      // On error, allow crawling
      return true;
    }
  }

  /**
   * Get the crawl delay specified in robots.txt
   */
  async getCrawlDelay(baseUrl: string): Promise<number | null> {
    try {
      const robots = await this.fetchRobots(baseUrl);

      if (!robots) {
        return null;
      }

      const delay = robots.getCrawlDelay(this.config.userAgent);
      return delay || null;
    } catch {
      return null;
    }
  }

  /**
   * Get sitemap URLs from robots.txt
   */
  async getSitemaps(baseUrl: string): Promise<string[]> {
    try {
      const robots = await this.fetchRobots(baseUrl);

      if (!robots) {
        return [];
      }

      return robots.getSitemaps() || [];
    } catch {
      return [];
    }
  }

  /**
   * Clear the robots.txt cache
   */
  clearCache(): void {
    this.cache.clear();
  }

  /**
   * Clear cache for a specific host
   */
  clearHostCache(hostname: string): void {
    this.cache.delete(hostname);
  }
}

// Singleton instance
let robotsCheckerInstance: RobotsChecker | null = null;

export function getRobotsChecker(config?: Partial<RobotsConfig>): RobotsChecker {
  if (!robotsCheckerInstance) {
    robotsCheckerInstance = new RobotsChecker(config);
  }
  return robotsCheckerInstance;
}
