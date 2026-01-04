import { useState, useEffect, useCallback } from 'react';
import type { FC, FormEvent } from 'react';
import { useTranslation } from 'react-i18next';
import { Bell, Plus, Trash2, Power, CheckCircle, AlertTriangle, X } from 'lucide-react';
import { api } from '../../lib/api';

interface AlertConfig {
  id: string;
  name: string;
  description: string | null;
  enabled: boolean;
  severity: string;
  metric_type: string;
  threshold_operator: string;
  threshold_value: number;
  duration_seconds: number;
  service_id: string | null;
  service_type: string | null;
  notification_channels: string[];
  notification_config: Record<string, any>;
  cooldown_minutes: number;
  last_triggered_at: string | null;
  trigger_count: number;
  is_firing: boolean;
  tags: Record<string, string>;
  created_at: string;
  updated_at: string;
}

interface AlertHistory {
  id: string;
  alert_config_id: string;
  alert_name: string;
  severity: string;
  triggered_at: string;
  resolved_at: string | null;
  is_resolved: boolean;
  metric_value: number;
  threshold_value: number;
  service_id: string | null;
  message: string;
  notifications_sent: boolean;
  notification_details: Record<string, any>;
  acknowledged: boolean;
  acknowledged_at: string | null;
  acknowledged_by: string | null;
  created_at: string;
}

interface AlertStats {
  total_triggered: number;
  active_count: number;
  by_severity: Record<string, number>;
  mttr_seconds: number;
  mttr_formatted: string;
  period_hours: number;
}

// Metric categories for better organization
type MetricCategory = 'system' | 'services' | 'mcp' | 'users' | 'training';

interface MetricTypeConfig {
  value: string;
  category: MetricCategory;
  isEvent: boolean; // Event-based metrics don't need threshold
  defaultOperator: string;
  defaultThreshold: number;
  unit?: string;
}

// Configuration for each metric type
const metricTypeConfigs: MetricTypeConfig[] = [
  // System metrics (need thresholds)
  { value: 'cpu', category: 'system', isEvent: false, defaultOperator: 'gt', defaultThreshold: 80, unit: '%' },
  { value: 'memory', category: 'system', isEvent: false, defaultOperator: 'gt', defaultThreshold: 85, unit: '%' },
  { value: 'disk', category: 'system', isEvent: false, defaultOperator: 'gt', defaultThreshold: 90, unit: '%' },

  // Service metrics
  { value: 'service_down', category: 'services', isEvent: true, defaultOperator: 'eq', defaultThreshold: 1 },
  { value: 'service_test_failed', category: 'services', isEvent: true, defaultOperator: 'eq', defaultThreshold: 1 },
  { value: 'service_latency', category: 'services', isEvent: false, defaultOperator: 'gt', defaultThreshold: 5000, unit: 'ms' },

  // MCP metrics
  { value: 'mcp_error_rate', category: 'mcp', isEvent: false, defaultOperator: 'gt', defaultThreshold: 10, unit: '%' },
  { value: 'mcp_request_volume', category: 'mcp', isEvent: false, defaultOperator: 'gt', defaultThreshold: 1000 },
  { value: 'mcp_duration', category: 'mcp', isEvent: false, defaultOperator: 'gt', defaultThreshold: 10000, unit: 'ms' },

  // User metrics
  { value: 'user_sync_failed', category: 'users', isEvent: true, defaultOperator: 'eq', defaultThreshold: 1 },
  { value: 'user_permission_denied', category: 'users', isEvent: false, defaultOperator: 'gt', defaultThreshold: 10 },

  // Training/Worker metrics
  { value: 'worker_offline', category: 'training', isEvent: true, defaultOperator: 'eq', defaultThreshold: 1 },
  { value: 'worker_gpu_usage', category: 'training', isEvent: false, defaultOperator: 'gt', defaultThreshold: 95, unit: '%' },
  { value: 'training_failed', category: 'training', isEvent: true, defaultOperator: 'eq', defaultThreshold: 1 },

  // Log-based metrics
  { value: 'error_rate', category: 'system', isEvent: false, defaultOperator: 'gt', defaultThreshold: 5, unit: '%' },
  { value: 'log_volume', category: 'system', isEvent: false, defaultOperator: 'gt', defaultThreshold: 10000 },
];

