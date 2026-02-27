/**
 * Shared Report Page
 *
 * Public page for viewing shared reports without authentication.
 */

import React from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from '../hooks/useTranslation';
import { shareLinksApi } from '../services/api';
import { Card, CardHeader, CardTitle, CardContent, Badge, Button } from '../components/common';

const SharedReport: React.FC = () => {
  const { t } = useTranslation();
  const { token } = useParams<{ token: string }>();

  const { data, isLoading, error } = useQuery({
    queryKey: ['shared-report', token],
    queryFn: () => shareLinksApi.getShared(token || ''),
    enabled: !!token,
    retry: false,
  });

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error) {
    const errorMessage = (error as any)?.response?.status === 410
      ? t('shared.expired')
      : t('shared.notFound');

    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
        <Card className="max-w-md w-full text-center">
          <CardContent className="py-12">
            <ErrorIcon className="h-16 w-16 text-gray-400 mx-auto mb-4" />
            <h1 className="text-xl font-semibold text-gray-900 mb-2">{errorMessage}</h1>
            <p className="text-gray-600 mb-6">{t('shared.errorDescription')}</p>
            <Link to="/">
              <Button>{t('shared.goHome')}</Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (!data) return null;

  const { report, scan, shared_by, expires_at } = data;
  const expiresDate = new Date(expires_at);
  const daysUntilExpiry = Math.ceil((expiresDate.getTime() - Date.now()) / (1000 * 60 * 60 * 24));

  const getScoreColor = (score: number | null) => {
    if (score === null) return 'text-gray-500';
    if (score >= 90) return 'text-green-600';
    if (score >= 70) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getScoreLabel = (score: number | null) => {
    if (score === null) return t('shared.noScore');
    if (score >= 90) return t('results.summary.scoreExcellent');
    if (score >= 70) return t('results.summary.scoreGood');
    if (score >= 50) return t('results.summary.scoreFair');
    return t('results.summary.scorePoor');
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b">
        <div className="max-w-4xl mx-auto px-4 py-4 flex justify-between items-center">
          <div className="flex items-center space-x-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-600 text-white font-bold text-sm">
              BC
            </div>
            <span className="font-semibold text-gray-900">{t('common.appName')}</span>
          </div>
          <Badge variant="info">
            {t('shared.expiresIn', { days: daysUntilExpiry })}
          </Badge>
        </div>
      </header>

      {/* Content */}
      <main className="max-w-4xl mx-auto px-4 py-8 space-y-6">
        {/* Title Card */}
        <Card>
          <CardHeader>
            <div className="flex justify-between items-start">
              <div>
                <CardTitle>{t('shared.title')}</CardTitle>
                {shared_by && (
                  <p className="text-sm text-gray-600 mt-1">
                    {t('shared.sharedBy')}: {shared_by}
                  </p>
                )}
              </div>
              <div className="text-right">
                <div className={`text-3xl font-bold ${getScoreColor(scan.score)}`}>
                  {scan.score !== null ? `${Math.round(scan.score)}%` : '-'}
                </div>
                <div className={`text-sm ${getScoreColor(scan.score)}`}>
                  {getScoreLabel(scan.score)}
                </div>
              </div>
            </div>
          </CardHeader>
        </Card>

        {/* Scan Details */}
        <Card>
          <CardHeader>
            <CardTitle>{t('shared.scanDetails')}</CardTitle>
          </CardHeader>
          <CardContent>
            <dl className="grid grid-cols-2 gap-4">
              <div>
                <dt className="text-sm text-gray-500">{t('shared.website')}</dt>
                <dd className="font-medium text-gray-900 truncate">
                  <a
                    href={scan.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-600 hover:underline"
                  >
                    {scan.url}
                  </a>
                </dd>
              </div>
              <div>
                <dt className="text-sm text-gray-500">{t('shared.pagesScanned')}</dt>
                <dd className="font-medium text-gray-900">{scan.pages_scanned}</dd>
              </div>
              <div>
                <dt className="text-sm text-gray-500">{t('shared.issuesFound')}</dt>
                <dd className="font-medium text-gray-900">{scan.issues_count}</dd>
              </div>
              <div>
                <dt className="text-sm text-gray-500">{t('shared.scannedAt')}</dt>
                <dd className="font-medium text-gray-900">
                  {scan.completed_at
                    ? new Date(scan.completed_at).toLocaleDateString()
                    : '-'}
                </dd>
              </div>
            </dl>
          </CardContent>
        </Card>

        {/* Report Info */}
        <Card>
          <CardHeader>
            <CardTitle>{t('shared.reportInfo')}</CardTitle>
          </CardHeader>
          <CardContent>
            <dl className="grid grid-cols-2 gap-4">
              <div>
                <dt className="text-sm text-gray-500">{t('shared.format')}</dt>
                <dd className="font-medium text-gray-900 uppercase">{report.format}</dd>
              </div>
              <div>
                <dt className="text-sm text-gray-500">{t('shared.language')}</dt>
                <dd className="font-medium text-gray-900">
                  {report.language === 'de' ? 'Deutsch' : 'English'}
                </dd>
              </div>
            </dl>
          </CardContent>
        </Card>

        {/* CTA Card */}
        <Card className="bg-blue-50 border-blue-200">
          <CardContent className="py-8 text-center">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              {t('shared.ctaTitle')}
            </h3>
            <p className="text-gray-600 mb-4">{t('shared.ctaDescription')}</p>
            <Link to="/register">
              <Button>{t('shared.ctaButton')}</Button>
            </Link>
          </CardContent>
        </Card>

        {/* Footer */}
        <footer className="text-center text-sm text-gray-500 py-4">
          <p>{t('shared.linkExpires', { date: expiresDate.toLocaleDateString() })}</p>
        </footer>
      </main>
    </div>
  );
};

// Error Icon
const ErrorIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth={2}
      d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
    />
  </svg>
);

export default SharedReport;
