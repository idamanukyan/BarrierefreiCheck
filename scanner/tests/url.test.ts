/**
 * URL Validation and SSRF Protection Tests
 *
 * Tests for URL validation, normalization, and security checks.
 */

import { describe, it, expect } from 'vitest';
import {
  validateUrl,
  validateUrlWithSSRFProtection,
  isPrivateIP,
  shouldSkipUrl,
  isSameDomain,
  resolveUrl,
} from '../src/utils/url.js';

describe('validateUrl', () => {
  describe('valid URLs', () => {
    it('should accept valid HTTPS URLs', () => {
      const result = validateUrl('https://example.com');
      expect(result.valid).toBe(true);
      expect(result.url?.normalized).toBe('https://example.com/');
    });

    it('should accept valid HTTP URLs', () => {
      const result = validateUrl('http://example.com');
      expect(result.valid).toBe(true);
      expect(result.url?.protocol).toBe('http:');
    });

    it('should add https:// to URLs without protocol', () => {
      const result = validateUrl('example.com');
      expect(result.valid).toBe(true);
      expect(result.url?.normalized).toContain('https://');
    });

    it('should accept URLs with paths', () => {
      const result = validateUrl('https://example.com/path/to/page');
      expect(result.valid).toBe(true);
      expect(result.url?.pathname).toBe('/path/to/page');
    });

    it('should accept URLs with query strings', () => {
      const result = validateUrl('https://example.com/search?q=test');
      expect(result.valid).toBe(true);
      expect(result.url?.search).toBe('?q=test');
    });

    it('should accept URLs with ports', () => {
      const result = validateUrl('https://example.com:8080');
      expect(result.valid).toBe(true);
      expect(result.url?.port).toBe('8080');
    });

    it('should accept international domain names', () => {
      const result = validateUrl('https://münchen.de');
      expect(result.valid).toBe(true);
    });

    it('should trim whitespace', () => {
      const result = validateUrl('  https://example.com  ');
      expect(result.valid).toBe(true);
    });
  });

  describe('invalid URLs', () => {
    it('should reject empty URLs', () => {
      const result = validateUrl('');
      expect(result.valid).toBe(false);
      expect(result.error).toContain('empty');
    });

    it('should reject localhost', () => {
      const result = validateUrl('http://localhost');
      expect(result.valid).toBe(false);
      expect(result.error).toContain('not allowed');
    });

    it('should reject localhost with port', () => {
      const result = validateUrl('http://localhost:3000');
      expect(result.valid).toBe(false);
    });

    it('should reject 127.0.0.1', () => {
      const result = validateUrl('http://127.0.0.1');
      expect(result.valid).toBe(false);
    });

    it('should reject private IP 10.x.x.x', () => {
      const result = validateUrl('http://10.0.0.1');
      expect(result.valid).toBe(false);
      expect(result.error).toContain('private');
    });

    it('should reject private IP 172.16.x.x', () => {
      const result = validateUrl('http://172.16.0.1');
      expect(result.valid).toBe(false);
    });

    it('should reject private IP 192.168.x.x', () => {
      const result = validateUrl('http://192.168.1.1');
      expect(result.valid).toBe(false);
    });

    it('should reject ftp:// protocol', () => {
      const result = validateUrl('ftp://example.com');
      expect(result.valid).toBe(false);
      expect(result.error).toContain('protocol');
    });

    it('should reject javascript: URLs', () => {
      const result = validateUrl('javascript:alert(1)');
      expect(result.valid).toBe(false);
    });

    it('should reject data: URLs', () => {
      const result = validateUrl('data:text/html,<h1>Hi</h1>');
      expect(result.valid).toBe(false);
    });
  });

  describe('SSRF protection - blocked hostnames', () => {
    it('should reject metadata.google.internal', () => {
      const result = validateUrl('http://metadata.google.internal');
      expect(result.valid).toBe(false);
    });

    it('should reject AWS metadata IP 169.254.169.254', () => {
      const result = validateUrl('http://169.254.169.254');
      expect(result.valid).toBe(false);
    });

    it('should reject kubernetes.default', () => {
      const result = validateUrl('http://kubernetes.default');
      expect(result.valid).toBe(false);
    });
  });
});

