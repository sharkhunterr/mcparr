import { useState, useEffect, useCallback } from 'react';
import type { FC } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Activity, FileText, Bell, RefreshCw, Wifi, WifiOff, CheckCircle, XCircle, Clock, Play, Pause, Settings, Loader2 } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { api, apiClient, getApiBaseUrl } from '../lib/api';
import { LogViewer } from '../components/Observability/LogViewer';
import { AlertManager } from '../components/Observability/AlertManager';
import { getServiceColor } from '../lib/serviceColors';

interface SystemMetrics {
  cpu_usage: number;
  cpu_load_avg: number;
  memory_usage: number;
  memory_used: number;
  memory_total: number;
  disk_usage: number;
  disk_used: number;
  disk_total: number;
  network_bytes_sent: number;
  network_bytes_recv: number;
  services_running: number;
  services_total: number;
  uptime: number;
}

interface ServiceHealth {
  id: string;
  name: string;
  status: string;
  enabled: boolean;
  healthy: boolean;
  last_test_at: string | null;
  last_test_success: boolean | null;
  last_error: string | null;
}

interface AlertStats {
  total: number;
  active: number;
  by_severity: Record<string, number>;
  resolved_last_24h: number;
}

interface LogStats {
  total: number;
  by_level: Record<string, number>;
  by_source: Record<string, number>;
  error_rate: number;
  period_hours: number;
}

interface ServiceHealthHistoryRecord {
  tested_at: string;
  success: boolean;
  response_time_ms: number | null;
  error_message: string | null;
}

interface ServiceHealthHistory {
  service_id: string;
  service_name: string;
  service_type: string;
  enabled: boolean;
  history: ServiceHealthHistoryRecord[];
}

interface SchedulerStatus {
  enabled: boolean;
  interval_minutes: number;
  running: boolean;
  last_run: string | null;
  next_run: string | null;
}

type TabType = 'metrics' | 'logs' | 'alerts';

const MetricCard: React.FC<{
  title: string;
  value: string | number;
  subtitle?: string;
  color?: string;
  icon?: React.ReactNode;
}> = ({ title, value, subtitle, color = 'blue', icon }) => (
  <div className="bg-white dark:bg-gray-800 rounded-lg p-3 sm:p-4 shadow">
    <div className="flex items-center justify-between">
      <div className="min-w-0 flex-1">
        <p className="text-xs sm:text-sm text-gray-500 dark:text-gray-400 truncate">{title}</p>
        <p className={`text-lg sm:text-2xl font-bold text-${color}-600 dark:text-${color}-400 truncate`}>
          {value}
        </p>
        {subtitle && (
          <p className="text-xs text-gray-400 dark:text-gray-500 mt-1 truncate">{subtitle}</p>
        )}
      </div>
      {icon && (
        <div className={`text-${color}-500 opacity-50 hidden sm:block ml-2`}>{icon}</div>
      )}
    </div>
  </div>
);

