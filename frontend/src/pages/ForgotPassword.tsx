/**
 * Forgot Password Page
 *
 * Password reset request form.
 */

import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from '../hooks/useTranslation';
import { authApi } from '../services/api';
import { Button, Input, Alert, Card } from '../components/common';

const ForgotPassword: React.FC = () => {
  const { t } = useTranslation();
  const [email, setEmail] = useState('');
  const [emailError, setEmailError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);
  const [error, setError] = useState('');

  const validate = () => {
    if (!email) {
      setEmailError(t('errors.validation.required'));
      return false;
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      setEmailError(t('errors.validation.email'));
      return false;
    }
    setEmailError('');
    return true;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!validate()) return;

    setIsLoading(true);

    try {
      await authApi.forgotPassword(email);
      setIsSuccess(true);
    } catch (err: any) {
      const message = err.response?.data?.detail || t('errors.generic');
      setError(message);
    } finally {
      setIsLoading(false);
    }
  };

  if (isSuccess) {
    return (
      <Card className="p-8 text-center">
        <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-green-100">
          <CheckIcon className="h-6 w-6 text-green-600" />
        </div>
        <h2 className="mt-4 text-xl font-semibold text-gray-900">
          E-Mail gesendet
        </h2>
        <p className="mt-2 text-gray-600">
          {t('auth.forgotPassword.success')}
        </p>
        <Link
          to="/login"
          className="mt-6 inline-block text-blue-600 hover:text-blue-700 font-medium"
        >
          {t('auth.forgotPassword.backToLogin')}
        </Link>
      </Card>
    );
  }

  return (
    <Card className="p-8">
      <div className="text-center mb-8">
        <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-blue-100">
          <LockIcon className="h-6 w-6 text-blue-600" />
        </div>
        <h1 className="mt-4 text-2xl font-bold text-gray-900">
          {t('auth.forgotPassword.title')}
        </h1>
        <p className="mt-2 text-gray-600">
          {t('auth.forgotPassword.subtitle')}
        </p>
      </div>

      {error && (
        <Alert
          variant="error"
          className="mb-6"
          dismissible
          onDismiss={() => setError('')}
        >
          {error}
        </Alert>
      )}

      <form onSubmit={handleSubmit} className="space-y-6">
        <Input
          name="email"
          type="email"
          label={t('auth.forgotPassword.email')}
          placeholder="name@firma.de"
          value={email}
          onChange={(e) => {
            setEmail(e.target.value);
            if (emailError) setEmailError('');
          }}
          error={emailError}
          autoComplete="email"
          required
          icon={<EmailIcon className="h-5 w-5" />}
        />

        <Button
          type="submit"
          fullWidth
          size="lg"
          loading={isLoading}
        >
          {t('auth.forgotPassword.submit')}
        </Button>
      </form>

      <p className="mt-8 text-center">
        <Link
          to="/login"
          className="text-sm text-blue-600 hover:text-blue-700 font-medium"
        >
          {t('auth.forgotPassword.backToLogin')}
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

const CheckIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
  </svg>
);

export default ForgotPassword;
