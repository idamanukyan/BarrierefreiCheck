/**
 * Dashboard Page
 *
 * Main dashboard with stats, charts, and recent activity.
 */

import React from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, LineChart, Line } from 'recharts';
import { useTranslation } from '../hooks/useTranslation';
import { useAuthStore } from '../store/authStore';
import { dashboardApi } from '../services/api';
import { Card, CardHeader, CardTitle, CardContent, Button, StatusBadge, ScoreBadge, Alert } from '../components/common';

const Dashboard: React.FC = () => {
  const { t, formatDate, formatNumber } = useTranslation();
  const { user } = useAuthStore();

  const { data: stats, isLoading, error } = useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: () => dashboardApi.getStats(),
    refetchInterval: 30000, // Refresh every 30 seconds
  });

  if (isLoading) {
    return <DashboardSkeleton />;
  }

  if (error) {
    return (
      <Alert variant="error" title={t('errors.generic')}>
        {t('errors.serverError')}
      </Alert>
    );
  }

  // Mock data for empty state
  const hasData = stats && stats.totalScans > 0;

  return (
    <div className="space-y-6">
      {/* Welcome header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            {t('dashboard.welcome', { name: user?.name?.split(' ')[0] || 'User' })}
          </h1>
          <p className="mt-1 text-gray-500">{t('dashboard.overview')}</p>
        </div>
        <Link to="/scans/new">
          <Button icon={<PlusIcon className="h-5 w-5" />}>
            {t('dashboard.startScan')}
          </Button>
        </Link>
      </div>

      {/* Stats cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title={t('dashboard.stats.totalScans')}
          value={formatNumber(stats?.totalScans || 0)}
          icon={<ScanIcon className="h-6 w-6" />}
          color="blue"
        />
        <StatCard
          title={t('dashboard.stats.pagesScanned')}
          value={formatNumber(stats?.pagesScanned || 0)}
          icon={<PageIcon className="h-6 w-6" />}
          color="green"
        />
        <StatCard
          title={t('dashboard.stats.issuesFound')}
          value={formatNumber(stats?.issuesFound || 0)}
          icon={<IssueIcon className="h-6 w-6" />}
          color="yellow"
        />
        <StatCard
          title={t('dashboard.stats.averageScore')}
          value={`${stats?.averageScore || 0}%`}
          icon={<ScoreIcon className="h-6 w-6" />}
          color="purple"
        />
      </div>

      {hasData ? (
        <>
          {/* Charts row */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Issues by impact */}
            <Card>
              <CardHeader>
                <CardTitle>{t('dashboard.chart.issuesByImpact')}</CardTitle>
              </CardHeader>
              <CardContent>
                <IssuesByImpactChart data={stats?.issuesByImpact} />
              </CardContent>
            </Card>

            {/* Score over time */}
            <Card>
              <CardHeader>
                <CardTitle>{t('dashboard.chart.scoreOverTime')}</CardTitle>
              </CardHeader>
              <CardContent>
                <ScoreHistoryChart data={stats?.scoreHistory} />
              </CardContent>
            </Card>
          </div>

          {/* Recent scans */}
          <Card>
            <CardHeader
              action={
                <Link to="/scans" className="text-sm text-blue-600 hover:text-blue-700">
                  {t('dashboard.viewAllScans')}
                </Link>
              }
            >
              <CardTitle>{t('dashboard.recentScans')}</CardTitle>
            </CardHeader>
            <CardContent>
              <RecentScansList scans={stats?.recentScans || []} />
            </CardContent>
          </Card>
        </>
      ) : (
        <EmptyState />
      )}
    </div>
  );
};

// Stat card component
interface StatCardProps {
  title: string;
  value: string;
  icon: React.ReactNode;
  color: 'blue' | 'green' | 'yellow' | 'purple';
}

const StatCard: React.FC<StatCardProps> = ({ title, value, icon, color }) => {
  const colors = {
    blue: 'bg-blue-100 text-blue-600',
    green: 'bg-green-100 text-green-600',
    yellow: 'bg-yellow-100 text-yellow-600',
    purple: 'bg-purple-100 text-purple-600',
  };

  return (
    <Card>
      <div className="flex items-center">
        <div className={`p-3 rounded-lg ${colors[color]}`}>{icon}</div>
        <div className="ml-4">
          <p className="text-sm font-medium text-gray-500">{title}</p>
          <p className="text-2xl font-bold text-gray-900">{value}</p>
        </div>
      </div>
    </Card>
  );
};

// Issues by impact pie chart
const IMPACT_COLORS = {
  critical: '#dc2626',
  serious: '#f59e0b',
  moderate: '#8b5cf6',
  minor: '#6b7280',
};

interface IssuesByImpactChartProps {
  data?: Record<string, number>;
}

