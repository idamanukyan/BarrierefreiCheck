/**
 * Reports Page
 *
 * List and manage generated reports.
 */

import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from '../hooks/useTranslation';
import { reportsApi } from '../services/api';
import { Card, Button, Alert } from '../components/common';

const Reports: React.FC = () => {
  const { t, formatDate, formatRelativeTime } = useTranslation();

  const { data, isLoading, error } = useQuery({
    queryKey: ['reports'],
    queryFn: () => reportsApi.list(),
  });

  if (isLoading) {
    return <ReportsSkeleton />;
  }

  if (error) {
    return (
      <Alert variant="error">
        {t('errors.generic')}
      </Alert>
    );
  }

  const reports = data?.items || [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">
          {t('reports.title')}
        </h1>
      </div>

      {reports.length === 0 ? (
        <Card className="text-center py-12">
          <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-gray-100">
            <ReportIcon className="h-8 w-8 text-gray-400" />
          </div>
          <h3 className="mt-4 text-lg font-semibold text-gray-900">
            {t('reports.list.empty')}
          </h3>
          <p className="mt-2 text-gray-500">
            {t('reports.list.createFirst')}
          </p>
        </Card>
      ) : (
        <Card padding="none">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    {t('scan.list.columns.url')}
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    {t('results.export.format')}
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    {t('scan.list.columns.date')}
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">
                    {t('scan.list.columns.actions')}
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {reports.map((report: any) => (
                  <tr key={report.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4">
                      <p className="text-sm font-medium text-gray-900">
                        {report.scanUrl}
                      </p>
                    </td>
                    <td className="px-6 py-4">
                      <span className="px-2 py-1 text-xs font-medium bg-gray-100 rounded uppercase">
                        {report.format}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-500">
                      {formatRelativeTime(report.createdAt)}
                    </td>
                    <td className="px-6 py-4 text-right">
                      <a
                        href={reportsApi.download(report.id)}
                        className="text-blue-600 hover:text-blue-700 text-sm font-medium"
                        download
                      >
                        {t('common.download')}
                      </a>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
};

// Skeleton
const ReportsSkeleton: React.FC = () => (
  <div className="space-y-6 animate-pulse">
    <div className="h-8 bg-gray-200 rounded w-1/4" />
    <div className="h-64 bg-gray-200 rounded-lg" />
  </div>
);

// Icons
const ReportIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
  </svg>
);

export default Reports;
