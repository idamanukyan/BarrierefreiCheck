/**
 * Share Link Dialog Component
 *
 * Modal for creating and managing share links for reports.
 */

import React, { useState, useEffect, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from '../../hooks/useTranslation';
import { shareLinksApi, ShareLink } from '../../services/api';
import { Button, Input, Alert, Badge } from '../common';

interface ShareLinkDialogProps {
  reportId: string;
  isOpen: boolean;
  onClose: () => void;
}

const ShareLinkDialog: React.FC<ShareLinkDialogProps> = ({ reportId, isOpen, onClose }) => {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const dialogRef = useRef<HTMLDivElement>(null);

  const [linkName, setLinkName] = useState('');
  const [expiresInDays, setExpiresInDays] = useState(7);
  const [newToken, setNewToken] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Fetch existing links
  const { data: linksData, isLoading } = useQuery({
    queryKey: ['share-links', reportId],
    queryFn: () => shareLinksApi.list(reportId),
    enabled: isOpen,
  });

  // Create link mutation
  const createMutation = useMutation({
    mutationFn: () => shareLinksApi.create(reportId, {
      name: linkName || undefined,
      expires_in_days: expiresInDays,
    }),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['share-links', reportId] });
      setNewToken(data.share_url);
      setLinkName('');
    },
    onError: (err: any) => {
      setError(err.response?.data?.detail || t('share.createError'));
      setTimeout(() => setError(null), 5000);
    },
  });

  // Revoke link mutation
  const revokeMutation = useMutation({
    mutationFn: (linkId: string) => shareLinksApi.revoke(reportId, linkId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['share-links', reportId] });
    },
    onError: (err: any) => {
      setError(err.response?.data?.detail || t('share.revokeError'));
      setTimeout(() => setError(null), 5000);
    },
  });

  // Handle escape key to close
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    if (isOpen) {
      document.addEventListener('keydown', handleEscape);
      return () => document.removeEventListener('keydown', handleEscape);
    }
  }, [isOpen, onClose]);

  // Reset state when dialog closes
  useEffect(() => {
    if (!isOpen) {
      setNewToken(null);
      setCopied(false);
      setError(null);
    }
  }, [isOpen]);

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault();
    createMutation.mutate();
  };

  const handleCopy = async () => {
    if (newToken) {
      try {
        await navigator.clipboard.writeText(newToken);
        setCopied(true);
        setTimeout(() => setCopied(false), 3000);
      } catch {
        setError(t('share.copyError'));
      }
    }
  };

  const handleRevoke = (linkId: string) => {
    if (window.confirm(t('share.confirmRevoke'))) {
      revokeMutation.mutate(linkId);
    }
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString();
  };

  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-40 bg-black bg-opacity-50"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Dialog */}
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="share-dialog-title"
        className="fixed inset-0 z-50 flex items-center justify-center p-4"
      >
        <div
          className="bg-white rounded-lg shadow-xl max-w-lg w-full max-h-[90vh] overflow-y-auto"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="flex justify-between items-center px-6 py-4 border-b">
            <h2 id="share-dialog-title" className="text-lg font-semibold text-gray-900">
              {t('share.title')}
            </h2>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600"
              aria-label={t('common.close')}
            >
              <CloseIcon className="h-5 w-5" />
            </button>
          </div>

          {/* Content */}
          <div className="px-6 py-4 space-y-6">
            {error && (
              <Alert variant="error" dismissible onDismiss={() => setError(null)}>
                {error}
              </Alert>
            )}

            {/* New token display */}
            {newToken && (
              <div className="bg-green-50 border border-green-200 rounded-lg p-4 space-y-3">
                <p className="text-sm text-green-800 font-medium">{t('share.linkCreated')}</p>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={newToken}
                    readOnly
                    className="flex-1 px-3 py-2 bg-white border border-green-300 rounded-lg text-sm font-mono"
                  />
                  <Button size="sm" onClick={handleCopy}>
                    {copied ? t('share.copied') : t('share.copy')}
                  </Button>
                </div>
                <p className="text-xs text-green-700">{t('share.linkWarning')}</p>
              </div>
            )}

            {/* Create new link form */}
            {!newToken && (
              <form onSubmit={handleCreate} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    {t('share.linkName')}
                  </label>
                  <Input
                    value={linkName}
                    onChange={(e) => setLinkName(e.target.value)}
                    placeholder={t('share.linkNamePlaceholder')}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    {t('share.expiresIn')}
                  </label>
                  <select
                    value={expiresInDays}
                    onChange={(e) => setExpiresInDays(Number(e.target.value))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  >
                    <option value={1}>1 {t('share.day')}</option>
                    <option value={7}>7 {t('share.days')}</option>
                    <option value={14}>14 {t('share.days')}</option>
                    <option value={30}>30 {t('share.days')}</option>
                    <option value={90}>90 {t('share.days')}</option>
                  </select>
                </div>
                <Button
                  type="submit"
                  loading={createMutation.isPending}
                  className="w-full"
                >
                  {t('share.createLink')}
                </Button>
              </form>
            )}

            {/* Existing links */}
            <div>
              <h3 className="text-sm font-medium text-gray-700 mb-3">
                {t('share.existingLinks')}
              </h3>
              {isLoading ? (
                <div className="text-center py-4 text-gray-500">{t('common.loading')}</div>
              ) : linksData?.items.length === 0 ? (
                <p className="text-center py-4 text-gray-500">{t('share.noLinks')}</p>
              ) : (
                <div className="space-y-2">
                  {linksData?.items.map((link) => (
                    <ShareLinkItem
                      key={link.id}
                      link={link}
                      onRevoke={() => handleRevoke(link.id)}
                      formatDate={formatDate}
                      t={t}
                    />
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Footer */}
          <div className="px-6 py-4 border-t bg-gray-50">
            <Button variant="secondary" onClick={onClose} className="w-full">
              {t('common.close')}
            </Button>
          </div>
        </div>
      </div>
    </>
  );
};

// Share Link Item Component
interface ShareLinkItemProps {
  link: ShareLink;
  onRevoke: () => void;
  formatDate: (date: string) => string;
  t: (key: string, params?: Record<string, any>) => string;
}

const ShareLinkItem: React.FC<ShareLinkItemProps> = ({ link, onRevoke, formatDate, t }) => {
  const isExpired = new Date(link.expires_at) < new Date();

  return (
    <div className={`flex items-center justify-between p-3 rounded-lg border ${
      isExpired ? 'bg-gray-50 border-gray-200' : 'bg-white border-gray-200'
    }`}>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="font-mono text-sm text-gray-600">{link.token_prefix}...</span>
          {link.name && <span className="text-sm text-gray-900">{link.name}</span>}
          {isExpired && <Badge variant="error">{t('share.expired')}</Badge>}
          {!link.is_active && <Badge variant="warning">{t('share.revoked')}</Badge>}
        </div>
        <div className="text-xs text-gray-500 mt-1">
          {t('share.expires')}: {formatDate(link.expires_at)} &bull; {link.access_count} {t('share.views')}
        </div>
      </div>
      {link.is_active && !isExpired && (
        <Button variant="ghost" size="sm" onClick={onRevoke}>
          {t('share.revoke')}
        </Button>
      )}
    </div>
  );
};

// Close Icon
const CloseIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
  </svg>
);

export default ShareLinkDialog;
