import { useState, useEffect, useCallback } from 'react';
import type { FC, FormEvent } from 'react';
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

const severityColors: Record<string, string> = {
  low: 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300',
  medium: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300',
  high: 'bg-orange-100 text-orange-700 dark:bg-orange-900 dark:text-orange-300',
  critical: 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300',
};

export const AlertManager: FC = () => {
  const [activeTab, setActiveTab] = useState<'active' | 'configs' | 'history'>('active');
  const [configs, setConfigs] = useState<AlertConfig[]>([]);
  const [history, setHistory] = useState<AlertHistory[]>([]);
  const [activeAlerts, setActiveAlerts] = useState<AlertHistory[]>([]);
  const [stats, setStats] = useState<AlertStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [severities, setSeverities] = useState<string[]>([]);
  const [metricTypes, setMetricTypes] = useState<string[]>([]);
  const [operators, setOperators] = useState<{ value: string; label: string }[]>([]);

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

  const fetchMetadata = useCallback(async () => {
    try {
      const [sevRes, metricRes, opRes] = await Promise.all([
        api.alerts.severities(),
        api.alerts.metricTypes(),
        api.alerts.operators(),
      ]);
      setSeverities(sevRes.severities || []);
      setMetricTypes(metricRes.metric_types || []);
      setOperators(opRes.operators || []);
    } catch (error) {
      console.error('Failed to fetch metadata:', error);
    }
  }, []);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      await Promise.all([fetchData(), fetchMetadata()]);
      setLoading(false);
    };
    load();
  }, [fetchData, fetchMetadata]);

  const handleToggleConfig = async (config: AlertConfig) => {
    try {
      await api.alerts.configs.toggle(config.id, !config.enabled);
      fetchData();
    } catch (error) {
      console.error('Failed to toggle alert:', error);
    }
  };

  const handleDeleteConfig = async (id: string) => {
    if (!confirm('Are you sure you want to delete this alert configuration?')) return;
    try {
      await api.alerts.configs.delete(id);
      fetchData();
    } catch (error) {
      console.error('Failed to delete alert:', error);
    }
  };

  const handleResolveAlert = async (id: string) => {
    try {
      await api.alerts.history.resolve(id, 'Manually resolved');
      fetchData();
    } catch (error) {
      console.error('Failed to resolve alert:', error);
    }
  };

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleString();
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900 dark:text-white">
            Alert Management
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Configure and manage system alerts
          </p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          Create Alert
        </button>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow">
            <div className="text-sm text-gray-500 dark:text-gray-400">Active Alerts</div>
            <div className={`text-2xl font-bold ${stats.active_count > 0 ? 'text-red-600 dark:text-red-400' : 'text-green-600 dark:text-green-400'}`}>
              {stats.active_count}
            </div>
          </div>
          <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow">
            <div className="text-sm text-gray-500 dark:text-gray-400">Triggered (24h)</div>
            <div className="text-2xl font-bold text-gray-900 dark:text-white">
              {stats.total_triggered}
            </div>
          </div>
          <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow">
            <div className="text-sm text-gray-500 dark:text-gray-400">MTTR</div>
            <div className="text-2xl font-bold text-gray-900 dark:text-white">
              {stats.mttr_formatted || '-'}
            </div>
          </div>
          <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow">
            <div className="text-sm text-gray-500 dark:text-gray-400">Critical (24h)</div>
            <div className="text-2xl font-bold text-red-600 dark:text-red-400">
              {stats.by_severity?.critical || 0}
            </div>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="border-b border-gray-200 dark:border-gray-700">
        <nav className="flex -mb-px space-x-8">
          {[
            { id: 'active', label: 'Active Alerts', count: activeAlerts.length },
            { id: 'configs', label: 'Configurations', count: configs.length },
            { id: 'history', label: 'History' },
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
              {tab.label}
              {tab.count !== undefined && (
                <span className={`ml-2 px-2 py-0.5 rounded-full text-xs ${
                  tab.id === 'active' && tab.count > 0
                    ? 'bg-red-100 text-red-600 dark:bg-red-900 dark:text-red-400'
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
        <div className="p-8 text-center text-gray-500 dark:text-gray-400">Loading...</div>
      ) : (
        <>
          {/* Active Alerts */}
          {activeTab === 'active' && (
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden">
              {activeAlerts.length === 0 ? (
                <div className="p-8 text-center text-gray-500 dark:text-gray-400">
                  <svg className="w-12 h-12 mx-auto mb-4 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  No active alerts - everything is running smoothly!
                </div>
              ) : (
                <ul className="divide-y divide-gray-200 dark:divide-gray-700">
                  {activeAlerts.map(alert => (
                    <li key={alert.id} className="p-4">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${severityColors[alert.severity]}`}>
                            {alert.severity.toUpperCase()}
                          </span>
                          <div>
                            <h4 className="text-sm font-medium text-gray-900 dark:text-white">
                              {alert.alert_name}
                            </h4>
                            <p className="text-sm text-gray-500 dark:text-gray-400">
                              Triggered {formatTimestamp(alert.triggered_at)}
                            </p>
                          </div>
                        </div>
                        <button
                          onClick={() => handleResolveAlert(alert.id)}
                          className="px-3 py-1 text-sm border border-green-500 text-green-600 rounded hover:bg-green-50 dark:hover:bg-green-900/20 transition-colors"
                        >
                          Resolve
                        </button>
                      </div>
                      <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
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
                  No alert configurations yet. Create one to get started!
                </div>
              ) : (
                <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                  <thead className="bg-gray-50 dark:bg-gray-900">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Name</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Severity</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Condition</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Status</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Triggered</th>
                      <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                    {configs.map(config => (
                      <tr key={config.id} className="hover:bg-gray-50 dark:hover:bg-gray-700">
                        <td className="px-4 py-3">
                          <div className="text-sm font-medium text-gray-900 dark:text-white">{config.name}</div>
                          {config.description && (
                            <div className="text-xs text-gray-500 dark:text-gray-400">{config.description}</div>
                          )}
                        </td>
                        <td className="px-4 py-3">
                          <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${severityColors[config.severity]}`}>
                            {config.severity}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-400">
                          {config.metric_type} {config.threshold_operator} {config.threshold_value}
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-2">
                            {config.is_firing && (
                              <span className="inline-flex px-2 py-1 text-xs font-medium rounded-full bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300">
                                FIRING
                              </span>
                            )}
                            <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${
                              config.enabled
                                ? 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300'
                                : 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300'
                            }`}>
                              {config.enabled ? 'Enabled' : 'Disabled'}
                            </span>
                          </div>
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-500 dark:text-gray-400">
                          {config.trigger_count}x
                        </td>
                        <td className="px-4 py-3 text-right">
                          <div className="flex items-center justify-end gap-2">
                            <button
                              onClick={() => handleToggleConfig(config)}
                              className="px-2 py-1 text-xs border border-gray-300 dark:border-gray-600 rounded hover:bg-gray-50 dark:hover:bg-gray-700"
                            >
                              {config.enabled ? 'Disable' : 'Enable'}
                            </button>
                            <button
                              onClick={() => handleDeleteConfig(config.id)}
                              className="px-2 py-1 text-xs border border-red-300 text-red-600 rounded hover:bg-red-50 dark:hover:bg-red-900/20"
                            >
                              Delete
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          )}

          {/* History */}
          {activeTab === 'history' && (
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden">
              {history.length === 0 ? (
                <div className="p-8 text-center text-gray-500 dark:text-gray-400">
                  No alert history yet
                </div>
              ) : (
                <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                  <thead className="bg-gray-50 dark:bg-gray-900">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Alert</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Severity</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Triggered</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Resolved</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Value</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                    {history.map(h => (
                      <tr key={h.id} className="hover:bg-gray-50 dark:hover:bg-gray-700">
                        <td className="px-4 py-3 text-sm font-medium text-gray-900 dark:text-white">
                          {h.alert_name}
                        </td>
                        <td className="px-4 py-3">
                          <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${severityColors[h.severity]}`}>
                            {h.severity}
                          </span>
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
                            <span className="inline-flex px-2 py-1 text-xs font-medium rounded-full bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300">
                              Active
                            </span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-500 dark:text-gray-400">
                          {h.metric_value} / {h.threshold_value}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          )}
        </>
      )}

      {/* Create Alert Modal */}
      {showCreateModal && (
        <CreateAlertModal
          severities={severities}
          metricTypes={metricTypes}
          operators={operators}
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
  severities: string[];
  metricTypes: string[];
  operators: { value: string; label: string }[];
  onClose: () => void;
  onCreated: () => void;
}

const CreateAlertModal: FC<CreateAlertModalProps> = ({
  severities,
  metricTypes,
  operators,
  onClose,
  onCreated,
}) => {
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    severity: 'medium',
    metric_type: 'cpu',
    threshold_operator: '>',
    threshold_value: 80,
    duration_seconds: 60,
    cooldown_minutes: 15,
  });
  const [saving, setSaving] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      await api.alerts.configs.create(formData);
      onCreated();
    } catch (error) {
      console.error('Failed to create alert:', error);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-md w-full">
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
          <h3 className="text-lg font-medium text-gray-900 dark:text-white">
            Create Alert Configuration
          </h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-500">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        <form onSubmit={handleSubmit} className="px-6 py-4 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Name</label>
            <input
              type="text"
              value={formData.name}
              onChange={e => setFormData({ ...formData, name: e.target.value })}
              className="mt-1 w-full rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Description</label>
            <textarea
              value={formData.description}
              onChange={e => setFormData({ ...formData, description: e.target.value })}
              className="mt-1 w-full rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
              rows={2}
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Severity</label>
              <select
                value={formData.severity}
                onChange={e => setFormData({ ...formData, severity: e.target.value })}
                className="mt-1 w-full rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
              >
                {severities.map(s => (
                  <option key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Metric</label>
              <select
                value={formData.metric_type}
                onChange={e => setFormData({ ...formData, metric_type: e.target.value })}
                className="mt-1 w-full rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
              >
                {metricTypes.map(m => (
                  <option key={m} value={m}>{m.toUpperCase()}</option>
                ))}
              </select>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Operator</label>
              <select
                value={formData.threshold_operator}
                onChange={e => setFormData({ ...formData, threshold_operator: e.target.value })}
                className="mt-1 w-full rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
              >
                {operators.map(op => (
                  <option key={op.value} value={op.value}>{op.label} ({op.value})</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Threshold</label>
              <input
                type="number"
                value={formData.threshold_value}
                onChange={e => setFormData({ ...formData, threshold_value: parseFloat(e.target.value) })}
                className="mt-1 w-full rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
              />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Duration (sec)</label>
              <input
                type="number"
                value={formData.duration_seconds}
                onChange={e => setFormData({ ...formData, duration_seconds: parseInt(e.target.value) })}
                className="mt-1 w-full rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Cooldown (min)</label>
              <input
                type="number"
                value={formData.cooldown_minutes}
                onChange={e => setFormData({ ...formData, cooldown_minutes: parseInt(e.target.value) })}
                className="mt-1 w-full rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
              />
            </div>
          </div>
          <div className="flex justify-end gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
            >
              {saving ? 'Creating...' : 'Create Alert'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default AlertManager;
