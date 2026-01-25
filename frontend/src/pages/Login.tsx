/**
 * Login Page
 *
 * User authentication page with email/password login.
 */

import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useTranslation } from '../hooks/useTranslation';
import { useAuthStore } from '../store/authStore';
import { Button, Input, Alert, Card, Checkbox } from '../components/common';

const Login: React.FC = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { login, error, clearError, isLoading } = useAuthStore();

  const [formData, setFormData] = useState({
    email: '',
    password: '',
    rememberMe: false,
  });
  const [formErrors, setFormErrors] = useState<Record<string, string>>({});

  const validate = () => {
    const errors: Record<string, string> = {};

    if (!formData.email) {
      errors.email = t('errors.validation.required');
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      errors.email = t('errors.validation.email');
    }

    if (!formData.password) {
      errors.password = t('errors.validation.required');
    }

    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    clearError();

    if (!validate()) return;

    try {
      await login(formData.email, formData.password);
      navigate('/dashboard');
    } catch {
      // Error is handled by the store
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value, type, checked } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value,
    }));

    // Clear field error on change
    if (formErrors[name]) {
      setFormErrors((prev) => ({ ...prev, [name]: '' }));
    }
  };

  return (
    <Card className="p-8">
      <div className="text-center mb-8">
        <h1 className="text-2xl font-bold text-gray-900">
          {t('auth.login.title')}
        </h1>
        <p className="mt-2 text-gray-600">
          {t('auth.login.subtitle')}
        </p>
      </div>

      {error && (
        <Alert
          variant="error"
          className="mb-6"
          dismissible
          onDismiss={clearError}
        >
          {error}
        </Alert>
      )}

      <form onSubmit={handleSubmit} className="space-y-6">
        <Input
          name="email"
          type="email"
          label={t('auth.login.email')}
          placeholder="name@firma.de"
          value={formData.email}
          onChange={handleChange}
          error={formErrors.email}
          autoComplete="email"
          required
          icon={<EmailIcon className="h-5 w-5" />}
        />

        <Input
          name="password"
          type="password"
          label={t('auth.login.password')}
          placeholder="********"
          value={formData.password}
          onChange={handleChange}
          error={formErrors.password}
          autoComplete="current-password"
          required
          icon={<LockIcon className="h-5 w-5" />}
        />

        <div className="flex items-center justify-between">
          <Checkbox
            name="rememberMe"
            label={t('auth.login.rememberMe')}
            checked={formData.rememberMe}
            onChange={handleChange}
          />
          <Link
            to="/forgot-password"
            className="text-sm text-blue-600 hover:text-blue-700"
          >
            {t('auth.login.forgotPassword')}
          </Link>
        </div>

        <Button
          type="submit"
          fullWidth
          size="lg"
          loading={isLoading}
        >
          {t('auth.login.submit')}
        </Button>
      </form>

      <p className="mt-8 text-center text-sm text-gray-600">
        {t('auth.login.noAccount')}{' '}
        <Link
          to="/register"
          className="font-medium text-blue-600 hover:text-blue-700"
        >
          {t('auth.login.signUp')}
        </Link>
      </p>
    </Card>
  );
};

// Icons
const EmailIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
  </svg>
);

const LockIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
  </svg>
);

export default Login;
