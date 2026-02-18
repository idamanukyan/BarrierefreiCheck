/**
 * Scan Progress Component
 *
 * Displays real-time progress for running scans.
 */

import React from 'react';
import { useTranslation } from '../../hooks/useTranslation';

export interface ScanProgressData {
  stage: string;
  pagesScanned: number;
  totalPages: number;
  currentUrl?: string;
  issuesFound: number;
}

interface ScanProgressProps {
  progress: ScanProgressData;
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
      <div
        className="h-2 bg-gray-200 rounded-full overflow-hidden"
        role="progressbar"
        aria-valuenow={percentage}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={t('scan.progress.title')}
      >
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

export default ScanProgress;
