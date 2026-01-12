import React, { useState, useEffect } from 'react';
import {
  Server,
  Plus,
  Globe,
  CheckCircle,
  XCircle,
  AlertCircle,
  Edit,
  Trash2,
  Play,
  Pause,
  RefreshCw,
  Zap,
  Clock,
  ExternalLink,
  PlayCircle,
  Loader2,
  X
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import ServiceForm from '../ServiceForm';
import ServiceTestModal from '../ServiceTestModal';
import { getApiBaseUrl } from '../../lib/api';
import { getServiceColor } from '../../lib/serviceColors';

interface Service {
  id: string;
  name: string;
  service_type: string;
  description?: string;
  base_url: string;
  external_url?: string;
  port?: number;
  api_key?: string;
  username?: string;
  password?: string;
  status: 'active' | 'inactive' | 'error' | 'testing' | 'unknown';
  enabled: boolean;
  health_check_enabled: boolean;
  health_check_interval: number;
  last_test_at?: string;
  last_test_success?: boolean;
  last_error?: string;
  created_at: string;
  updated_at: string;
}

interface TestAllResult {
  service_id: string;
  service_name: string;
  service_type: string;
  status: 'pending' | 'testing' | 'success' | 'error';
  error_message?: string;
  response_time_ms?: number;
}

const ServiceList: React.FC = () => {
  const { t } = useTranslation(['services', 'common']);
  const [services, setServices] = useState<Service[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedService, setSelectedService] = useState<Service | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [testingService, setTestingService] = useState<Service | null>(null);

  // Test All state
  const [showTestAllModal, setShowTestAllModal] = useState(false);
  const [testAllResults, setTestAllResults] = useState<TestAllResult[]>([]);
  const [testingAll, setTestingAll] = useState(false);

  useEffect(() => {
    fetchServices();
  }, []);

  const fetchServices = async () => {
    try {
      setError(null);
      const timestamp = new Date().getTime();
      const response = await fetch(`${getApiBaseUrl()}/api/services/?_t=${timestamp}`);

      if (!response.ok) {
        throw new Error(`Failed to fetch services: ${response.statusText}`);
      }

      const data = await response.json();
      setServices(data);
      setLoading(false);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch services';
      setError(errorMessage);
      setLoading(false);
    }
  };

  // Helper to extract error message from API response
  const getErrorMessage = (errorData: any, fallback: string): string => {
    if (typeof errorData.detail === 'string') {
      return errorData.detail;
    }
    if (Array.isArray(errorData.detail) && errorData.detail.length > 0) {
      // Pydantic validation error format
      const firstError = errorData.detail[0];
      const field = firstError.loc?.slice(1).join('.') || 'field';
      return `${field}: ${firstError.msg}`;
    }
    return errorData.message || fallback;
  };

  const handleCreateService = async (serviceData: any) => {
    try {
      const response = await fetch(`${getApiBaseUrl()}/api/services/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          ...serviceData,
          port: serviceData.port ? parseInt(serviceData.port) : null,
          health_check_interval: parseInt(serviceData.health_check_interval)
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(getErrorMessage(errorData, 'Failed to create service'));
      }

      await fetchServices();
      setShowCreateModal(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create service');
      throw err;
    }
  };

  const handleUpdateService = async (serviceData: any) => {
    if (!selectedService) return;

    try {
      const response = await fetch(`${getApiBaseUrl()}/api/services/${selectedService.id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          ...serviceData,
          port: serviceData.port ? parseInt(serviceData.port) : null,
          health_check_interval: parseInt(serviceData.health_check_interval)
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(getErrorMessage(errorData, 'Failed to update service'));
      }

      await fetchServices();
      setSelectedService(null);
      setShowEditModal(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update service');
      throw err;
    }
  };

  const handleToggleService = async (serviceId: string, enabled: boolean) => {
    try {
      const endpoint = enabled ? 'disable' : 'enable';
      const response = await fetch(`${getApiBaseUrl()}/api/services/${serviceId}/${endpoint}`, {
        method: 'PATCH',
      });

      if (!response.ok) {
        throw new Error(`Failed to ${endpoint} service`);
      }

      await fetchServices();
    } catch (err) {
      setError(err instanceof Error ? err.message : `Failed to toggle service`);
    }
  };

  const handleTestConnection = (service: Service) => {
    setTestingService(service);
  };

  const handleTestComplete = async () => {
    await fetchServices();
  };

  const handleTestAll = async () => {
    const enabledServices = services.filter(s => s.enabled);
    if (enabledServices.length === 0) return;

    // Initialize results
    const initialResults: TestAllResult[] = enabledServices.map(s => ({
      service_id: s.id,
      service_name: s.name,
      service_type: s.service_type,
      status: 'pending' as const
    }));

    setTestAllResults(initialResults);
    setShowTestAllModal(true);
    setTestingAll(true);

    // Test each service sequentially
    for (let i = 0; i < enabledServices.length; i++) {
      const service = enabledServices[i];

      // Update status to testing
      setTestAllResults(prev => prev.map(r =>
        r.service_id === service.id ? { ...r, status: 'testing' as const } : r
      ));

      try {
        const startTime = Date.now();
        const response = await fetch(`${getApiBaseUrl()}/api/services/${service.id}/test`, {
          method: 'POST',
        });
        const duration = Date.now() - startTime;
        const result = await response.json();

        if (response.ok && result.success) {
          setTestAllResults(prev => prev.map(r =>
            r.service_id === service.id
              ? { ...r, status: 'success' as const, response_time_ms: result.response_time_ms || duration }
              : r
          ));
        } else {
          setTestAllResults(prev => prev.map(r =>
            r.service_id === service.id
              ? { ...r, status: 'error' as const, error_message: result.error_message || 'Test failed' }
              : r
          ));
        }
      } catch (err) {
        setTestAllResults(prev => prev.map(r =>
          r.service_id === service.id
            ? { ...r, status: 'error' as const, error_message: err instanceof Error ? err.message : 'Unknown error' }
            : r
        ));
      }
    }

    setTestingAll(false);
    await fetchServices();
  };

  const handleDeleteService = async (serviceId: string) => {
    if (!window.confirm(t('services:confirm.delete'))) {
      return;
    }

    try {
      const response = await fetch(`${getApiBaseUrl()}/api/services/${serviceId}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        throw new Error('Failed to delete service');
      }

      await fetchServices();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete service');
    }
  };

  const formatLastTest = (dateStr?: string) => {
    if (!dateStr) return t('services:time.never');
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return t('services:time.justNow');
    if (diffMins < 60) return t('services:time.minutesAgo', { count: diffMins });
    if (diffHours < 24) return t('services:time.hoursAgo', { count: diffHours });
    return t('services:time.daysAgo', { count: diffDays });
  };

  if (loading) {
    return (
      <div className="animate-pulse">
        <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded w-1/4 mb-6"></div>
        <div className="space-y-3">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="bg-gray-200 dark:bg-gray-700 h-20 rounded-lg"></div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div>
      {/* Header with actions */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
        <p className="text-sm text-gray-500 dark:text-gray-400">
          {t(services.length > 1 ? 'services:subtitle_plural' : 'services:subtitle', { count: services.length })}
        </p>
        <div className="flex gap-2">
          <button
            onClick={fetchServices}
            className="p-2 border border-gray-300 dark:border-gray-600 text-gray-600 dark:text-gray-400 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
            title={t('common:actions.refresh')}
          >
            <RefreshCw className="w-4 h-4" />
          </button>
          <button
            onClick={handleTestAll}
            disabled={testingAll || services.filter(s => s.enabled).length === 0}
            className="bg-orange-600 hover:bg-orange-700 disabled:bg-gray-400 disabled:cursor-not-allowed text-white px-4 py-2 rounded-lg flex items-center gap-2 transition-colors"
            title={t('services:actions.testAll')}
          >
            {testingAll ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <PlayCircle className="w-4 h-4" />
            )}
            <span className="hidden sm:inline">{t('services:actions.testAll')}</span>
          </button>
          <button
            onClick={() => setShowCreateModal(true)}
            className="bg-orange-600 hover:bg-orange-700 text-white px-4 py-2 rounded-lg flex items-center gap-2 transition-colors"
          >
            <Plus className="w-4 h-4" />
            <span className="hidden sm:inline">{t('common:actions.add')}</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 mb-6">
          <div className="flex items-center">
            <XCircle className="w-5 h-5 text-red-500 mr-2 flex-shrink-0" />
            <span className="text-red-700 dark:text-red-400 text-sm">{error}</span>
          </div>
        </div>
      )}

      {services.length === 0 ? (
        <div className="text-center py-12 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-dashed border-gray-300 dark:border-gray-600">
          <Server className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">{t('services:empty.title')}</h3>
          <p className="text-gray-500 dark:text-gray-400 mb-6 text-sm">
            {t('services:empty.description')}
          </p>
          <button
            onClick={() => setShowCreateModal(true)}
            className="bg-orange-600 hover:bg-orange-700 text-white px-4 py-2 rounded-lg inline-flex items-center gap-2"
          >
            <Plus className="w-4 h-4" />
            {t('services:empty.action')}
          </button>
        </div>
      ) : (
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
          {/* Table Header - Desktop */}
          <div className="hidden md:grid md:grid-cols-12 gap-4 px-4 py-3 bg-gray-50 dark:bg-gray-900/50 border-b border-gray-200 dark:border-gray-700 text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
            <div className="col-span-4">{t('services:table.headers.service')}</div>
            <div className="col-span-3">{t('services:table.headers.url')}</div>
            <div className="col-span-2 text-center">{t('services:table.headers.status')}</div>
            <div className="col-span-1 text-center">{t('services:table.headers.test')}</div>
            <div className="col-span-2 text-right">{t('services:table.headers.actions')}</div>
          </div>

          {/* Services List */}
          <div className="divide-y divide-gray-200 dark:divide-gray-700">
            {services.map((service) => {
              const colors = getServiceColor(service.service_type);
              const Icon = colors.icon;
              const isHealthy = service.enabled && service.last_test_success === true;
              const hasError = service.enabled && service.last_test_success === false;
              const isDisabled = !service.enabled;

              return (
                <div
                  key={service.id}
                  className={`px-4 py-3 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors ${
                    isDisabled ? 'opacity-50' : ''
                  }`}
                >
                  {/* Mobile Layout */}
                  <div className="md:hidden space-y-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3 min-w-0">
                        <span className={`w-2.5 h-2.5 rounded-full flex-shrink-0 ${colors.dot}`}></span>
                        <div className="min-w-0">
                          <h3 className="font-medium text-gray-900 dark:text-white truncate">{service.name}</h3>
                          <p className="text-xs text-gray-500 dark:text-gray-400 capitalize">{service.service_type}</p>
                        </div>
                      </div>
                      <div className={`flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${
                        isDisabled
                          ? 'bg-gray-100 dark:bg-gray-700 text-gray-500'
                          : isHealthy
                          ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400'
                          : hasError
                          ? 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400'
                          : 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-400'
                      }`}>
                        {isDisabled ? <Pause className="w-3 h-3" /> : isHealthy ? <CheckCircle className="w-3 h-3" /> : hasError ? <XCircle className="w-3 h-3" /> : <AlertCircle className="w-3 h-3" />}
                        <span>{isDisabled ? t('services:status.off') : isHealthy ? t('services:status.ok') : hasError ? t('services:status.error') : t('services:status.na')}</span>
                      </div>
                    </div>

                    <div className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
                      <Globe className="w-3.5 h-3.5" />
                      <span className="truncate font-mono">{service.base_url}{service.port ? `:${service.port}` : ''}</span>
                    </div>

                    <div className="flex items-center justify-between pt-2 border-t border-gray-100 dark:border-gray-700">
                      <div className="flex items-center gap-1 text-xs text-gray-400">
                        <Clock className="w-3.5 h-3.5" />
                        {formatLastTest(service.last_test_at)}
                      </div>
                      <div className="flex items-center gap-1">
                        <button
                          onClick={() => handleToggleService(service.id, service.enabled)}
                          className={`p-1.5 rounded transition-colors ${
                            service.enabled
                              ? 'text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20'
                              : 'text-green-600 hover:bg-green-50 dark:hover:bg-green-900/20'
                          }`}
                          title={service.enabled ? t('common:actions.disable') : t('common:actions.enable')}
                        >
                          {service.enabled ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
                        </button>
                        <button
                          onClick={() => handleTestConnection(service)}
                          disabled={!service.enabled}
                          className="p-1.5 text-orange-600 hover:bg-orange-50 dark:hover:bg-orange-900/20 rounded transition-colors disabled:opacity-40"
                          title={t('common:actions.test')}
                        >
                          <Zap className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => {
                            setSelectedService(service);
                            setShowEditModal(true);
                          }}
                          className="p-1.5 text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors"
                          title={t('common:actions.edit')}
                        >
                          <Edit className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => handleDeleteService(service.id)}
                          className="p-1.5 text-gray-500 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded transition-colors"
                          title={t('common:actions.delete')}
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  </div>

                  {/* Desktop Layout */}
                  <div className="hidden md:grid md:grid-cols-12 gap-4 items-center">
                    {/* Service Info */}
                    <div className="col-span-4 flex items-center gap-3 min-w-0">
                      <div className={`p-2 rounded-lg ${colors.bg}`}>
                        <Icon className={`w-4 h-4 ${colors.text}`} />
                      </div>
                      <div className="min-w-0">
                        <h3 className="font-medium text-gray-900 dark:text-white truncate">{service.name}</h3>
                        <p className="text-xs text-gray-500 dark:text-gray-400 capitalize">{service.service_type}</p>
                      </div>
                    </div>

                    {/* URL */}
                    <div className="col-span-3 flex items-center gap-2 min-w-0">
                      <span className="text-sm text-gray-600 dark:text-gray-300 truncate font-mono">
                        {service.base_url}{service.port ? `:${service.port}` : ''}
                      </span>
                      <a
                        href={`${service.base_url}${service.port ? `:${service.port}` : ''}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="p-1 text-gray-400 hover:text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded transition-colors flex-shrink-0"
                      >
                        <ExternalLink className="w-3.5 h-3.5" />
                      </a>
                    </div>

                    {/* Status */}
                    <div className="col-span-2 flex justify-center">
                      <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${
                        isDisabled
                          ? 'bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400'
                          : isHealthy
                          ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400'
                          : hasError
                          ? 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400'
                          : 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-400'
                      }`}>
                        {isDisabled ? (
                          <Pause className="w-3 h-3" />
                        ) : isHealthy ? (
                          <CheckCircle className="w-3 h-3" />
                        ) : hasError ? (
                          <XCircle className="w-3 h-3" />
                        ) : (
                          <AlertCircle className="w-3 h-3" />
                        )}
                        {isDisabled ? t('services:status.disabled') : isHealthy ? t('services:status.online') : hasError ? t('services:status.error') : t('services:status.unknown')}
                      </div>
                    </div>

                    {/* Last Test */}
                    <div className="col-span-1 text-center">
                      <span className="text-xs text-gray-500 dark:text-gray-400">
                        {formatLastTest(service.last_test_at)}
                      </span>
                    </div>

                    {/* Actions */}
                    <div className="col-span-2 flex items-center justify-end gap-1">
                      <button
                        onClick={() => handleToggleService(service.id, service.enabled)}
                        className={`p-1.5 rounded transition-colors ${
                          service.enabled
                            ? 'text-orange-600 hover:bg-orange-50 dark:hover:bg-orange-900/20'
                            : 'text-green-600 hover:bg-green-50 dark:hover:bg-green-900/20'
                        }`}
                        title={service.enabled ? t('common:actions.disable') : t('common:actions.enable')}
                      >
                        {service.enabled ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
                      </button>
                      <button
                        onClick={() => handleTestConnection(service)}
                        disabled={!service.enabled}
                        className="p-1.5 text-orange-600 hover:bg-orange-50 dark:hover:bg-orange-900/20 rounded transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                        title={t('services:actions.testConnection')}
                      >
                        <Zap className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => {
                          setSelectedService(service);
                          setShowEditModal(true);
                        }}
                        className="p-1.5 text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors"
                        title={t('common:actions.edit')}
                      >
                        <Edit className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => handleDeleteService(service.id)}
                        className="p-1.5 text-gray-500 dark:text-gray-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded transition-colors"
                        title={t('common:actions.delete')}
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>

                  {/* Error Message */}
                  {service.last_error && hasError && (
                    <div className="mt-2 ml-0 md:ml-11 p-2 bg-red-50 dark:bg-red-900/20 rounded text-xs text-red-600 dark:text-red-400">
                      {service.last_error}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Service creation modal */}
      <ServiceForm
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        onSubmit={handleCreateService}
        isEditing={false}
      />

      {/* Service edit modal */}
      {selectedService && showEditModal && (
        <ServiceForm
          isOpen={showEditModal}
          onClose={() => {
            setSelectedService(null);
            setShowEditModal(false);
          }}
          onSubmit={handleUpdateService}
          initialData={{
            name: selectedService.name,
            service_type: selectedService.service_type,
            description: selectedService.description || '',
            base_url: selectedService.base_url,
            external_url: selectedService.external_url || '',
            port: selectedService.port?.toString() || '',
            api_key: selectedService.api_key || '',
            username: selectedService.username || '',
            password: selectedService.password || '',
            enabled: selectedService.enabled,
            health_check_enabled: selectedService.health_check_enabled,
            health_check_interval: selectedService.health_check_interval?.toString() || '300'
          }}
          isEditing={true}
        />
      )}

      {/* Service test modal */}
      {testingService && (
        <ServiceTestModal
          isOpen={!!testingService}
          onClose={() => setTestingService(null)}
          service={testingService}
          onTestComplete={handleTestComplete}
        />
      )}

      {/* Test All Modal */}
      {showTestAllModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white dark:bg-gray-800 rounded-lg w-full max-w-lg max-h-[90vh] overflow-hidden flex flex-col">
            {/* Header */}
            <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
              <div className="flex items-center gap-3">
                {testingAll ? (
                  <Loader2 className="w-6 h-6 text-blue-500 animate-spin" />
                ) : (
                  <PlayCircle className="w-6 h-6 text-emerald-500" />
                )}
                <div>
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                    {t('services:testAll.title')}
                  </h3>
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    {t(testAllResults.length > 1 ? 'services:testAll.subtitle_plural' : 'services:testAll.subtitle', { count: testAllResults.length })}
                  </p>
                </div>
              </div>
              <button
                onClick={() => setShowTestAllModal(false)}
                disabled={testingAll}
                className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors disabled:opacity-50"
              >
                <X className="w-5 h-5 text-gray-500" />
              </button>
            </div>

            {/* Results List */}
            <div className="flex-1 overflow-y-auto p-4">
              <div className="space-y-2">
                {testAllResults.map((result) => {
                  const colors = getServiceColor(result.service_type);
                  const Icon = colors.icon;

                  return (
                    <div
                      key={result.service_id}
                      className={`p-3 rounded-lg border transition-all ${
                        result.status === 'testing'
                          ? 'border-blue-200 dark:border-blue-800 bg-blue-50 dark:bg-blue-900/20'
                          : result.status === 'success'
                          ? 'border-green-200 dark:border-green-800 bg-green-50 dark:bg-green-900/20'
                          : result.status === 'error'
                          ? 'border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/20'
                          : 'border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <div className={`p-1.5 rounded ${colors.bg}`}>
                            <Icon className={`w-4 h-4 ${colors.text}`} />
                          </div>
                          <div>
                            <span className="font-medium text-gray-900 dark:text-white">
                              {result.service_name}
                            </span>
                            <span className="text-xs text-gray-500 dark:text-gray-400 ml-2 capitalize">
                              {result.service_type}
                            </span>
                          </div>
                        </div>

                        <div className="flex items-center gap-2">
                          {result.response_time_ms && (
                            <span className="text-xs text-gray-500 dark:text-gray-400">
                              {result.response_time_ms}ms
                            </span>
                          )}
                          {result.status === 'pending' && (
                            <Clock className="w-4 h-4 text-gray-400" />
                          )}
                          {result.status === 'testing' && (
                            <Loader2 className="w-4 h-4 text-blue-500 animate-spin" />
                          )}
                          {result.status === 'success' && (
                            <CheckCircle className="w-4 h-4 text-green-500" />
                          )}
                          {result.status === 'error' && (
                            <XCircle className="w-4 h-4 text-red-500" />
                          )}
                        </div>
                      </div>

                      {result.error_message && (
                        <div className="mt-2 text-xs text-red-600 dark:text-red-400">
                          {result.error_message}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Footer with Summary */}
            <div className="border-t border-gray-200 dark:border-gray-700 p-4">
              <div className="flex items-center justify-between mb-4">
                <div className="flex gap-4 text-sm">
                  <span className="flex items-center gap-1 text-green-600 dark:text-green-400">
                    <CheckCircle className="w-4 h-4" />
                    {testAllResults.filter(r => r.status === 'success').length} {t('services:testAll.summary.ok')}
                  </span>
                  <span className="flex items-center gap-1 text-red-600 dark:text-red-400">
                    <XCircle className="w-4 h-4" />
                    {testAllResults.filter(r => r.status === 'error').length} {t('services:testAll.summary.error')}
                  </span>
                  {testingAll && (
                    <span className="flex items-center gap-1 text-blue-600 dark:text-blue-400">
                      <Loader2 className="w-4 h-4 animate-spin" />
                      {testAllResults.filter(r => r.status === 'pending' || r.status === 'testing').length} {t('services:testAll.summary.inProgress')}
                    </span>
                  )}
                </div>
              </div>

              <button
                onClick={() => setShowTestAllModal(false)}
                disabled={testingAll}
                className="w-full py-2 px-4 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 rounded-lg transition-colors disabled:opacity-50"
              >
                {testingAll ? t('services:testAll.testing') : t('services:testAll.close')}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ServiceList;
