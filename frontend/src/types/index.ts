/**
 * Shared Type Definitions
 *
 * Centralized TypeScript interfaces for the application.
 */

// Re-export from scanStore for backwards compatibility
export type { ScanStatus, ImpactLevel, WcagLevel } from '../store/scanStore';

// ============================================================================
// Scan Types
// ============================================================================

export interface ScanProgress {
  stage: string;
  pagesScanned: number;
  totalPages: number;
  currentUrl?: string;
  issuesFound: number;
}

export interface IssuesByImpact {
  critical: number;
  serious: number;
  moderate: number;
  minor: number;
}

export interface IssuesByWcag {
  A: number;
  AA: number;
  AAA: number;
}

export interface ElementInfo {
  selector?: string;
  html?: string;
  target?: string[];
}

export interface Issue {
  id: string;
  ruleId: string;
  impact: 'critical' | 'serious' | 'moderate' | 'minor';
  wcagCriteria?: string[];
  wcagLevel?: 'A' | 'AA' | 'AAA';
  bfsgReference?: string;
  title: string;
  description?: string;
  fix?: string;
  element?: ElementInfo;
  helpUrl?: string;
  screenshotUrl?: string;
  pageUrl?: string;
}

export interface Page {
  id: string;
  url: string;
  title?: string;
  score?: number;
  issuesCount: number;
  passedRules?: number;
  failedRules?: number;
  loadTimeMs?: number;
  scanTimeMs?: number;
  error?: string;
  scannedAt?: string;
}

export interface Scan {
  id: string;
  url: string;
  crawl: boolean;
  maxPages: number;
  status: 'queued' | 'crawling' | 'scanning' | 'processing' | 'completed' | 'failed' | 'cancelled';
  progress?: ScanProgress;
  score?: number;
  pagesScanned: number;
  issuesCount: number;
  issuesByImpact?: IssuesByImpact;
  issuesByWcag?: IssuesByWcag;
  pages?: Page[];
  createdAt: string;
  startedAt?: string;
  completedAt?: string;
  duration?: number;
  errorMessage?: string;
}

// ============================================================================
// Billing Types
// ============================================================================

export type PlanId = 'free' | 'starter' | 'professional' | 'enterprise';
export type SubscriptionStatus = 'active' | 'canceled' | 'past_due' | 'trialing' | 'inactive';

export interface Plan {
  id: PlanId;
  name: string;
  name_de: string;
  price: number;
  features_de: string[];
  features_en?: string[];
  scansPerMonth?: number;
  maxPagesPerScan?: number;
}

export interface Subscription {
  plan: PlanId;
  status: SubscriptionStatus;
  current_period_start?: string;
  current_period_end?: string;
  cancel_at_period_end?: boolean;
}

export interface Usage {
  scans_used: number;
  scans_limit: number;
  pages_scanned: number;
  reports_generated: number;
  period_start?: string;
  period_end?: string;
}

export interface Payment {
  id: string;
  amount: number;
  currency: string;
  status: 'completed' | 'pending' | 'failed' | 'refunded';
  description?: string;
  invoice_pdf_url?: string;
  created_at: string;
}

// ============================================================================
// User Types
// ============================================================================

export interface User {
  id: string;
  email: string;
  name: string;
  company?: string;
  phone?: string;
  plan: PlanId;
  createdAt: string;
  updatedAt?: string;
}

// ============================================================================
// API Types
// ============================================================================

export interface ApiError {
  detail: string;
  code?: string;
  field?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
}

// ============================================================================
// Dashboard Types
// ============================================================================

export interface DashboardStats {
  totalScans: number;
  pagesScanned: number;
  issuesFound: number;
  averageScore: number;
  recentScans: Scan[];
  issuesByImpact: IssuesByImpact;
  issuesByWcag: IssuesByWcag;
  scoreHistory: Array<{ date: string; score: number }>;
}

// ============================================================================
// Domain Types
// ============================================================================

export type DomainStatus = 'pending' | 'verified' | 'unverified';

export interface Domain {
  id: string;
  domain: string;
  display_name: string | null;
  description: string | null;
  status: DomainStatus;
  total_scans: number;
  last_scan_at: string | null;
  last_score: number | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface DomainListResponse {
  items: Domain[];
  total: number;
  limit: number;
  remaining: number;
}

export interface BulkCreateResult {
  domain: string;
  success: boolean;
  id?: string;
  error?: string;
}

export interface BulkCreateResponse {
  created: Domain[];
  errors: BulkCreateResult[];
  total_created: number;
  total_errors: number;
}

export interface BulkDeleteResponse {
  deleted_count: number;
  deleted_ids: string[];
}
