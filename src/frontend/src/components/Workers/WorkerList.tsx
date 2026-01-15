import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { RefreshCw, Plus } from 'lucide-react';
import { api } from '../../lib/api';
import { WorkerCard } from './WorkerCard';
import { WorkerForm } from './WorkerForm';
import { HelpTooltip } from '../common';

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

export function WorkerList() {
  const { t } = useTranslation('training');
  const [workers, setWorkers] = useState<Worker[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [editingWorker, setEditingWorker] = useState<Worker | undefined>();
  const [deletingWorker, setDeletingWorker] = useState<Worker | null>(null);

  useEffect(() => {
    loadWorkers();
  }, []);

  const loadWorkers = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.workers.list();
      setWorkers(data);
    } catch (err: any) {
      setError(err.message || t('workers.failedToLoad'));
    } finally {
      setLoading(false);
    }
  };

  const handleCreateWorker = async (data: any) => {
    await api.workers.create(data);
    setShowForm(false);
    await loadWorkers();
  };

  const handleUpdateWorker = async (data: any) => {
    if (!editingWorker) return;
    await api.workers.update(editingWorker.id, data);
    setEditingWorker(undefined);
    await loadWorkers();
  };

  const handleDeleteWorker = async () => {
    if (!deletingWorker) return;
    try {
      await api.workers.delete(deletingWorker.id);
      setDeletingWorker(null);
      await loadWorkers();
    } catch (err: any) {
      alert(err.message || t('workers.failedToDelete'));
    }
  };

  const handleRefreshAll = async () => {
    try {
      await api.workers.refreshAll();
      // Reload after a short delay to get updated statuses
      setTimeout(loadWorkers, 2000);
    } catch (err) {
      console.error('Failed to refresh workers:', err);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-500"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
        <p className="text-red-600 dark:text-red-400">{error}</p>
        <button
          onClick={loadWorkers}
          className="mt-2 text-sm text-red-600 dark:text-red-400 hover:underline"
        >
          {t('workers.retry')}
        </button>
      </div>
    );
  }

  return (
    <div>
      {/* Actions bar */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-3 sm:p-4 mb-6">
        <div className="flex flex-row gap-2 sm:gap-3 items-center">
          <button
            onClick={handleRefreshAll}
            className="p-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-600 flex items-center transition-colors flex-shrink-0"
            title={t('workers.refreshAll')}
          >
            <RefreshCw className="w-4 h-4" />
          </button>
          <button
            onClick={() => setShowForm(true)}
            className="px-3 py-2 text-sm font-medium text-white bg-purple-600 hover:bg-purple-700 rounded-lg flex items-center gap-2 transition-colors"
          >
            <Plus className="w-4 h-4" />
            <span className="hidden sm:inline">{t('workers.addWorker')}</span>
          </button>
          <div className="flex-1" />
          <HelpTooltip topicId="trainingWorkers" />
        </div>
      </div>

      {/* Workers Grid */}
      {workers.length === 0 ? (
        <div className="text-center py-12 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
          <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z" />
          </svg>
          <h3 className="mt-2 text-sm font-medium text-gray-900 dark:text-white">{t('workers.noWorkers')}</h3>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            {t('workers.noWorkersHint')}
          </p>
          <button
            onClick={() => setShowForm(true)}
            className="mt-4 px-4 py-2 text-sm font-medium text-white bg-purple-600 hover:bg-purple-700 rounded-lg"
          >
            {t('workers.addWorker')}
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {workers.map((worker) => (
            <WorkerCard
              key={worker.id}
              worker={worker}
              onRefresh={loadWorkers}
              onEdit={(w) => setEditingWorker(w)}
              onDelete={(w) => setDeletingWorker(w)}
            />
          ))}
        </div>
      )}

      {/* Add/Edit Form Modal */}
      {(showForm || editingWorker) && (
        <WorkerForm
          worker={editingWorker}
          onSubmit={editingWorker ? handleUpdateWorker : handleCreateWorker}
          onCancel={() => {
            setShowForm(false);
            setEditingWorker(undefined);
          }}
        />
      )}

      {/* Delete Confirmation Modal */}
      {deletingWorker && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-md w-full mx-4 p-6">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">{t('workers.deleteWorker')}</h3>
            <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
              {t('workers.deleteConfirmMessage', { name: deletingWorker.name })}
            </p>
            <div className="mt-6 flex justify-end space-x-3">
              <button
                onClick={() => setDeletingWorker(null)}
                className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 rounded-md"
              >
                {t('workers.cancel')}
              </button>
              <button
                onClick={handleDeleteWorker}
                className="px-4 py-2 text-sm font-medium text-white bg-red-600 hover:bg-red-700 rounded-md"
              >
                {t('workers.delete')}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
