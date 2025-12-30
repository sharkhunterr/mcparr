import { useState } from 'react';
import { api } from '../../lib/api';

interface Worker {
  id: string;
  name: string;
  description?: string;
  url: string;
  status: string;
  enabled: boolean;
  last_seen_at?: string;
  last_error?: string;
  gpu_available: boolean;
  gpu_count: number;
  gpu_names: string[];
  gpu_memory_total_mb: number;
  worker_version?: string;
  platform?: string;
  current_job_id?: string;
  current_session_id?: string;
  total_jobs_completed: number;
  total_training_time_seconds: number;
}

interface WorkerCardProps {
  worker: Worker;
  onRefresh: () => void;
  onEdit: (worker: Worker) => void;
  onDelete: (worker: Worker) => void;
}

const statusColors: Record<string, { bg: string; text: string; dot: string }> = {
  online: { bg: 'bg-green-100 dark:bg-green-900/30', text: 'text-green-800 dark:text-green-300', dot: 'bg-green-500' },
  training: { bg: 'bg-blue-100 dark:bg-blue-900/30', text: 'text-blue-800 dark:text-blue-300', dot: 'bg-blue-500 animate-pulse' },
  offline: { bg: 'bg-gray-100 dark:bg-gray-800', text: 'text-gray-600 dark:text-gray-400', dot: 'bg-gray-400' },
  error: { bg: 'bg-red-100 dark:bg-red-900/30', text: 'text-red-800 dark:text-red-300', dot: 'bg-red-500' },
  unknown: { bg: 'bg-yellow-100 dark:bg-yellow-900/30', text: 'text-yellow-800 dark:text-yellow-300', dot: 'bg-yellow-500' },
};