const ProgressBar: React.FC<{
  value: number;
  max?: number;
  color?: string;
  showLabel?: boolean;
}> = ({ value, max = 100, color = 'blue', showLabel = true }) => {
  const percentage = Math.min((value / max) * 100, 100);
  const barColor = percentage > 90 ? 'red' : percentage > 70 ? 'yellow' : color;

  return (
    <div className="w-full">
      <div className="flex justify-between items-center mb-1">
        {showLabel && (
          <span className="text-xs sm:text-sm text-gray-600 dark:text-gray-400">
            {percentage.toFixed(1)}%
          </span>
        )}
      </div>
      <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
        <div
          className={`bg-${barColor}-500 h-2 rounded-full transition-all duration-300`}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
};

// Service Uptime Bar Chart Component
// Shows the last N tests as bars (one bar per test, not per time interval)
const ServiceUptimeChart: React.FC<{
  healthHistory: ServiceHealthHistory[];
  intervalMinutes: number;
}> = ({ healthHistory, intervalMinutes }) => {
  const { t } = useTranslation('monitoring');
  // Number of bars to display - show enough to cover ~24h worth of tests
  const maxBars = Math.min(Math.ceil((24 * 60) / intervalMinutes), 48);

  if (healthHistory.length === 0) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg p-4 sm:p-6 shadow">
        <h2 className="text-base sm:text-lg font-medium text-gray-900 dark:text-white mb-4">
          {t('serviceContinuity.title')}
        </h2>
        <p className="text-gray-500 dark:text-gray-400 text-center py-4">
          {t('serviceContinuity.noHistory')}
        </p>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg p-4 sm:p-6 shadow">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-base sm:text-lg font-medium text-gray-900 dark:text-white">
          {t('serviceContinuity.title')}
        </h2>
        <div className="flex items-center gap-3 text-xs">
          <div className="flex items-center gap-1">
            <div className="w-3 h-3 rounded-sm bg-green-500" />
            <span className="text-gray-500 dark:text-gray-400">{t('serviceContinuity.ok')}</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-3 h-3 rounded-sm bg-red-500" />
            <span className="text-gray-500 dark:text-gray-400">{t('serviceContinuity.error')}</span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {healthHistory.map((service) => {
          const colors = getServiceColor(service.service_type);
          const Icon = colors.icon;

          // Take the last N tests (already sorted by most recent first)
          const tests = service.history.slice(0, maxBars);

          // Reverse to show oldest first (left to right chronological)
          const displayTests = [...tests].reverse();

          // Calculate uptime percentage
          const totalTests = tests.length;
          const successTests = tests.filter(h => h.success).length;
          const uptimePercent = totalTests > 0
            ? (successTests / totalTests * 100).toFixed(1)
            : '---';
          const currentStatus = service.history[0]?.success;

          return (
            <div key={service.service_id} className="p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 min-w-0">
                  <div className={`p-1.5 rounded flex-shrink-0 ${colors.bg}`}>
                    <Icon className={`w-3.5 h-3.5 ${colors.text}`} />
                  </div>
                  <span className="text-sm font-medium text-gray-900 dark:text-white truncate">
                    {service.service_name}
                  </span>
                </div>
                <div className="flex items-center gap-1.5 flex-shrink-0">
                  <span className={`text-xs font-medium ${
                    currentStatus === true ? 'text-green-600 dark:text-green-400' :
                    currentStatus === false ? 'text-red-600 dark:text-red-400' :
                    'text-gray-500 dark:text-gray-400'
                  }`}>
                    {uptimePercent}%
                  </span>
                  {currentStatus === true && <CheckCircle className="w-3.5 h-3.5 text-green-500" />}
                  {currentStatus === false && <XCircle className="w-3.5 h-3.5 text-red-500" />}
                  {currentStatus === undefined && <Clock className="w-3.5 h-3.5 text-gray-400" />}
                </div>
              </div>

              {/* Bar chart - one bar per test */}
              <div className="flex items-center gap-px h-4">
                {displayTests.length === 0 ? (
                  <div className="flex-1 h-full rounded-sm bg-gray-300 dark:bg-gray-600" title="Pas de test" />
                ) : (
                  displayTests.map((test, idx) => {
                    const barClass = test.success ? 'bg-green-500' : 'bg-red-500';

                    // Format time for tooltip
                    const timestamp = test.tested_at.endsWith('Z') ? test.tested_at : test.tested_at + 'Z';
                    const date = new Date(timestamp);
                    const time = date.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
                    const status = test.success ? t('serviceContinuity.ok') : t('status.error');
                    const tooltip = `${time} - ${status}`;

                    return (
                      <div
                        key={idx}
                        className={`flex-1 h-full rounded-sm ${barClass}`}
                        title={tooltip}
                      />
                    );
                  })
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

// Scheduler Controls Component
const SchedulerControls: React.FC<{
  scheduler: SchedulerStatus | null;
  onRefresh: () => void;
}> = ({ scheduler, onRefresh }) => {
  const { t } = useTranslation('monitoring');
  const [loading, setLoading] = useState(false);
  const [selectedInterval, setSelectedInterval] = useState(15);
  const [showSettings, setShowSettings] = useState(false);

  const intervalOptions = [
    { value: 5, label: t('scheduler.intervals.5min') },
    { value: 15, label: t('scheduler.intervals.15min') },
    { value: 30, label: t('scheduler.intervals.30min') },
    { value: 60, label: t('scheduler.intervals.1hour') },
  ];

  const handleToggle = async () => {
    setLoading(true);
    try {
      if (scheduler?.enabled) {
        await fetch(`${getApiBaseUrl()}/api/services/health/scheduler/stop`, { method: 'POST' });
      } else {
        await fetch(`${getApiBaseUrl()}/api/services/health/scheduler/start?interval_minutes=${selectedInterval}`, { method: 'POST' });
      }
      onRefresh();
    } catch (error) {
      console.error('Failed to toggle scheduler:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleRunNow = async () => {
    setLoading(true);
    try {
      await fetch(`${getApiBaseUrl()}/api/services/health/scheduler/run-now`, { method: 'POST' });
      onRefresh();
    } catch (error) {
      console.error('Failed to run health checks:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleIntervalChange = async (minutes: number) => {
    setSelectedInterval(minutes);
    if (scheduler?.enabled) {
      setLoading(true);
      try {
        await fetch(`${getApiBaseUrl()}/api/services/health/scheduler/interval?interval_minutes=${minutes}`, { method: 'PUT' });
        onRefresh();
      } catch (error) {
        console.error('Failed to update interval:', error);
      } finally {
        setLoading(false);
      }
    }
  };

  const formatLastRun = (lastRun: string | null) => {
    if (!lastRun) return t('scheduler.never');
    const date = new Date(lastRun);
    return date.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow mb-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className={`p-2 rounded-lg ${scheduler?.enabled ? 'bg-green-100 dark:bg-green-900/30' : 'bg-gray-100 dark:bg-gray-700'}`}>
            <Clock className={`w-5 h-5 ${scheduler?.enabled ? 'text-green-600 dark:text-green-400' : 'text-gray-500'}`} />
          </div>
          <div>
            <h3 className="text-sm font-medium text-gray-900 dark:text-white">
              {t('scheduler.title')}
            </h3>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              {scheduler?.enabled
                ? t('scheduler.active', { interval: scheduler.interval_minutes })
                : t('scheduler.disabled')}
              {scheduler?.last_run && ` • ${t('scheduler.lastRun')}: ${formatLastRun(scheduler.last_run)}`}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Settings toggle */}
          <button
            onClick={() => setShowSettings(!showSettings)}
            className={`p-2 rounded-lg transition-colors ${
              showSettings
                ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400'
                : 'hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-500'
            }`}
            title={t('scheduler.settings')}
          >
            <Settings className="w-4 h-4" />
          </button>

          {/* Run now button */}
          <button
            onClick={handleRunNow}
            disabled={loading || scheduler?.running}
            className="px-3 py-1.5 text-sm bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 rounded-lg hover:bg-blue-200 dark:hover:bg-blue-900/50 transition-colors disabled:opacity-50 flex items-center gap-1.5"
          >
            {loading || scheduler?.running ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Play className="w-4 h-4" />
            )}
            {t('scheduler.test')}
          </button>

          {/* Toggle button */}
          <button
            onClick={handleToggle}
            disabled={loading}
            className={`px-3 py-1.5 text-sm rounded-lg transition-colors flex items-center gap-1.5 ${
              scheduler?.enabled
                ? 'bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400 hover:bg-red-200 dark:hover:bg-red-900/50'
                : 'bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400 hover:bg-green-200 dark:hover:bg-green-900/50'
            } disabled:opacity-50`}
          >
            {scheduler?.enabled ? (
              <>
                <Pause className="w-4 h-4" />
                {t('scheduler.stop')}
              </>
            ) : (
              <>
                <Play className="w-4 h-4" />
                {t('scheduler.enable')}
              </>
            )}
          </button>
        </div>
      </div>

      {/* Settings panel */}
      {showSettings && (
        <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-4">
            <span className="text-sm text-gray-600 dark:text-gray-400">{t('scheduler.interval')}:</span>
            <div className="flex gap-2">
              {intervalOptions.map(option => (
                <button
                  key={option.value}
                  onClick={() => handleIntervalChange(option.value)}
                  className={`px-3 py-1 text-xs rounded-lg transition-colors ${
                    (scheduler?.enabled ? scheduler.interval_minutes : selectedInterval) === option.value
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
                  }`}
                >
                  {option.label}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

const formatUptime = (seconds: number): string => {
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);

  if (days > 0) return `${days}d ${hours}h`;
  if (hours > 0) return `${hours}h ${minutes}m`;
  return `${minutes}m`;
};

const formatBytes = (bytes: number): string => {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

// Metrics Tab Content
const MetricsTab: React.FC<{
  metrics: SystemMetrics | null;
  services: ServiceHealth[];
  healthHistory: ServiceHealthHistory[];
  alertStats: AlertStats | null;
  logStats: LogStats | null;
  loading: boolean;
  scheduler: SchedulerStatus | null;
  onRefresh: () => void;
}> = ({ metrics, services, healthHistory, alertStats, logStats, loading, scheduler, onRefresh }) => {
  const { t } = useTranslation('monitoring');
  const healthyServices = services.filter(s => s.healthy && s.enabled).length;
  const enabledServices = services.filter(s => s.enabled).length;

  if (loading) {
    return <div className="text-center py-12 text-gray-500">{t('metrics.loadingMetrics')}</div>;
  }

  return (
    <div className="space-y-4 sm:space-y-6">
      {/* System Resources */}
      <div className="bg-white dark:bg-gray-800 rounded-lg p-4 sm:p-6 shadow">
        <h2 className="text-base sm:text-lg font-medium text-gray-900 dark:text-white mb-4">
          {t('systemResources.title')}
        </h2>
        {metrics ? (
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-6">
            <div>
              <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center mb-2">
                <span className="text-xs sm:text-sm font-medium text-gray-700 dark:text-gray-300">{t('systemResources.cpu')}</span>
                <span className="text-xs sm:text-sm text-gray-500">{metrics.cpu_usage.toFixed(1)}%</span>
              </div>
              <ProgressBar value={metrics.cpu_usage} color="blue" showLabel={false} />
            </div>

            <div>
              <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center mb-2">
                <span className="text-xs sm:text-sm font-medium text-gray-700 dark:text-gray-300">{t('systemResources.memory')}</span>
                <span className="text-xs sm:text-sm text-gray-500 truncate">
                  {(metrics.memory_used / (1024 ** 3)).toFixed(1)}/{(metrics.memory_total / (1024 ** 3)).toFixed(0)}GB
                </span>
              </div>
              <ProgressBar value={metrics.memory_usage} color="green" showLabel={false} />
            </div>

            <div>
              <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center mb-2">
                <span className="text-xs sm:text-sm font-medium text-gray-700 dark:text-gray-300">{t('systemResources.disk')}</span>
                <span className="text-xs sm:text-sm text-gray-500 truncate">
                  {(metrics.disk_used / (1024 ** 3)).toFixed(0)}/{(metrics.disk_total / (1024 ** 3)).toFixed(0)}GB
                </span>
              </div>
              <ProgressBar value={metrics.disk_usage} color="purple" showLabel={false} />
            </div>

            <div>
              <div className="flex justify-between items-center mb-2">
                <span className="text-xs sm:text-sm font-medium text-gray-700 dark:text-gray-300">{t('systemResources.uptime')}</span>
              </div>
              <p className="text-lg sm:text-2xl font-bold text-gray-900 dark:text-white">
                {formatUptime(metrics.uptime)}
              </p>
            </div>
          </div>
        ) : (
          <p className="text-gray-500 dark:text-gray-400">{t('systemResources.failed')}</p>
        )}
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        <MetricCard
          title={t('metrics.services')}
          value={`${healthyServices}/${enabledServices}`}
          subtitle={t('metrics.healthyServices')}
          color={healthyServices === enabledServices ? 'green' : 'yellow'}
        />
        <MetricCard
          title={t('metrics.activeAlerts')}
          value={alertStats?.active || 0}
          subtitle={`${alertStats?.total || 0} ${t('metrics.configs')}`}
          color={(alertStats?.active || 0) > 0 ? 'red' : 'green'}
        />
        <MetricCard
          title={t('metrics.logs24h')}
          value={logStats?.total?.toLocaleString() || 0}
          subtitle={`${logStats?.error_rate?.toFixed(1) || 0}% ${t('metrics.errorRate')}`}
          color={(logStats?.error_rate || 0) > 10 ? 'red' : 'blue'}
        />
        <MetricCard
          title={t('metrics.networkIO')}
          value={metrics ? formatBytes(metrics.network_bytes_recv + metrics.network_bytes_sent) : '-'}
          subtitle={t('metrics.totalTransferred')}
          color="purple"
        />
      </div>

      {/* Scheduler Controls & Service Uptime Chart */}
      <SchedulerControls scheduler={scheduler} onRefresh={onRefresh} />
      <ServiceUptimeChart healthHistory={healthHistory} intervalMinutes={scheduler?.interval_minutes || 15} />

      {/* Log Distribution */}
      {logStats && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 sm:gap-6">
          <div className="bg-white dark:bg-gray-800 rounded-lg p-4 sm:p-6 shadow">
            <h2 className="text-base sm:text-lg font-medium text-gray-900 dark:text-white mb-4">
              {t('logDistribution.byLevel')}
            </h2>
            <div className="space-y-3">
              {Object.entries(logStats.by_level).map(([level, count]) => {
                const colors: Record<string, string> = {
                  debug: 'gray',
                  info: 'blue',
                  warning: 'yellow',
                  error: 'red',
                  critical: 'purple',
                };
                const color = colors[level] || 'gray';
                const percentage = logStats.total > 0 ? (count / logStats.total) * 100 : 0;

                return (
                  <div key={level}>
                    <div className="flex justify-between items-center mb-1">
                      <span className={`text-xs sm:text-sm font-medium capitalize text-${color}-600 dark:text-${color}-400`}>
                        {level}
                      </span>
                      <span className="text-xs sm:text-sm text-gray-500">{count}</span>
                    </div>
                    <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                      <div
                        className={`bg-${color}-500 h-2 rounded-full`}
                        style={{ width: `${percentage}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-lg p-4 sm:p-6 shadow">
            <h2 className="text-base sm:text-lg font-medium text-gray-900 dark:text-white mb-4">
              {t('logDistribution.bySource')}
            </h2>
            <div className="space-y-3">
              {Object.entries(logStats.by_source).map(([source, count]) => {
                const percentage = logStats.total > 0 ? (count / logStats.total) * 100 : 0;

                return (
                  <div key={source}>
                    <div className="flex justify-between items-center mb-1">
                      <span className="text-xs sm:text-sm font-medium text-gray-700 dark:text-gray-300 truncate">
                        {source}
                      </span>
                      <span className="text-xs sm:text-sm text-gray-500 ml-2">{count}</span>
                    </div>
                    <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                      <div
                        className="bg-blue-500 h-2 rounded-full"
                        style={{ width: `${percentage}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* Alert Summary */}
      {alertStats && alertStats.active > 0 && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 sm:p-6">
          <h2 className="text-base sm:text-lg font-medium text-red-900 dark:text-red-100 mb-4">
            {t('alertSummary.title', { count: alertStats.active })}
          </h2>
          <div className="flex flex-wrap gap-2 sm:gap-4">
            {Object.entries(alertStats.by_severity || {}).map(([severity, count]) => {
              if (count === 0) return null;
              const colors: Record<string, string> = {
                low: 'blue',
                medium: 'yellow',
                high: 'orange',
                critical: 'red',
              };
              const color = colors[severity] || 'gray';

              return (
                <div
                  key={severity}
                  className={`px-3 py-1 sm:px-4 sm:py-2 rounded-lg bg-${color}-100 dark:bg-${color}-900/40`}
                >
                  <span className={`text-xs sm:text-sm font-medium capitalize text-${color}-700 dark:text-${color}-300`}>
                    {severity}: {count}
                  </span>
                </div>
              );
            })}
          </div>
          <p className="text-xs sm:text-sm text-red-700 dark:text-red-300 mt-4">
            {t('alertSummary.resolved24h', { count: alertStats.resolved_last_24h })}
          </p>
        </div>
      )}
    </div>
  );
};

const Monitoring: FC = () => {
  const { t } = useTranslation('monitoring');
  const [searchParams, setSearchParams] = useSearchParams();
  const initialTab = (searchParams.get('tab') as TabType) || 'metrics';
  const [activeTab, setActiveTab] = useState<TabType>(initialTab);

  // Update URL when tab changes
  const handleTabChange = (tab: TabType) => {
    setActiveTab(tab);
    if (tab === 'metrics') {
      searchParams.delete('tab');
    } else {
      searchParams.set('tab', tab);
    }
    setSearchParams(searchParams, { replace: true });
  };
  const [metrics, setMetrics] = useState<SystemMetrics | null>(null);
  const [services, setServices] = useState<ServiceHealth[]>([]);
  const [healthHistory, setHealthHistory] = useState<ServiceHealthHistory[]>([]);
  const [alertStats, setAlertStats] = useState<AlertStats | null>(null);
  const [logStats, setLogStats] = useState<LogStats | null>(null);
  const [scheduler, setScheduler] = useState<SchedulerStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const fetchData = useCallback(async () => {
    try {
      const [metricsRes, servicesRes, alertStatsRes, logStatsRes, healthHistoryRes, schedulerRes] = await Promise.all([
        api.system.currentMetrics().catch(() => null),
        api.services.list().catch(() => []),
        api.alerts.stats(24).catch(() => null),
        api.logs.stats(24).catch(() => null),
        fetch(`${getApiBaseUrl()}/api/services/health/history?hours=24`).then(r => r.json()).catch(() => []),
        fetch(`${getApiBaseUrl()}/api/services/health/scheduler/status`).then(r => r.json()).catch(() => null),
      ]);

      if (metricsRes) setMetrics(metricsRes);
      if (Array.isArray(servicesRes)) {
        const healthPromises = servicesRes.map(async (service: any) => {
          try {
            const health = await apiClient.get(`/api/services/${service.id}/health`);
            return health;
          } catch {
            return {
              id: service.id,
              name: service.name,
              status: service.status,
              enabled: service.enabled,
              healthy: false,
              last_test_at: null,
              last_test_success: null,
              last_error: 'Unable to fetch health',
            };
          }
        });
        const healthResults = await Promise.all(healthPromises);
        setServices(healthResults);
      }
      if (alertStatsRes) setAlertStats(alertStatsRes);
      if (logStatsRes) setLogStats(logStatsRes);
      if (Array.isArray(healthHistoryRes)) setHealthHistory(healthHistoryRes);
      if (schedulerRes) setScheduler(schedulerRes);

      setLastUpdated(new Date());
    } catch (error) {
      console.error('Failed to fetch monitoring data:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  useEffect(() => {
    if (autoRefresh && activeTab === 'metrics') {
      const interval = setInterval(fetchData, 10000);
      return () => clearInterval(interval);
    }
  }, [autoRefresh, fetchData, activeTab]);

  const tabs = [
    { id: 'metrics' as TabType, label: t('tabs.metrics'), icon: Activity },
    { id: 'logs' as TabType, label: t('tabs.logs'), icon: FileText },
    { id: 'alerts' as TabType, label: t('tabs.alerts'), icon: Bell, badge: alertStats?.active },
  ];

  return (
    <div className="p-4 sm:p-6 space-y-4 sm:space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <Activity className="w-6 h-6 sm:w-8 sm:h-8 text-blue-600" />
            {t('title')}
          </h1>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
            {t('subtitle')}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2 sm:gap-3">
          {activeTab === 'metrics' && lastUpdated && (
            <span className="text-xs sm:text-sm text-gray-500 dark:text-gray-400 flex items-center gap-1">
              {autoRefresh ? (
                <Wifi className="w-3 h-3 sm:w-4 sm:h-4 text-green-500" />
              ) : (
                <WifiOff className="w-3 h-3 sm:w-4 sm:h-4 text-gray-400" />
              )}
              <span className="hidden sm:inline">{t('updatedAt')}:</span> {lastUpdated.toLocaleTimeString()}
            </span>
          )}
          {activeTab === 'metrics' && (
            <label className="flex items-center gap-2 text-xs sm:text-sm text-gray-600 dark:text-gray-400">
              <input
                type="checkbox"
                checked={autoRefresh}
                onChange={(e) => setAutoRefresh(e.target.checked)}
                className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <span className="hidden sm:inline">{t('autoRefresh')}</span>
            </label>
          )}
          <button
            onClick={fetchData}
            className="p-2 sm:px-4 sm:py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors flex items-center gap-2"
          >
            <RefreshCw className="w-4 h-4" />
            <span className="hidden sm:inline">{t('actions.refresh')}</span>
          </button>
        </div>
      </div>

      {/* Tabs Navigation */}
      <div className="overflow-x-auto -mx-4 px-4 sm:mx-0 sm:px-0">
        <nav className="flex gap-1.5 sm:gap-2 min-w-max sm:min-w-0 sm:flex-wrap">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => handleTabChange(tab.id)}
              className={`flex items-center gap-1.5 py-1.5 px-2.5 sm:py-2 sm:px-3 rounded-full font-medium text-xs sm:text-sm transition-all whitespace-nowrap ${
                activeTab === tab.id
                  ? 'bg-blue-600 text-white shadow-sm'
                  : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
              }`}
            >
              <tab.icon className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
              <span>{tab.label}</span>
              {tab.badge !== undefined && tab.badge > 0 && (
                <span className={`px-1.5 py-0.5 rounded-full text-xs ${
                  activeTab === tab.id
                    ? 'bg-white/20 text-white'
                    : 'bg-red-100 text-red-600 dark:bg-red-900 dark:text-red-400'
                }`}>
                  {tab.badge}
                </span>
              )}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      <div>
        {activeTab === 'metrics' && (
          <MetricsTab
            metrics={metrics}
            services={services}
            healthHistory={healthHistory}
            alertStats={alertStats}
            logStats={logStats}
            loading={loading}
            scheduler={scheduler}
            onRefresh={fetchData}
          />
        )}
        {activeTab === 'logs' && <LogViewer />}
        {activeTab === 'alerts' && <AlertManager />}
      </div>
    </div>
  );
};

export default Monitoring;
