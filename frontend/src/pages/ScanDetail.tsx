/**
 * Scan Detail Page
 *
 * Shows detailed scan results with issues, pages, and export options.
 */

import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from '../hooks/useTranslation';
import { scansApi } from '../services/api';
import { Card, CardHeader, CardTitle, CardContent, Button, StatusBadge, ScoreBadge, ImpactBadge, WcagBadge, Alert } from '../components/common';
import type { Scan, Issue, Page } from '../types';

const ScanDetail: React.FC = () => {
  const { scanId } = useParams<{ scanId: string }>();
  const { t, formatDate, formatNumber, formatDuration } = useTranslation();
  const [activeTab, setActiveTab] = useState<'summary' | 'issues' | 'pages'>('summary');

  const { data: scan, isLoading, error, refetch } = useQuery({
    queryKey: ['scan', scanId],
    queryFn: () => scansApi.get(scanId!),
    enabled: !!scanId,
    refetchInterval: (data) => {
      // Poll while scan is in progress
      if (data && ['queued', 'crawling', 'scanning', 'processing'].includes(data.status)) {
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

  const isRunning = ['queued', 'crawling', 'scanning', 'processing'].includes(scan.status);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <Link to="/scans" className="text-gray-400 hover:text-gray-600">
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
      </div>

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
          <div className="border-b border-gray-200">
            <nav className="flex gap-4">
              {(['summary', 'issues', 'pages'] as const).map((tab) => (
                <button
                  key={tab}
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
            </nav>
          </div>

          {/* Tab content */}
          {activeTab === 'summary' && <SummaryTab scan={scan} />}
          {activeTab === 'issues' && <IssuesTab scanId={scanId!} />}
          {activeTab === 'pages' && <PagesTab scan={scan} />}
        </>
      )}
    </div>
  );
};

// Scan progress component
interface ScanProgressProps {
  progress: {
    stage: string;
    pagesScanned: number;
    totalPages: number;
    currentUrl?: string;
    issuesFound: number;
  };
}

const ScanProgress: React.FC<ScanProgressProps> = ({ progress }) => {
  const { t } = useTranslation();
  const percentage = progress.totalPages > 0
    ? Math.round((progress.pagesScanned / progress.totalPages) * 100)
    : 0;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="font-medium text-gray-900">{t('scan.progress.title')}</h3>
          <p className="text-sm text-gray-500">
            {t('scan.progress.stage', { stage: t(`scan.status.${progress.stage}`) })}
          </p>
        </div>
        <div className="text-right">
          <p className="text-2xl font-bold text-gray-900">{percentage}%</p>
          <p className="text-sm text-gray-500">
            {t('scan.progress.pagesScanned', {
              scanned: progress.pagesScanned,
              total: progress.totalPages,
            })}
          </p>
        </div>
      </div>

      {/* Progress bar */}
      <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
        <div
          className="h-full bg-blue-600 transition-all duration-500"
          style={{ width: `${percentage}%` }}
        />
      </div>

      {progress.currentUrl && (
        <p className="text-sm text-gray-500 truncate">
          {t('scan.progress.currentPage', { url: progress.currentUrl })}
        </p>
      )}

      <p className="text-sm text-gray-600">
        {t('scan.progress.issuesFound', { count: progress.issuesFound })}
      </p>
    </div>
  );
};

// Summary tab
const SummaryTab: React.FC<{ scan: Scan }> = ({ scan }) => {
  const { t, formatDate, formatNumber, formatDuration } = useTranslation();

  const impactData = scan.issuesByImpact || {};
  const wcagData = scan.issuesByWcag || {};

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Overview */}
      <Card>
        <CardHeader>
          <CardTitle>{t('results.summary.title')}</CardTitle>
        </CardHeader>
        <CardContent>
          <dl className="space-y-4">
            <div className="flex justify-between">
              <dt className="text-gray-500">{t('results.summary.pagesScanned')}</dt>
              <dd className="font-medium">{formatNumber(scan.pagesScanned || 0)}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-gray-500">{t('results.summary.totalIssues')}</dt>
              <dd className="font-medium">{formatNumber(scan.issuesCount || 0)}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-gray-500">{t('results.summary.scanDuration')}</dt>
              <dd className="font-medium">{formatDuration(scan.duration || 0)}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-gray-500">{t('results.summary.completedAt')}</dt>
              <dd className="font-medium">
                {scan.completedAt ? formatDate(scan.completedAt, {
                  dateStyle: 'medium',
                  timeStyle: 'short',
                }) : '-'}
              </dd>
            </div>
          </dl>
        </CardContent>
      </Card>

      {/* Issues by impact */}
      <Card>
        <CardHeader>
          <CardTitle>{t('results.issues.byImpact')}</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {(['critical', 'serious', 'moderate', 'minor'] as const).map((impact) => (
              <div key={impact} className="flex items-center justify-between">
                <ImpactBadge impact={impact} />
                <span className="font-medium">{formatNumber(impactData[impact] || 0)}</span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Issues by WCAG level */}
      <Card>
        <CardHeader>
          <CardTitle>{t('results.issues.byWcag')}</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {(['A', 'AA', 'AAA'] as const).map((level) => (
              <div key={level} className="flex items-center justify-between">
                <WcagBadge level={level} />
                <span className="font-medium">{formatNumber(wcagData[level] || 0)}</span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Score breakdown */}
      <Card>
        <CardHeader>
          <CardTitle>{t('results.summary.score')}</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center py-4">
            <div className="relative">
              <svg className="w-32 h-32">
                <circle
                  className="text-gray-200"
                  strokeWidth="10"
                  stroke="currentColor"
                  fill="transparent"
                  r="56"
                  cx="64"
                  cy="64"
                />
                <circle
                  className={`${
                    scan.score >= 90
                      ? 'text-green-500'
                      : scan.score >= 70
                      ? 'text-blue-500'
                      : scan.score >= 50
                      ? 'text-yellow-500'
                      : 'text-red-500'
                  }`}
                  strokeWidth="10"
                  strokeDasharray={`${(scan.score / 100) * 352} 352`}
                  strokeLinecap="round"
                  stroke="currentColor"
                  fill="transparent"
                  r="56"
                  cx="64"
                  cy="64"
                  transform="rotate(-90 64 64)"
                />
              </svg>
              <div className="absolute inset-0 flex items-center justify-center">
                <span className="text-3xl font-bold">{scan.score || 0}%</span>
              </div>
            </div>
          </div>
          <p className="text-center text-gray-500 mt-2">
            {scan.score >= 90
              ? t('results.summary.scoreExcellent')
              : scan.score >= 70
              ? t('results.summary.scoreGood')
              : scan.score >= 50
              ? t('results.summary.scoreFair')
              : t('results.summary.scorePoor')}
          </p>
        </CardContent>
      </Card>
    </div>
  );
};

// Issues tab
const IssuesTab: React.FC<{ scanId: string }> = ({ scanId }) => {
  const { t } = useTranslation();
  const [impactFilter, setImpactFilter] = useState<string>('all');

  const { data, isLoading } = useQuery({
    queryKey: ['scan-issues', scanId, impactFilter],
    queryFn: () =>
      scansApi.getIssues(scanId, {
        impact: impactFilter === 'all' ? undefined : impactFilter,
      }),
  });

  if (isLoading) {
    return <div className="animate-pulse space-y-4">
      {[1, 2, 3].map((i) => (
        <div key={i} className="h-32 bg-gray-100 rounded-lg" />
      ))}
    </div>;
  }

  const issues = data?.items || [];

  return (
    <div className="space-y-4">
      {/* Filter */}
      <div className="flex gap-2">
        {['all', 'critical', 'serious', 'moderate', 'minor'].map((filter) => (
          <button
            key={filter}
            onClick={() => setImpactFilter(filter)}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
              impactFilter === filter
                ? 'bg-blue-100 text-blue-700'
                : 'text-gray-600 hover:bg-gray-100'
            }`}
          >
            {filter === 'all' ? t('common.all') : t(`results.impact.${filter}`)}
          </button>
        ))}
      </div>

      {/* Issues list */}
      {issues.length === 0 ? (
        <Card className="text-center py-12">
          <p className="text-gray-500">{t('results.issues.noIssues')}</p>
        </Card>
      ) : (
        <div className="space-y-4">
          {issues.map((issue: Issue) => (
            <IssueCard key={issue.id} issue={issue} />
          ))}
        </div>
      )}
    </div>
  );
};

// Issue card component
const IssueCard: React.FC<{ issue: Issue }> = ({ issue }) => {
  const { t } = useTranslation();
  const [expanded, setExpanded] = useState(false);

  return (
    <Card>
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full text-left p-4"
      >
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-2">
              <ImpactBadge impact={issue.impact} size="sm" />
              <WcagBadge level={issue.wcagLevel} size="sm" />
            </div>
            <h3 className="font-medium text-gray-900">{issue.title}</h3>
            <p className="mt-1 text-sm text-gray-500 line-clamp-2">
              {issue.description}
            </p>
          </div>
          <ChevronIcon
            className={`h-5 w-5 text-gray-400 transform transition-transform ${
              expanded ? 'rotate-180' : ''
            }`}
          />
        </div>
      </button>

      {expanded && (
        <div className="px-4 pb-4 border-t border-gray-100 pt-4 space-y-4">
          <div>
            <h4 className="text-sm font-medium text-gray-900 mb-1">
              {t('results.issue.description')}
            </h4>
            <p className="text-sm text-gray-600">{issue.description}</p>
          </div>

          <div>
            <h4 className="text-sm font-medium text-gray-900 mb-1">
              {t('results.issue.howToFix')}
            </h4>
            <p className="text-sm text-gray-600">{issue.fix}</p>
          </div>

          {issue.element && (
            <div>
              <h4 className="text-sm font-medium text-gray-900 mb-1">
                {t('results.issue.element')}
              </h4>
              <pre className="text-xs bg-gray-100 p-3 rounded overflow-x-auto">
                {issue.element.html}
              </pre>
            </div>
          )}

          {issue.bfsgReference && (
            <div>
              <h4 className="text-sm font-medium text-gray-900 mb-1">
                {t('results.issue.bfsgReference')}
              </h4>
              <p className="text-sm text-gray-600">{issue.bfsgReference}</p>
            </div>
          )}
        </div>
      )}
    </Card>
  );
};

// Pages tab
const PagesTab: React.FC<{ scan: Scan }> = ({ scan }) => {
  const { t, formatNumber } = useTranslation();
  const pages = scan.pages || [];

  return (
    <Card padding="none">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                URL
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                {t('scan.list.columns.issues')}
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                {t('scan.list.columns.score')}
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {pages.map((page: Page, index: number) => (
              <tr key={index} className="hover:bg-gray-50">
                <td className="px-6 py-4">
                  <p className="text-sm text-gray-900 truncate max-w-md">{page.url}</p>
                  {page.title && (
                    <p className="text-xs text-gray-500 truncate">{page.title}</p>
                  )}
                </td>
                <td className="px-6 py-4 text-sm text-gray-500">
                  {formatNumber(page.issuesCount || 0)}
                </td>
                <td className="px-6 py-4">
                  {page.score !== undefined ? (
                    <ScoreBadge score={page.score} size="sm" />
                  ) : (
                    '-'
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
};

// Skeleton
const ScanDetailSkeleton: React.FC = () => (
  <div className="space-y-6 animate-pulse">
    <div className="h-8 bg-gray-200 rounded w-1/3" />
    <div className="h-4 bg-gray-200 rounded w-1/2" />
    <div className="h-10 bg-gray-200 rounded w-full" />
    <div className="grid grid-cols-2 gap-6">
      <div className="h-48 bg-gray-200 rounded-lg" />
      <div className="h-48 bg-gray-200 rounded-lg" />
    </div>
  </div>
);

// Icons
const ArrowLeftIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
  </svg>
);

const DownloadIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
  </svg>
);

const ChevronIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
  </svg>
);

export default ScanDetail;
