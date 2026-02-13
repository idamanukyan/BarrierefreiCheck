# Contributing to AccessibilityChecker

Thank you for your interest in contributing to AccessibilityChecker! This document provides guidelines and instructions for contributing.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Pull Request Process](#pull-request-process)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Documentation](#documentation)

## Code of Conduct

By participating in this project, you agree to maintain a respectful and inclusive environment. We expect all contributors to:

- Be respectful and considerate in all interactions
- Welcome newcomers and help them get started
- Focus on constructive feedback
- Accept responsibility for mistakes and learn from them

## Getting Started

### Prerequisites

- Node.js 20 LTS
- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- Docker & Docker Compose

### Fork and Clone

1. Fork the repository on GitHub
2. Clone your fork locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/accessibilitychecker.git
   cd accessibilitychecker
   ```
3. Add the upstream repository:
   ```bash
   git remote add upstream https://github.com/ORIGINAL_OWNER/accessibilitychecker.git
   ```

## Development Setup

### Quick Start with Docker

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f
```

### Manual Setup

1. **API (Python/FastAPI)**
   ```bash
   cd api
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   pip install -r requirements.txt

   # Run database migrations
   alembic upgrade head

   # Start the server
   uvicorn app.main:app --reload
   ```

2. **Scanner (Node.js)**
   ```bash
   cd scanner
   npm install
   npm run dev
   ```

3. **Frontend (React)**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

### Environment Configuration

Copy `.env.example` to `.env` and configure the required variables:

```bash
cp .env.example .env
```

See the [README](README.md#environment-variables) for details on each variable.

## Making Changes

### Branch Naming

Use descriptive branch names with the following prefixes:

- `feature/` - New features (e.g., `feature/add-pdf-export`)
- `fix/` - Bug fixes (e.g., `fix/scan-timeout-issue`)
- `docs/` - Documentation changes (e.g., `docs/update-api-reference`)
- `refactor/` - Code refactoring (e.g., `refactor/simplify-auth-flow`)
- `test/` - Test additions/changes (e.g., `test/add-scanner-tests`)

### Commit Messages

Follow conventional commit format:

```
type(scope): brief description

[optional body with more details]

[optional footer with breaking changes or issue references]
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Code style (formatting, no logic change)
- `refactor`: Code refactoring
- `test`: Adding/updating tests
- `chore`: Build, CI, dependencies

**Examples:**
```
feat(scanner): add support for custom scan rules

fix(api): handle timeout in scan queue

docs(readme): update installation instructions
```

### Keep Commits Focused

- Each commit should represent a single logical change
- Avoid mixing unrelated changes in one commit
- Write meaningful commit messages

## Pull Request Process

1. **Update your fork**
   ```bash
   git fetch upstream
   git checkout main
   git merge upstream/main
   ```

2. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Make your changes**
   - Write code
   - Add tests
   - Update documentation if needed

4. **Run tests locally**
   ```bash
   # API tests
   cd api && pytest

   # Frontend tests
   cd frontend && npm run test

   # Scanner tests
   cd scanner && npm run test
   ```

5. **Push and create PR**
   ```bash
   git push origin feature/your-feature-name
   ```
   Then create a Pull Request on GitHub.

### PR Requirements

- [ ] Tests pass (CI must be green)
- [ ] Code follows project style guidelines
- [ ] Documentation is updated if needed
- [ ] Commit messages follow conventions
- [ ] PR description explains the changes

### PR Review

- All PRs require at least one approval
- Address review feedback promptly
- Keep discussions constructive

## Coding Standards

### Python (API)

- Follow PEP 8 style guide
- Use type hints for function signatures
- Use Ruff for linting and formatting:
  ```bash
  ruff check .
  ruff format .
  ```
- Use mypy for type checking:
  ```bash
  mypy app --ignore-missing-imports
  ```

### TypeScript (Frontend/Scanner)

- Use ESLint and Prettier:
  ```bash
  npm run lint
  npm run format
  ```
- Prefer functional components with hooks
- Use TypeScript strict mode
- Avoid `any` types

### General Guidelines

- Write self-documenting code with clear names
- Keep functions small and focused
- Handle errors appropriately
- Avoid premature optimization
- Don't over-engineer solutions

## Testing

### Test Requirements

- All new features must include tests
- Bug fixes should include regression tests
- Maintain or improve code coverage

### Running Tests

```bash
# API (Python)
cd api
pytest tests/ -v --cov=app

# Frontend (React)
cd frontend
npm run test

# Scanner (Node.js)
cd scanner
npm run test
```

### Test Structure

- Unit tests for individual functions/components
- Integration tests for API endpoints
- E2E tests for critical user flows

## Documentation

### When to Update Docs

- Adding new features
- Changing API endpoints
- Modifying configuration options
- Updating installation steps

### Documentation Files

- `README.md` - Project overview and quick start
- `ARCHITECTURE.md` - System architecture details
- `SECURITY.md` - Security policies
- `CONTRIBUTING.md` - This file
- `docs/` - Additional documentation

### API Documentation

API documentation is auto-generated from code:
- FastAPI endpoints at `/api/docs` (Swagger UI)
- OpenAPI schema at `/api/openapi.json`

## Questions?

- Check existing [issues](https://github.com/OWNER/accessibilitychecker/issues)
- Open a new issue for bugs or feature requests
- Contact maintainers at idamyan01@gmail.com

Thank you for contributing!
