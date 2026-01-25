/**
 * Settings Page
 *
 * User profile, notifications, and account settings.
 */

import React, { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { useTranslation } from '../hooks/useTranslation';
import { useAuthStore } from '../store/authStore';
import { userApi } from '../services/api';
import { Card, CardHeader, CardTitle, CardContent, CardFooter, Button, Input, Checkbox, Alert } from '../components/common';
import { LanguageSwitcher } from '../components/common/LanguageSwitcher';

const Settings: React.FC = () => {
  const { t } = useTranslation();
  const [activeTab, setActiveTab] = useState<'profile' | 'notifications' | 'language'>('profile');

  const tabs = [
    { id: 'profile', label: t('settings.profile.title') },
    { id: 'notifications', label: t('settings.notifications.title') },
    { id: 'language', label: t('settings.language.title') },
  ];

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">
        {t('settings.title')}
      </h1>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="flex gap-4">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`py-3 px-1 border-b-2 font-medium text-sm transition-colors ${
                activeTab === tab.id
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab content */}
      {activeTab === 'profile' && <ProfileSettings />}
      {activeTab === 'notifications' && <NotificationSettings />}
      {activeTab === 'language' && <LanguageSettings />}
    </div>
  );
};

// Profile settings
const ProfileSettings: React.FC = () => {
  const { t } = useTranslation();
  const { user, updateUser } = useAuthStore();
  const [formData, setFormData] = useState({
    name: user?.name || '',
    company: user?.company || '',
  });
  const [success, setSuccess] = useState(false);

  const updateMutation = useMutation({
    mutationFn: (data: typeof formData) => userApi.updateProfile(data),
    onSuccess: (data) => {
      updateUser(data);
      setSuccess(true);
      setTimeout(() => setSuccess(false), 3000);
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    updateMutation.mutate(formData);
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData((prev) => ({
      ...prev,
      [e.target.name]: e.target.value,
    }));
  };

  return (
    <Card>
      <form onSubmit={handleSubmit}>
        <CardHeader>
          <CardTitle>{t('settings.profile.title')}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          {success && (
            <Alert variant="success" dismissible onDismiss={() => setSuccess(false)}>
              {t('common.success')}
            </Alert>
          )}

          {updateMutation.error && (
            <Alert variant="error" dismissible onDismiss={() => updateMutation.reset()}>
              {t('errors.generic')}
            </Alert>
          )}

          <Input
            name="name"
            label={t('settings.profile.name')}
            value={formData.name}
            onChange={handleChange}
            icon={<UserIcon className="h-5 w-5" />}
          />

          <Input
            name="email"
            label={t('settings.profile.email')}
            value={user?.email || ''}
            disabled
            icon={<EmailIcon className="h-5 w-5" />}
          />

          <Input
            name="company"
            label={t('settings.profile.company')}
            value={formData.company}
            onChange={handleChange}
            icon={<BuildingIcon className="h-5 w-5" />}
          />
        </CardContent>
        <CardFooter>
          <Button
            type="submit"
            loading={updateMutation.isPending}
          >
            {t('settings.profile.save')}
          </Button>
        </CardFooter>
      </form>
    </Card>
  );
};

// Notification settings
const NotificationSettings: React.FC = () => {
  const { t } = useTranslation();
  const [settings, setSettings] = useState({
    scanComplete: true,
    weeklyReport: true,
    monthlyReport: false,
    newsletter: false,
  });

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSettings((prev) => ({
      ...prev,
      [e.target.name]: e.target.checked,
    }));
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle subtitle={t('settings.notifications.email')}>
          {t('settings.notifications.title')}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <Checkbox
          name="scanComplete"
          label={t('settings.notifications.scanComplete')}
          description="Erhalten Sie eine E-Mail, wenn ein Scan abgeschlossen ist"
          checked={settings.scanComplete}
          onChange={handleChange}
        />
        <Checkbox
          name="weeklyReport"
          label={t('settings.notifications.weeklyReport')}
          description="Wöchentliche Zusammenfassung Ihrer Scan-Ergebnisse"
          checked={settings.weeklyReport}
          onChange={handleChange}
        />
        <Checkbox
          name="monthlyReport"
          label={t('settings.notifications.monthlyReport')}
          description="Monatlicher Bericht mit Trends und Verbesserungen"
          checked={settings.monthlyReport}
          onChange={handleChange}
        />
        <Checkbox
          name="newsletter"
          label={t('settings.notifications.newsletter')}
          description="Neuigkeiten zu Barrierefreiheit und BFSG"
          checked={settings.newsletter}
          onChange={handleChange}
        />
      </CardContent>
      <CardFooter>
        <Button>{t('common.save')}</Button>
      </CardFooter>
    </Card>
  );
};

// Language settings
const LanguageSettings: React.FC = () => {
  const { t } = useTranslation();

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t('settings.language.title')}</CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-gray-600 mb-4">
          {t('settings.language.select')}
        </p>
        <LanguageSwitcher variant="buttons" />
      </CardContent>
    </Card>
  );
};

// Icons
const UserIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
  </svg>
);

const EmailIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
  </svg>
);

const BuildingIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
  </svg>
);

export default Settings;
