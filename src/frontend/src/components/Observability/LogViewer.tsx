import React, { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { Search, Download, RefreshCw, X, Filter } from 'lucide-react';
import { api } from '../../lib/api';
import LogExport from '../LogExport';

interface Service {
  id: string;
  name: string;
  type: string;
}

interface LogEntry {
  id: string;
  level: string;
  message: string;
  source: string;
  component: string | null;
  correlation_id: string | null;
  request_id: string | null;
  user_id: string | null;
  service_id: string | null;
  service_type: string | null;
  extra_data: Record<string, any>;
  exception_type: string | null;
  exception_message: string | null;
  stack_trace: string | null;
  duration_ms: number | null;
  logged_at: string;
  created_at: string;
}

interface LogStats {
  total: number;
  by_level: Record<string, number>;
  by_source: Record<string, number>;
  error_rate: number;
  period_hours: number;
}

interface LogFilters {
  level?: string;
  source?: string;
  service_id?: string;
  search?: string;
  start_time?: string;
  end_time?: string;
}

const levelColors: Record<string, string> = {
  debug: 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300',
  info: 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300',
  warning: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300',
  error: 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300',
  critical: 'bg-purple-100 text-purple-700 dark:bg-purple-900 dark:text-purple-300',
};

export const LogViewer: React.FC = () => {
  const { t } = useTranslation('monitoring');
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [stats, setStats] = useState<LogStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);
  const [filters, setFilters] = useState<LogFilters>({});
  const [sources, setSources] = useState<string[]>([]);
  const [levels, setLevels] = useState<string[]>([]);
  const [services, setServices] = useState<Service[]>([]);
  const [selectedLog, setSelectedLog] = useState<LogEntry | null>(null);
  const [page, setPage] = useState(0);
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [showExportModal, setShowExportModal] = useState(false);
  const limit = 50;

  const fetchLogs = useCallback(async () => {
    try {
      const response = await api.logs.list({
        ...filters,
        skip: page * limit,
        limit,
      });
      setLogs(response.items);
      setTotal(response.total);
    } catch (error) {
      console.error('Failed to fetch logs:', error);
    }
  }, [filters, page]);

  const fetchStats = useCallback(async () => {
    try {
      const response = await api.logs.stats(24);
      setStats(response);
    } catch (error) {
      console.error('Failed to fetch log stats:', error);
    }
  }, []);

  const fetchMetadata = useCallback(async () => {
    try {
      const [sourcesRes, levelsRes, servicesRes] = await Promise.all([
        api.logs.sources(),
        api.logs.levels(),
        api.services.list(),
      ]);
      setSources(sourcesRes.sources || []);
      setLevels(levelsRes.levels || []);
      setServices(servicesRes || []);
    } catch (error) {
      console.error('Failed to fetch metadata:', error);
    }
  }, []);

  useEffect(() => {
    const loadInitialData = async () => {
      setLoading(true);
      await Promise.all([fetchLogs(), fetchStats(), fetchMetadata()]);
      setLoading(false);
    };
    loadInitialData();
  }, [fetchLogs, fetchStats, fetchMetadata]);

  useEffect(() => {
    if (autoRefresh) {
      const interval = setInterval(() => {
        fetchLogs();
        fetchStats();
      }, 5000);
      return () => clearInterval(interval);
    }
  }, [autoRefresh, fetchLogs, fetchStats]);

  const handleFilterChange = (key: keyof LogFilters, value: string) => {
    setFilters(prev => ({
      ...prev,
      [key]: value || undefined,
    }));
    setPage(0);
  };

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleString();
  };

  const totalPages = Math.ceil(total / limit);

  const hasActiveFilters = filters.level || filters.source || filters.service_id || filters.search;

  return (
    <div className="space-y-6">
      {/* Actions bar */}
      <div className="flex gap-2">
        <label className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg">
          <input
            type="checkbox"
            checked={autoRefresh}
            onChange={e => setAutoRefresh(e.target.checked)}
            className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
          />
          <span className="hidden sm:inline">{t('autoRefresh')}</span>
        </label>
        <button
          onClick={() => setShowExportModal(true)}
          className="px-3 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors flex items-center gap-2"
        >
          <Download className="w-4 h-4" />
          <span className="hidden sm:inline">{t('logs.export')}</span>
        </button>
        <button
          onClick={() => { fetchLogs(); fetchStats(); }}
          className="px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors flex items-center gap-2"
        >
          <RefreshCw className="w-4 h-4" />
          <span className="hidden sm:inline">{t('actions.refresh')}</span>
        </button>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-2 sm:gap-4">
          <div className="bg-white dark:bg-gray-800 rounded-lg p-2.5 sm:p-4 shadow">
            <div className="text-xs sm:text-sm text-gray-500 dark:text-gray-400 truncate">{t('logs.stats.total')}</div>
            <div className="text-lg sm:text-2xl font-bold text-gray-900 dark:text-white">
              {stats.total.toLocaleString()}
            </div>
          </div>
          <div className="bg-white dark:bg-gray-800 rounded-lg p-2.5 sm:p-4 shadow">
            <div className="text-xs sm:text-sm text-gray-500 dark:text-gray-400 truncate">{t('logs.stats.errorRate')}</div>
            <div className="text-lg sm:text-2xl font-bold text-red-600 dark:text-red-400">
              {stats.error_rate}%
            </div>
          </div>
          <div className="bg-white dark:bg-gray-800 rounded-lg p-2.5 sm:p-4 shadow">
            <div className="text-xs sm:text-sm text-gray-500 dark:text-gray-400 truncate">{t('logs.stats.errors')}</div>
            <div className="text-lg sm:text-2xl font-bold text-red-600 dark:text-red-400">
              {(stats.by_level?.error || 0) + (stats.by_level?.critical || 0)}
            </div>
          </div>
          <div className="bg-white dark:bg-gray-800 rounded-lg p-2.5 sm:p-4 shadow">
            <div className="text-xs sm:text-sm text-gray-500 dark:text-gray-400 truncate">{t('logs.stats.warnings')}</div>
            <div className="text-lg sm:text-2xl font-bold text-yellow-600 dark:text-yellow-400">
              {stats.by_level?.warning || 0}
            </div>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow space-y-3">
        {/* Search row */}
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="flex-1 min-w-0 relative">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              value={filters.search || ''}
              onChange={e => handleFilterChange('search', e.target.value)}
              placeholder={t('logs.searchPlaceholder')}
              className="w-full pl-9 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            />
          </div>
          {hasActiveFilters && (
            <button
              onClick={() => { setFilters({}); setPage(0); }}
              className="px-3 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors flex items-center gap-2 text-sm"
            >
              <X className="w-4 h-4" />
              <span className="hidden sm:inline">{t('logs.clearFilters')}</span>
            </button>
          )}
        </div>
        {/* Filter selects row */}
        <div className="flex flex-wrap items-center gap-2">
          <Filter className="w-4 h-4 text-gray-400 hidden sm:block" />
          <select
            value={filters.level || ''}
            onChange={e => handleFilterChange('level', e.target.value)}
            className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm"
          >
            <option value="">{t('logs.allLevels')}</option>
            {levels.map(level => (
              <option key={level} value={level}>
                {level.charAt(0).toUpperCase() + level.slice(1)}
              </option>
            ))}
          </select>
          <select
            value={filters.source || ''}
            onChange={e => handleFilterChange('source', e.target.value)}
            className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm"
          >
            <option value="">{t('logs.allSources')}</option>
            {sources.map(source => (
              <option key={source} value={source}>{source}</option>
            ))}
          </select>
          <select
            value={filters.service_id || ''}
            onChange={e => handleFilterChange('service_id', e.target.value)}
            className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm"
          >
            <option value="">{t('logs.allServices')}</option>
            {services.map(service => (
              <option key={service.id} value={service.id}>
                {service.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Log Table */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden">
        {loading ? (
          <div className="p-8 text-center text-gray-500 dark:text-gray-400">
            Loading logs...
          </div>
        ) : logs.length === 0 ? (
          <div className="p-8 text-center text-gray-500 dark:text-gray-400">
            No logs found
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                <thead className="bg-gray-50 dark:bg-gray-900">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Time
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Level
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Source
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Message
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Duration
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                  {logs.map(log => (
                    <tr
                      key={log.id}
                      onClick={() => setSelectedLog(log)}
                      className="hover:bg-gray-50 dark:hover:bg-gray-700 cursor-pointer transition-colors"
                    >
                      <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                        {formatTimestamp(log.logged_at)}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${levelColors[log.level] || levelColors.info}`}>
                          {log.level.toUpperCase()}
                        </span>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                        {log.source}
                        {log.component && (
                          <span className="text-gray-400 dark:text-gray-500">/{log.component}</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-900 dark:text-white max-w-md truncate">
                        {log.message}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                        {log.duration_ms ? `${log.duration_ms}ms` : '-'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            <div className="px-4 py-3 border-t border-gray-200 dark:border-gray-700 flex items-center justify-between">
              <div className="text-sm text-gray-500 dark:text-gray-400">
                Showing {page * limit + 1} to {Math.min((page + 1) * limit, total)} of {total} logs
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => setPage(p => Math.max(0, p - 1))}
                  disabled={page === 0}
                  className="px-3 py-1 border border-gray-300 dark:border-gray-600 rounded text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50 dark:hover:bg-gray-700"
                >
                  Previous
                </button>
                <span className="px-3 py-1 text-sm text-gray-600 dark:text-gray-400">
                  Page {page + 1} of {totalPages}
                </span>
                <button
                  onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))}
                  disabled={page >= totalPages - 1}
                  className="px-3 py-1 border border-gray-300 dark:border-gray-600 rounded text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50 dark:hover:bg-gray-700"
                >
                  Next
                </button>
              </div>
            </div>
          </>
        )}
      </div>

      {/* Log Detail Modal */}
      {selectedLog && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-3xl w-full max-h-[80vh] overflow-y-auto">
            <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
              <h3 className="text-lg font-medium text-gray-900 dark:text-white">
                Log Details
              </h3>
              <button
                onClick={() => setSelectedLog(null)}
                className="text-gray-400 hover:text-gray-500 dark:hover:text-gray-300"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <div className="px-6 py-4 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-sm font-medium text-gray-500 dark:text-gray-400">Time</label>
                  <p className="text-gray-900 dark:text-white">{formatTimestamp(selectedLog.logged_at)}</p>
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-500 dark:text-gray-400">Level</label>
                  <p>
                    <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${levelColors[selectedLog.level]}`}>
                      {selectedLog.level.toUpperCase()}
                    </span>
                  </p>
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-500 dark:text-gray-400">Source</label>
                  <p className="text-gray-900 dark:text-white">{selectedLog.source}</p>
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-500 dark:text-gray-400">Component</label>
                  <p className="text-gray-900 dark:text-white">{selectedLog.component || '-'}</p>
                </div>
                {selectedLog.correlation_id && (
                  <div className="col-span-2">
                    <label className="text-sm font-medium text-gray-500 dark:text-gray-400">Correlation ID</label>
                    <p className="text-gray-900 dark:text-white font-mono text-sm">{selectedLog.correlation_id}</p>
                  </div>
                )}
                {selectedLog.duration_ms && (
                  <div>
                    <label className="text-sm font-medium text-gray-500 dark:text-gray-400">Duration</label>
                    <p className="text-gray-900 dark:text-white">{selectedLog.duration_ms}ms</p>
                  </div>
                )}
              </div>
              <div>
                <label className="text-sm font-medium text-gray-500 dark:text-gray-400">Message</label>
                <p className="text-gray-900 dark:text-white bg-gray-50 dark:bg-gray-900 p-3 rounded-lg mt-1">
                  {selectedLog.message}
                </p>
              </div>
              {selectedLog.exception_type && (
                <div>
                  <label className="text-sm font-medium text-gray-500 dark:text-gray-400">Exception</label>
                  <div className="bg-red-50 dark:bg-red-900/20 p-3 rounded-lg mt-1">
                    <p className="font-mono text-sm text-red-700 dark:text-red-300">
                      {selectedLog.exception_type}: {selectedLog.exception_message}
                    </p>
                    {selectedLog.stack_trace && (
                      <pre className="mt-2 text-xs text-red-600 dark:text-red-400 overflow-x-auto">
                        {selectedLog.stack_trace}
                      </pre>
                    )}
                  </div>
                </div>
              )}
              {Object.keys(selectedLog.extra_data || {}).length > 0 && (
                <div>
                  <label className="text-sm font-medium text-gray-500 dark:text-gray-400">Extra Data</label>
                  <pre className="bg-gray-50 dark:bg-gray-900 p-3 rounded-lg mt-1 text-sm overflow-x-auto">
                    {JSON.stringify(selectedLog.extra_data, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Export Modal */}
      {showExportModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-lg w-full">
            <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
              <h3 className="text-lg font-medium text-gray-900 dark:text-white">
                Export Logs
              </h3>
              <button
                onClick={() => setShowExportModal(false)}
                className="text-gray-400 hover:text-gray-500 dark:hover:text-gray-300"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <div className="p-6">
              <LogExport filters={filters} onClose={() => setShowExportModal(false)} />
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default LogViewer;
