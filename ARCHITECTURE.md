# AccessibilityChecker - System Architecture

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [System Components](#system-components)
3. [Data Flow](#data-flow)
4. [Technology Stack](#technology-stack)
5. [Database Schema](#database-schema)
6. [Security Architecture](#security-architecture)
7. [Infrastructure](#infrastructure)
8. [API Design](#api-design)
9. [WCAG Testing Engine](#wcag-testing-engine)

---

## Architecture Overview

AccessibilityChecker follows a modern, event-driven microservice architecture with clear separation between frontend, API, and scan workers.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              ARCHITECTURE DIAGRAM                            │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────┐     ┌──────────────┐     ┌──────────────────────────────────┐
│              │     │              │     │         SCAN WORKERS              │
│   Browser    │────▶│   Frontend   │     │  ┌────────────────────────────┐  │
│   (User)     │     │  (React SPA) │     │  │  Worker 1 (Node.js)        │  │
│              │     │              │     │  │  ├── Puppeteer             │  │
└──────────────┘     └──────┬───────┘     │  │  └── axe-core              │  │
                           │              │  └────────────────────────────┘  │
                           │              │  ┌────────────────────────────┐  │
                           ▼              │  │  Worker 2 (Node.js)        │  │
                    ┌──────────────┐      │  │  ├── Puppeteer             │  │
                    │              │      │  │  └── axe-core              │  │
                    │  API Gateway │◀────▶│  └────────────────────────────┘  │
                    │  (FastAPI)   │      │  ┌────────────────────────────┐  │
                    │              │      │  │  Worker N...               │  │
                    └──────┬───────┘      │  └────────────────────────────┘  │
                           │              └──────────────────────────────────┘
          ┌────────────────┼────────────────┐                │
          │                │                │                │
          ▼                ▼                ▼                │
   ┌────────────┐   ┌────────────┐   ┌────────────┐         │
   │            │   │            │   │            │         │
   │ PostgreSQL │   │   Redis    │   │   MinIO    │◀────────┘
   │ (Database) │   │  (Queue)   │   │ (Storage)  │
   │            │   │            │   │            │
   └────────────┘   └────────────┘   └────────────┘
```

### Component Responsibilities

| Component | Technology | Responsibility |
|-----------|------------|----------------|
| **Frontend** | React + TypeScript | User interface, dashboard, report viewing |
| **API Gateway** | Python FastAPI | Authentication, request routing, rate limiting |
| **Scan Orchestrator** | Part of API | Job scheduling, crawler coordination, result aggregation |
| **Scan Workers** | Node.js + Puppeteer | Headless browser execution, axe-core testing |
| **Report Generator** | Puppeteer/PDFKit | PDF creation, template rendering |
| **Database** | PostgreSQL | User data, scan results, subscriptions |
| **Queue** | Redis + BullMQ | Job queue for asynchronous scans |
| **Object Storage** | MinIO (S3-API) | Screenshots, PDF reports, scan snapshots |

---

## System Components

### 1. Frontend (React SPA)

```
frontend/
├── src/
│   ├── components/          # Reusable UI components
│   │   ├── common/          # Buttons, inputs, modals
│   │   ├── dashboard/       # Dashboard-specific components
│   │   ├── reports/         # Report display components
│   │   └── scan/            # Scan-related components
│   ├── pages/               # Route pages
│   │   ├── Home.tsx
│   │   ├── Dashboard.tsx
│   │   ├── ScanResults.tsx
│   │   ├── Reports.tsx
│   │   └── Settings.tsx
│   ├── hooks/               # Custom React hooks
│   ├── services/            # API client services
│   ├── store/               # State management
│   ├── utils/               # Utility functions
│   └── i18n/                # Internationalization (German/English)
├── public/
└── package.json
```

**Key Features:**
- Landing page with value proposition and URL input
- Real-time scan progress indicator
- Results dashboard with score overview
- Issue list with filtering and search
- PDF report download
- User account management

### 2. API Gateway (FastAPI)

```
api/
├── app/
│   ├── main.py              # Application entry point
│   ├── config.py            # Configuration management
│   ├── dependencies.py      # Dependency injection
│   ├── routers/
│   │   ├── auth.py          # Authentication endpoints
│   │   ├── scans.py         # Scan management
│   │   ├── reports.py       # Report generation
│   │   ├── users.py         # User management
│   │   └── billing.py       # Stripe integration
│   ├── models/
│   │   ├── user.py          # User model
│   │   ├── scan.py          # Scan model
│   │   ├── issue.py         # Issue model
│   │   └── subscription.py  # Subscription model
│   ├── schemas/             # Pydantic schemas
│   ├── services/
│   │   ├── scan_service.py  # Scan orchestration
│   │   ├── auth_service.py  # JWT handling
│   │   └── billing_service.py
│   └── utils/
│       ├── security.py      # Password hashing, JWT
│       └── validators.py    # Input validation
├── alembic/                 # Database migrations
├── tests/
└── requirements.txt
```

**Key Endpoints:**
- `POST /api/v1/auth/register` - User registration
- `POST /api/v1/auth/login` - JWT authentication
- `POST /api/v1/scans` - Start new scan
- `GET /api/v1/scans/{id}` - Get scan status/results
- `GET /api/v1/scans/{id}/report` - Generate PDF
- `POST /api/v1/billing/checkout` - Stripe checkout

### 3. Scan Workers (Node.js)

```
scanner/
├── src/
│   ├── index.ts             # Worker entry point
│   ├── crawler/
│   │   ├── Crawler.ts       # Website crawler
│   │   ├── LinkExtractor.ts # Link discovery
│   │   └── RobotsTxt.ts     # robots.txt parser
│   ├── axe/
│   │   ├── AxeRunner.ts     # axe-core execution
│   │   ├── ResultMapper.ts  # Result transformation
│   │   └── RuleTranslator.ts# German translations
│   ├── workers/
│   │   ├── ScanWorker.ts    # Main scan job handler
│   │   └── ReportWorker.ts  # PDF generation
│   ├── utils/
│   │   ├── screenshot.ts    # Screenshot capture
│   │   └── browser.ts       # Puppeteer helpers
│   └── translations/        # German rule data
│       └── rules-de.json
├── tests/
└── package.json
```

**Worker Flow:**
1. Pull job from BullMQ queue
2. Launch Puppeteer browser
3. Navigate to target URL
4. Inject and execute axe-core
5. Capture screenshots of violations
6. Map results to German translations
7. Store results in database
8. Upload screenshots to MinIO
9. Update job status

---

## Data Flow

### Scan Request Flow

```
┌────────────────────────────────────────────────────────────────────────────┐
│                            SCAN REQUEST FLOW                                │
└────────────────────────────────────────────────────────────────────────────┘

1. User enters URL
        │
        ▼
2. Frontend → POST /api/v1/scans
        │
        ▼
3. API validates request, checks user quota
        │
        ▼
4. Create scan record in PostgreSQL (status: "queued")
        │
        ▼
5. Push scan job to Redis/BullMQ queue
        │
        ▼
6. Return scan_id to frontend (polling begins)
        │
        ▼
7. Worker picks up job from queue
        │
        ▼
8. Puppeteer loads URL, crawls pages (if multi-page)
        │
        ▼
9. For each page:
   ├── Load page in Puppeteer
   ├── Inject axe-core
   ├── Execute accessibility tests
   ├── Capture screenshots of violations
   └── Store page results
        │
        ▼
10. Aggregate results, calculate compliance score
        │
        ▼
11. Update scan record (status: "completed")
        │
        ▼
12. Frontend receives update via polling
        │
        ▼
13. Display results dashboard
```

### Report Generation Flow

```
1. User requests PDF report
        │
        ▼
2. API retrieves scan data from PostgreSQL
        │
        ▼
3. Generate HTML template with scan results
        │
        ▼
4. Render HTML to PDF using Puppeteer
        │
        ▼
5. Upload PDF to MinIO
        │
        ▼
6. Return download URL to user
```

---

## Technology Stack

### Frontend

| Technology | Version | Purpose |
|------------|---------|---------|
| React | 18.x | UI framework |
| TypeScript | 5.x | Type safety |
| Tailwind CSS | 3.x | Styling |
| Vite | 5.x | Build tool |
| React Router | 6.x | Routing |
| TanStack Query | 5.x | Data fetching |
| Recharts | 2.x | Charts/visualization |
| Zustand | 4.x | State management |

### Backend

| Technology | Version | Purpose |
|------------|---------|---------|
| Python | 3.11+ | Runtime |
| FastAPI | 0.100+ | Web framework |
| SQLAlchemy | 2.x | ORM |
| Alembic | 1.x | Migrations |
| Pydantic | 2.x | Validation |
| python-jose | - | JWT handling |
| bcrypt | - | Password hashing |
| stripe | - | Payment processing |

### Scanner

| Technology | Version | Purpose |
|------------|---------|---------|
| Node.js | 20 LTS | Runtime |
| TypeScript | 5.x | Type safety |
| Puppeteer | 21.x | Browser automation |
| axe-core | 4.8+ | Accessibility testing |
| BullMQ | 4.x | Job queue |

### Infrastructure

| Technology | Purpose |
|------------|---------|
| PostgreSQL 15+ | Primary database |
| Redis 7+ | Caching & job queue |
| MinIO | S3-compatible object storage |
| Docker | Containerization |
| GitHub Actions | CI/CD |
| Hetzner Cloud | Hosting (German/EU) |

---

## Database Schema

### Entity Relationship Diagram

```
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│     users       │       │     scans       │       │     pages       │
├─────────────────┤       ├─────────────────┤       ├─────────────────┤
│ id (PK)         │───┐   │ id (PK)         │───┐   │ id (PK)         │
│ email           │   │   │ user_id (FK)    │   │   │ scan_id (FK)    │
│ password_hash   │   └──▶│ url             │   └──▶│ url             │
│ created_at      │       │ status          │       │ status          │
│ plan            │       │ score           │       │ issues_count    │
│ stripe_customer │       │ pages_scanned   │       │ scanned_at      │
└─────────────────┘       │ created_at      │       └────────┬────────┘
                          │ completed_at    │                │
                          └─────────────────┘                │
                                                             │
┌─────────────────┐       ┌─────────────────┐                │
│ subscriptions   │       │     issues      │◀───────────────┘
├─────────────────┤       ├─────────────────┤
│ id (PK)         │       │ id (PK)         │
│ user_id (FK)    │       │ page_id (FK)    │
│ plan            │       │ rule_id         │
│ status          │       │ impact          │
│ stripe_sub_id   │       │ wcag_criteria   │
│ current_period  │       │ bfsg_reference  │
│ created_at      │       │ element_selector│
└─────────────────┘       │ screenshot_url  │
                          │ created_at      │
                          └─────────────────┘
```

### Key Tables

#### users
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    company VARCHAR(255),
    plan VARCHAR(50) DEFAULT 'free',
    stripe_customer_id VARCHAR(255),
    email_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

#### scans
```sql
CREATE TABLE scans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    url VARCHAR(2048) NOT NULL,
    crawl BOOLEAN DEFAULT FALSE,
    max_pages INTEGER DEFAULT 1,
    status VARCHAR(50) DEFAULT 'queued',
    score DECIMAL(5,2),
    pages_scanned INTEGER DEFAULT 0,
    issues_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);
```

#### issues
```sql
CREATE TABLE issues (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    page_id UUID REFERENCES pages(id) ON DELETE CASCADE,
    rule_id VARCHAR(100) NOT NULL,
    impact VARCHAR(50) NOT NULL,
    wcag_criteria TEXT[],
    bfsg_reference VARCHAR(255),
    title_de TEXT NOT NULL,
    description_de TEXT,
    fix_suggestion_de TEXT,
    element_selector TEXT,
    element_html TEXT,
    screenshot_url VARCHAR(2048),
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## Security Architecture

### Authentication Flow

```
┌────────────────────────────────────────────────────────────────────────────┐
│                          AUTHENTICATION FLOW                                │
└────────────────────────────────────────────────────────────────────────────┘

1. Registration
   ├── Email + Password → API
   ├── Password hashed with bcrypt (cost=12)
   ├── User created in database
   └── Verification email sent

2. Login
   ├── Email + Password → API
   ├── Verify password hash
   ├── Generate JWT (15min expiry)
   ├── Generate Refresh Token (7 days)
   └── Return both tokens

3. Authenticated Requests
   ├── Include JWT in Authorization header
   ├── API validates JWT signature
   ├── Check token expiry
   └── Extract user context

4. Token Refresh
   ├── Submit refresh token
   ├── Validate refresh token
   ├── Issue new JWT
   └── Optionally rotate refresh token
```

### Security Measures

| Layer | Measure | Implementation |
|-------|---------|----------------|
| **Transport** | TLS 1.3 | All traffic encrypted |
| **Authentication** | JWT + Refresh | Short-lived access tokens |
| **Passwords** | bcrypt | Cost factor 12 |
| **API** | Rate limiting | 100 req/min per user |
| **API** | CORS | Whitelist origins |
| **API** | Input validation | Pydantic schemas |
| **Scan** | Isolation | Separate browser context |
| **Data** | Encryption | Sensitive fields encrypted |
| **GDPR** | Data minimization | Only necessary data stored |
| **GDPR** | Deletion | 90-day retention policy |

### Authorization (RBAC)

```
Roles:
├── user      → Basic scan features
├── agency    → Multi-client management
├── admin     → Full system access
└── api       → Programmatic access only
```

---

## Infrastructure

### Production Environment (Hetzner Cloud)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         PRODUCTION INFRASTRUCTURE                            │
└─────────────────────────────────────────────────────────────────────────────┘

                         ┌─────────────────┐
                         │   Cloudflare    │
                         │   (CDN + WAF)   │
                         └────────┬────────┘
                                  │
                         ┌────────▼────────┐
                         │  Load Balancer  │
                         │   (Hetzner)     │
                         └────────┬────────┘
                                  │
            ┌─────────────────────┼─────────────────────┐
            │                     │                     │
   ┌────────▼────────┐   ┌───────▼────────┐   ┌───────▼────────┐
   │   App Server 1  │   │  App Server 2  │   │  App Server N  │
   │   (API + FE)    │   │   (API + FE)   │   │   (API + FE)   │
   │   CX31 4vCPU    │   │   CX31 4vCPU   │   │   CX31 4vCPU   │
   └─────────────────┘   └────────────────┘   └────────────────┘
            │                     │                     │
            └─────────────────────┼─────────────────────┘
                                  │
   ┌──────────────────────────────┼──────────────────────────────┐
   │                              │                              │
┌──▼──────────┐        ┌─────────▼─────────┐        ┌───────────▼───┐
│ PostgreSQL  │        │      Redis        │        │    MinIO      │
│ (Primary)   │        │   (Queue/Cache)   │        │  (S3 Storage) │
│ CX21 2vCPU  │        │   CX11 1vCPU      │        │  Storage Box  │
└─────┬───────┘        └───────────────────┘        └───────────────┘
      │
┌─────▼───────┐
│ PostgreSQL  │
│ (Replica)   │
└─────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                           SCAN WORKER CLUSTER                               │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐            │
│  │  Worker 1  │  │  Worker 2  │  │  Worker 3  │  │  Worker N  │            │
│  │  CX21      │  │  CX21      │  │  CX21      │  │  CX21      │            │
│  │  Puppeteer │  │  Puppeteer │  │  Puppeteer │  │  Puppeteer │            │
│  └────────────┘  └────────────┘  └────────────┘  └────────────┘            │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Cost Breakdown (MVP)

| Component | Specification | Cost/Month |
|-----------|---------------|------------|
| App Server | Hetzner CX31 (4 vCPU, 8GB) | €15 |
| Scan Workers | Hetzner CX21 x2 (2 vCPU, 4GB) | €20 |
| Database | Hetzner CX11 + PostgreSQL | €8 |
| Redis | Hetzner CX11 | €5 |
| Object Storage | Hetzner S3 (50GB) | €3 |
| Domain + SSL | Cloudflare (Free) | €0 |
| Email | Mailgun Starter | €15 |
| **Total** | | **~€66/month** |

---

## API Design

### RESTful Endpoints

#### Authentication

```
POST   /api/v1/auth/register         # Create account
POST   /api/v1/auth/login            # Get tokens
POST   /api/v1/auth/refresh          # Refresh access token
POST   /api/v1/auth/logout           # Invalidate tokens
POST   /api/v1/auth/forgot-password  # Request reset
POST   /api/v1/auth/reset-password   # Set new password
GET    /api/v1/auth/verify/{token}   # Verify email
```

#### Scans

```
POST   /api/v1/scans                 # Start new scan
GET    /api/v1/scans                 # List user's scans
GET    /api/v1/scans/{id}            # Get scan details
DELETE /api/v1/scans/{id}            # Delete scan
GET    /api/v1/scans/{id}/issues     # Get issues (paginated)
GET    /api/v1/scans/{id}/report     # Generate PDF report
GET    /api/v1/scans/{id}/progress   # SSE for real-time updates
```

#### Users

```
GET    /api/v1/users/me              # Get current user
PATCH  /api/v1/users/me              # Update profile
DELETE /api/v1/users/me              # Delete account
GET    /api/v1/users/me/usage        # Get usage stats
```

#### Billing

```
GET    /api/v1/billing/plans         # List available plans
POST   /api/v1/billing/checkout      # Create Stripe checkout
GET    /api/v1/billing/subscription  # Get current subscription
POST   /api/v1/billing/portal        # Stripe customer portal
POST   /api/v1/billing/webhook       # Stripe webhooks
```

### Request/Response Examples

#### Start Scan

**Request:**
```json
POST /api/v1/scans
Authorization: Bearer <token>

{
  "url": "https://example.de",
  "crawl": true,
  "max_pages": 100
}
```

**Response:**
```json
{
  "scan_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "url": "https://example.de",
  "crawl": true,
  "max_pages": 100,
  "estimated_time_seconds": 120,
  "created_at": "2025-01-15T10:30:00Z"
}
```

#### Get Issues

**Request:**
```
GET /api/v1/scans/{scan_id}/issues?page=1&per_page=20&impact=critical,serious
```

**Response:**
```json
{
  "issues": [
    {
      "id": "issue-uuid",
      "rule_id": "color-contrast",
      "wcag_criteria": ["1.4.3"],
      "bfsg_reference": "§3 Abs. 2 Nr. 1 BFSG, Anlage 1 Abschnitt I",
      "impact": "serious",
      "title_de": "Unzureichender Farbkontrast",
      "description_de": "Der Kontrast zwischen Vordergrund- und Hintergrundfarbe ist für normale Textgröße zu gering.",
      "fix_suggestion_de": "Erhöhen Sie den Kontrast auf mindestens 4.5:1. Verwenden Sie einen Kontrastrechner.",
      "element": {
        "selector": "#header > nav > a.menu-link",
        "html_snippet": "<a class=\"menu-link\" style=\"color: #999\">Kontakt</a>"
      },
      "page_url": "https://example.de/",
      "screenshot_url": "https://storage.example.de/screenshots/abc123.png"
    }
  ],
  "total": 234,
  "page": 1,
  "per_page": 20,
  "pages": 12
}
```

---

## WCAG Testing Engine

### axe-core Integration

AccessibilityChecker uses [axe-core](https://github.com/dequelabs/axe-core) as its accessibility testing engine. axe-core is the industry standard, used by Microsoft, Google, and other major companies.

### Test Execution Flow

```typescript
// Simplified scan execution
async function scanPage(url: string): Promise<ScanResult> {
  const browser = await puppeteer.launch({ headless: true });
  const page = await browser.newPage();

  await page.goto(url, { waitUntil: 'networkidle2' });

  // Inject axe-core
  await page.addScriptTag({ path: require.resolve('axe-core') });

  // Run accessibility tests
  const results = await page.evaluate(async () => {
    return await axe.run(document, {
      runOnly: ['wcag2a', 'wcag2aa'],
      resultTypes: ['violations', 'passes', 'incomplete']
    });
  });

  await browser.close();

  return mapResultsToGerman(results);
}
```

### WCAG Coverage

| Category | Criteria | Automatable | Coverage |
|----------|----------|-------------|----------|
| Fully Automated | Contrast, alt text presence, form labels | 100% | ~25 criteria |
| Partially Automated | Link text, heading structure, focus order | ~70% | ~15 criteria |
| Manual Required | Caption quality, timing, consistency | 0% | ~10 criteria |

**Note:** Automated tests detect approximately 40% of WCAG issues. Full compliance requires additional manual testing.

### German Rule Translations

Each axe-core rule is mapped to German translations and BFSG references:

```json
{
  "color-contrast": {
    "rule_id": "color-contrast",
    "wcag_criteria": ["1.4.3"],
    "bfsg_reference": "§3 Abs. 2 Nr. 1 BFSG, Anlage 1 Abschnitt I",
    "title_de": "Unzureichender Farbkontrast",
    "description_de": "Der Kontrast zwischen Vordergrund- und Hintergrundfarbe ist für normale Textgröße zu gering.",
    "impact_de": "Nutzer mit Sehbeeinträchtigungen können den Text nicht lesen.",
    "fix_de": "Erhöhen Sie den Kontrast auf mindestens 4.5:1. Verwenden Sie einen Kontrastrechner wie WebAIM.",
    "code_example": "color: #333; background: #fff; /* 12.6:1 Kontrast */"
  }
}
```

### Compliance Score Calculation

```
Score = (Passed Rules / Applicable Rules) × 100

Weighted by impact:
- Critical:  ×3
- Serious:   ×2
- Moderate:  ×1
- Minor:     ×0.5

Score Ranges:
- 90-100%: Good (green)
- 70-89%:  Needs improvement (yellow)
- <70%:    Critical (red)
```

---

## Deployment

### Docker Compose (Development)

```yaml
version: '3.8'

services:
  api:
    build: ./api
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@postgres:5432/accessibilitychecker
      - REDIS_URL=redis://redis:6379
    depends_on:
      - postgres
      - redis

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"

  scanner:
    build: ./scanner
    environment:
      - REDIS_URL=redis://redis:6379
    depends_on:
      - redis
    deploy:
      replicas: 2

  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: accessibilitychecker
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

  minio:
    image: minio/minio
    command: server /data --console-address ":9001"
    ports:
      - "9000:9000"
      - "9001:9001"
    volumes:
      - minio_data:/data

volumes:
  postgres_data:
  redis_data:
  minio_data:
```

### CI/CD Pipeline (GitHub Actions)

```yaml
name: CI/CD

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run API tests
        run: |
          cd api
          pip install -r requirements.txt
          pytest
      - name: Run Frontend tests
        run: |
          cd frontend
          npm ci
          npm test
      - name: Run Scanner tests
        run: |
          cd scanner
          npm ci
          npm test

  deploy:
    needs: test
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to production
        run: |
          # SSH deploy to Hetzner
          # Docker pull & restart
```

---

## Monitoring & Observability

### Metrics (Prometheus + Grafana)

- Request latency (p50, p95, p99)
- Scan duration
- Queue depth
- Error rates
- Active users
- Resource utilization

### Error Tracking (Sentry)

- API exceptions
- Frontend errors
- Worker failures
- Performance issues

### Logging

- Structured JSON logging
- Request/response logging
- Scan job logging
- Audit trail for security events

---

## Next Steps

1. **Phase 0 (Week 1):** Setup repository, CI/CD, infrastructure
2. **Phase 1 (Week 2-3):** Implement scan engine (Puppeteer + axe-core)
3. **Phase 2 (Week 3-4):** German translations and BFSG mapping
4. **Phase 3 (Week 4-5):** Frontend development
5. **Phase 4 (Week 5-6):** Reporting and billing
6. **Phase 5 (Week 6-7):** Polish and beta testing
7. **V1.0 (Week 8):** Public launch
