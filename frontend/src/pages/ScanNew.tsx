/**
 * New Scan Page
 *
 * Form to start a new accessibility scan.
 */

import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';
import { useTranslation } from '../hooks/useTranslation';
import { useAuthStore } from '../store/authStore';
import { useScanStore } from '../store/scanStore';
import { scansApi, CreateScanData } from '../services/api';
import { Card, CardHeader, CardTitle, CardContent, CardFooter, Button, Input, Checkbox, Alert } from '../components/common';

const ScanNew: React.FC = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { user } = useAuthStore();
  const { addScan, setCurrentScan } = useScanStore();

  const [formData, setFormData] = useState({
    url: '',
    crawl: false,
    maxPages: 10,
    respectRobotsTxt: true,
    captureScreenshots: true,
  });
  const [formErrors, setFormErrors] = useState<Record<string, string>>({});

  // Get max pages based on user plan
  const planLimits: Record<string, number> = {
    free: 1,
    starter: 25,
    professional: 100,
    enterprise: 500,
  };
  const maxPagesAllowed = planLimits[user?.plan || 'free'] || 1;

  const createScanMutation = useMutation({
    mutationFn: (data: CreateScanData) => scansApi.create(data),
    onSuccess: (scan) => {
      addScan(scan);
      setCurrentScan(scan);
      navigate(`/scans/${scan.id}`);
    },
  });

  const validateUrl = (url: string): boolean => {
    try {
      const parsed = new URL(url);
      return ['http:', 'https:'].includes(parsed.protocol);
    } catch {
      return false;
    }
  };

  const validate = () => {
    const errors: Record<string, string> = {};

    if (!formData.url) {
      errors.url = t('errors.validation.required');
    } else if (!validateUrl(formData.url)) {
      errors.url = t('errors.validation.url');
    }

    if (formData.crawl && formData.maxPages < 1) {
      errors.maxPages = t('errors.validation.required');
    }

    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validate()) return;

    // Normalize URL
    let url = formData.url;
    if (!url.startsWith('http://') && !url.startsWith('https://')) {
      url = 'https://' + url;
    }

    createScanMutation.mutate({
      url,
      crawl: formData.crawl,
      maxPages: formData.crawl ? formData.maxPages : 1,
      options: {
        respectRobotsTxt: formData.respectRobotsTxt,
        captureScreenshots: formData.captureScreenshots,
      },
    });
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value, type, checked } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : type === 'number' ? parseInt(value) || 0 : value,
    }));

    if (formErrors[name]) {
      setFormErrors((prev) => ({ ...prev, [name]: '' }));
    }
  };

  return (
    <div className="max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">
        {t('scan.new.title')}
      </h1>

      <Card>
        <form onSubmit={handleSubmit}>
          <CardContent className="space-y-6">
            {createScanMutation.error && (
              <Alert variant="error" dismissible onDismiss={() => createScanMutation.reset()}>
                {(createScanMutation.error as any)?.response?.data?.detail || t('errors.generic')}
              </Alert>
            )}

            {/* URL Input */}
            <Input
              name="url"
              type="text"
              label={t('scan.new.url')}
              placeholder={t('scan.new.urlPlaceholder')}
              hint={t('scan.new.urlHelp')}
              value={formData.url}
              onChange={handleChange}
              error={formErrors.url}
              required
              icon={<GlobeIcon className="h-5 w-5" />}
            />

            {/* Scan type selection */}
            <div className="space-y-4">
              <label className="block text-sm font-medium text-gray-700">
                {t('scan.new.options')}
              </label>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <ScanTypeCard
                  selected={!formData.crawl}
                  onClick={() => setFormData((prev) => ({ ...prev, crawl: false }))}
                  title={t('scan.new.singlePage')}
                  description={t('scan.new.singlePageDesc')}
                  icon={<PageIcon className="h-6 w-6" />}
                />
                <ScanTypeCard
                  selected={formData.crawl}
                  onClick={() => setFormData((prev) => ({ ...prev, crawl: true }))}
                  title={t('scan.new.multiPage')}
                  description={t('scan.new.multiPageDesc')}
                  icon={<PagesIcon className="h-6 w-6" />}
                  disabled={maxPagesAllowed === 1}
                  disabledReason={maxPagesAllowed === 1 ? t('scan.new.upgradePrompt') : undefined}
                />
              </div>
            </div>

            {/* Max pages (only for multi-page) */}
            {formData.crawl && (
              <div>
                <Input
                  name="maxPages"
                  type="number"
                  label={t('scan.new.maxPages')}
                  hint={t('scan.new.maxPagesHelp', { max: maxPagesAllowed })}
                  value={formData.maxPages}
                  onChange={handleChange}
                  error={formErrors.maxPages}
                  min={1}
                  max={maxPagesAllowed}
                />
                {maxPagesAllowed < 100 && (
                  <p className="mt-2 text-sm text-gray-500">
                    {t('scan.new.planLimit', { max: maxPagesAllowed })}
                  </p>
                )}
              </div>
            )}

            {/* Advanced options */}
            <details className="group">
              <summary className="cursor-pointer text-sm font-medium text-gray-700 flex items-center">
                <ChevronIcon className="h-5 w-5 mr-1 transform group-open:rotate-90 transition-transform" />
                {t('scan.new.advanced')}
              </summary>
              <div className="mt-4 space-y-4 pl-6">
                <Checkbox
                  name="respectRobotsTxt"
                  label={t('scan.new.respectRobots')}
                  description={t('scan.new.respectRobotsHelp')}
                  checked={formData.respectRobotsTxt}
                  onChange={handleChange}
                />
                <Checkbox
                  name="captureScreenshots"
                  label={t('scan.new.captureScreenshots')}
                  description={t('scan.new.captureScreenshotsHelp')}
                  checked={formData.captureScreenshots}
                  onChange={handleChange}
                />
              </div>
            </details>
          </CardContent>

          <CardFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => navigate(-1)}
            >
              {t('common.cancel')}
            </Button>
            <Button
              type="submit"
              loading={createScanMutation.isPending}
              icon={<ScanIcon className="h-5 w-5" />}
            >
              {createScanMutation.isPending ? t('scan.new.submitting') : t('scan.new.submit')}
            </Button>
          </CardFooter>
        </form>
      </Card>
    </div>
  );
};

