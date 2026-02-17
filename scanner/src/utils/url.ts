/**
 * URL Validator and Normalizer
 *
 * Handles URL validation, normalization, and domain extraction
 * for the accessibility scanner with SSRF protection.
 */

import { URL } from 'url';
import dns from 'dns';
import { promisify } from 'util';
import { logger } from './logger.js';

const dnsLookup = promisify(dns.lookup);

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

// ============================================================================
// SSRF Protection - Private/Internal IP Ranges
// ============================================================================

interface IpRange {
  start: bigint;
  end: bigint;
}

// IPv4 private/internal ranges that should be blocked
const BLOCKED_IPV4_RANGES: IpRange[] = [
  // 10.0.0.0/8 - Private Class A
  { start: ipToBigInt('10.0.0.0'), end: ipToBigInt('10.255.255.255') },
  // 172.16.0.0/12 - Private Class B
  { start: ipToBigInt('172.16.0.0'), end: ipToBigInt('172.31.255.255') },
  // 192.168.0.0/16 - Private Class C
  { start: ipToBigInt('192.168.0.0'), end: ipToBigInt('192.168.255.255') },
  // 127.0.0.0/8 - Loopback
  { start: ipToBigInt('127.0.0.0'), end: ipToBigInt('127.255.255.255') },
  // 169.254.0.0/16 - Link-local
  { start: ipToBigInt('169.254.0.0'), end: ipToBigInt('169.254.255.255') },
  // 0.0.0.0/8 - Current network
  { start: ipToBigInt('0.0.0.0'), end: ipToBigInt('0.255.255.255') },
  // 100.64.0.0/10 - Shared address space (CGN)
  { start: ipToBigInt('100.64.0.0'), end: ipToBigInt('100.127.255.255') },
  // 192.0.0.0/24 - IETF Protocol Assignments
  { start: ipToBigInt('192.0.0.0'), end: ipToBigInt('192.0.0.255') },
  // 192.0.2.0/24 - TEST-NET-1
  { start: ipToBigInt('192.0.2.0'), end: ipToBigInt('192.0.2.255') },
  // 198.51.100.0/24 - TEST-NET-2
  { start: ipToBigInt('198.51.100.0'), end: ipToBigInt('198.51.100.255') },
  // 203.0.113.0/24 - TEST-NET-3
  { start: ipToBigInt('203.0.113.0'), end: ipToBigInt('203.0.113.255') },
  // 224.0.0.0/4 - Multicast
  { start: ipToBigInt('224.0.0.0'), end: ipToBigInt('239.255.255.255') },
  // 240.0.0.0/4 - Reserved
  { start: ipToBigInt('240.0.0.0'), end: ipToBigInt('255.255.255.254') },
  // 255.255.255.255/32 - Broadcast
  { start: ipToBigInt('255.255.255.255'), end: ipToBigInt('255.255.255.255') },
];

// Blocked hostnames (metadata endpoints, localhost aliases)
const BLOCKED_HOSTNAMES = [
  'localhost',
  'localhost.localdomain',
  'ip6-localhost',
  'ip6-loopback',
  // Cloud metadata endpoints
  'metadata.google.internal',
  'metadata.google.com',
  '169.254.169.254',           // AWS/Azure/GCP metadata IP
  'instance-data',             // AWS metadata hostname
  'metadata',                  // Generic metadata
  'metadata.internal',
  // Azure specific
  '168.63.129.16',             // Azure DNS/DHCP
  // Kubernetes
  'kubernetes.default',
  'kubernetes.default.svc',
];

/**
 * Convert IPv4 address to BigInt for range comparison
 */
function ipToBigInt(ip: string): bigint {
  const parts = ip.split('.').map(Number);
  if (parts.length !== 4 || parts.some(p => isNaN(p) || p < 0 || p > 255)) {
    return BigInt(-1);
  }
  return BigInt(parts[0]) * BigInt(256 ** 3) +
         BigInt(parts[1]) * BigInt(256 ** 2) +
         BigInt(parts[2]) * BigInt(256) +
         BigInt(parts[3]);
}

/**
 * Check if an IPv4 address is in a private/internal range
 */
function isPrivateIPv4(ip: string): boolean {
  const ipNum = ipToBigInt(ip);
  if (ipNum < 0) return false;

  for (const range of BLOCKED_IPV4_RANGES) {
    if (ipNum >= range.start && ipNum <= range.end) {
      return true;
    }
  }
  return false;
}

/**
 * Check if an IPv6 address is private/internal
 */
