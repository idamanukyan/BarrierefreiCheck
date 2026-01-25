/**
 * Scan List Page
 *
 * List of all user scans with filtering and pagination.
 */

import React from 'react';
import { Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from '../hooks/useTranslation';
import { useScanStore } from '../store/scanStore';
import { scansApi } from '../services/api';
import { Card, Button, StatusBadge, ScoreBadge, Alert } from '../components/common';

const ScanList: React.FC = () => {
  const { t, formatRelativeTime, formatNumber } = useTranslation();
  const queryClient = useQueryClient();
  const { currentPage, pageSize, statusFilter, setPage, setStatusFilter } = useScanStore();

  const { data, isLoading, error } = useQuery({
    queryKey: ['scans', currentPage, pageSize, statusFilter],
    queryFn: () =>
      scansApi.list({
        page: currentPage,
        pageSize,
        status: statusFilter === 'all' ? undefined : statusFilter,
      }),
  });

  const deleteMutation = useMutation({
    mutationFn: (scanId: string) => scansApi.delete(scanId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['scans'] });
    },
  });

  const handleDelete = (scanId: string, e: React.MouseEvent) => {
    e.preventDefault();
    if (window.confirm(t('common.confirm') + '?')) {
      deleteMutation.mutate(scanId);
    }
  };

  const statusOptions = [
    { value: 'all', label: t('scan.list.filters.all') },
    { value: 'completed', label: t('scan.list.filters.completed') },
    { value: 'scanning', label: t('scan.list.filters.running') },
    { value: 'failed', label: t('scan.list.filters.failed') },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <h1 className="text-2xl font-bold text-gray-900">
          {t('scan.list.title')}
        </h1>
        <Link to="/scans/new">
          <Button icon={<PlusIcon className="h-5 w-5" />}>
            {t('dashboard.startScan')}
          </Button>
        </Link>
      </div>

      {/* Filters */}
      <Card padding="sm">
        <div className="flex flex-wrap gap-2">
          {statusOptions.map((option) => (
            <button
              key={option.value}
              onClick={() => setStatusFilter(option.value as any)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                statusFilter === option.value
                  ? 'bg-blue-100 text-blue-700'
                  : 'text-gray-600 hover:bg-gray-100'
              }`}
            >
              {option.label}
            </button>
          ))}
        </div>
      </Card>

      {/* Error state */}
      {error && (
        <Alert variant="error">
          {t('errors.generic')}
        </Alert>
      )}

      {/* Loading state */}
      {isLoading && <ScanListSkeleton />}

      {/* Empty state */}
      {!isLoading && data?.items.length === 0 && (
        <Card className="text-center py-12">
          <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-gray-100">
            <SearchIcon className="h-8 w-8 text-gray-400" />
          </div>
          <h3 className="mt-4 text-lg font-semibold text-gray-900">
            {t('scan.list.empty')}
          </h3>
          <p className="mt-2 text-gray-500">
            {t('scan.list.startFirst')}
          </p>
          <Link to="/scans/new" className="mt-6 inline-block">
            <Button>
              {t('dashboard.startScan')}
            </Button>
          </Link>
        </Card>
      )}

      {/* Scan list */}
      {!isLoading && data && data.items.length > 0 && (
        <>
          <Card padding="none">
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      {t('scan.list.columns.url')}
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      {t('scan.list.columns.status')}
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      {t('scan.list.columns.pages')}
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      {t('scan.list.columns.issues')}
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      {t('scan.list.columns.score')}
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      {t('scan.list.columns.date')}
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                      {t('scan.list.columns.actions')}
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {data.items.map((scan: any) => (
                    <tr key={scan.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <Link
                          to={`/scans/${scan.id}`}
                          className="text-blue-600 hover:text-blue-700 font-medium"
                        >
                          {truncateUrl(scan.url)}
                        </Link>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <StatusBadge status={scan.status} />
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {scan.pagesScanned !== undefined ? formatNumber(scan.pagesScanned) : '-'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {scan.issuesCount !== undefined ? formatNumber(scan.issuesCount) : '-'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        {scan.score !== undefined && scan.score !== null ? (
                          <ScoreBadge score={scan.score} />
                        ) : (
                          '-'
                        )}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {formatRelativeTime(scan.createdAt)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                        <div className="flex items-center justify-end gap-2">
                          <Link
                            to={`/scans/${scan.id}`}
                            className="text-blue-600 hover:text-blue-900"
                          >
                            {t('scan.list.actions.view')}
                          </Link>
                          <button
                            onClick={(e) => handleDelete(scan.id, e)}
                            className="text-red-600 hover:text-red-900"
                          >
                            {t('common.delete')}
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>

          {/* Pagination */}
          {data.totalPages > 1 && (
            <div className="flex items-center justify-between">
              <p className="text-sm text-gray-500">
                {t('common.showing')} {(currentPage - 1) * pageSize + 1}-
                {Math.min(currentPage * pageSize, data.total)} {t('common.of')}{' '}
                {data.total} {t('common.results')}
              </p>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage(currentPage - 1)}
                  disabled={currentPage === 1}
                >
                  {t('common.previous')}
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage(currentPage + 1)}
                  disabled={currentPage >= data.totalPages}
                >
                  {t('common.next')}
                </Button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
};

// Helper to truncate long URLs
function truncateUrl(url: string, maxLength: number = 40): string {
  try {
    const parsed = new URL(url);
    const display = parsed.hostname + parsed.pathname;
    return display.length > maxLength ? display.substring(0, maxLength) + '...' : display;
  } catch {
    return url.length > maxLength ? url.substring(0, maxLength) + '...' : url;
  }
}

// Loading skeleton
const ScanListSkeleton: React.FC = () => (
  <Card padding="none">
    <div className="animate-pulse">
      <div className="h-12 bg-gray-100" />
      {[1, 2, 3, 4, 5].map((i) => (
        <div key={i} className="border-t border-gray-200 px-6 py-4 flex items-center gap-4">
          <div className="h-4 bg-gray-200 rounded w-1/4" />
          <div className="h-4 bg-gray-200 rounded w-16" />
          <div className="h-4 bg-gray-200 rounded w-12" />
          <div className="h-4 bg-gray-200 rounded w-12" />
          <div className="h-4 bg-gray-200 rounded w-12" />
          <div className="h-4 bg-gray-200 rounded w-24" />
        </div>
      ))}
    </div>
  </Card>
);

// Icons
const PlusIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
  </svg>
);

const SearchIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
  </svg>
);

export default ScanList;
