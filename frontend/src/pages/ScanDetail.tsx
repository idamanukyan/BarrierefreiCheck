/**
 * Scan Detail Page
 *
 * Shows detailed scan results with issues, pages, and export options.
 */

import React, { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from '../hooks/useTranslation';
import { scansApi } from '../services/api';
import { Card, CardContent, Button, StatusBadge, ScoreBadge, Alert } from '../components/common';
import {
  ScanProgress,
  ScanSummaryTab,
  ScanIssuesTab,
  ScanPagesTab,
} from '../components/scan';

// Icons
const ArrowLeftIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
  </svg>
);

const DownloadIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
  </svg>
);

// Tab type
type TabType = 'summary' | 'issues' | 'pages';

// Skeleton loader
const ScanDetailSkeleton: React.FC = () => (
  <div className="space-y-6 animate-pulse" aria-busy="true" aria-label="Loading scan details">
    <div className="h-8 bg-gray-200 rounded w-1/3" />
    <div className="h-4 bg-gray-200 rounded w-1/2" />
    <div className="h-10 bg-gray-200 rounded w-full" />
    <div className="grid grid-cols-2 gap-6">
      <div className="h-48 bg-gray-200 rounded-lg" />
      <div className="h-48 bg-gray-200 rounded-lg" />
    </div>
  </div>
);

// Running scan statuses
const RUNNING_STATUSES = ['queued', 'crawling', 'scanning', 'processing'];

const ScanDetail: React.FC = () => {
  const { scanId } = useParams<{ scanId: string }>();
  const { t } = useTranslation();
  const [activeTab, setActiveTab] = useState<TabType>('summary');

  const { data: scan, isLoading, error } = useQuery({
    queryKey: ['scan', scanId],
    queryFn: () => scansApi.get(scanId!),
    enabled: !!scanId,
    refetchInterval: (query) => {
      const data = query.state.data;
      // Poll while scan is in progress
      if (data && RUNNING_STATUSES.includes(data.status)) {
        return 3000;
      }
      return false;
    },
  });

  if (isLoading) {
    return <ScanDetailSkeleton />;
  }

  if (error || !scan) {
    return (
      <Alert variant="error" title={t('errors.notFound')}>
        {t('errors.generic')}
      </Alert>
    );
  }

  const isRunning = RUNNING_STATUSES.includes(scan.status);

  return (
    <div className="space-y-6">
      {/* Header */}
      <header className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <Link
              to="/scans"
              className="text-gray-400 hover:text-gray-600"
              aria-label={t('common.back')}
            >
              <ArrowLeftIcon className="h-5 w-5" />
            </Link>
            <h1 className="text-2xl font-bold text-gray-900">
              {t('scan.detail.title')}
            </h1>
          </div>
          <p className="mt-1 text-gray-500">{scan.url}</p>
        </div>
        <div className="flex items-center gap-3">
          <StatusBadge status={scan.status} />
          {scan.score !== undefined && <ScoreBadge score={scan.score} size="lg" />}
          {!isRunning && (
            <Button variant="outline" icon={<DownloadIcon className="h-5 w-5" />}>
              {t('scan.detail.exportReport')}
            </Button>
          )}
        </div>
      </header>

      {/* Progress bar for running scans */}
      {isRunning && scan.progress && (
        <Card>
          <CardContent>
            <ScanProgress progress={scan.progress} />
          </CardContent>
        </Card>
      )}

      {/* Tabs */}
      {!isRunning && (
        <>
          <nav className="border-b border-gray-200" aria-label={t('scan.detail.tabs')}>
            <div className="flex gap-4" role="tablist">
              {(['summary', 'issues', 'pages'] as const).map((tab) => (
                <button
                  key={tab}
                  role="tab"
                  aria-selected={activeTab === tab}
                  aria-controls={`tabpanel-${tab}`}
                  id={`tab-${tab}`}
                  onClick={() => setActiveTab(tab)}
                  className={`py-3 px-1 border-b-2 font-medium text-sm transition-colors ${
                    activeTab === tab
                      ? 'border-blue-500 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700'
                  }`}
                >
                  {tab === 'summary' && t('scan.detail.summary')}
                  {tab === 'issues' && `${t('scan.detail.issues')} (${scan.issuesCount || 0})`}
                  {tab === 'pages' && `${t('scan.detail.pages')} (${scan.pagesScanned || 0})`}
                </button>
              ))}
            </div>
          </nav>

          {/* Tab panels */}
          <div
            role="tabpanel"
            id={`tabpanel-${activeTab}`}
            aria-labelledby={`tab-${activeTab}`}
          >
            {activeTab === 'summary' && <ScanSummaryTab scan={scan} />}
            {activeTab === 'issues' && <ScanIssuesTab scanId={scanId!} />}
            {activeTab === 'pages' && <ScanPagesTab scan={scan} />}
          </div>
        </>
      )}
    </div>
  );
};

export default ScanDetail;
