/**
 * Web Vitals Performance Monitoring
 *
 * Monitors Core Web Vitals metrics for performance optimization.
 * Metrics tracked:
 * - LCP (Largest Contentful Paint): Loading performance
 * - FID (First Input Delay): Interactivity
 * - CLS (Cumulative Layout Shift): Visual stability
 * - FCP (First Contentful Paint): Initial render
 * - TTFB (Time to First Byte): Server response time
 */

import { onCLS, onFCP, onFID, onLCP, onTTFB, Metric } from 'web-vitals';

// Threshold values for good performance (in ms or unitless for CLS)
const THRESHOLDS = {
  LCP: { good: 2500, needsImprovement: 4000 },
  FID: { good: 100, needsImprovement: 300 },
  CLS: { good: 0.1, needsImprovement: 0.25 },
  FCP: { good: 1800, needsImprovement: 3000 },
  TTFB: { good: 800, needsImprovement: 1800 },
};

type MetricRating = 'good' | 'needs-improvement' | 'poor';

interface WebVitalReport {
  name: string;
  value: number;
  rating: MetricRating;
  delta: number;
  id: string;
  navigationType: string;
}

/**
 * Get rating for a metric value
 */
function getRating(name: string, value: number): MetricRating {
  const threshold = THRESHOLDS[name as keyof typeof THRESHOLDS];
  if (!threshold) return 'good';

  if (value <= threshold.good) return 'good';
  if (value <= threshold.needsImprovement) return 'needs-improvement';
  return 'poor';
}

/**
 * Format metric value for display
 */
function formatMetricValue(name: string, value: number): string {
  if (name === 'CLS') {
    return value.toFixed(3);
  }
  return `${Math.round(value)}ms`;
}

/**
 * Handler for web vital metrics
 */
function handleMetric(metric: Metric, reportCallback?: (report: WebVitalReport) => void): void {
  const rating = getRating(metric.name, metric.value);

  const report: WebVitalReport = {
    name: metric.name,
    value: metric.value,
    rating,
    delta: metric.delta,
    id: metric.id,
    navigationType: metric.navigationType,
  };

  // Log to console in development
  if (process.env.NODE_ENV === 'development') {
    const emoji = rating === 'good' ? '\u2705' : rating === 'needs-improvement' ? '\u26A0\uFE0F' : '\u274C';
    console.log(
      `${emoji} [Web Vitals] ${metric.name}: ${formatMetricValue(metric.name, metric.value)} (${rating})`
    );
  }

  // Call custom report callback if provided
  if (reportCallback) {
    reportCallback(report);
  }
}

/**
 * Send metrics to analytics endpoint
 */
async function sendToAnalytics(report: WebVitalReport): Promise<void> {
  // Only send in production
  if (process.env.NODE_ENV !== 'production') return;

  try {
    // Use sendBeacon for reliable delivery even on page unload
    const body = JSON.stringify({
      ...report,
      url: window.location.href,
      timestamp: new Date().toISOString(),
    });

    if (navigator.sendBeacon) {
      navigator.sendBeacon('/api/v1/metrics/web-vitals', body);
    } else {
      // Fallback to fetch for browsers without sendBeacon
      await fetch('/api/v1/metrics/web-vitals', {
        method: 'POST',
        body,
        headers: { 'Content-Type': 'application/json' },
        keepalive: true,
      });
    }
  } catch (error) {
    // Silently fail - don't interrupt user experience for analytics
    console.debug('Failed to send web vitals:', error);
  }
}

/**
 * Initialize Web Vitals monitoring
 *
 * Call this in your main entry point (main.tsx) to start monitoring.
 *
 * @param reportCallback Optional callback for custom metric handling
 *
 * @example
 * // Basic usage
 * initWebVitals();
 *
 * // With custom callback
 * initWebVitals((report) => {
 *   analytics.track('web_vital', report);
 * });
 */
export function initWebVitals(reportCallback?: (report: WebVitalReport) => void): void {
  const callback = (metric: Metric) => handleMetric(metric, reportCallback);

  // Core Web Vitals
  onLCP(callback);
  onFID(callback);
  onCLS(callback);

  // Additional metrics
  onFCP(callback);
  onTTFB(callback);

  if (process.env.NODE_ENV === 'development') {
    console.log('[Web Vitals] Monitoring initialized');
  }
}

/**
 * Initialize Web Vitals with analytics reporting
 *
 * Sends metrics to the backend for aggregation and monitoring.
 */
export function initWebVitalsWithAnalytics(): void {
  initWebVitals(sendToAnalytics);
}

/**
 * Get current performance summary
 *
 * Returns a snapshot of navigation timing metrics.
 * Useful for debugging performance issues.
 */
export function getPerformanceSummary(): Record<string, number> | null {
  if (typeof window === 'undefined' || !window.performance) {
    return null;
  }

  const timing = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming;
  if (!timing) return null;

  return {
    dns: timing.domainLookupEnd - timing.domainLookupStart,
    tcp: timing.connectEnd - timing.connectStart,
    ssl: timing.secureConnectionStart > 0 ? timing.connectEnd - timing.secureConnectionStart : 0,
    ttfb: timing.responseStart - timing.requestStart,
    download: timing.responseEnd - timing.responseStart,
    domParse: timing.domInteractive - timing.responseEnd,
    domReady: timing.domContentLoadedEventEnd - timing.navigationStart,
    load: timing.loadEventEnd - timing.navigationStart,
  };
}

export type { WebVitalReport, MetricRating };
