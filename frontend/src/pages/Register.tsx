/**
 * Register Page
 *
 * New user registration with email, password, and profile info.
 */

import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useTranslation } from '../hooks/useTranslation';
import { useAuthStore } from '../store/authStore';
import { Button, Input, Alert, Card, Checkbox } from '../components/common';

const Register: React.FC = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { register, error, clearError, isLoading } = useAuthStore();

  const [formData, setFormData] = useState({
    name: '',
    company: '',
    email: '',
    password: '',
    confirmPassword: '',
    acceptTerms: false,
  });
  const [formErrors, setFormErrors] = useState<Record<string, string>>({});

  const validate = () => {
    const errors: Record<string, string> = {};

    if (!formData.name) {
      errors.name = t('errors.validation.required');
    } else if (formData.name.length < 2) {
      errors.name = t('errors.validation.minLength', { min: 2 });
    }

    if (!formData.email) {
      errors.email = t('errors.validation.required');
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      errors.email = t('errors.validation.email');
    }

    if (!formData.password) {
      errors.password = t('errors.validation.required');
    } else if (formData.password.length < 8) {
      errors.password = t('errors.validation.minLength', { min: 8 });
    } else if (!/(?=.*[A-Z])(?=.*\d)/.test(formData.password)) {
      errors.password = t('auth.register.passwordRequirements');
    }

    if (!formData.confirmPassword) {
      errors.confirmPassword = t('errors.validation.required');
    } else if (formData.password !== formData.confirmPassword) {
      errors.confirmPassword = t('errors.validation.passwordMismatch');
    }

    if (!formData.acceptTerms) {
      errors.acceptTerms = t('errors.validation.required');
    }

    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    clearError();

    if (!validate()) return;

    try {
      await register({
        name: formData.name,
        email: formData.email,
        password: formData.password,
        company: formData.company || undefined,
      });
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
          {t('auth.register.title')}
        </h1>
        <p className="mt-2 text-gray-600">
          {t('auth.register.subtitle')}
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

      <form onSubmit={handleSubmit} className="space-y-5">
        <Input
          name="name"
          type="text"
          label={t('auth.register.name')}
          placeholder="Max Mustermann"
          value={formData.name}
          onChange={handleChange}
          error={formErrors.name}
          autoComplete="name"
          required
          icon={<UserIcon className="h-5 w-5" />}
        />

        <Input
          name="company"
          type="text"
          label={t('auth.register.company')}
          placeholder="Muster GmbH"
          value={formData.company}
          onChange={handleChange}
          autoComplete="organization"
          icon={<BuildingIcon className="h-5 w-5" />}
        />

        <Input
          name="email"
          type="email"
          label={t('auth.register.email')}
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
          label={t('auth.register.password')}
          placeholder="********"
          value={formData.password}
          onChange={handleChange}
          error={formErrors.password}
          hint={t('auth.register.passwordRequirements')}
          autoComplete="new-password"
          required
          icon={<LockIcon className="h-5 w-5" />}
        />

        <Input
          name="confirmPassword"
          type="password"
          label={t('auth.register.confirmPassword')}
          placeholder="********"
          value={formData.confirmPassword}
          onChange={handleChange}
          error={formErrors.confirmPassword}
          autoComplete="new-password"
          required
          icon={<LockIcon className="h-5 w-5" />}
        />

        <Checkbox
          name="acceptTerms"
          label={t('auth.register.terms')}
          checked={formData.acceptTerms}
          onChange={handleChange}
        />
        {formErrors.acceptTerms && (
          <p className="text-sm text-red-600 -mt-3">{formErrors.acceptTerms}</p>
        )}

        <Button
          type="submit"
          fullWidth
          size="lg"
          loading={isLoading}
        >
          {t('auth.register.submit')}
        </Button>
      </form>

      <p className="mt-8 text-center text-sm text-gray-600">
        {t('auth.register.hasAccount')}{' '}
        <Link
          to="/login"
          className="font-medium text-blue-600 hover:text-blue-700"
        >
          {t('auth.register.signIn')}
        </Link>
      </p>
    </Card>
  );
};

// Icons
const UserIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
  </svg>
);

const BuildingIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
  </svg>
);

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

export default Register;
