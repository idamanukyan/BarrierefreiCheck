/**
 * BullMQ Queue Configuration
 *
 * Sets up job queues for accessibility scanning tasks.
 */

import { Queue, QueueEvents, Job } from 'bullmq';
import { Redis } from 'ioredis';
import { logger } from '../utils/logger.js';

// Queue names
export const SCAN_QUEUE = 'accessibility-scans';
export const REPORT_QUEUE = 'report-generation';

// Job types
export interface ScanJobData {
  scanId: string;
  url: string;
  crawl: boolean;
  maxPages: number;
  userId: string;
  options?: {
    waitTime?: number;
    respectRobotsTxt?: boolean;
    captureScreenshots?: boolean;
  };
}

export interface PageScanJobData {
  scanId: string;
  pageUrl: string;
  pageIndex: number;
  captureScreenshots: boolean;
}

export interface ReportJobData {
  scanId: string;
  format: 'pdf' | 'html' | 'json';
  language: 'de' | 'en';
  includeScreenshots: boolean;
  branding?: {
    logo?: string;
    companyName?: string;
  };
}

export interface JobProgress {
  stage: 'crawling' | 'scanning' | 'processing' | 'complete';
  pagesScanned: number;
  totalPages: number;
  currentUrl?: string;
  issuesFound: number;
}

// Redis connection
let redisConnection: Redis | null = null;

/**
 * Get Redis connection
 */
export function getRedisConnection(): Redis {
  if (!redisConnection) {
    const redisUrl = process.env.REDIS_URL || 'redis://localhost:6379';
    redisConnection = new Redis(redisUrl, {
      maxRetriesPerRequest: null,
    });

    redisConnection.on('connect', () => {
      logger.info('Redis connected');
    });

    redisConnection.on('error', (err) => {
      logger.error('Redis error:', err);
    });
  }

  return redisConnection;
}

/**
 * Close Redis connection
 */
export async function closeRedisConnection(): Promise<void> {
  if (redisConnection) {
    await redisConnection.quit();
    redisConnection = null;
  }
}

// Queue instances
let scanQueue: Queue<ScanJobData> | null = null;
let reportQueue: Queue<ReportJobData> | null = null;

/**
 * Get scan queue
 */
export function getScanQueue(): Queue<ScanJobData> {
  if (!scanQueue) {
    scanQueue = new Queue<ScanJobData>(SCAN_QUEUE, {
      connection: getRedisConnection(),
      defaultJobOptions: {
        attempts: 3,
        backoff: {
          type: 'exponential',
          delay: 5000,
        },
        removeOnComplete: {
          age: 24 * 3600, // Keep completed jobs for 24 hours
          count: 1000,
        },
        removeOnFail: {
          age: 7 * 24 * 3600, // Keep failed jobs for 7 days
        },
      },
    });

    logger.info(`Scan queue "${SCAN_QUEUE}" initialized`);
  }

  return scanQueue;
}

/**
 * Get report queue
 */
export function getReportQueue(): Queue<ReportJobData> {
  if (!reportQueue) {
    reportQueue = new Queue<ReportJobData>(REPORT_QUEUE, {
      connection: getRedisConnection(),
      defaultJobOptions: {
        attempts: 2,
        backoff: {
          type: 'fixed',
          delay: 3000,
        },
        removeOnComplete: {
          age: 3600, // Keep for 1 hour
          count: 100,
        },
        removeOnFail: {
          age: 24 * 3600,
        },
      },
    });

    logger.info(`Report queue "${REPORT_QUEUE}" initialized`);
  }

  return reportQueue;
}

/**
 * Add a scan job to the queue
 */
export async function addScanJob(
  data: ScanJobData,
  priority: number = 0
): Promise<Job<ScanJobData>> {
  const queue = getScanQueue();

  const job = await queue.add(`scan-${data.scanId}`, data, {
    priority,
    jobId: data.scanId, // Use scanId as job ID for easy lookup
  });

  logger.info(`Scan job added: ${data.scanId} for ${data.url}`);

  return job;
}

/**
 * Add a report job to the queue
 */
export async function addReportJob(
  data: ReportJobData
): Promise<Job<ReportJobData>> {
  const queue = getReportQueue();

  const job = await queue.add(`report-${data.scanId}`, data, {
    jobId: `report-${data.scanId}-${Date.now()}`,
  });

  logger.info(`Report job added: ${data.scanId}`);

  return job;
}

/**
 * Get job by ID
 */
export async function getScanJob(
  jobId: string
): Promise<Job<ScanJobData> | undefined> {
  const queue = getScanQueue();
  return queue.getJob(jobId);
}

/**
 * Get queue status
 */
export async function getQueueStatus(): Promise<{
  waiting: number;
  active: number;
  completed: number;
  failed: number;
  delayed: number;
}> {
  const queue = getScanQueue();

  const [waiting, active, completed, failed, delayed] = await Promise.all([
    queue.getWaitingCount(),
    queue.getActiveCount(),
    queue.getCompletedCount(),
    queue.getFailedCount(),
    queue.getDelayedCount(),
  ]);

  return { waiting, active, completed, failed, delayed };
}

/**
 * Subscribe to queue events
 */
export function subscribeToQueueEvents(
  onProgress?: (jobId: string, progress: JobProgress) => void,
  onCompleted?: (jobId: string, result: unknown) => void,
  onFailed?: (jobId: string, error: Error) => void
): QueueEvents {
  const queueEvents = new QueueEvents(SCAN_QUEUE, {
    connection: getRedisConnection(),
  });

  if (onProgress) {
    queueEvents.on('progress', ({ jobId, data }) => {
      onProgress(jobId, data as JobProgress);
    });
  }

  if (onCompleted) {
    queueEvents.on('completed', ({ jobId, returnvalue }) => {
      onCompleted(jobId, returnvalue);
    });
  }

  if (onFailed) {
    queueEvents.on('failed', ({ jobId, failedReason }) => {
      onFailed(jobId, new Error(failedReason));
    });
  }

  return queueEvents;
}

/**
 * Clean up old jobs
 */
export async function cleanOldJobs(
  maxAge: number = 7 * 24 * 3600 * 1000 // 7 days
): Promise<void> {
  const queue = getScanQueue();
  const gracePeriod = maxAge;

  await queue.clean(gracePeriod, 1000, 'completed');
  await queue.clean(gracePeriod, 1000, 'failed');

  logger.info('Old jobs cleaned');
}

/**
 * Graceful shutdown
 */
export async function shutdownQueues(): Promise<void> {
  if (scanQueue) {
    await scanQueue.close();
    scanQueue = null;
  }

  if (reportQueue) {
    await reportQueue.close();
    reportQueue = null;
  }

  await closeRedisConnection();

  logger.info('Queues shut down');
}
