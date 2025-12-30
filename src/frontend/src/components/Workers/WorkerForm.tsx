import { useState, useEffect } from 'react';
import { api } from '../../lib/api';

interface Worker {
  id?: string;
  name: string;
  description?: string;
  url: string;
  api_key?: string;
  enabled?: boolean;
  ollama_service_id?: string;
}

interface OllamaService {
  id: string;
  name: string;
  url: string;
}

interface WorkerFormProps {
  worker?: Worker;
  onSubmit: (data: Worker) => Promise<void>;
  onCancel: () => void;
}

export function WorkerForm({ worker, onSubmit, onCancel }: WorkerFormProps) {
  const [formData, setFormData] = useState<Worker>({
    name: '',
    description: '',
    url: 'http://',
    api_key: '',
    enabled: true,
    ollama_service_id: '',
    ...worker,
  });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [ollamaServices, setOllamaServices] = useState<OllamaService[]>([]);
  const [loadingServices, setLoadingServices] = useState(true);

  useEffect(() => {
    loadOllamaServices();
  }, []);

  const loadOllamaServices = async () => {
    try {
      const services = await api.services.list();
      const ollama = services.filter((s: any) => s.service_type === 'ollama' && s.enabled);
      setOllamaServices(ollama);
    } catch (err) {
      console.error('Failed to load Ollama services:', err);
    } finally {
      setLoadingServices(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);

    try {
      await onSubmit(formData);
    } catch (err: any) {
      setError(err.message || 'Failed to save worker');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-lg w-full mx-4">
        <div className="p-6 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
            {worker?.id ? 'Edit Worker' : 'Add Training Worker'}
          </h2>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Configure a GPU training worker for fine-tuning models
          </p>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {error && (
            <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-md">
              <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Name *
            </label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="IA PC Worker"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Description
            </label>
            <input
              type="text"
              value={formData.description || ''}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="GPU worker for LLM training"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Worker URL *
            </label>
            <input
              type="url"
              value={formData.url}
              onChange={(e) => setFormData({ ...formData, url: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white font-mono text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="http://192.168.1.100:8080"
              required
            />
            <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
              URL of the training worker API (Docker container)
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              API Key (optional)
            </label>
            <input
              type="password"
              value={formData.api_key || ''}
              onChange={(e) => setFormData({ ...formData, api_key: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="Optional API key for authentication"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Ollama Service (for model import)
            </label>
            <select
              value={formData.ollama_service_id || ''}
              onChange={(e) => setFormData({ ...formData, ollama_service_id: e.target.value || undefined })}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              disabled={loadingServices}
            >
              <option value="">Use worker default</option>
              {ollamaServices.map((service) => (
                <option key={service.id} value={service.id}>
                  {service.name} ({service.url})
                </option>
              ))}
            </select>
            <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
              Select which Ollama server to import the trained model to
            </p>
          </div>

          {worker?.id && (
            <div className="flex items-center">
              <input
                type="checkbox"
                id="enabled"
                checked={formData.enabled}
                onChange={(e) => setFormData({ ...formData, enabled: e.target.checked })}
                className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
              />
              <label htmlFor="enabled" className="ml-2 text-sm text-gray-700 dark:text-gray-300">
                Worker enabled
              </label>
            </div>
          )}

          <div className="flex justify-end space-x-3 pt-4 border-t border-gray-200 dark:border-gray-700">
            <button
              type="button"
              onClick={onCancel}
              className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 rounded-md"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-md disabled:opacity-50"
            >
              {submitting ? 'Saving...' : worker?.id ? 'Save Changes' : 'Add Worker'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
