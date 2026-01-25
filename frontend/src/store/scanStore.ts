/**
 * Scan Store
 *
 * Manages scan state and real-time updates using Zustand.
 */

import { create } from 'zustand';

export type ScanStatus = 'queued' | 'crawling' | 'scanning' | 'processing' | 'completed' | 'failed' | 'cancelled';
export type ImpactLevel = 'critical' | 'serious' | 'moderate' | 'minor';
export type WcagLevel = 'A' | 'AA' | 'AAA';

export interface ScanProgress {
  stage: ScanStatus;
  pagesScanned: number;
  totalPages: number;
  currentUrl?: string;
  issuesFound: number;
}

export interface AccessibilityIssue {
  id: string;
  ruleId: string;
  impact: ImpactLevel;
  wcagLevel: WcagLevel;
  wcagCriteria: string[];
  title: string;
  description: string;
  fix: string;
  element: {
    selector: string;
    html: string;
    target: string[];
  };
  screenshotPath?: string;
  pageUrl: string;
}

export interface PageResult {
  id: string;
  url: string;
  title: string;
  score: number;
  issuesCount: number;
  scanTime: number;
  timestamp: string;
  error?: string;
}

export interface ScanSummary {
  totalPages: number;
  totalIssues: number;
  issuesByImpact: Record<ImpactLevel, number>;
  issuesByWcagLevel: Record<WcagLevel, number>;
  overallScore: number;
  scanDuration: number;
  completedAt: string;
}

export interface Scan {
  id: string;
  userId: string;
  url: string;
  status: ScanStatus;
  crawl: boolean;
  maxPages: number;
  score?: number;
  progress?: ScanProgress;
  summary?: ScanSummary;
  pages?: PageResult[];
  issues?: AccessibilityIssue[];
  error?: string;
  createdAt: string;
  updatedAt: string;
  completedAt?: string;
}

interface ScanState {
  // Current scan being viewed/monitored
  currentScan: Scan | null;
  currentScanProgress: ScanProgress | null;

  // List of user's scans
  scans: Scan[];
  scansLoading: boolean;
  scansError: string | null;

  // Pagination
  totalScans: number;
  currentPage: number;
  pageSize: number;

  // Filters
  statusFilter: ScanStatus | 'all';

  // Actions
  setCurrentScan: (scan: Scan | null) => void;
  updateScanProgress: (progress: ScanProgress) => void;
  updateScanStatus: (scanId: string, status: ScanStatus) => void;
  setScans: (scans: Scan[], total: number) => void;
  addScan: (scan: Scan) => void;
  removeScan: (scanId: string) => void;
  setScansLoading: (loading: boolean) => void;
  setScansError: (error: string | null) => void;
  setPage: (page: number) => void;
  setStatusFilter: (status: ScanStatus | 'all') => void;
  reset: () => void;
}

const initialState = {
  currentScan: null,
  currentScanProgress: null,
  scans: [],
  scansLoading: false,
  scansError: null,
  totalScans: 0,
  currentPage: 1,
  pageSize: 10,
  statusFilter: 'all' as const,
};

export const useScanStore = create<ScanState>()((set, get) => ({
  ...initialState,

  setCurrentScan: (scan) => set({ currentScan: scan }),

  updateScanProgress: (progress) => {
    set({ currentScanProgress: progress });

    // Also update the scan in the list if it exists
    const { scans, currentScan } = get();
    if (currentScan) {
      set({
        currentScan: { ...currentScan, progress, status: progress.stage },
      });
    }

    const updatedScans = scans.map((s) =>
      s.id === currentScan?.id ? { ...s, progress, status: progress.stage } : s
    );
    set({ scans: updatedScans });
  },

  updateScanStatus: (scanId, status) => {
    const { scans, currentScan } = get();

    if (currentScan?.id === scanId) {
      set({ currentScan: { ...currentScan, status } });
    }

    const updatedScans = scans.map((s) =>
      s.id === scanId ? { ...s, status } : s
    );
    set({ scans: updatedScans });
  },

  setScans: (scans, total) => set({ scans, totalScans: total }),

  addScan: (scan) => {
    const { scans, totalScans } = get();
    set({
      scans: [scan, ...scans],
      totalScans: totalScans + 1,
    });
  },

  removeScan: (scanId) => {
    const { scans, totalScans, currentScan } = get();
    set({
      scans: scans.filter((s) => s.id !== scanId),
      totalScans: Math.max(0, totalScans - 1),
      currentScan: currentScan?.id === scanId ? null : currentScan,
    });
  },

  setScansLoading: (loading) => set({ scansLoading: loading }),

  setScansError: (error) => set({ scansError: error }),

  setPage: (page) => set({ currentPage: page }),

  setStatusFilter: (status) => set({ statusFilter: status, currentPage: 1 }),

  reset: () => set(initialState),
}));