export function WorkerCard({ worker, onRefresh, onEdit, onDelete }: WorkerCardProps) {
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);
  const [showMetrics, setShowMetrics] = useState(false);
  const [metrics, setMetrics] = useState<any>(null);
  const [loadingMetrics, setLoadingMetrics] = useState(false);

  const statusStyle = statusColors[worker.status] || statusColors.unknown;

  const handleTest = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const result = await api.workers.test(worker.id);
      setTestResult(result);
      onRefresh();
    } catch (err: any) {
      setTestResult({ success: false, message: err.message || 'Test failed' });
    } finally {
      setTesting(false);
    }
  };

  const handleRefresh = async () => {
    try {
      await api.workers.refresh(worker.id);
      onRefresh();
    } catch (err) {
      console.error('Failed to refresh worker:', err);
    }
  };

  const handleToggleMetrics = async () => {
    if (!showMetrics && worker.status !== 'offline') {
      setLoadingMetrics(true);
      try {
        const data = await api.workers.getMetrics(worker.id);
        setMetrics(data);
      } catch (err) {
        console.error('Failed to load metrics:', err);
      } finally {
        setLoadingMetrics(false);
      }
    }
    setShowMetrics(!showMetrics);
  };

  const formatDuration = (seconds: number) => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    if (hours > 0) return `${hours}h ${minutes}m`;
    return `${minutes}m`;
  };

  return (
    <div className={`bg-white dark:bg-gray-800 rounded-lg shadow-sm border ${
      !worker.enabled ? 'opacity-60 border-gray-200 dark:border-gray-700' : 'border-gray-200 dark:border-gray-700'
    }`}>
      {/* Header */}
      <div className="p-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-start justify-between">
          <div className="flex items-center space-x-3">
            <div className={`w-10 h-10 rounded-lg ${worker.gpu_available ? 'bg-green-100 dark:bg-green-900/30' : 'bg-gray-100 dark:bg-gray-700'} flex items-center justify-center`}>
              <svg className={`w-6 h-6 ${worker.gpu_available ? 'text-green-600 dark:text-green-400' : 'text-gray-400'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z" />
              </svg>
            </div>
            <div>
              <h3 className="font-semibold text-gray-900 dark:text-white">{worker.name}</h3>
              <p className="text-sm text-gray-500 dark:text-gray-400 font-mono">{worker.url}</p>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${statusStyle.bg} ${statusStyle.text}`}>
              <span className={`w-2 h-2 mr-1.5 rounded-full ${statusStyle.dot}`}></span>
              {worker.status}
            </span>
          </div>
        </div>
        {worker.description && (
          <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">{worker.description}</p>
        )}
      </div>

      {/* GPU Info */}
      {worker.gpu_available && (
        <div className="px-4 py-3 bg-gray-50 dark:bg-gray-700/50 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <svg className="w-5 h-5 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z" />
              </svg>
              <span className="text-sm font-medium text-gray-900 dark:text-white">
                {worker.gpu_count} GPU{worker.gpu_count > 1 ? 's' : ''}
              </span>
            </div>
            <span className="text-sm text-gray-500 dark:text-gray-400">
              {(worker.gpu_memory_total_mb / 1024).toFixed(1)} GB VRAM
            </span>
          </div>
          {worker.gpu_names.length > 0 && (
            <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
              {worker.gpu_names.join(', ')}
            </p>
          )}
        </div>
      )}

      {/* Stats */}
      <div className="px-4 py-3 grid grid-cols-3 gap-4 text-center border-b border-gray-200 dark:border-gray-700">
        <div>
          <p className="text-lg font-semibold text-gray-900 dark:text-white">{worker.total_jobs_completed}</p>
          <p className="text-xs text-gray-500 dark:text-gray-400">Jobs</p>
        </div>
        <div>
          <p className="text-lg font-semibold text-gray-900 dark:text-white">
            {formatDuration(worker.total_training_time_seconds)}
          </p>
          <p className="text-xs text-gray-500 dark:text-gray-400">Training time</p>
        </div>
        <div>
          <p className="text-lg font-semibold text-gray-900 dark:text-white">
            {worker.worker_version || '-'}
          </p>
          <p className="text-xs text-gray-500 dark:text-gray-400">Version</p>
        </div>
      </div>

      {/* Metrics Panel */}
      {showMetrics && (
        <div className="px-4 py-3 bg-gray-50 dark:bg-gray-700/50 border-b border-gray-200 dark:border-gray-700">
          {loadingMetrics ? (
            <div className="flex items-center justify-center py-2">
              <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-500"></div>
            </div>
          ) : metrics ? (
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-gray-500 dark:text-gray-400">CPU:</span>
                <span className="ml-2 text-gray-900 dark:text-white">{metrics.cpu_percent?.toFixed(1)}%</span>
              </div>
              <div>
                <span className="text-gray-500 dark:text-gray-400">RAM:</span>
                <span className="ml-2 text-gray-900 dark:text-white">{metrics.memory_percent?.toFixed(1)}%</span>
              </div>
              {metrics.gpu_utilization_percent !== null && (
                <>
                  <div>
                    <span className="text-gray-500 dark:text-gray-400">GPU:</span>
                    <span className="ml-2 text-gray-900 dark:text-white">{metrics.gpu_utilization_percent?.toFixed(1)}%</span>
                  </div>
                  <div>
                    <span className="text-gray-500 dark:text-gray-400">VRAM:</span>
                    <span className="ml-2 text-gray-900 dark:text-white">{metrics.gpu_memory_percent?.toFixed(1)}%</span>
                  </div>
                  {metrics.gpu_temperature_c && (
                    <div>
                      <span className="text-gray-500 dark:text-gray-400">GPU Temp:</span>
                      <span className="ml-2 text-gray-900 dark:text-white">{metrics.gpu_temperature_c}°C</span>
                    </div>
                  )}
                  {metrics.gpu_power_draw_w && (
                    <div>
                      <span className="text-gray-500 dark:text-gray-400">Power:</span>
                      <span className="ml-2 text-gray-900 dark:text-white">{metrics.gpu_power_draw_w?.toFixed(0)}W</span>
                    </div>
                  )}
                </>
              )}
            </div>
          ) : (
            <p className="text-sm text-gray-500 dark:text-gray-400">No metrics available</p>
          )}
        </div>
      )}

      {/* Error */}
      {worker.last_error && (
        <div className="px-4 py-2 bg-red-50 dark:bg-red-900/20 border-b border-red-200 dark:border-red-800">
          <p className="text-sm text-red-600 dark:text-red-400">{worker.last_error}</p>
        </div>
      )}

      {/* Test Result */}
      {testResult && (
        <div className={`px-4 py-2 ${testResult.success ? 'bg-green-50 dark:bg-green-900/20' : 'bg-red-50 dark:bg-red-900/20'} border-b border-gray-200 dark:border-gray-700`}>
          <p className={`text-sm ${testResult.success ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
            {testResult.message}
          </p>
        </div>
      )}

      {/* Actions */}
      <div className="px-4 py-3 flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <button
            onClick={handleTest}
            disabled={testing}
            className="px-3 py-1.5 text-sm font-medium text-blue-600 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded-md disabled:opacity-50"
          >
            {testing ? 'Testing...' : 'Test'}
          </button>
          <button
            onClick={handleRefresh}
            className="px-3 py-1.5 text-sm font-medium text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700 rounded-md"
          >
            Refresh
          </button>
          {worker.status !== 'offline' && (
            <button
              onClick={handleToggleMetrics}
              className="px-3 py-1.5 text-sm font-medium text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700 rounded-md"
            >
              {showMetrics ? 'Hide Metrics' : 'Metrics'}
            </button>
          )}
        </div>
        <div className="flex items-center space-x-2">
          <button
            onClick={() => onEdit(worker)}
            className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
            title="Edit"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
            </svg>
          </button>
          <button
            onClick={() => onDelete(worker)}
            className="p-2 text-gray-400 hover:text-red-600 dark:hover:text-red-400"
            title="Delete"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
}
