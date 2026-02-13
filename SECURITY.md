# Security Policy

## Supported Versions

We release patches for security vulnerabilities for the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 1.x.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

We take security vulnerabilities seriously. If you discover a security issue, please report it responsibly.

### How to Report

**Please do NOT report security vulnerabilities through public GitHub issues.**

Instead, please report them via email to:

**security@accessibilitychecker.de**

Or contact the maintainer directly at:

**idamyan01@gmail.com**

### What to Include

Please include the following information in your report:

1. **Type of vulnerability** (e.g., SQL injection, XSS, authentication bypass)
2. **Location** of the affected source code (file path, line numbers if known)
3. **Step-by-step instructions** to reproduce the issue
4. **Proof of concept** or exploit code (if available)
5. **Impact assessment** - what an attacker could achieve
6. **Suggested fix** (if you have one)

### What to Expect

- **Acknowledgment**: We will acknowledge receipt of your report within 48 hours.
- **Assessment**: We will assess the vulnerability and determine its severity within 7 days.
- **Updates**: We will keep you informed of our progress.
- **Resolution**: We aim to resolve critical vulnerabilities within 30 days.
- **Credit**: We will credit you in our security advisories (unless you prefer to remain anonymous).

### Safe Harbor

We consider security research conducted in accordance with this policy to be:

- Authorized and we will not initiate legal action against you
- Exempt from our Terms of Service restrictions
- Helpful and conducted in good faith

Please make a good faith effort to avoid privacy violations, data destruction, and service disruption.

## Security Measures

### Authentication & Authorization

- JWT tokens with short expiration (15 minutes access, 7 days refresh)
- bcrypt password hashing with cost factor 12
- Role-based access control (RBAC)
- Rate limiting on authentication endpoints

### Data Protection

- HTTPS/TLS enforcement in production
- Security headers (HSTS, CSP, X-Frame-Options, etc.)
- Input validation and sanitization
- SSRF protection for URL scanning

### Infrastructure

- Non-root Docker containers
- Network isolation between services
- Resource limits and health checks
- Automated security scanning in CI/CD

## Security Best Practices for Deployment

### Environment Variables

1. **Never commit secrets** - Use `.env` files (gitignored) or secret management
2. **Use strong secrets** - Generate with `python -c "import secrets; print(secrets.token_urlsafe(32))"`
3. **Rotate regularly** - Especially JWT_SECRET and database passwords
4. **Validate in production** - Set `APP_ENV=production` to enable security checks

### Production Checklist

- [ ] All `CHANGE_ME` values replaced in configuration
- [ ] `APP_ENV` set to `production`
- [ ] `APP_DEBUG` set to `false`
- [ ] Strong JWT_SECRET (32+ characters)
- [ ] HTTPS configured with valid certificates
- [ ] CORS_ORIGINS restricted to production domains
- [ ] Database uses SSL connection
- [ ] Secrets stored in secure vault (not environment files)
- [ ] Firewall rules configured
- [ ] Regular security updates scheduled

### Monitoring

We recommend monitoring for:

- Failed authentication attempts
- Rate limit violations
- Unusual scan patterns
- Error spikes

## Dependencies

We regularly scan dependencies for vulnerabilities using:

- Trivy for container and filesystem scanning
- GitHub Dependabot for dependency updates
- pip-audit for Python packages

## Contact

For security concerns, contact:
- Email: security@accessibilitychecker.de
- Maintainer: idamyan01@gmail.com

For non-security issues, please use [GitHub Issues](https://github.com/anthropics/claude-code/issues).