function isPrivateIPv6(ip: string): boolean {
  const normalized = ip.toLowerCase();

  // Loopback
  if (normalized === '::1') return true;

  // IPv4-mapped IPv6 (::ffff:x.x.x.x)
  if (normalized.startsWith('::ffff:')) {
    const ipv4Part = normalized.slice(7);
    return isPrivateIPv4(ipv4Part);
  }

  // Unique local addresses (fc00::/7)
  if (normalized.startsWith('fc') || normalized.startsWith('fd')) return true;

  // Link-local (fe80::/10)
  if (normalized.startsWith('fe8') || normalized.startsWith('fe9') ||
      normalized.startsWith('fea') || normalized.startsWith('feb')) return true;

  // Multicast (ff00::/8)
  if (normalized.startsWith('ff')) return true;

  return false;
}

/**
 * Check if an IP address (IPv4 or IPv6) is private/internal
 */
export function isPrivateIP(ip: string): boolean {
  // Check if IPv6
  if (ip.includes(':')) {
    return isPrivateIPv6(ip);
  }
  return isPrivateIPv4(ip);
}

/**
 * Check if hostname is in the blocked list
 */
function isBlockedHostname(hostname: string): boolean {
  const lower = hostname.toLowerCase();
  return BLOCKED_HOSTNAMES.some(blocked =>
    lower === blocked || lower.endsWith('.' + blocked)
  );
}

/**
 * Resolve hostname and check if it resolves to a private IP (SSRF protection)
 */
export async function validateHostnameSecurity(hostname: string): Promise<{ safe: boolean; error?: string; ip?: string }> {
  // Check blocked hostnames first
  if (isBlockedHostname(hostname)) {
    logger.warn(`SSRF protection: Blocked hostname ${hostname}`);
    return { safe: false, error: `Hostname '${hostname}' is not allowed for security reasons` };
  }

  // Check if hostname is already an IP address
  if (/^\d{1,3}(\.\d{1,3}){3}$/.test(hostname)) {
    if (isPrivateIPv4(hostname)) {
      logger.warn(`SSRF protection: Blocked private IP ${hostname}`);
      return { safe: false, error: 'Scanning private/internal IP addresses is not allowed' };
    }
    return { safe: true, ip: hostname };
  }

  // Resolve hostname to IP
  try {
    const result = await dnsLookup(hostname, { all: false });
    const resolvedIP = result.address;

    if (isPrivateIP(resolvedIP)) {
      logger.warn(`SSRF protection: ${hostname} resolves to private IP ${resolvedIP}`);
      return { safe: false, error: 'The hostname resolves to a private/internal address which is not allowed' };
    }

    return { safe: true, ip: resolvedIP };
  } catch (error) {
    logger.warn(`DNS resolution failed for ${hostname}:`, error);
    return { safe: false, error: `Unable to resolve hostname '${hostname}'. Please check the URL.` };
  }
}

/**
 * Validate and parse a URL (synchronous basic validation)
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

    // Block localhost and obvious private addresses synchronously
    if (isLocalhost(parsed.hostname)) {
      return { valid: false, error: 'Localhost URLs are not allowed' };
    }

    // Block known dangerous hostnames
    if (isBlockedHostname(parsed.hostname)) {
      return { valid: false, error: `Hostname '${parsed.hostname}' is not allowed for security reasons` };
    }

    // Quick check for IP addresses that are clearly private
    if (/^\d{1,3}(\.\d{1,3}){3}$/.test(parsed.hostname) && isPrivateIPv4(parsed.hostname)) {
      return { valid: false, error: 'Scanning private/internal IP addresses is not allowed' };
    }

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
 * Validate URL with full SSRF protection including DNS resolution check.
 * This is async because it performs DNS lookups to detect DNS rebinding attacks.
 */
export async function validateUrlWithSSRFProtection(urlString: string): Promise<UrlValidationResult> {
  // First do basic validation
  const basicResult = validateUrl(urlString);
  if (!basicResult.valid || !basicResult.url) {
    return basicResult;
  }

  // Then check DNS resolution for SSRF
  const securityCheck = await validateHostnameSecurity(basicResult.url.hostname);
  if (!securityCheck.safe) {
    return { valid: false, error: securityCheck.error };
  }

  return basicResult;
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
 * Check if hostname is localhost or loopback address
 */
export function isLocalhost(hostname: string): boolean {
  const lower = hostname.toLowerCase();
  const localhostPatterns = [
    'localhost',
    'localhost.localdomain',
    '127.0.0.1',
    '::1',
    '0.0.0.0',
    '[::1]',
  ];

  // Direct match
  if (localhostPatterns.includes(lower)) {
    return true;
  }

  // Check for 127.x.x.x range
  if (/^127\.\d{1,3}\.\d{1,3}\.\d{1,3}$/.test(lower)) {
    return true;
  }

  return false;
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
