/**
 * Issue Card Component
 *
 * Displays a single accessibility issue with expandable details.
 */

import React, { useState } from 'react';
import { useTranslation } from '../../hooks/useTranslation';
import { Card, ImpactBadge, WcagBadge } from '../common';
import type { Issue } from '../../types';

interface IssueCardProps {
  issue: Issue;
}

const ChevronIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
  </svg>
);

const IssueCard: React.FC<IssueCardProps> = ({ issue }) => {
  const { t } = useTranslation();
  const [expanded, setExpanded] = useState(false);

  return (
    <Card>
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full text-left p-4"
        aria-expanded={expanded}
        aria-controls={`issue-details-${issue.id}`}
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
        <div
          id={`issue-details-${issue.id}`}
          className="px-4 pb-4 border-t border-gray-100 pt-4 space-y-4"
        >
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
                <code>{issue.element.html}</code>
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

export default IssueCard;
