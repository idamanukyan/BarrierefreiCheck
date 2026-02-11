/**
 * Billing Page
 *
 * Subscription management, plan selection, and payment history.
 */

import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from '../hooks/useTranslation';
import { Card, CardHeader, CardTitle, CardContent, Button, Alert, Badge } from '../components/common';
import type { Plan, Subscription, Usage, Payment, PlanId } from '../types';

// Mock API - replace with actual API calls
const billingApi = {
  getPlans: async () => ({
    plans: [
      {
        id: 'free',
        name: 'Free',
        name_de: 'Kostenlos',
        price: 0,
        features_de: ['5 Scans pro Monat', 'Einzelseitige Scans', 'Basis-Berichte'],
      },
      {
        id: 'starter',
        name: 'Starter',
        name_de: 'Starter',
        price: 4900,
        features_de: ['50 Scans pro Monat', 'Bis zu 25 Seiten pro Scan', 'PDF-Berichte', 'E-Mail-Support'],
      },
      {
        id: 'professional',
        name: 'Professional',
        name_de: 'Professional',
        price: 14900,
        features_de: ['Unbegrenzte Scans', 'Bis zu 100 Seiten pro Scan', 'White-Label-Berichte', 'API-Zugang', 'Prioritäts-Support'],
      },
      {
        id: 'enterprise',
        name: 'Enterprise',
        name_de: 'Enterprise',
        price: 0,
        features_de: ['Unbegrenzte Scans und Seiten', 'Dedizierte Infrastruktur', 'SLA-Garantie', 'Account Manager'],
      },
    ],
  }),
  getSubscription: async () => ({
    plan: 'free',
    status: 'active',
    current_period_end: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString(),
  }),
  getUsage: async () => ({
    scans_used: 3,
    scans_limit: 5,
    pages_scanned: 3,
    reports_generated: 1,
  }),
  getPayments: async () => ({ items: [] }),
};

const Billing: React.FC = () => {
  const { t, formatCurrency, formatDate } = useTranslation();
  const [activeTab, setActiveTab] = useState<'overview' | 'plans' | 'payments'>('overview');

  const { data: plans } = useQuery({
    queryKey: ['plans'],
    queryFn: billingApi.getPlans,
  });

  const { data: subscription } = useQuery({
    queryKey: ['subscription'],
    queryFn: billingApi.getSubscription,
  });

  const { data: usage } = useQuery({
    queryKey: ['usage'],
    queryFn: billingApi.getUsage,
  });

  const { data: payments } = useQuery({
    queryKey: ['payments'],
    queryFn: billingApi.getPayments,
  });

  const tabs = [
    { id: 'overview', label: t('billing.currentPlan') },
    { id: 'plans', label: 'Pläne' },
    { id: 'payments', label: t('billing.invoices') },
  ];

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">
        {t('billing.title')}
      </h1>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="flex gap-4">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as 'overview' | 'plans' | 'payments')}
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

      {activeTab === 'overview' && (
        <OverviewTab
          subscription={subscription}
          usage={usage}
          plans={plans?.plans}
        />
      )}
      {activeTab === 'plans' && <PlansTab plans={plans?.plans} currentPlan={subscription?.plan} />}
      {activeTab === 'payments' && <PaymentsTab payments={payments?.items} />}
    </div>
  );
};

// Overview Tab
interface OverviewTabProps {
  subscription?: Subscription;
  usage?: Usage;
  plans?: Plan[];
}

const OverviewTab: React.FC<OverviewTabProps> = ({ subscription, usage, plans }) => {
  const { t, formatDate } = useTranslation();

  const currentPlan = plans?.find((p: Plan) => p.id === subscription?.plan);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Current Plan */}
      <Card>
        <CardHeader>
          <CardTitle>{t('billing.currentPlan')}</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-2xl font-bold text-gray-900">
                {currentPlan?.name_de || 'Kostenlos'}
              </h3>
              {currentPlan?.price > 0 && (
                <p className="text-gray-500">
                  {(currentPlan.price / 100).toFixed(2)} EUR / Monat
                </p>
              )}
            </div>
            <Badge variant={subscription?.status === 'active' ? 'success' : 'warning'}>
              {subscription?.status === 'active' ? 'Aktiv' : subscription?.status}
            </Badge>
          </div>

          {subscription?.current_period_end && (
            <p className="text-sm text-gray-500">
              Nächste Abrechnung: {formatDate(subscription.current_period_end)}
            </p>
          )}

          <div className="mt-4 pt-4 border-t border-gray-100">
            <h4 className="text-sm font-medium text-gray-700 mb-2">Enthaltene Features:</h4>
            <ul className="space-y-1">
              {currentPlan?.features_de?.map((feature: string, i: number) => (
                <li key={i} className="flex items-center text-sm text-gray-600">
                  <CheckIcon className="h-4 w-4 text-green-500 mr-2" />
                  {feature}
                </li>
              ))}
            </ul>
          </div>
        </CardContent>
      </Card>

      {/* Usage */}
      <Card>
        <CardHeader>
          <CardTitle>{t('billing.usage')}</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {/* Scans */}
            <div>
              <div className="flex justify-between text-sm mb-1">
                <span className="text-gray-600">Scans diesen Monat</span>
                <span className="font-medium">
                  {usage?.scans_used || 0} / {usage?.scans_limit === -1 ? '∞' : usage?.scans_limit || 5}
                </span>
              </div>
              <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                <div
                  className="h-full bg-blue-600 rounded-full transition-all"
                  style={{
                    width: usage?.scans_limit === -1
                      ? '10%'
                      : `${Math.min(100, ((usage?.scans_used || 0) / (usage?.scans_limit || 5)) * 100)}%`,
                  }}
                />
              </div>
            </div>

            {/* Pages */}
            <div className="flex justify-between py-2 border-t border-gray-100">
              <span className="text-gray-600">Gescannte Seiten</span>
              <span className="font-medium">{usage?.pages_scanned || 0}</span>
            </div>

            {/* Reports */}
            <div className="flex justify-between py-2 border-t border-gray-100">
              <span className="text-gray-600">Generierte Berichte</span>
              <span className="font-medium">{usage?.reports_generated || 0}</span>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

