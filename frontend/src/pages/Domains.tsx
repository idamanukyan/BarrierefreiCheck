/**
 * Domains Page
 *
 * Manage monitored domains with bulk operations for agencies.
 */

import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from '../hooks/useTranslation';
import { domainsApi, CreateDomainData } from '../services/api';
import { Card, CardHeader, CardTitle, CardContent, Button, Input, Alert, Badge } from '../components/common';
import type { Domain } from '../types';

const Domains: React.FC = () => {
  const { t } = useTranslation();
  const queryClient = useQueryClient();

  const [newDomain, setNewDomain] = useState('');
  const [bulkInput, setBulkInput] = useState('');
  const [showBulkAdd, setShowBulkAdd] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Fetch domains
  const { data, isLoading, error: fetchError } = useQuery({
    queryKey: ['domains'],
    queryFn: () => domainsApi.list(),
  });

  // Mutations
  const createMutation = useMutation({
    mutationFn: (domain: string) => domainsApi.create({ domain }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['domains'] });
      setNewDomain('');
      setSuccess(t('domains.addSuccess'));
      setTimeout(() => setSuccess(null), 3000);
    },
    onError: (err: any) => {
      setError(err.response?.data?.detail || t('domains.addError'));
      setTimeout(() => setError(null), 5000);
    },
  });

  const bulkCreateMutation = useMutation({
    mutationFn: (domains: CreateDomainData[]) => domainsApi.bulkCreate(domains),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ['domains'] });
      setBulkInput('');
      setShowBulkAdd(false);
      if (result.total_errors > 0) {
        setSuccess(t('domains.bulkPartialSuccess', {
          created: result.total_created,
          errors: result.total_errors,
        }));
      } else {
        setSuccess(t('domains.bulkSuccess', { count: result.total_created }));
      }
      setTimeout(() => setSuccess(null), 5000);
    },
    onError: (err: any) => {
      setError(err.response?.data?.detail || t('domains.addError'));
      setTimeout(() => setError(null), 5000);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => domainsApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['domains'] });
      setSuccess(t('domains.deleteSuccess'));
      setTimeout(() => setSuccess(null), 3000);
    },
    onError: (err: any) => {
      setError(err.response?.data?.detail || t('domains.deleteError'));
      setTimeout(() => setError(null), 5000);
    },
  });

  const bulkDeleteMutation = useMutation({
    mutationFn: (ids: string[]) => domainsApi.bulkDelete(ids),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ['domains'] });
      setSelectedIds(new Set());
      setSuccess(t('domains.bulkDeleteSuccess', { count: result.deleted_count }));
      setTimeout(() => setSuccess(null), 3000);
    },
    onError: (err: any) => {
      setError(err.response?.data?.detail || t('domains.deleteError'));
      setTimeout(() => setError(null), 5000);
    },
  });

  const handleAddDomain = (e: React.FormEvent) => {
    e.preventDefault();
    if (newDomain.trim()) {
      createMutation.mutate(newDomain.trim());
    }
  };

  const handleBulkAdd = () => {
    const domains = bulkInput
      .split(/[\n,]/)
      .map((d) => d.trim())
      .filter((d) => d.length > 0)
      .map((domain) => ({ domain }));

    if (domains.length > 0) {
      bulkCreateMutation.mutate(domains);
    }
  };

  const handleBulkDelete = () => {
    if (selectedIds.size > 0 && window.confirm(t('domains.confirmBulkDelete'))) {
      bulkDeleteMutation.mutate(Array.from(selectedIds));
    }
  };

  const toggleSelect = (id: string) => {
    const newSet = new Set(selectedIds);
    if (newSet.has(id)) {
      newSet.delete(id);
    } else {
      newSet.add(id);
    }
    setSelectedIds(newSet);
  };

  const selectAll = () => {
    if (data?.items) {
      if (selectedIds.size === data.items.length) {
        setSelectedIds(new Set());
      } else {
        setSelectedIds(new Set(data.items.map((d) => d.id)));
      }
    }
  };

  const getScoreVariant = (score: number | null): 'success' | 'warning' | 'error' => {
    if (score === null) return 'warning';
    if (score >= 90) return 'success';
    if (score >= 70) return 'warning';
    return 'error';
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-gray-900">{t('domains.title')}</h1>
        {data && (
          <Badge variant={data.remaining === 0 ? 'error' : 'info'}>
            {data.total} / {data.limit === -1 ? '∞' : data.limit} {t('domains.used')}
          </Badge>
        )}
      </div>

      {/* Alerts */}
      {error && (
        <Alert variant="error" dismissible onDismiss={() => setError(null)}>
          {error}
        </Alert>
      )}
      {success && (
        <Alert variant="success" dismissible onDismiss={() => setSuccess(null)}>
          {success}
        </Alert>
      )}
      {fetchError && (
        <Alert variant="error">{t('errors.generic')}</Alert>
      )}

      {/* Add Domain Form */}
      <Card>
        <CardContent className="pt-6">
          <form onSubmit={handleAddDomain} className="flex gap-4">
            <Input
              value={newDomain}
              onChange={(e) => setNewDomain(e.target.value)}
              placeholder={t('domains.placeholder')}
              className="flex-1"
            />
            <Button
              type="submit"
              loading={createMutation.isPending}
              disabled={!newDomain.trim() || data?.remaining === 0}
            >
              {t('domains.add')}
            </Button>
            <Button
              type="button"
              variant="secondary"
              onClick={() => setShowBulkAdd(!showBulkAdd)}
            >
              {t('domains.bulkAdd')}
            </Button>
          </form>

          {showBulkAdd && (
            <div className="mt-4 space-y-4">
              <textarea
                value={bulkInput}
                onChange={(e) => setBulkInput(e.target.value)}
                placeholder={t('domains.bulkPlaceholder')}
                className="w-full h-32 p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
              <div className="flex gap-2">
                <Button
                  onClick={handleBulkAdd}
                  loading={bulkCreateMutation.isPending}
                  disabled={!bulkInput.trim()}
                >
                  {t('domains.addAll')}
                </Button>
                <Button variant="secondary" onClick={() => setShowBulkAdd(false)}>
                  {t('common.cancel')}
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Bulk Actions */}
      {selectedIds.size > 0 && (
        <div className="flex gap-4 items-center bg-blue-50 p-4 rounded-lg border border-blue-200">
          <span className="text-blue-700 font-medium">
            {selectedIds.size} {t('domains.selected')}
          </span>
          <Button
            variant="danger"
            size="sm"
            onClick={handleBulkDelete}
            loading={bulkDeleteMutation.isPending}
          >
            {t('domains.deleteSelected')}
          </Button>
          <Button variant="secondary" size="sm" onClick={() => setSelectedIds(new Set())}>
            {t('common.cancel')}
          </Button>
        </div>
      )}

      {/* Domain List */}
      <Card>
        <CardHeader>
          <div className="flex justify-between items-center">
            <CardTitle>{t('domains.list')}</CardTitle>
            {data && data.items.length > 0 && (
              <Button variant="ghost" size="sm" onClick={selectAll}>
                {selectedIds.size === data.items.length
                  ? t('domains.deselectAll')
                  : t('domains.selectAll')}
              </Button>
            )}
          </div>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="text-center py-8 text-gray-500">{t('common.loading')}</div>
          ) : data?.items.length === 0 ? (
            <div className="text-center py-8 text-gray-500">{t('domains.empty')}</div>
          ) : (
            <div className="divide-y divide-gray-100">
              {data?.items.map((domain) => (
                <DomainRow
                  key={domain.id}
                  domain={domain}
                  selected={selectedIds.has(domain.id)}
                  onToggle={() => toggleSelect(domain.id)}
                  onDelete={() => {
                    if (window.confirm(t('domains.confirmDelete'))) {
                      deleteMutation.mutate(domain.id);
                    }
                  }}
                  scoreVariant={getScoreVariant(domain.last_score)}
                  t={t}
                />
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

// Domain Row Component
interface DomainRowProps {
  domain: Domain;
  selected: boolean;
  onToggle: () => void;
  onDelete: () => void;
  scoreVariant: 'success' | 'warning' | 'error';
  t: (key: string, params?: Record<string, any>) => string;
}

const DomainRow: React.FC<DomainRowProps> = ({
  domain,
  selected,
  onToggle,
  onDelete,
  scoreVariant,
  t,
}) => {
  return (
    <div className="flex items-center gap-4 py-4 hover:bg-gray-50 -mx-4 px-4 rounded-lg transition-colors">
      <input
        type="checkbox"
        checked={selected}
        onChange={onToggle}
        className="h-4 w-4 text-blue-600 rounded border-gray-300 focus:ring-blue-500"
        aria-label={t('domains.selectDomain', { domain: domain.domain })}
      />
      <div className="flex-1 min-w-0">
        <div className="font-medium text-gray-900 truncate">{domain.domain}</div>
        {domain.display_name && (
          <div className="text-sm text-gray-500 truncate">{domain.display_name}</div>
        )}
      </div>
      <div className="text-sm text-gray-500 hidden sm:block">
        {domain.total_scans} {t('domains.scans')}
      </div>
      {domain.last_score !== null && (
        <Badge variant={scoreVariant}>{Math.round(domain.last_score)}%</Badge>
      )}
      <Button variant="ghost" size="sm" onClick={onDelete}>
        <TrashIcon className="h-4 w-4 text-gray-400 hover:text-red-500" />
      </Button>
    </div>
  );
};

// Trash Icon
const TrashIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth={2}
      d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
    />
  </svg>
);

export default Domains;
