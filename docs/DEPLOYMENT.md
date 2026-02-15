# Deployment Runbook

This document provides step-by-step instructions for deploying AccessibilityChecker to production.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Infrastructure Overview](#infrastructure-overview)
- [Initial Deployment](#initial-deployment)
- [Updating the Application](#updating-the-application)
- [Rollback Procedures](#rollback-procedures)
- [Database Migrations](#database-migrations)
- [Monitoring & Health Checks](#monitoring--health-checks)
- [Troubleshooting](#troubleshooting)
- [Disaster Recovery](#disaster-recovery)

## Prerequisites

### Server Requirements

- Ubuntu 22.04 LTS or similar Linux distribution
- Docker 24.0+ and Docker Compose 2.0+
- Minimum 4GB RAM, 2 vCPUs, 40GB SSD
- Domain with DNS configured

### Required Secrets

Before deployment, ensure you have:

- [ ] `POSTGRES_PASSWORD` - Strong database password
- [ ] `JWT_SECRET` - 32+ character secret (generate with `python -c "import secrets; print(secrets.token_urlsafe(32))"`)
- [ ] `MINIO_ROOT_PASSWORD` - MinIO admin password
- [ ] `STRIPE_SECRET_KEY` - Stripe API key (if using payments)
- [ ] `STRIPE_WEBHOOK_SECRET` - Stripe webhook secret

## Infrastructure Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        Load Balancer                         │
│                    (nginx/Cloudflare)                        │
└─────────────────────┬───────────────────────────────────────┘
                      │
         ┌────────────┴────────────┐
         │                         │
┌────────▼────────┐       ┌───────▼────────┐
│    Frontend     │       │      API       │
│    (nginx)      │       │   (FastAPI)    │
│    Port 80      │       │   Port 8000    │
└─────────────────┘       └───────┬────────┘
                                  │
              ┌───────────────────┼───────────────────┐
              │                   │                   │
     ┌────────▼────────┐ ┌───────▼────────┐ ┌───────▼────────┐
     │   PostgreSQL    │ │     Redis      │ │     MinIO      │
     │   Port 5432     │ │   Port 6379    │ │   Port 9000    │
     └─────────────────┘ └────────┬───────┘ └────────────────┘
                                  │
                         ┌────────▼────────┐
                         │    Scanner      │
                         │   (Worker)      │
                         └─────────────────┘
```

### Network Isolation

- **internal**: Database, Redis, MinIO, Scanner (not exposed)
- **external**: API, Frontend (exposed via ports)

## Initial Deployment

### 1. Server Setup

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo apt install docker-compose-plugin

# Verify installation
docker --version
docker compose version
```

### 2. Clone Repository

```bash
git clone https://github.com/YOUR_ORG/accessibilitychecker.git
cd accessibilitychecker
```

### 3. Configure Environment

```bash
# Create production environment file
cp .env.example .env.prod

# Edit with production values
nano .env.prod
```

**Required settings in `.env.prod`:**

```env
APP_ENV=production
APP_DEBUG=false

POSTGRES_USER=accesscheck
POSTGRES_PASSWORD=<STRONG_PASSWORD>

JWT_SECRET=<32_CHAR_SECRET>

MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=<STRONG_PASSWORD>

S3_ACCESS_KEY=<SAME_AS_MINIO_ROOT_USER>
S3_SECRET_KEY=<SAME_AS_MINIO_ROOT_PASSWORD>

CORS_ORIGINS=https://yourdomain.com

STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
```

### 4. Build and Deploy

```bash
# Build images
docker compose -f docker-compose.prod.yml build

# Start services
docker compose -f docker-compose.prod.yml up -d

# Check status
docker compose -f docker-compose.prod.yml ps
```

### 5. Run Database Migrations

```bash
# Execute migrations
docker compose -f docker-compose.prod.yml exec api alembic upgrade head
```

### 6. Create MinIO Buckets

```bash
# Access MinIO console at http://your-server:9001
# Or use mc CLI:
docker compose -f docker-compose.prod.yml exec minio mc alias set local http://localhost:9000 minioadmin <password>
docker compose -f docker-compose.prod.yml exec minio mc mb local/screenshots
docker compose -f docker-compose.prod.yml exec minio mc mb local/reports
```

### 7. Verify Deployment

```bash
# Check health endpoint
curl http://localhost:8000/api/v1/health

# Check deep health (all dependencies)
curl http://localhost:8000/api/v1/health/deep

# View logs
docker compose -f docker-compose.prod.yml logs -f
```

## Updating the Application

### Standard Update (No Breaking Changes)

```bash
cd /path/to/accessibilitychecker

# Pull latest changes
git pull origin main

# Rebuild and restart
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d

# Run migrations if needed
docker compose -f docker-compose.prod.yml exec api alembic upgrade head

# Verify
curl http://localhost:8000/api/v1/health
```

### Blue-Green Deployment

For zero-downtime updates, use the blue-green deployment workflow:

```bash
# See .github/workflows/deploy-blue-green.yml
# Triggered automatically on release tags
```

### Manual Blue-Green (if needed)

```bash
# Start new version alongside old
docker compose -f docker-compose.prod.yml up -d --scale api=2

# Test new instance
curl http://localhost:8001/api/v1/health

# If healthy, remove old instance
docker compose -f docker-compose.prod.yml up -d --scale api=1

# Or rollback
docker compose -f docker-compose.prod.yml up -d --scale api=1 --no-deps api
```

## Rollback Procedures

### Quick Rollback (Last Working Version)

```bash
# Check current version
docker compose -f docker-compose.prod.yml exec api printenv APP_VERSION

# Stop current version
docker compose -f docker-compose.prod.yml down

# Checkout previous version
git checkout <previous-tag>

# Rebuild and start
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d
```

### Database Rollback

```bash
# List migration history
docker compose -f docker-compose.prod.yml exec api alembic history

# Downgrade one revision
docker compose -f docker-compose.prod.yml exec api alembic downgrade -1

# Or downgrade to specific revision
docker compose -f docker-compose.prod.yml exec api alembic downgrade <revision_id>
```

## Database Migrations

### Running Migrations

```bash
# Upgrade to latest
docker compose -f docker-compose.prod.yml exec api alembic upgrade head

# Upgrade specific number of revisions
docker compose -f docker-compose.prod.yml exec api alembic upgrade +1
```

### Creating New Migration

```bash
# Generate migration from model changes
docker compose exec api alembic revision --autogenerate -m "description"

# Create empty migration
docker compose exec api alembic revision -m "description"
```

### Pre-deployment Migration Check

```bash
# Show pending migrations
docker compose -f docker-compose.prod.yml exec api alembic history

# Dry-run (show SQL without executing)
docker compose -f docker-compose.prod.yml exec api alembic upgrade head --sql
```

## Monitoring & Health Checks

### Health Endpoints

| Endpoint | Purpose |
|----------|---------|
| `GET /api/v1/health` | Simple liveness check |
| `GET /api/v1/health/deep` | Full dependency check |
| `GET /metrics` | Prometheus metrics |

### Log Monitoring

```bash
# All services
docker compose -f docker-compose.prod.yml logs -f

# Specific service
docker compose -f docker-compose.prod.yml logs -f api

# Last N lines
docker compose -f docker-compose.prod.yml logs --tail=100 api
```

### Resource Monitoring

```bash
# Container stats
docker stats

# Disk usage
docker system df
```

### Prometheus Metrics

Metrics available at `/metrics`:
- `http_requests_total` - Request count by endpoint and status code
- `http_request_duration_seconds` - Request latency histogram
- `scans_total` - Scans by status (created/completed/failed)
- `scan_duration_seconds` - Scan duration histogram
- `accessibility_issues_total` - Issues found by impact level
- `reports_generated_total` - Reports by format and status
- `auth_attempts_total` - Authentication events
- `db_query_duration_seconds` - Database query latency
- `cache_hits_total` / `cache_misses_total` - Cache performance
- `external_service_requests_total` - External API calls

### Grafana Dashboards

Grafana provides visualization and alerting for all metrics.

**Access:**
- Development: http://localhost:3001
- Production: https://monitoring.yourdomain.de (or port 3001)
- Default credentials: `admin` / (set in `GRAFANA_ADMIN_PASSWORD`)

**Available Dashboards:**

| Dashboard | Description |
|-----------|-------------|
| API Overview | Request rates, latency percentiles, error rates, endpoint breakdown |
| Scan Metrics | Scan throughput, duration, failure rates, issues by impact |
| Business Metrics | Auth attempts, reports generated, cache hit rates, external services |
| Infrastructure | Database query latency, WebSocket connections, email delivery |

**Starting Monitoring Services:**

```bash
# Development
docker compose up -d prometheus grafana

# Production
docker compose -f docker-compose.prod.yml up -d prometheus grafana

# View Grafana logs
docker compose logs -f grafana
```

**Alert Rules:**

Alerts are displayed in Grafana's Alerting panel (no external notifications configured by default).

| Alert | Threshold | Severity |
|-------|-----------|----------|
| HighErrorRate | >5% 5xx errors for 5min | Critical |
| HighAPILatency | p99 >5s for 5min | Critical |
| HighScanFailureRate | >20% failures for 5min | Critical |
| SlowDatabaseQueries | p95 >1s for 5min | Critical |
| ElevatedErrorRate | >1% 5xx for 10min | Warning |
| LowCacheHitRate | <80% for 15min | Warning |

To view alerts: Grafana → Alerting → Alert rules

## Troubleshooting

### Common Issues

#### Container Won't Start

```bash
# Check logs
docker compose -f docker-compose.prod.yml logs api

# Check container status
docker compose -f docker-compose.prod.yml ps

# Restart specific service
docker compose -f docker-compose.prod.yml restart api
```

#### Database Connection Failed

```bash
# Check PostgreSQL is running
docker compose -f docker-compose.prod.yml exec postgres pg_isready

# Check connection from API
docker compose -f docker-compose.prod.yml exec api python -c "from app.database import engine; print(engine.connect())"
```

#### Redis Connection Failed

```bash
# Check Redis is running
docker compose -f docker-compose.prod.yml exec redis redis-cli ping

# Check Redis memory
docker compose -f docker-compose.prod.yml exec redis redis-cli info memory
```

#### Scanner Not Processing Jobs

```bash
# Check scanner logs
docker compose -f docker-compose.prod.yml logs scanner

# Check Redis queue
docker compose -f docker-compose.prod.yml exec redis redis-cli llen bull:scan-queue:wait
```

#### High Memory Usage

```bash
# Check container memory
docker stats --no-stream

# Restart heavy containers
docker compose -f docker-compose.prod.yml restart scanner
```

### Emergency Commands

```bash
# Stop all services
docker compose -f docker-compose.prod.yml down

# Force remove stuck containers
docker compose -f docker-compose.prod.yml down --remove-orphans

# Clean up unused resources
docker system prune -a
```

## Disaster Recovery

### Backup Procedures

#### Database Backup

```bash
# Create backup
docker compose -f docker-compose.prod.yml exec postgres pg_dump -U accesscheck accessibilitychecker > backup_$(date +%Y%m%d).sql

# Compress
gzip backup_$(date +%Y%m%d).sql

# Copy to remote storage
aws s3 cp backup_$(date +%Y%m%d).sql.gz s3://your-backup-bucket/
```

#### Automated Backups (Cron)

```bash
# Add to crontab
0 2 * * * /path/to/backup-script.sh
```

### Restore Procedures

#### Database Restore

```bash
# Stop API and scanner (prevent writes)
docker compose -f docker-compose.prod.yml stop api scanner

# Restore from backup
gunzip -c backup_20250213.sql.gz | docker compose -f docker-compose.prod.yml exec -T postgres psql -U accesscheck accessibilitychecker

# Start services
docker compose -f docker-compose.prod.yml start api scanner
```

#### Full System Restore

1. Set up new server with Docker
2. Clone repository
3. Restore `.env.prod` configuration
4. Restore database from backup
5. Start services
6. Verify health endpoints
7. Update DNS if needed

### Recovery Time Objectives

| Scenario | RTO | RPO |
|----------|-----|-----|
| Service restart | < 5 min | 0 |
| Container rebuild | < 15 min | 0 |
| Database restore | < 30 min | Last backup |
| Full system restore | < 2 hours | Last backup |

## Security Checklist

Before going live:

- [ ] All `CHANGE_ME` values replaced
- [ ] `APP_ENV=production`
- [ ] `APP_DEBUG=false`
- [ ] Strong passwords for all services
- [ ] HTTPS configured (via reverse proxy)
- [ ] Firewall rules in place
- [ ] Backup automation configured
- [ ] Monitoring alerts configured
- [ ] Log rotation enabled

## Contact

For deployment issues:
- Email: idamyan01@gmail.com
- GitHub Issues: https://github.com/ORG/accessibilitychecker/issues
