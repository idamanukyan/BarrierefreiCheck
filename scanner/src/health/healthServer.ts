/**
 * Health Check HTTP Server for Scanner
 *
 * Provides health check endpoints for container orchestration
 * and load balancer probes.
 */

import * as http from 'http';
import { logger } from '../utils/logger.js';
import { getRedisConnection, getQueueStatus } from '../workers/queue.js';
import { getBrowserStatus } from '../utils/browser.js';

const HEALTH_PORT = parseInt(process.env.HEALTH_PORT || '8080', 10);

interface HealthStatus {
  status: 'healthy' | 'degraded' | 'unhealthy';
  version: string;
  uptime: number;
  timestamp: string;
  checks?: {
    redis: ComponentHealth;
    queue: QueueHealth;
    browser: ComponentHealth;
  };
}

interface ComponentHealth {
  status: 'healthy' | 'unhealthy';
  latencyMs?: number;
  error?: string;
}

interface QueueHealth extends ComponentHealth {
  waiting?: number;
  active?: number;
  completed?: number;
  failed?: number;
}

const startTime = Date.now();

/**
 * Check Redis connectivity
 */
async function checkRedis(): Promise<ComponentHealth> {
  const start = Date.now();
  try {
    const redis = getRedisConnection();
    await redis.ping();
    return {
      status: 'healthy',
      latencyMs: Date.now() - start,
    };
  } catch (error) {
    logger.error('Redis health check failed:', error);
    return {
      status: 'unhealthy',
      error: error instanceof Error ? error.message : 'Connection failed',
    };
  }
}

/**
 * Check queue status
 */
async function checkQueue(): Promise<QueueHealth> {
  const start = Date.now();
  try {
    const status = await getQueueStatus();
    return {
      status: 'healthy',
      latencyMs: Date.now() - start,
      waiting: status.waiting,
      active: status.active,
      completed: status.completed,
      failed: status.failed,
    };
  } catch (error) {
    logger.error('Queue health check failed:', error);
    return {
      status: 'unhealthy',
      error: error instanceof Error ? error.message : 'Queue unavailable',
    };
  }
}

/**
 * Check browser manager status
 */
async function checkBrowser(): Promise<ComponentHealth> {
  const start = Date.now();
  try {
    const browserStatus = await getBrowserStatus();
    return {
      status: browserStatus.available ? 'healthy' : 'unhealthy',
      latencyMs: Date.now() - start,
      ...(browserStatus.error && { error: browserStatus.error }),
    };
  } catch (error) {
    return {
      status: 'unhealthy',
      error: error instanceof Error ? error.message : 'Browser unavailable',
    };
  }
}

/**
 * Get simple health status (for liveness probes)
 */
function getSimpleHealth(): HealthStatus {
  return {
    status: 'healthy',
    version: process.env.APP_VERSION || '0.1.0',
    uptime: Math.floor((Date.now() - startTime) / 1000),
    timestamp: new Date().toISOString(),
  };
}

/**
 * Get deep health status (for readiness probes)
 */
async function getDeepHealth(): Promise<HealthStatus> {
  const [redisHealth, queueHealth, browserHealth] = await Promise.all([
    checkRedis(),
    checkQueue(),
    checkBrowser(),
  ]);

  const statuses = [redisHealth.status, queueHealth.status, browserHealth.status];

  let overallStatus: 'healthy' | 'degraded' | 'unhealthy';
  if (statuses.every((s) => s === 'healthy')) {
    overallStatus = 'healthy';
  } else if (statuses.some((s) => s === 'unhealthy')) {
    // Redis is critical, browser is not (it can be launched on demand)
    if (redisHealth.status === 'unhealthy') {
      overallStatus = 'unhealthy';
    } else {
      overallStatus = 'degraded';
    }
  } else {
    overallStatus = 'degraded';
  }

  return {
    status: overallStatus,
    version: process.env.APP_VERSION || '0.1.0',
    uptime: Math.floor((Date.now() - startTime) / 1000),
    timestamp: new Date().toISOString(),
    checks: {
      redis: redisHealth,
      queue: queueHealth,
      browser: browserHealth,
    },
  };
}

/**
 * HTTP request handler
 */
async function handleRequest(
  req: http.IncomingMessage,
  res: http.ServerResponse
): Promise<void> {
  const url = req.url || '/';

  // Set common headers
  res.setHeader('Content-Type', 'application/json');
  res.setHeader('Cache-Control', 'no-cache, no-store');

  try {
    if (url === '/health' || url === '/health/live') {
      // Simple liveness check
      const health = getSimpleHealth();
      res.statusCode = 200;
      res.end(JSON.stringify(health));
    } else if (url === '/health/ready') {
      // Deep readiness check
      const health = await getDeepHealth();
      res.statusCode = health.status === 'unhealthy' ? 503 : 200;
      res.end(JSON.stringify(health));
    } else if (url === '/metrics') {
      // Basic metrics endpoint
      const queueStatus = await getQueueStatus();
      const metrics = {
        scanner_uptime_seconds: Math.floor((Date.now() - startTime) / 1000),
        scanner_queue_waiting: queueStatus.waiting,
        scanner_queue_active: queueStatus.active,
        scanner_queue_completed: queueStatus.completed,
        scanner_queue_failed: queueStatus.failed,
      };
      res.statusCode = 200;
      res.end(JSON.stringify(metrics));
    } else {
      res.statusCode = 404;
      res.end(JSON.stringify({ error: 'Not found' }));
    }
  } catch (error) {
    logger.error('Health check error:', error);
    res.statusCode = 500;
    res.end(
      JSON.stringify({
        status: 'unhealthy',
        error: error instanceof Error ? error.message : 'Internal error',
      })
    );
  }
}

let healthServer: http.Server | null = null;

/**
 * Start the health check HTTP server
 */
export function startHealthServer(): http.Server {
  if (healthServer) {
    return healthServer;
  }

  healthServer = http.createServer(handleRequest);

  healthServer.listen(HEALTH_PORT, () => {
    logger.info(`Health check server listening on port ${HEALTH_PORT}`);
    logger.info(`  - Liveness:  http://localhost:${HEALTH_PORT}/health/live`);
    logger.info(`  - Readiness: http://localhost:${HEALTH_PORT}/health/ready`);
    logger.info(`  - Metrics:   http://localhost:${HEALTH_PORT}/metrics`);
  });

  healthServer.on('error', (error) => {
    logger.error('Health server error:', error);
  });

  return healthServer;
}

/**
 * Stop the health check HTTP server
 */
export async function stopHealthServer(): Promise<void> {
  if (healthServer) {
    return new Promise((resolve) => {
      healthServer!.close(() => {
        logger.info('Health check server stopped');
        healthServer = null;
        resolve();
      });
    });
  }
}
