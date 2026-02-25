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
export const DEAD_LETTER_QUEUE = 'accessibility-scans-dlq';

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
let deadLetterQueue: Queue<ScanJobData & { originalError: string; failedAt: string; attempts: number }> | null = null;

/**
 * Get dead letter queue for permanently failed jobs
 */
export function getDeadLetterQueue(): Queue<ScanJobData & { originalError: string; failedAt: string; attempts: number }> {
  if (!deadLetterQueue) {
    deadLetterQueue = new Queue(DEAD_LETTER_QUEUE, {
      connection: getRedisConnection(),
      defaultJobOptions: {
        removeOnComplete: false, // Keep DLQ jobs for manual review
        removeOnFail: false,
      },
    });

    logger.info(`Dead letter queue "${DEAD_LETTER_QUEUE}" initialized`);
  }

  return deadLetterQueue;
}

/**
 * Move a failed job to the dead letter queue
 */
export async function moveToDeadLetterQueue(
  job: Job<ScanJobData>,
  error: string
): Promise<void> {
  const dlq = getDeadLetterQueue();

  await dlq.add(
    `dlq-${job.data.scanId}`,
    {
      ...job.data,
      originalError: error,
      failedAt: new Date().toISOString(),
      attempts: job.attemptsMade,
    },
    {
      jobId: `dlq-${job.data.scanId}-${Date.now()}`,
    }
  );

  logger.warn(`Job ${job.id} moved to dead letter queue after ${job.attemptsMade} attempts`);
}

/**
 * Get dead letter queue status
 */
export async function getDeadLetterQueueStatus(): Promise<{
  waiting: number;
  failed: number;
  jobs: Array<{
    id: string | undefined;
    scanId: string;
    url: string;
    error: string;
    failedAt: string;
    attempts: number;
  }>;
}> {
  const dlq = getDeadLetterQueue();

  const [waiting, jobs] = await Promise.all([
    dlq.getWaitingCount(),
    dlq.getJobs(['waiting', 'delayed'], 0, 100),
  ]);

  return {
    waiting,
    failed: waiting,
    jobs: jobs.map((job) => ({
      id: job.id,
      scanId: job.data.scanId,
      url: job.data.url,
      error: job.data.originalError || 'Unknown error',
      failedAt: job.data.failedAt || 'Unknown',
      attempts: job.data.attempts || 0,
    })),
  };
}

/**
 * Retry a job from the dead letter queue
 */
export async function retryFromDeadLetterQueue(
  dlqJobId: string
): Promise<Job<ScanJobData> | null> {
  const dlq = getDeadLetterQueue();
  const dlqJob = await dlq.getJob(dlqJobId);

  if (!dlqJob) {
    logger.warn(`DLQ job ${dlqJobId} not found`);
    return null;
  }

  // Re-add to main queue
  const mainQueue = getScanQueue();
  const newJob = await mainQueue.add(
    `retry-${dlqJob.data.scanId}`,
    {
      scanId: dlqJob.data.scanId,
      url: dlqJob.data.url,
      crawl: dlqJob.data.crawl,
      maxPages: dlqJob.data.maxPages,
      userId: dlqJob.data.userId,
      options: dlqJob.data.options,
    },
    {
      jobId: `retry-${dlqJob.data.scanId}-${Date.now()}`,
    }
  );

  // Remove from DLQ
  await dlqJob.remove();

  logger.info(`Job ${dlqJobId} retried from DLQ, new job ID: ${newJob.id}`);
  return newJob;
}

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

  if (deadLetterQueue) {
    await deadLetterQueue.close();
    deadLetterQueue = null;
  }

  await closeRedisConnection();

  logger.info('Queues shut down');
}
