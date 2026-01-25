# AccessibilityChecker

**BFSG Compliance & WCAG 2.1 Testing Platform for German Businesses & Web Agencies**

> Check German BFSG compliance in 5 minutes - not 5 days.

## Overview

AccessibilityChecker is a web-based SaaS platform that enables German businesses and web agencies to:
- Automatically test websites for WCAG 2.1 AA compliance
- Generate German-language compliance reports with BFSG mapping
- Track remediation progress with actionable fix instructions

### The Problem

Germany's Accessibility Strengthening Act (BFSG) requires all businesses offering digital products and services to consumers to comply with accessibility standards (EN 301 549 / WCAG 2.1 Level AA) by **June 28, 2025**. According to Aktion Mensch's 2024 study, only 2.5% of German corporate websites currently meet these requirements.

**Non-compliance penalties:** Up to €100,000 per violation

### Key Features

- **BFSG Focus:** Explicit mapping of WCAG criteria to legal BFSG requirements
- **German-First:** Fully German interface, error reports, and remediation guides
- **Agency-Friendly:** White-label reports, multi-client management, reseller program
- **Affordable:** Starting at €49/month vs. €10,000+/year for enterprise solutions
- **Actionable:** Concrete code examples and priority rankings for efficient remediation

## Tech Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| Frontend | React 18 + TypeScript | User interface, dashboard |
| UI Framework | Tailwind CSS 3 | Styling |
| Charts | Recharts | Data visualization |
| Backend API | Python FastAPI | REST API, authentication |
| Scan Engine | Node.js 20 LTS | Puppeteer coordination |
| Browser Automation | Puppeteer | Headless Chrome |
| A11y Testing | axe-core | WCAG rule engine |
| Database | PostgreSQL 15+ | Primary data store |
| Cache/Queue | Redis + BullMQ | Job queue system |
| Object Storage | MinIO (S3-API) | Screenshots, PDFs |
| PDF Generation | Puppeteer/PDFKit | Report generation |
| Payments | Stripe | Subscription billing |
| Hosting | Hetzner Cloud | German/EU GDPR-compliant |

## Project Structure

```
accessibilitychecker/
├── frontend/           # React SPA
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── hooks/
│   │   ├── services/
│   │   └── utils/
│   └── package.json
├── api/                # FastAPI Backend
│   ├── app/
│   │   ├── routers/
│   │   ├── models/
│   │   ├── services/
│   │   └── utils/
│   ├── alembic/        # DB migrations
│   └── requirements.txt
├── scanner/            # Node.js Scan Workers
│   ├── src/
│   │   ├── crawler/
│   │   ├── axe/
│   │   ├── workers/
│   │   └── utils/
│   └── package.json
├── shared/             # Shared resources
│   └── translations/   # German rule translations
├── infrastructure/     # Docker, CI/CD
│   ├── docker/
│   └── k8s/
├── docs/               # Documentation
└── docker-compose.yml
```

## Getting Started

### Prerequisites

- Node.js 20 LTS
- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- Docker & Docker Compose

### Local Development

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/accessibilitychecker.git
cd accessibilitychecker

# Start infrastructure services
docker-compose up -d postgres redis minio

# Setup API
cd api
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload

# Setup Scanner (new terminal)
cd scanner
npm install
npm run dev

# Setup Frontend (new terminal)
cd frontend
npm install
npm run dev
```

### Environment Variables

Copy `.env.example` to `.env` and configure:

```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/accessibilitychecker

# Redis
REDIS_URL=redis://localhost:6379

# MinIO/S3
S3_ENDPOINT=http://localhost:9000
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin

# Stripe
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...

# JWT
JWT_SECRET=your-secret-key
JWT_ALGORITHM=HS256
```

## API Endpoints

### Scans

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/scans` | Start new accessibility scan |
| GET | `/api/v1/scans/{id}` | Get scan status and results |
| GET | `/api/v1/scans/{id}/report` | Generate PDF report |
| GET | `/api/v1/scans/{id}/issues` | List all issues (paginated) |

### Example: Start a Scan

```bash
curl -X POST https://api.accessibilitychecker.de/api/v1/scans \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.de", "crawl": true, "max_pages": 100}'
```

## Pricing Tiers

| Feature | Free | Starter €49/mo | Professional €99/mo | Agency €249/mo |
|---------|------|----------------|---------------------|----------------|
| Pages/scan | 5 | 100 | 500 | 1,000 |
| Domains | 1 | 1 | 3 | 10 |
| Scans/month | 3 | 20 | Unlimited | Unlimited |
| BFSG Reports | Watermark | Full | Full | White-label |
| Scheduled scans | - | - | Weekly | Daily |
| API access | - | - | 1,000/mo | 5,000/mo |

## Development Phases

| Phase | Focus | Timeline |
|-------|-------|----------|
| Phase 0 | Setup & Foundation | Week 1 |
| Phase 1 | Scan Engine | Week 2-3 |
| Phase 2 | German Localization | Week 3-4 |
| Phase 3 | Frontend & Dashboard | Week 4-5 |
| Phase 4 | Reporting & Billing | Week 5-6 |
| Phase 5 | Polish & Beta | Week 6-7 |
| V1.0 | Public Launch | Week 8 |

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is proprietary software. All rights reserved.

## Contact

For questions or support, please contact [your-email@example.com]

---

**BFSG Deadline: June 28, 2025** - Start checking your website accessibility today!
