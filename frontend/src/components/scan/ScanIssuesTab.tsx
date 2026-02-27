/**
 * Scan Issues Tab Component
 *
 * Displays filterable list of accessibility issues with export functionality.
 */

import React, { useState, useRef, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from '../../hooks/useTranslation';
import { scansApi, exportApi } from '../../services/api';
import { Card, Button } from '../common';
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
  const [exportMenuOpen, setExportMenuOpen] = useState(false);
  const exportMenuRef = useRef<HTMLDivElement>(null);

  const { data, isLoading } = useQuery({
    queryKey: ['scan-issues', scanId, impactFilter],
    queryFn: () =>
      scansApi.getIssues(scanId, {
        impact: impactFilter === 'all' ? undefined : impactFilter,
      }),
  });

  // Close export menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (exportMenuRef.current && !exportMenuRef.current.contains(event.target as Node)) {
        setExportMenuOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleExport = (format: 'csv' | 'json') => {
    const url = exportApi.issuesUrl(scanId, format);
    window.open(url, '_blank');
    setExportMenuOpen(false);
  };

  if (isLoading) {
    return <IssuesLoadingSkeleton />;
  }

  const issues = data?.items || [];

  const filterOptions = ['all', 'critical', 'serious', 'moderate', 'minor'] as const;

  return (
    <div className="space-y-4">
      {/* Filter and Export */}
      <div className="flex justify-between items-center">
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

        {/* Export Dropdown */}
        <div className="relative" ref={exportMenuRef}>
          <Button
            variant="secondary"
            size="sm"
            onClick={() => setExportMenuOpen(!exportMenuOpen)}
            aria-expanded={exportMenuOpen}
            aria-haspopup="true"
          >
            {t('common.export')}
            <svg className="ml-2 h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </Button>
          {exportMenuOpen && (
            <div className="absolute right-0 mt-2 w-48 rounded-md shadow-lg bg-white ring-1 ring-black ring-opacity-5 z-10">
              <div className="py-1" role="menu" aria-orientation="vertical">
                <button
                  onClick={() => handleExport('csv')}
                  className="block w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                  role="menuitem"
                >
                  {t('results.export.formats.csv')}
                </button>
                <button
                  onClick={() => handleExport('json')}
                  className="block w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                  role="menuitem"
                >
                  {t('results.export.formats.json')}
                </button>
              </div>
            </div>
          )}
        </div>
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