// Plans Tab
interface PlansTabProps {
  plans?: Plan[];
  currentPlan?: PlanId;
}

const PlansTab: React.FC<PlansTabProps> = ({ plans, currentPlan }) => {
  const { t } = useTranslation();

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      {plans?.map((plan: Plan) => (
        <Card
          key={plan.id}
          className={`relative ${
            currentPlan === plan.id ? 'ring-2 ring-blue-500' : ''
          }`}
        >
          {currentPlan === plan.id && (
            <div className="absolute -top-3 left-1/2 -translate-x-1/2">
              <Badge variant="primary">Aktueller Plan</Badge>
            </div>
          )}

          <CardContent className="pt-6">
            <h3 className="text-xl font-bold text-gray-900">{plan.name_de}</h3>

            <div className="mt-4">
              {plan.price > 0 ? (
                <>
                  <span className="text-3xl font-bold">{(plan.price / 100).toFixed(0)}</span>
                  <span className="text-gray-500"> EUR/Monat</span>
                </>
              ) : plan.id === 'enterprise' ? (
                <span className="text-2xl font-bold text-gray-900">Individuell</span>
              ) : (
                <span className="text-3xl font-bold">Kostenlos</span>
              )}
            </div>

            <ul className="mt-6 space-y-3">
              {plan.features_de?.map((feature: string, i: number) => (
                <li key={i} className="flex items-start text-sm">
                  <CheckIcon className="h-5 w-5 text-green-500 mr-2 flex-shrink-0" />
                  <span className="text-gray-600">{feature}</span>
                </li>
              ))}
            </ul>

            <div className="mt-6">
              {currentPlan === plan.id ? (
                <Button variant="outline" fullWidth disabled>
                  Aktueller Plan
                </Button>
              ) : plan.id === 'enterprise' ? (
                <Button variant="outline" fullWidth>
                  Kontaktieren
                </Button>
              ) : plan.id === 'free' ? (
                <Button variant="outline" fullWidth>
                  {t('billing.downgrade')}
                </Button>
              ) : (
                <Button fullWidth>
                  {t('billing.upgrade')}
                </Button>
              )}
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
};

// Payments Tab
interface PaymentsTabProps {
  payments?: Payment[];
}

const PaymentsTab: React.FC<PaymentsTabProps> = ({ payments }) => {
  const { t, formatDate, formatCurrency } = useTranslation();

  if (!payments || payments.length === 0) {
    return (
      <Card className="text-center py-12">
        <InvoiceIcon className="h-12 w-12 text-gray-400 mx-auto mb-4" />
        <h3 className="text-lg font-medium text-gray-900">Keine Rechnungen</h3>
        <p className="text-gray-500 mt-1">
          Ihre Rechnungen werden hier angezeigt, sobald Sie ein kostenpflichtiges Abonnement haben.
        </p>
      </Card>
    );
  }

  return (
    <Card padding="none">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Datum
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Beschreibung
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Betrag
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Status
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">
                Rechnung
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {payments.map((payment: Payment) => (
              <tr key={payment.id} className="hover:bg-gray-50">
                <td className="px-6 py-4 text-sm text-gray-500">
                  {formatDate(payment.created_at)}
                </td>
                <td className="px-6 py-4 text-sm text-gray-900">
                  {payment.description || 'Abonnement'}
                </td>
                <td className="px-6 py-4 text-sm font-medium text-gray-900">
                  {formatCurrency(payment.amount / 100)}
                </td>
                <td className="px-6 py-4">
                  <Badge
                    variant={payment.status === 'completed' ? 'success' : 'warning'}
                    size="sm"
                  >
                    {payment.status === 'completed' ? 'Bezahlt' : payment.status}
                  </Badge>
                </td>
                <td className="px-6 py-4 text-right">
                  {payment.invoice_pdf_url && (
                    <a
                      href={payment.invoice_pdf_url}
                      className="text-blue-600 hover:text-blue-700 text-sm"
                      download
                    >
                      PDF
                    </a>
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

// Icons
const CheckIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
  </svg>
);

const InvoiceIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
  </svg>
);

export default Billing;