describe('isPrivateIP', () => {
  describe('IPv4 private ranges', () => {
    it('should detect 10.x.x.x as private', () => {
      expect(isPrivateIP('10.0.0.1')).toBe(true);
      expect(isPrivateIP('10.255.255.255')).toBe(true);
    });

    it('should detect 172.16-31.x.x as private', () => {
      expect(isPrivateIP('172.16.0.1')).toBe(true);
      expect(isPrivateIP('172.31.255.255')).toBe(true);
    });

    it('should NOT detect 172.32.x.x as private', () => {
      expect(isPrivateIP('172.32.0.1')).toBe(false);
    });

    it('should detect 192.168.x.x as private', () => {
      expect(isPrivateIP('192.168.0.1')).toBe(true);
      expect(isPrivateIP('192.168.255.255')).toBe(true);
    });

    it('should detect 127.x.x.x (loopback) as private', () => {
      expect(isPrivateIP('127.0.0.1')).toBe(true);
      expect(isPrivateIP('127.255.255.255')).toBe(true);
    });

    it('should detect link-local 169.254.x.x as private', () => {
      expect(isPrivateIP('169.254.1.1')).toBe(true);
      expect(isPrivateIP('169.254.169.254')).toBe(true); // AWS metadata
    });

    it('should NOT detect public IPs as private', () => {
      expect(isPrivateIP('8.8.8.8')).toBe(false);
      expect(isPrivateIP('1.1.1.1')).toBe(false);
      expect(isPrivateIP('93.184.216.34')).toBe(false); // example.com
    });
  });

  describe('IPv6 private ranges', () => {
    it('should detect ::1 (loopback) as private', () => {
      expect(isPrivateIP('::1')).toBe(true);
    });

    it('should detect unique local addresses (fc00::/7) as private', () => {
      expect(isPrivateIP('fc00::1')).toBe(true);
      expect(isPrivateIP('fd00::1')).toBe(true);
    });

    it('should detect link-local (fe80::/10) as private', () => {
      expect(isPrivateIP('fe80::1')).toBe(true);
    });

    it('should detect IPv4-mapped IPv6 with private IPv4', () => {
      expect(isPrivateIP('::ffff:192.168.1.1')).toBe(true);
      expect(isPrivateIP('::ffff:10.0.0.1')).toBe(true);
    });

    it('should NOT detect IPv4-mapped IPv6 with public IPv4 as private', () => {
      expect(isPrivateIP('::ffff:8.8.8.8')).toBe(false);
    });
  });
});

describe('shouldSkipUrl', () => {
  it('should skip mailto: links', () => {
    expect(shouldSkipUrl('mailto:test@example.com')).toBe(true);
  });

  it('should skip tel: links', () => {
    expect(shouldSkipUrl('tel:+1234567890')).toBe(true);
  });

  it('should skip javascript: links', () => {
    expect(shouldSkipUrl('javascript:void(0)')).toBe(true);
  });

  it('should skip data: URLs', () => {
    expect(shouldSkipUrl('data:image/png;base64,abc')).toBe(true);
  });

  it('should skip anchor-only links', () => {
    expect(shouldSkipUrl('#section')).toBe(true);
  });

  it('should skip PDF files', () => {
    expect(shouldSkipUrl('https://example.com/doc.pdf')).toBe(true);
  });

  it('should skip image files', () => {
    expect(shouldSkipUrl('https://example.com/image.jpg')).toBe(true);
    expect(shouldSkipUrl('https://example.com/image.png')).toBe(true);
    expect(shouldSkipUrl('https://example.com/image.gif')).toBe(true);
  });

  it('should skip video files', () => {
    expect(shouldSkipUrl('https://example.com/video.mp4')).toBe(true);
  });

  it('should NOT skip HTML pages', () => {
    expect(shouldSkipUrl('https://example.com/page.html')).toBe(false);
    expect(shouldSkipUrl('https://example.com/page')).toBe(false);
    expect(shouldSkipUrl('https://example.com/')).toBe(false);
  });
});

describe('isSameDomain', () => {
  it('should match same exact domain', () => {
    expect(isSameDomain('example.com', 'example.com')).toBe(true);
  });

  it('should match www and non-www', () => {
    expect(isSameDomain('www.example.com', 'example.com')).toBe(true);
    expect(isSameDomain('example.com', 'www.example.com')).toBe(true);
  });

  it('should NOT match different domains', () => {
    expect(isSameDomain('example.com', 'other.com')).toBe(false);
  });

  it('should NOT match subdomains by default', () => {
    expect(isSameDomain('sub.example.com', 'example.com')).toBe(false);
  });

  it('should be case insensitive', () => {
    expect(isSameDomain('EXAMPLE.COM', 'example.com')).toBe(true);
  });
});

describe('resolveUrl', () => {
  const baseUrl = 'https://example.com/path/page.html';

  it('should resolve absolute URLs', () => {
    expect(resolveUrl('https://other.com/page', baseUrl)).toBe('https://other.com/page');
  });

  it('should resolve protocol-relative URLs', () => {
    expect(resolveUrl('//cdn.example.com/file.js', baseUrl)).toBe('https://cdn.example.com/file.js');
  });

  it('should resolve root-relative URLs', () => {
    expect(resolveUrl('/about', baseUrl)).toBe('https://example.com/about');
  });

  it('should resolve relative URLs', () => {
    expect(resolveUrl('other.html', baseUrl)).toBe('https://example.com/path/other.html');
  });

  it('should resolve parent directory references', () => {
    expect(resolveUrl('../index.html', baseUrl)).toBe('https://example.com/index.html');
  });
});

describe('validateUrlWithSSRFProtection', () => {
  it('should accept public URLs', async () => {
    const result = await validateUrlWithSSRFProtection('https://example.com');
    expect(result.valid).toBe(true);
  });

  it('should reject URLs that resolve to private IPs', async () => {
    // This test depends on DNS resolution, so we test with known blocked hostnames
    const result = await validateUrlWithSSRFProtection('http://localhost');
    expect(result.valid).toBe(false);
  });

  it('should reject metadata endpoints', async () => {
    const result = await validateUrlWithSSRFProtection('http://169.254.169.254/latest/meta-data/');
    expect(result.valid).toBe(false);
  });
});
