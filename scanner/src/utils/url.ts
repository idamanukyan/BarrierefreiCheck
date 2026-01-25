/**
 * URL Validator and Normalizer
 *
 * Handles URL validation, normalization, and domain extraction
 * for the accessibility scanner.
 */

import { URL } from 'url';
import { logger } from './logger.js';

export interface ParsedUrl {
  original: string;
  normalized: string;
  protocol: string;
  hostname: string;
  port: string;
  pathname: string;
  search: string;
  hash: string;
  domain: string; // hostname without 'www.'
}

export interface UrlValidationResult {
  valid: boolean;
  url?: ParsedUrl;
  error?: string;
}

// Allowed protocols for scanning
const ALLOWED_PROTOCOLS = ['http:', 'https:'];

// File extensions to skip during crawling
const SKIP_EXTENSIONS = [
  '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
  '.zip', '.rar', '.tar', '.gz', '.7z',
  '.mp3', '.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm',
  '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp', '.ico',
  '.css', '.js', '.json', '.xml', '.txt',
  '.exe', '.dmg', '.msi', '.apk', '.ipa',
];

// URL patterns to skip
const SKIP_PATTERNS = [
  /^mailto:/i,
  /^tel:/i,
  /^javascript:/i,
  /^data:/i,
  /^#/,
  /^ftp:/i,
];

/**
 * Validate and parse a URL
 */
export function validateUrl(urlString: string): UrlValidationResult {
  try {
    // Trim whitespace
    const trimmed = urlString.trim();

    if (!trimmed) {
      return { valid: false, error: 'URL cannot be empty' };
    }

    // Add protocol if missing
    let urlWithProtocol = trimmed;
    if (!trimmed.match(/^https?:\/\//i)) {
      urlWithProtocol = `https://${trimmed}`;
    }

    // Parse the URL
    const parsed = new URL(urlWithProtocol);

    // Check protocol
    if (!ALLOWED_PROTOCOLS.includes(parsed.protocol)) {
      return {
        valid: false,
        error: `Invalid protocol: ${parsed.protocol}. Only HTTP and HTTPS are supported.`,
      };
    }

    // Check for valid hostname
    if (!parsed.hostname || parsed.hostname.length === 0) {
      return { valid: false, error: 'Invalid hostname' };
    }

    // Check for localhost in production (optional - can be removed for testing)
    // if (process.env.NODE_ENV === 'production' && isLocalhost(parsed.hostname)) {
    //   return { valid: false, error: 'Localhost URLs are not allowed in production' };
    // }

    const normalizedUrl = normalizeUrl(parsed);

    return {
      valid: true,
      url: {
        original: urlString,
        normalized: normalizedUrl,
        protocol: parsed.protocol,
        hostname: parsed.hostname,
        port: parsed.port,
        pathname: parsed.pathname,
        search: parsed.search,
        hash: parsed.hash,
        domain: getDomain(parsed.hostname),
      },
    };
  } catch (error) {
    logger.debug(`URL validation failed for "${urlString}":`, error);
    return {
      valid: false,
      error: `Invalid URL format: ${urlString}`,
    };
  }
}

/**
 * Normalize a URL for consistent comparison
 */
export function normalizeUrl(url: URL | string): string {
  const parsed = typeof url === 'string' ? new URL(url) : url;

  // Remove trailing slash from pathname (except for root)
  let pathname = parsed.pathname;
  if (pathname.length > 1 && pathname.endsWith('/')) {
    pathname = pathname.slice(0, -1);
  }

  // Remove default ports
  let port = parsed.port;
  if (
    (parsed.protocol === 'https:' && port === '443') ||
    (parsed.protocol === 'http:' && port === '80')
  ) {
    port = '';
  }

  // Construct normalized URL (without hash)
  let normalized = `${parsed.protocol}//${parsed.hostname}`;
  if (port) {
    normalized += `:${port}`;
  }
  normalized += pathname;

  // Keep search params but sort them for consistency
  if (parsed.search) {
    const params = new URLSearchParams(parsed.search);
    params.sort();
    const sortedSearch = params.toString();
    if (sortedSearch) {
      normalized += `?${sortedSearch}`;
    }
  }

  return normalized.toLowerCase();
}

/**
 * Get the base domain from a hostname (removes 'www.')
 */
export function getDomain(hostname: string): string {
  return hostname.replace(/^www\./i, '').toLowerCase();
}

/**
 * Check if a URL belongs to the same domain
 */
export function isSameDomain(url1: string, url2: string): boolean {
  try {
    const parsed1 = new URL(url1);
    const parsed2 = new URL(url2);
    return getDomain(parsed1.hostname) === getDomain(parsed2.hostname);
  } catch {
    return false;
  }
}

/**
 * Check if a URL should be skipped (non-HTML resources)
 */
export function shouldSkipUrl(url: string): boolean {
  // Check skip patterns
  for (const pattern of SKIP_PATTERNS) {
    if (pattern.test(url)) {
      return true;
    }
  }

  // Check file extensions
  try {
    const parsed = new URL(url);
    const pathname = parsed.pathname.toLowerCase();
    for (const ext of SKIP_EXTENSIONS) {
      if (pathname.endsWith(ext)) {
        return true;
      }
    }
  } catch {
    // If URL parsing fails, skip it
    return true;
  }

  return false;
}

/**
 * Check if hostname is localhost
 */
export function isLocalhost(hostname: string): boolean {
  const localhostPatterns = [
    'localhost',
    '127.0.0.1',
    '::1',
    '0.0.0.0',
  ];
  return localhostPatterns.includes(hostname.toLowerCase());
}

/**
 * Resolve a relative URL against a base URL
 */
export function resolveUrl(baseUrl: string, relativeUrl: string): string | null {
  try {
    // Handle empty or invalid relative URLs
    if (!relativeUrl || relativeUrl.trim() === '') {
      return null;
    }

    // Skip URLs that should be ignored
    if (shouldSkipUrl(relativeUrl)) {
      return null;
    }

    const resolved = new URL(relativeUrl, baseUrl);

    // Only allow http(s) protocols
    if (!ALLOWED_PROTOCOLS.includes(resolved.protocol)) {
      return null;
    }

    return normalizeUrl(resolved);
  } catch {
    return null;
  }
}

/**
 * Extract all links from a list of href attributes
 */
export function extractLinks(
  baseUrl: string,
  hrefs: string[],
  sameDomainOnly: boolean = true
): string[] {
  const links = new Set<string>();
  const baseDomain = getDomain(new URL(baseUrl).hostname);

  for (const href of hrefs) {
    const resolved = resolveUrl(baseUrl, href);
    if (!resolved) continue;

    // Filter by domain if required
    if (sameDomainOnly) {
      try {
        const resolvedDomain = getDomain(new URL(resolved).hostname);
        if (resolvedDomain !== baseDomain) {
          continue;
        }
      } catch {
        continue;
      }
    }

    links.add(resolved);
  }

  return Array.from(links);
}
