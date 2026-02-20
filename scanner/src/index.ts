/**
 * AccessibilityChecker Scanner - Worker Entry Point
 *
 * This is the main entry point for the scan worker that processes
 * accessibility testing jobs from the Redis queue.
 */

import { Worker } from 'bullmq';
import dotenv from 'dotenv';
import { logger } from './utils/logger.js';
import { createScanWorker, shutdownWorker } from './workers/scanWorker.js';
import { shutdownQueues, getQueueStatus } from './workers/queue.js';
import { closeBrowserManager } from './utils/browser.js';
import { startHealthServer, stopHealthServer } from './health/healthServer.js';

// Load environment variables
dotenv.config();

const CONCURRENCY = parseInt(process.env.WORKER_CONCURRENCY || '2', 10);

logger.info('🚀 AccessibilityChecker Scanner starting...');
logger.info(`📡 Redis URL: ${process.env.REDIS_URL || 'redis://localhost:6379'}`);
logger.info(`⚙️  Concurrency: ${CONCURRENCY}`);

// Create the scan worker
let scanWorker: Worker | null = null;

async function start(): Promise<void> {
  try {
    // Start health check server
    startHealthServer();

    // Start the scan worker
    scanWorker = createScanWorker(CONCURRENCY);

    // Log initial queue status
    const status = await getQueueStatus();
    logger.info(`📊 Queue status - Waiting: ${status.waiting}, Active: ${status.active}`);

    logger.info('✅ Scanner worker initialized');
    logger.info('⏳ Waiting for jobs...');
  } catch (error) {
    logger.error('Failed to start scanner:', error);
    process.exit(1);
  }
}

// Graceful shutdown
async function shutdown(signal: string): Promise<void> {
  logger.info(`🛑 Received ${signal}, shutting down...`);

  try {
    // Stop health server first to stop accepting new probes
    await stopHealthServer();

    if (scanWorker) {
      await shutdownWorker(scanWorker);
    }

    await closeBrowserManager();
    await shutdownQueues();

    logger.info('👋 Scanner shutdown complete');
    process.exit(0);
  } catch (error) {
    logger.error('Error during shutdown:', error);
    process.exit(1);
  }
}

// Handle shutdown signals
process.on('SIGTERM', () => shutdown('SIGTERM'));
process.on('SIGINT', () => shutdown('SIGINT'));

// Handle uncaught errors
process.on('uncaughtException', (error) => {
  logger.error('Uncaught exception:', error);
  shutdown('uncaughtException');
});

process.on('unhandledRejection', (reason, promise) => {
  logger.error('Unhandled rejection at:', promise, 'reason:', reason);
});

// Start the worker
start();