const IssuesByImpactChart: React.FC<IssuesByImpactChartProps> = ({ data }) => {
  const { t } = useTranslation();

  const chartData = data
    ? Object.entries(data).map(([key, value]) => ({
        name: t(`results.impact.${key}`),
        value,
        color: IMPACT_COLORS[key as keyof typeof IMPACT_COLORS],
      }))
    : [];

  if (chartData.every((d) => d.value === 0)) {
    return (
      <div className="h-64 flex items-center justify-center text-gray-500">
        {t('common.noResults')}
      </div>
    );
  }

  return (
    <div className="h-64">
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={chartData}
            cx="50%"
            cy="50%"
            innerRadius={60}
            outerRadius={80}
            paddingAngle={5}
            dataKey="value"
            label={({ name, value }) => `${name}: ${value}`}
          >
            {chartData.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.color} />
            ))}
          </Pie>
          <Tooltip />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
};

// Score history line chart
interface ScoreHistoryChartProps {
  data?: Array<{ date: string; score: number }>;
}

const ScoreHistoryChart: React.FC<ScoreHistoryChartProps> = ({ data }) => {
  const { t, formatDate } = useTranslation();

  if (!data || data.length === 0) {
    return (
      <div className="h-64 flex items-center justify-center text-gray-500">
        {t('common.noResults')}
      </div>
    );
  }

  return (
    <div className="h-64">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data}>
          <XAxis
            dataKey="date"
            tickFormatter={(value) => formatDate(value, { month: 'short', day: 'numeric' })}
          />
          <YAxis domain={[0, 100]} />
          <Tooltip
            formatter={(value: number) => [`${value}%`, 'Score']}
            labelFormatter={(label) => formatDate(label)}
          />
          <Line
            type="monotone"
            dataKey="score"
            stroke="#3b82f6"
            strokeWidth={2}
            dot={{ fill: '#3b82f6' }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};

// Recent scans list
interface RecentScansListProps {
  scans: Array<{
    id: string;
    url: string;
    status: string;
    score?: number;
    createdAt: string;
  }>;
}

const RecentScansList: React.FC<RecentScansListProps> = ({ scans }) => {
  const { t, formatDate, formatRelativeTime } = useTranslation();

  if (scans.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        {t('scan.list.empty')}
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200">
        <thead>
          <tr>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              {t('scan.list.columns.url')}
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              {t('scan.list.columns.status')}
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              {t('scan.list.columns.score')}
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              {t('scan.list.columns.date')}
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-200">
          {scans.map((scan) => (
            <tr key={scan.id} className="hover:bg-gray-50">
              <td className="px-4 py-4 whitespace-nowrap">
                <Link
                  to={`/scans/${scan.id}`}
                  className="text-blue-600 hover:text-blue-700 font-medium"
                >
                  {new URL(scan.url).hostname}
                </Link>
              </td>
              <td className="px-4 py-4 whitespace-nowrap">
                <StatusBadge status={scan.status as any} size="sm" />
              </td>
              <td className="px-4 py-4 whitespace-nowrap">
                {scan.score !== undefined ? (
                  <ScoreBadge score={scan.score} size="sm" />
                ) : (
                  '-'
                )}
              </td>
              <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-500">
                {formatRelativeTime(scan.createdAt)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

// Empty state
const EmptyState: React.FC = () => {
  const { t } = useTranslation();

  return (
    <Card className="text-center py-12">
      <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-blue-100">
        <ScanIcon className="h-8 w-8 text-blue-600" />
      </div>
      <h3 className="mt-4 text-lg font-semibold text-gray-900">
        {t('dashboard.empty.title')}
      </h3>
      <p className="mt-2 text-gray-500 max-w-md mx-auto">
        {t('dashboard.empty.description')}
      </p>
      <Link to="/scans/new" className="mt-6 inline-block">
        <Button size="lg" icon={<PlusIcon className="h-5 w-5" />}>
          {t('dashboard.empty.action')}
        </Button>
      </Link>
    </Card>
  );
};

// Loading skeleton
const DashboardSkeleton: React.FC = () => (
  <div className="space-y-6 animate-pulse">
    <div className="h-8 bg-gray-200 rounded w-1/3" />
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {[1, 2, 3, 4].map((i) => (
        <div key={i} className="h-24 bg-gray-200 rounded-lg" />
      ))}
    </div>
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <div className="h-80 bg-gray-200 rounded-lg" />
      <div className="h-80 bg-gray-200 rounded-lg" />
    </div>
  </div>
);

// Icons
const PlusIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
  </svg>
);

const ScanIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
  </svg>
);

const PageIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
  </svg>
);

const IssueIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
  </svg>
);

const ScoreIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
  </svg>
);

export default Dashboard;
