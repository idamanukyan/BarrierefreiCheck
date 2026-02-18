/**
 * Scan Issues Tab Component
 *
 * Displays filterable list of accessibility issues.
 */

import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from '../../hooks/useTranslation';
import { scansApi } from '../../services/api';
import { Card } from '../common';
import IssueCard from './IssueCard';
import type { Issue } from '../../types';

interface ScanIssuesTabProps {
  scanId: string;
}

const IssuesLoadingSkeleton: React.FC = () => (
  <div className="animate-pulse space-y-4" aria-busy="true" aria-label="Loading issues">
    {[1, 2, 3].map((i) => (
      <div key={i} className="h-32 bg-gray-100 rounded-lg" />
    ))}
  </div>
);

const ScanIssuesTab: React.FC<ScanIssuesTabProps> = ({ scanId }) => {
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
    return <IssuesLoadingSkeleton />;
  }

  const issues = data?.items || [];

  const filterOptions = ['all', 'critical', 'serious', 'moderate', 'minor'] as const;

  return (
    <div className="space-y-4">
      {/* Filter */}
      <div className="flex gap-2" role="group" aria-label={t('results.issues.filterByImpact')}>
        {filterOptions.map((filter) => (
          <button
            key={filter}
            onClick={() => setImpactFilter(filter)}
            aria-pressed={impactFilter === filter}
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
        <div className="space-y-4" role="list" aria-label={t('results.issues.title')}>
          {issues.map((issue: Issue) => (
            <div key={issue.id} role="listitem">
              <IssueCard issue={issue} />
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default ScanIssuesTab;
