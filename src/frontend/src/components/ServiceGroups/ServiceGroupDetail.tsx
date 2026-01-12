import { useState, useEffect } from 'react';
import type { FC } from 'react';
import {
  X,
  Save,
  Loader2,
  Server,
  Info,
  Plus,
  Trash2,
  Check
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { getApiBaseUrl } from '../../lib/api';
import type { ServiceGroup, AvailableService } from '../../types/api';

interface ServiceGroupDetailProps {
  group: ServiceGroup;
  onClose: () => void;
  onUpdated: () => void;
}

type TabType = 'info' | 'services';

const PRESET_COLORS = [
  '#f97316', // Orange (default)
  '#6366f1', // Indigo
  '#8b5cf6', // Violet
  '#ec4899', // Pink
  '#ef4444', // Red
  '#f97316', // Orange
  '#eab308', // Yellow
  '#22c55e', // Green
  '#06b6d4', // Cyan
  '#3b82f6', // Blue
];

const ServiceGroupDetail: FC<ServiceGroupDetailProps> = ({ group, onClose, onUpdated }) => {
  const { t } = useTranslation('services');
  const [activeTab, setActiveTab] = useState<TabType>('info');
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Info tab state
  const [name, setName] = useState(group.name);
  const [description, setDescription] = useState(group.description || '');
  const [color, setColor] = useState(group.color || '#f97316');
  const [priority, setPriority] = useState(group.priority);

  // Services tab state
  const [groupServices, setGroupServices] = useState<string[]>(group.service_types || []);
  const [availableServices, setAvailableServices] = useState<AvailableService[]>([]);
  const [servicesLoading, setServicesLoading] = useState(false);

  const backendUrl = getApiBaseUrl();

  useEffect(() => {
    if (activeTab === 'services') {
      fetchAvailableServices();
    }
  }, [activeTab]);

  const fetchAvailableServices = async () => {
    try {
      setServicesLoading(true);
      const response = await fetch(`${backendUrl}/api/service-groups/available-services`);
      if (!response.ok) throw new Error('Failed to fetch services');
      const data = await response.json();
      setAvailableServices(data.services);

      // Also refresh group services
      const groupResponse = await fetch(`${backendUrl}/api/service-groups/${group.id}`);
      if (groupResponse.ok) {
        const groupData = await groupResponse.json();
        setGroupServices(groupData.service_types || []);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch services');
    } finally {
      setServicesLoading(false);
    }
  };

  const handleSaveInfo = async () => {
    try {
      setSaving(true);
      setError(null);
      const response = await fetch(`${backendUrl}/api/service-groups/${group.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, description, color, priority })
      });
      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Failed to update group');
      }
      onUpdated();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update group');
    } finally {
      setSaving(false);
    }
  };

  const handleToggleService = async (serviceType: string) => {
    const isInGroup = groupServices.includes(serviceType);
    try {
      setError(null);
      if (isInGroup) {
        // Remove service from group
        const response = await fetch(`${backendUrl}/api/service-groups/${group.id}/services/${serviceType}`, {
          method: 'DELETE'
        });
        if (!response.ok) throw new Error('Failed to remove service');
        setGroupServices(prev => prev.filter(s => s !== serviceType));
      } else {
        // Add service to group
        const response = await fetch(`${backendUrl}/api/service-groups/${group.id}/services`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ service_type: serviceType })
        });
        if (!response.ok) throw new Error('Failed to add service');
        setGroupServices(prev => [...prev, serviceType]);
      }
      onUpdated();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update services');
    }
  };

  const tabs: { id: TabType; label: string; icon: React.ReactNode }[] = [
    { id: 'info', label: t('serviceGroups.detail.tabs.info'), icon: <Info className="w-4 h-4" /> },
    { id: 'services', label: t('serviceGroups.detail.tabs.services'), icon: <Server className="w-4 h-4" /> },
  ];

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div
            className="w-4 h-4 rounded-full"
            style={{ backgroundColor: color }}
          />
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">{group.name}</h2>
          {group.is_system && (
            <span className="px-2 py-0.5 text-xs bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-400 rounded">
              {t('serviceGroups.list.system')}
            </span>
          )}
        </div>
        <button
          onClick={onClose}
          className="p-1.5 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Tabs */}
      <div className="px-4 py-2 border-b border-gray-200 dark:border-gray-700">
        <div className="flex space-x-1">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center space-x-2 px-3 py-2 text-sm font-medium rounded-lg transition-colors ${
                activeTab === tab.id
                  ? 'bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-300'
                  : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700'
              }`}
            >
              {tab.icon}
              <span>{tab.label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="mx-4 mt-4 p-3 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-800">
          <span className="text-sm text-red-700 dark:text-red-400">{error}</span>
        </div>
      )}

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4">
        {activeTab === 'info' && (
          <div className="space-y-4">
            {/* Name */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                {t('serviceGroups.detail.name')}
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                disabled={group.is_system}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent disabled:opacity-50"
              />
            </div>

            {/* Description */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                {t('serviceGroups.detail.description')}
              </label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={3}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent resize-none"
              />
            </div>

            {/* Color */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                {t('serviceGroups.detail.color')}
              </label>
              <div className="flex flex-wrap gap-2">
                {PRESET_COLORS.map((c) => (
                  <button
                    key={c}
                    onClick={() => setColor(c)}
                    className={`w-8 h-8 rounded-full border-2 transition-all ${
                      color === c
                        ? 'border-gray-900 dark:border-white scale-110'
                        : 'border-transparent hover:scale-105'
                    }`}
                    style={{ backgroundColor: c }}
                  />
                ))}
              </div>
            </div>

            {/* Priority */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                {t('serviceGroups.detail.priority')}
              </label>
              <input
                type="number"
                value={priority}
                onChange={(e) => setPriority(parseInt(e.target.value) || 0)}
                className="w-24 px-3 py-2 border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent"
              />
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                {t('serviceGroups.detail.priorityHelp')}
              </p>
            </div>

            {/* Save button */}
            <div className="pt-4">
              <button
                onClick={handleSaveInfo}
                disabled={saving || !name.trim()}
                className="flex items-center space-x-2 px-4 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700 disabled:opacity-50 transition-colors"
              >
                {saving ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Save className="w-4 h-4" />
                )}
                <span>{t('serviceGroups.detail.save')}</span>
              </button>
            </div>
          </div>
        )}

        {activeTab === 'services' && (
          <div className="space-y-4">
            <p className="text-sm text-gray-600 dark:text-gray-400">
              {t('serviceGroups.detail.servicesHelp')}
            </p>

            {servicesLoading ? (
              <div className="flex justify-center py-8">
                <Loader2 className="w-6 h-6 text-orange-600 animate-spin" />
              </div>
            ) : (
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                {availableServices.map((service) => {
                  const isInGroup = groupServices.includes(service.service_type);
                  return (
                    <button
                      key={service.service_type}
                      onClick={() => handleToggleService(service.service_type)}
                      className={`p-3 rounded-lg border text-left transition-all ${
                        isInGroup
                          ? 'border-orange-500 bg-orange-50 dark:bg-orange-900/20'
                          : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
                      } ${!service.configured ? 'opacity-50' : ''}`}
                    >
                      <div className="flex items-center justify-between">
                        <span className={`font-medium text-sm ${
                          isInGroup ? 'text-orange-700 dark:text-orange-300' : 'text-gray-700 dark:text-gray-300'
                        }`}>
                          {service.display_name}
                        </span>
                        {isInGroup && (
                          <Check className="w-4 h-4 text-orange-600" />
                        )}
                      </div>
                      {!service.configured && (
                        <span className="text-xs text-gray-400">
                          {t('serviceGroups.detail.notConfigured')}
                        </span>
                      )}
                    </button>
                  );
                })}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default ServiceGroupDetail;