const severityColors: Record<string, string> = {
  low: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
  medium: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300',
  high: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300',
  critical: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300',
};

export const AlertManager: FC = () => {
  const { t } = useTranslation('monitoring');
  const { t: tCommon } = useTranslation('common');

  const [activeTab, setActiveTab] = useState<'active' | 'configs' | 'history'>('active');
  const [configs, setConfigs] = useState<AlertConfig[]>([]);
  const [history, setHistory] = useState<AlertHistory[]>([]);
  const [activeAlerts, setActiveAlerts] = useState<AlertHistory[]>([]);
  const [stats, setStats] = useState<AlertStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);

  const fetchData = useCallback(async () => {
    try {
      const [configsRes, historyRes, activeRes, statsRes] = await Promise.all([
        api.alerts.configs.list(),
        api.alerts.history.list({ limit: 50 }),
        api.alerts.history.active(),
        api.alerts.stats(24),
      ]);
      setConfigs(configsRes.items);
      setHistory(historyRes.items);
      setActiveAlerts(activeRes);
      setStats(statsRes);
    } catch (error) {
      console.error('Failed to fetch alerts:', error);
    }
  }, []);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      await fetchData();
      setLoading(false);
    };
    load();
  }, [fetchData]);

  const handleToggleConfig = async (config: AlertConfig) => {
    try {
      await api.alerts.configs.toggle(config.id, !config.enabled);
      fetchData();
    } catch (error) {
      console.error('Failed to toggle alert:', error);
    }
  };

  const handleDeleteConfig = async (id: string) => {
    if (!confirm(t('alerts.confirmDelete'))) return;
    try {
      await api.alerts.configs.delete(id);
      fetchData();
    } catch (error) {
      console.error('Failed to delete alert:', error);
    }
  };

  const handleResolveAlert = async (id: string) => {
    try {
      await api.alerts.history.resolve(id, t('alerts.manuallyResolved'));
      fetchData();
    } catch (error) {
      console.error('Failed to resolve alert:', error);
    }
  };

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleString();
  };

  const getMetricLabel = (metricType: string) => {
    return t(`alerts.metricTypes.${metricType}`, { defaultValue: metricType });
  };

  const getOperatorLabel = (operator: string) => {
    const labels: Record<string, string> = {
      gt: '>',
      lt: '<',
      eq: '=',
      ne: '≠',
      gte: '≥',
      lte: '≤',
    };
    return labels[operator] || operator;
  };

  const getConditionDisplay = (config: AlertConfig) => {
    const metricConfig = metricTypeConfigs.find(m => m.value === config.metric_type);
    if (metricConfig?.isEvent) {
      return t('alerts.eventTrigger');
    }
    const unit = metricConfig?.unit || '';
    return `${getOperatorLabel(config.threshold_operator)} ${config.threshold_value}${unit}`;
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900 dark:text-white">
            {t('alerts.title')}
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            {t('alerts.subtitle')}
          </p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors self-start sm:self-auto"
        >
          <Plus className="w-4 h-4" />
          <span className="hidden sm:inline">{t('alerts.create')}</span>
        </button>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-2 sm:gap-4">
          <div className="bg-white dark:bg-gray-800 rounded-lg p-2.5 sm:p-4 shadow">
            <div className="text-xs sm:text-sm text-gray-500 dark:text-gray-400 truncate">{t('alerts.stats.active')}</div>
            <div className={`text-lg sm:text-2xl font-bold ${stats.active_count > 0 ? 'text-red-600 dark:text-red-400' : 'text-green-600 dark:text-green-400'}`}>
              {stats.active_count}
            </div>
          </div>
          <div className="bg-white dark:bg-gray-800 rounded-lg p-2.5 sm:p-4 shadow">
            <div className="text-xs sm:text-sm text-gray-500 dark:text-gray-400 truncate">{t('alerts.stats.triggered24h')}</div>
            <div className="text-lg sm:text-2xl font-bold text-gray-900 dark:text-white">
              {stats.total_triggered}
            </div>
          </div>
          <div className="bg-white dark:bg-gray-800 rounded-lg p-2.5 sm:p-4 shadow">
            <div className="text-xs sm:text-sm text-gray-500 dark:text-gray-400 truncate">{t('alerts.stats.mttr')}</div>
            <div className="text-lg sm:text-2xl font-bold text-gray-900 dark:text-white">
              {stats.mttr_formatted || '—'}
            </div>
          </div>
          <div className="bg-white dark:bg-gray-800 rounded-lg p-2.5 sm:p-4 shadow">
            <div className="text-xs sm:text-sm text-gray-500 dark:text-gray-400 truncate">{t('alerts.stats.critical24h')}</div>
            <div className="text-lg sm:text-2xl font-bold text-red-600 dark:text-red-400">
              {stats.by_severity?.critical || 0}
            </div>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="border-b border-gray-200 dark:border-gray-700">
        <nav className="flex -mb-px space-x-8">
          {[
            { id: 'active', labelKey: 'alerts.tabs.active', count: activeAlerts.length },
            { id: 'configs', labelKey: 'alerts.tabs.configs', count: configs.length },
            { id: 'history', labelKey: 'alerts.tabs.history' },
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as typeof activeTab)}
              className={`py-4 px-1 border-b-2 font-medium text-sm ${
                activeTab === tab.id
                  ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                  : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300'
              }`}
            >
              {t(tab.labelKey)}
              {tab.count !== undefined && (
                <span className={`ml-2 px-2 py-0.5 rounded-full text-xs ${
                  tab.id === 'active' && tab.count > 0
                    ? 'bg-red-100 text-red-600 dark:bg-red-900/30 dark:text-red-400'
                    : 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400'
                }`}>
                  {tab.count}
                </span>
              )}
            </button>
          ))}
        </nav>
      </div>

      {/* Content */}
      {loading ? (
        <div className="p-8 text-center text-gray-500 dark:text-gray-400">{tCommon('common.loading')}</div>
      ) : (
        <>
          {/* Active Alerts */}
          {activeTab === 'active' && (
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden">
              {activeAlerts.length === 0 ? (
                <div className="p-8 text-center text-gray-500 dark:text-gray-400">
                  <CheckCircle className="w-12 h-12 mx-auto mb-4 text-green-500" />
                  {t('alerts.noActive')}
                </div>
              ) : (
                <ul className="divide-y divide-gray-200 dark:divide-gray-700">
                  {activeAlerts.map(alert => (
                    <li key={alert.id} className="p-4">
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                        <div className="flex items-start sm:items-center gap-3">
                          <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full whitespace-nowrap ${severityColors[alert.severity]}`}>
                            {t(`alerts.severity.${alert.severity}`)}
                          </span>
                          <div className="min-w-0">
                            <h4 className="text-sm font-medium text-gray-900 dark:text-white truncate">
                              {alert.alert_name}
                            </h4>
                            <p className="text-xs sm:text-sm text-gray-500 dark:text-gray-400">
                              {formatTimestamp(alert.triggered_at)}
                            </p>
                          </div>
                        </div>
                        <button
                          onClick={() => handleResolveAlert(alert.id)}
                          className="inline-flex items-center gap-1 px-3 py-1.5 text-sm bg-green-600 text-white rounded hover:bg-green-700 transition-colors ml-auto sm:ml-0"
                          title={t('alerts.resolve')}
                        >
                          <CheckCircle className="w-4 h-4" />
                          <span className="hidden sm:inline">{t('alerts.resolve')}</span>
                        </button>
                      </div>
                      <p className="mt-2 text-sm text-gray-600 dark:text-gray-400 break-words">
                        {alert.message}
                      </p>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}

          {/* Configurations */}
          {activeTab === 'configs' && (
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden">
              {configs.length === 0 ? (
                <div className="p-8 text-center text-gray-500 dark:text-gray-400">
                  <Bell className="w-12 h-12 mx-auto mb-4 text-gray-400" />
                  {t('alerts.noConfigs')}
                </div>
              ) : (
                <>
                  {/* Mobile view - Cards */}
                  <ul className="divide-y divide-gray-200 dark:divide-gray-700 sm:hidden">
                    {configs.map(config => (
                      <li key={config.id} className="p-4">
                        <div className="flex items-start justify-between gap-3">
                          <div className="min-w-0 flex-1">
                            <div className="flex items-center gap-2 flex-wrap mb-2">
                              <span className={`inline-flex px-2 py-0.5 text-xs font-medium rounded ${severityColors[config.severity]}`}>
                                {t(`alerts.severity.${config.severity}`)}
                              </span>
                              {config.is_firing && (
                                <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-full bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300">
                                  <AlertTriangle className="w-3 h-3" />
                                  {t('alerts.firing')}
                                </span>
                              )}
                              <span className={`inline-flex px-2 py-0.5 text-xs font-medium rounded-full ${
                                config.enabled
                                  ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300'
                                  : 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300'
                              }`}>
                                {config.enabled ? tCommon('status.enabled') : tCommon('status.disabled')}
                              </span>
                            </div>
                            <div className="text-sm font-medium text-gray-900 dark:text-white">{config.name}</div>
                            <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                              {getMetricLabel(config.metric_type)} • {getConditionDisplay(config)}
                            </div>
                          </div>
                          <div className="flex items-center gap-1">
                            <button
                              onClick={() => handleToggleConfig(config)}
                              className="p-2 text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors"
                            >
                              <Power className="w-4 h-4" />
                            </button>
                            <button
                              onClick={() => handleDeleteConfig(config.id)}
                              className="p-2 text-red-500 hover:text-red-700 hover:bg-red-50 dark:hover:bg-red-900/20 rounded transition-colors"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </div>
                        </div>
                      </li>
                    ))}
                  </ul>

                  {/* Desktop view - Table */}
                  <table className="hidden sm:table min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                    <thead className="bg-gray-50 dark:bg-gray-900">
                      <tr>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">{t('alerts.table.name')}</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">{t('alerts.table.type')}</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">{t('alerts.table.condition')}</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">{t('alerts.table.status')}</th>
                        <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">{t('alerts.table.actions')}</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                      {configs.map(config => (
                        <tr key={config.id} className="hover:bg-gray-50 dark:hover:bg-gray-700">
                          <td className="px-4 py-3">
                            <div className="flex items-center gap-2">
                              <span className={`inline-flex px-2 py-0.5 text-xs font-medium rounded ${severityColors[config.severity]}`}>
                                {t(`alerts.severity.${config.severity}`)}
                              </span>
                              <div>
                                <div className="text-sm font-medium text-gray-900 dark:text-white">{config.name}</div>
                                {config.description && (
                                  <div className="text-xs text-gray-500 dark:text-gray-400">{config.description}</div>
                                )}
                              </div>
                            </div>
                          </td>
                          <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-400">
                            {getMetricLabel(config.metric_type)}
                          </td>
                          <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-400">
                            {getConditionDisplay(config)}
                          </td>
                          <td className="px-4 py-3">
                            <div className="flex items-center gap-2">
                              {config.is_firing && (
                                <span className="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium rounded-full bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300">
                                  <AlertTriangle className="w-3 h-3" />
                                  {t('alerts.firing')}
                                </span>
                              )}
                              <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${
                                config.enabled
                                  ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300'
                                  : 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300'
                              }`}>
                                {config.enabled ? tCommon('status.enabled') : tCommon('status.disabled')}
                              </span>
                            </div>
                          </td>
                          <td className="px-4 py-3 text-right">
                            <div className="flex items-center justify-end gap-2">
                              <button
                                onClick={() => handleToggleConfig(config)}
                                className="p-1.5 text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors"
                                title={config.enabled ? tCommon('actions.disable') : tCommon('actions.enable')}
                              >
                                <Power className="w-4 h-4" />
                              </button>
                              <button
                                onClick={() => handleDeleteConfig(config.id)}
                                className="p-1.5 text-red-500 hover:text-red-700 hover:bg-red-50 dark:hover:bg-red-900/20 rounded transition-colors"
                                title={tCommon('actions.delete')}
                              >
                                <Trash2 className="w-4 h-4" />
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </>
              )}
            </div>
          )}

          {/* History */}
          {activeTab === 'history' && (
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden">
              {history.length === 0 ? (
                <div className="p-8 text-center text-gray-500 dark:text-gray-400">
                  {t('alerts.noHistory')}
                </div>
              ) : (
                <>
                  {/* Mobile view - Cards */}
                  <ul className="divide-y divide-gray-200 dark:divide-gray-700 sm:hidden">
                    {history.map(h => (
                      <li key={h.id} className="p-4">
                        <div className="flex items-start gap-3 mb-2">
                          <span className={`inline-flex px-2 py-0.5 text-xs font-medium rounded ${severityColors[h.severity]}`}>
                            {t(`alerts.severity.${h.severity}`)}
                          </span>
                          <span className="text-sm font-medium text-gray-900 dark:text-white flex-1">{h.alert_name}</span>
                          {h.is_resolved ? (
                            <CheckCircle className="w-4 h-4 text-green-500" />
                          ) : (
                            <AlertTriangle className="w-4 h-4 text-red-500" />
                          )}
                        </div>
                        <div className="text-xs text-gray-500 dark:text-gray-400 space-y-1">
                          <div>{t('alerts.table.triggered')}: {formatTimestamp(h.triggered_at)}</div>
                          {h.is_resolved && h.resolved_at && (
                            <div className="text-green-600 dark:text-green-400">{t('alerts.table.resolved')}: {formatTimestamp(h.resolved_at)}</div>
                          )}
                          {!h.is_resolved && (
                            <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-full bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300">
                              {t('alerts.activeLabel')}
                            </span>
                          )}
                        </div>
                        <p className="mt-2 text-xs text-gray-600 dark:text-gray-400 break-words">
                          {h.message}
                        </p>
                      </li>
                    ))}
                  </ul>

                  {/* Desktop view - Table */}
                  <table className="hidden sm:table min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                    <thead className="bg-gray-50 dark:bg-gray-900">
                      <tr>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">{t('alerts.table.alert')}</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">{t('alerts.table.triggered')}</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">{t('alerts.table.resolved')}</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">{t('alerts.table.message')}</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                      {history.map(h => (
                        <tr key={h.id} className="hover:bg-gray-50 dark:hover:bg-gray-700">
                          <td className="px-4 py-3">
                            <div className="flex items-center gap-2">
                              <span className={`inline-flex px-2 py-0.5 text-xs font-medium rounded ${severityColors[h.severity]}`}>
                                {t(`alerts.severity.${h.severity}`)}
                              </span>
                              <span className="text-sm font-medium text-gray-900 dark:text-white">{h.alert_name}</span>
                            </div>
                          </td>
                          <td className="px-4 py-3 text-sm text-gray-500 dark:text-gray-400">
                            {formatTimestamp(h.triggered_at)}
                          </td>
                          <td className="px-4 py-3">
                            {h.is_resolved ? (
                              <span className="text-sm text-green-600 dark:text-green-400">
                                {formatTimestamp(h.resolved_at!)}
                              </span>
                            ) : (
                              <span className="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium rounded-full bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300">
                                <AlertTriangle className="w-3 h-3" />
                                {t('alerts.activeLabel')}
                              </span>
                            )}
                          </td>
                          <td className="px-4 py-3 text-sm text-gray-500 dark:text-gray-400 max-w-xs truncate">
                            {h.message}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </>
              )}
            </div>
          )}
        </>
      )}

      {/* Create Alert Modal */}
      {showCreateModal && (
        <CreateAlertModal
          onClose={() => setShowCreateModal(false)}
          onCreated={() => {
            setShowCreateModal(false);
            fetchData();
          }}
        />
      )}
    </div>
  );
};

interface CreateAlertModalProps {
  onClose: () => void;
  onCreated: () => void;
}

const CreateAlertModal: FC<CreateAlertModalProps> = ({ onClose, onCreated }) => {
  const { t } = useTranslation('monitoring');
  const { t: tCommon } = useTranslation('common');

  const [selectedCategory, setSelectedCategory] = useState<MetricCategory>('system');
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    severity: 'medium',
    metric_type: 'cpu',
    threshold_operator: 'gt',
    threshold_value: 80,
    duration_seconds: 60,
    cooldown_minutes: 15,
  });
  const [saving, setSaving] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const categories: { id: MetricCategory; icon: string }[] = [
    { id: 'system', icon: '💻' },
    { id: 'services', icon: '🔌' },
    { id: 'mcp', icon: '🤖' },
    { id: 'users', icon: '👥' },
    { id: 'training', icon: '🧠' },
  ];

  const filteredMetrics = metricTypeConfigs.filter(m => m.category === selectedCategory);

  const handleMetricChange = (metricType: string) => {
    const config = metricTypeConfigs.find(m => m.value === metricType);
    if (config) {
      setFormData(prev => ({
        ...prev,
        metric_type: metricType,
        threshold_operator: config.defaultOperator,
        threshold_value: config.defaultThreshold,
      }));
    }
  };

  const selectedMetricConfig = metricTypeConfigs.find(m => m.value === formData.metric_type);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await api.alerts.configs.create(formData);
      onCreated();
    } catch (err: any) {
      console.error('Failed to create alert:', err);
      setError(err.message || 'Failed to create alert');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-lg w-full max-h-[90vh] overflow-y-auto">
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between sticky top-0 bg-white dark:bg-gray-800">
          <h3 className="text-lg font-medium text-gray-900 dark:text-white">
            {t('alerts.createTitle')}
          </h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-500">
            <X className="w-6 h-6" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="px-6 py-4 space-y-5">
          {/* Error message */}
          {error && (
            <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-red-700 dark:text-red-400 text-sm">
              {error}
            </div>
          )}

          {/* Name */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              {t('alerts.form.name')}
            </label>
            <input
              type="text"
              value={formData.name}
              onChange={e => setFormData({ ...formData, name: e.target.value })}
              placeholder={t('alerts.form.namePlaceholder')}
              className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              required
            />
          </div>

          {/* Category Tabs */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              {t('alerts.form.category')}
            </label>
            <div className="flex flex-wrap gap-2">
              {categories.map(cat => (
                <button
                  key={cat.id}
                  type="button"
                  onClick={() => {
                    setSelectedCategory(cat.id);
                    const firstMetric = metricTypeConfigs.find(m => m.category === cat.id);
                    if (firstMetric) {
                      handleMetricChange(firstMetric.value);
                    }
                  }}
                  className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                    selectedCategory === cat.id
                      ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300'
                      : 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-600'
                  }`}
                >
                  <span>{cat.icon}</span>
                  {t(`alerts.categories.${cat.id}`)}
                </button>
              ))}
            </div>
          </div>

          {/* Metric Type */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              {t('alerts.form.metric')}
            </label>
            <div className="grid grid-cols-1 gap-2">
              {filteredMetrics.map(metric => (
                <label
                  key={metric.value}
                  className={`flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${
                    formData.metric_type === metric.value
                      ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                      : 'border-gray-200 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700'
                  }`}
                >
                  <input
                    type="radio"
                    name="metric_type"
                    value={metric.value}
                    checked={formData.metric_type === metric.value}
                    onChange={() => handleMetricChange(metric.value)}
                    className="sr-only"
                  />
                  <div className="flex-1">
                    <div className="text-sm font-medium text-gray-900 dark:text-white">
                      {t(`alerts.metricTypes.${metric.value}`)}
                    </div>
                    <div className="text-xs text-gray-500 dark:text-gray-400">
                      {metric.isEvent
                        ? t('alerts.eventBased')
                        : t('alerts.thresholdBased', { default: `${metric.defaultThreshold}${metric.unit || ''}` })
                      }
                    </div>
                  </div>
                  {formData.metric_type === metric.value && (
                    <CheckCircle className="w-5 h-5 text-blue-500" />
                  )}
                </label>
              ))}
            </div>
          </div>

          {/* Severity */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              {t('alerts.form.severity')}
            </label>
            <div className="flex gap-2">
              {['low', 'medium', 'high', 'critical'].map(sev => (
                <button
                  key={sev}
                  type="button"
                  onClick={() => setFormData({ ...formData, severity: sev })}
                  className={`flex-1 py-2 px-3 rounded-lg text-sm font-medium transition-colors ${
                    formData.severity === sev
                      ? severityColors[sev]
                      : 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400'
                  }`}
                >
                  {t(`alerts.severity.${sev}`)}
                </button>
              ))}
            </div>
          </div>

          {/* Threshold (only for non-event metrics) */}
          {selectedMetricConfig && !selectedMetricConfig.isEvent && (
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                {t('alerts.form.threshold')}
              </label>
              <div className="flex items-center gap-2">
                <select
                  value={formData.threshold_operator}
                  onChange={e => setFormData({ ...formData, threshold_operator: e.target.value })}
                  className="px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                >
                  <option value="gt">&gt; {t('alerts.operators.gt')}</option>
                  <option value="gte">≥ {t('alerts.operators.gte')}</option>
                  <option value="lt">&lt; {t('alerts.operators.lt')}</option>
                  <option value="lte">≤ {t('alerts.operators.lte')}</option>
                  <option value="eq">= {t('alerts.operators.eq')}</option>
                </select>
                <input
                  type="number"
                  value={formData.threshold_value}
                  onChange={e => setFormData({ ...formData, threshold_value: parseFloat(e.target.value) })}
                  className="flex-1 px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                />
                {selectedMetricConfig.unit && (
                  <span className="text-sm text-gray-500 dark:text-gray-400">{selectedMetricConfig.unit}</span>
                )}
              </div>
            </div>
          )}

          {/* Advanced options toggle */}
          <button
            type="button"
            onClick={() => setShowAdvanced(!showAdvanced)}
            className="text-sm text-blue-600 dark:text-blue-400 hover:underline"
          >
            {showAdvanced ? t('alerts.form.hideAdvanced') : t('alerts.form.showAdvanced')}
          </button>

          {/* Advanced options */}
          {showAdvanced && (
            <div className="space-y-4 pt-2 border-t border-gray-200 dark:border-gray-700">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  {t('alerts.form.description')}
                </label>
                <textarea
                  value={formData.description}
                  onChange={e => setFormData({ ...formData, description: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                  rows={2}
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    {t('alerts.form.duration')}
                  </label>
                  <div className="flex items-center gap-2">
                    <input
                      type="number"
                      value={formData.duration_seconds}
                      onChange={e => setFormData({ ...formData, duration_seconds: parseInt(e.target.value) })}
                      className="flex-1 px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                    />
                    <span className="text-sm text-gray-500">s</span>
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    {t('alerts.form.cooldown')}
                  </label>
                  <div className="flex items-center gap-2">
                    <input
                      type="number"
                      value={formData.cooldown_minutes}
                      onChange={e => setFormData({ ...formData, cooldown_minutes: parseInt(e.target.value) })}
                      className="flex-1 px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                    />
                    <span className="text-sm text-gray-500">min</span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Actions */}
          <div className="flex justify-end gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700"
            >
              {tCommon('actions.cancel')}
            </button>
            <button
              type="submit"
              disabled={saving || !formData.name}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {saving ? t('alerts.creating') : t('alerts.create')}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default AlertManager;
