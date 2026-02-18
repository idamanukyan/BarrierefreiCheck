/**
 * Scan Pages Tab Component
 *
 * Displays table of all pages scanned with their scores.
 */

import React from 'react';
import { useTranslation } from '../../hooks/useTranslation';
import { Card, ScoreBadge } from '../common';
import type { Scan, Page } from '../../types';

interface ScanPagesTabProps {
  scan: Scan;
}

const ScanPagesTab: React.FC<ScanPagesTabProps> = ({ scan }) => {
  const { t, formatNumber } = useTranslation();
  const pages = scan.pages || [];

  if (pages.length === 0) {
    return (
      <Card className="text-center py-12">
        <p className="text-gray-500">{t('scan.detail.noPages')}</p>
      </Card>
    );
  }

  return (
    <Card padding="none">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th
                scope="col"
                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase"
              >
                URL
              </th>
              <th
                scope="col"
                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase"
              >
                {t('scan.list.columns.issues')}
              </th>
              <th
                scope="col"
                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase"
              >
                {t('scan.list.columns.score')}
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {pages.map((page: Page, index: number) => (
              <tr key={page.id || index} className="hover:bg-gray-50">
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
                    <span className="text-gray-400">-</span>
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

export default ScanPagesTab;