// Scan type selection card
interface ScanTypeCardProps {
  selected: boolean;
  onClick: () => void;
  title: string;
  description: string;
  icon: React.ReactNode;
  disabled?: boolean;
  disabledReason?: string;
}

const ScanTypeCard: React.FC<ScanTypeCardProps> = ({
  selected,
  onClick,
  title,
  description,
  icon,
  disabled,
  disabledReason,
}) => (
  <button
    type="button"
    onClick={disabled ? undefined : onClick}
    className={`relative p-4 rounded-lg border-2 text-left transition-colors ${
      disabled
        ? 'border-gray-200 bg-gray-50 cursor-not-allowed opacity-60'
        : selected
        ? 'border-blue-500 bg-blue-50'
        : 'border-gray-200 hover:border-gray-300'
    }`}
    disabled={disabled}
  >
    <div className={`${selected ? 'text-blue-600' : 'text-gray-400'}`}>
      {icon}
    </div>
    <h4 className="mt-2 font-medium text-gray-900">{title}</h4>
    <p className="mt-1 text-sm text-gray-500">{description}</p>
    {disabledReason && (
      <p className="mt-2 text-xs text-blue-600">{disabledReason}</p>
    )}
    {selected && (
      <div className="absolute top-3 right-3">
        <CheckCircleIcon className="h-5 w-5 text-blue-500" />
      </div>
    )}
  </button>
);

// Icons
const GlobeIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9" />
  </svg>
);

const PageIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
  </svg>
);

const PagesIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7v8a2 2 0 002 2h6M8 7V5a2 2 0 012-2h4.586a1 1 0 01.707.293l4.414 4.414a1 1 0 01.293.707V15a2 2 0 01-2 2h-2M8 7H6a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2v-2" />
  </svg>
);

const ScanIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
  </svg>
);

const ChevronIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
  </svg>
);

const CheckCircleIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} fill="currentColor" viewBox="0 0 20 20">
    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
  </svg>
);

export default ScanNew;
