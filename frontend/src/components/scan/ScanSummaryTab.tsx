/**
 * Scan Summary Tab Component
 *
 * Displays scan overview with score, issues by impact/WCAG level.
 */

import React from 'react';
import { useTranslation } from '../../hooks/useTranslation';
import { Card, CardHeader, CardTitle, CardContent, ImpactBadge, WcagBadge } from '../common';
import type { Scan } from '../../types';

interface ScanSummaryTabProps {
  scan: Scan;
}

const ScoreRing: React.FC<{ score: number }> = ({ score }) => {
  const getScoreColor = (s: number) => {
    if (s >= 90) return 'text-green-500';
    if (s >= 70) return 'text-blue-500';
    if (s >= 50) return 'text-yellow-500';
    return 'text-red-500';
  };

  return (
    <div className="relative">
      <svg className="w-32 h-32" role="img" aria-label={`Score: ${score}%`}>
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
          className={getScoreColor(score)}
          strokeWidth="10"
          strokeDasharray={`${(score / 100) * 352} 352`}
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
        <span className="text-3xl font-bold">{score || 0}%</span>
      </div>
    </div>
  );
};

const ScanSummaryTab: React.FC<ScanSummaryTabProps> = ({ scan }) => {
  const { t, formatDate, formatNumber, formatDuration } = useTranslation();

  const impactData = scan.issuesByImpact || {};
  const wcagData = scan.issuesByWcag || {};

  const getScoreMessage = (score: number) => {
    if (score >= 90) return t('results.summary.scoreExcellent');
    if (score >= 70) return t('results.summary.scoreGood');
    if (score >= 50) return t('results.summary.scoreFair');
    return t('results.summary.scorePoor');
  };

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
            <ScoreRing score={scan.score} />
          </div>
          <p className="text-center text-gray-500 mt-2">
            {getScoreMessage(scan.score)}
          </p>
        </CardContent>
      </Card>
    </div>
  );
};

export default ScanSummaryTab;
