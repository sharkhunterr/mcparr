import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Search, Zap, ToggleLeft, ToggleRight, Loader2, ChevronDown, ChevronRight } from 'lucide-react';
import { getApiBaseUrl } from '../../lib/api';
import { getServiceColor } from '../../lib/serviceColors';

interface SearchableService {
  service_id: string;
  service_name: string;
  service_type: string;
  search_tool: string;
  enabled_for_global_search: boolean;
  priority: number;
  service_enabled: boolean;
}

interface GlobalSearchSettings {
  enabled: boolean;
  hide_notifications: boolean;
}

export default function GlobalSearchConfig() {
  const { t } = useTranslation('mcp');
  const [services, setServices] = useState<SearchableService[]>([]);
  const [settings, setSettings] = useState<GlobalSearchSettings>({ enabled: true, hide_notifications: false });
  const [loading, setLoading] = useState(true);
  const [updating, setUpdating] = useState<string | null>(null);
  const [updatingSettings, setUpdatingSettings] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [servicesExpanded, setServicesExpanded] = useState(false);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [servicesRes, settingsRes] = await Promise.all([
        fetch(`${getApiBaseUrl()}/api/global-search/services`),
        fetch(`${getApiBaseUrl()}/api/global-search/settings`),
      ]);

      if (!servicesRes.ok) throw new Error('Failed to fetch services');
      if (!settingsRes.ok) throw new Error('Failed to fetch settings');

      const servicesData = await servicesRes.json();
      const settingsData = await settingsRes.json();

      setServices(servicesData);
      setSettings(settingsData);
    } catch (err) {
      setError('Failed to load configuration');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const updateSettings = async (newSettings: Partial<GlobalSearchSettings>) => {
    setUpdatingSettings(true);
    try {
      const response = await fetch(`${getApiBaseUrl()}/api/global-search/settings`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newSettings),
      });

      if (!response.ok) throw new Error('Failed to update settings');

      const data = await response.json();
      setSettings(data);
    } catch (err) {
      console.error('Failed to update settings:', err);
    } finally {
      setUpdatingSettings(false);
    }
  };

  const toggleService = async (serviceId: string, currentEnabled: boolean) => {
    setUpdating(serviceId);
    try {
      const response = await fetch(`${getApiBaseUrl()}/api/global-search/config/${serviceId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled: !currentEnabled }),
      });

      if (!response.ok) throw new Error('Failed to update');

      setServices((prev) =>
        prev.map((s) =>
          s.service_id === serviceId
            ? { ...s, enabled_for_global_search: !currentEnabled }
            : s
        )
      );
    } catch (err) {
      console.error('Failed to toggle service:', err);
    } finally {
      setUpdating(null);
    }
  };

  const toggleAll = async (enable: boolean) => {
    for (const service of services) {
      if (service.enabled_for_global_search !== enable && service.service_enabled) {
        await toggleService(service.service_id, !enable);
      }
    }
  };

  const enabledCount = services.filter(s => s.enabled_for_global_search && s.service_enabled).length;
  const totalCount = services.filter(s => s.service_enabled).length;

  if (loading) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
        <div className="flex items-center justify-center py-8">
          <Loader2 className="w-6 h-6 animate-spin text-teal-600" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
        <div className="text-center text-red-500 py-8">{error}</div>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-4 sm:p-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-4">
        <div className="flex items-center gap-3">
          <Search className="w-5 h-5 text-teal-600 flex-shrink-0" />
          <div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2 flex-wrap">
              {t('globalSearch.title')}
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-teal-100 text-teal-700 dark:bg-teal-900/30 dark:text-teal-300">
                <Zap className="w-3 h-3" />
                Smart
              </span>
            </h3>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              {t('globalSearch.description')}
            </p>
          </div>
        </div>
      </div>

      {/* Global Settings - Single line */}
      <div className="mb-4 p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
        <div className="flex flex-wrap items-center gap-4 sm:gap-6">
          {/* Enable toggle */}
          <button
            onClick={() => updateSettings({ enabled: !settings.enabled })}
            disabled={updatingSettings}
            className="flex items-center gap-2"
          >
            {updatingSettings ? (
              <Loader2 className="w-5 h-5 animate-spin text-gray-400" />
            ) : settings.enabled ? (
              <ToggleRight className="w-5 h-5 text-green-500" />
            ) : (
              <ToggleLeft className="w-5 h-5 text-gray-400" />
            )}
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
              {t('globalSearch.featureEnabled')}
            </span>
          </button>

          {/* Separator */}
          <div className="hidden sm:block w-px h-5 bg-gray-300 dark:bg-gray-600" />

          {/* Hide notifications toggle */}
          <button
            onClick={() => updateSettings({ hide_notifications: !settings.hide_notifications })}
            disabled={updatingSettings}
            className="flex items-center gap-2"
          >
            {updatingSettings ? (
              <Loader2 className="w-5 h-5 animate-spin text-gray-400" />
            ) : settings.hide_notifications ? (
              <ToggleRight className="w-5 h-5 text-green-500" />
            ) : (
              <ToggleLeft className="w-5 h-5 text-gray-400" />
            )}
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
              {t('globalSearch.hideNotifications')}
            </span>
          </button>
        </div>
      </div>

      {/* Feature disabled message */}
      {!settings.enabled && (
        <div className="mb-4 p-3 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg">
          <p className="text-sm text-yellow-700 dark:text-yellow-300">
            {t('globalSearch.featureDisabledMessage')}
          </p>
        </div>
      )}

      {services.length === 0 ? (
        <div className="text-center py-8">
          <p className="text-gray-500 dark:text-gray-400 text-sm">
            {t('globalSearch.noSearchableServices')}
          </p>
          <p className="text-gray-400 dark:text-gray-500 text-xs mt-1">
            {t('globalSearch.noSearchableServicesHint')}
          </p>
        </div>
      ) : (
        <>
          {/* Expandable Services Section */}
          <div className={`border border-gray-200 dark:border-gray-700 rounded-lg ${!settings.enabled ? 'opacity-50 pointer-events-none' : ''}`}>
            {/* Expand Header */}
            <button
              onClick={() => setServicesExpanded(!servicesExpanded)}
              className="w-full flex items-center justify-between p-3 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
            >
              <div className="flex items-center gap-2">
                {servicesExpanded ? (
                  <ChevronDown className="w-4 h-4 text-gray-500" />
                ) : (
                  <ChevronRight className="w-4 h-4 text-gray-500" />
                )}
                <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  {t('globalSearch.configDescription')}
                </span>
              </div>
              <span className="text-xs text-gray-500 dark:text-gray-400 bg-gray-100 dark:bg-gray-700 px-2 py-1 rounded">
                {enabledCount}/{totalCount}
              </span>
            </button>

            {/* Expanded Content */}
            {servicesExpanded && (
              <div className="border-t border-gray-200 dark:border-gray-700 p-3">
                {/* Enable/Disable All */}
                <div className="flex items-center gap-2 mb-3">
                  <button
                    onClick={() => toggleAll(true)}
                    className="text-xs px-2 py-1 rounded bg-green-100 text-green-700 hover:bg-green-200 dark:bg-green-900/30 dark:text-green-300 dark:hover:bg-green-900/50"
                  >
                    {t('globalSearch.enableAll')}
                  </button>
                  <button
                    onClick={() => toggleAll(false)}
                    className="text-xs px-2 py-1 rounded bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600"
                  >
                    {t('globalSearch.disableAll')}
                  </button>
                </div>

                {/* Services List - Compact */}
                <div className="flex flex-wrap gap-2">
                  {services.map((service) => {
                    const serviceColor = getServiceColor(service.service_type);
                    const isDisabledService = !service.service_enabled;

                    return (
                      <button
                        key={service.service_id}
                        onClick={() =>
                          !isDisabledService &&
                          toggleService(service.service_id, service.enabled_for_global_search)
                        }
                        disabled={isDisabledService || updating === service.service_id}
                        className={`inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border text-sm transition-colors ${
                          isDisabledService
                            ? 'bg-gray-50 dark:bg-gray-900/50 border-gray-200 dark:border-gray-700 opacity-50 cursor-not-allowed'
                            : service.enabled_for_global_search
                            ? 'bg-green-50 dark:bg-green-900/20 border-green-300 dark:border-green-700 hover:bg-green-100 dark:hover:bg-green-900/30'
                            : 'bg-gray-50 dark:bg-gray-800 border-gray-200 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-700'
                        }`}
                      >
                        {updating === service.service_id ? (
                          <Loader2 className="w-3 h-3 animate-spin text-gray-400" />
                        ) : service.enabled_for_global_search ? (
                          <ToggleRight className="w-4 h-4 text-green-500" />
                        ) : (
                          <ToggleLeft className="w-4 h-4 text-gray-400" />
                        )}
                        <span
                          className={`font-medium ${serviceColor.text}`}
                        >
                          {service.service_name}
                        </span>
                      </button>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
