import React, { useState, useEffect } from 'react';
import { X, Eye, EyeOff, HelpCircle, AlertCircle } from 'lucide-react';
import { useTranslation } from 'react-i18next';

interface ServiceFormData {
  name: string;
  service_type: string;
  description: string;
  base_url: string;
  external_url: string;
  port: string;
  api_key: string;
  username: string;
  password: string;
  enabled: boolean;
  health_check_enabled: boolean;
  health_check_interval: string;
  config?: Record<string, unknown>;
}

interface ServiceFormProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: ServiceFormData) => Promise<void>;
  initialData?: Partial<ServiceFormData>;
  isEditing?: boolean;
}

const SERVICE_TYPES = [
  {
    value: 'plex',
    label: 'Plex Media Server',
    description: 'Personal media streaming service',
    fields: ['api_key'],
    defaultPort: '32400',
    authType: 'token',
    urlPlaceholder: 'http://plex.local'
  },
  {
    value: 'overseerr',
    label: 'Overseerr',
    description: 'Media request and management system',
    fields: ['api_key'],
    defaultPort: '5055',
    authType: 'api_key',
    urlPlaceholder: 'http://overseerr.local'
  },
  {
    value: 'tautulli',
    label: 'Tautulli',
    description: 'Plex monitoring and statistics',
    fields: ['api_key'],
    defaultPort: '8181',
    authType: 'api_key',
    urlPlaceholder: 'http://tautulli.local'
  },
  {
    value: 'zammad',
    label: 'Zammad',
    description: 'Helpdesk and ticketing system',
    fields: ['api_key'],
    defaultPort: '3000',
    authType: 'token',
    urlPlaceholder: 'http://zammad.local'
  },
  {
    value: 'authentik',
    label: 'Authentik',
    description: 'Identity provider and SSO',
    fields: ['api_key'],
    defaultPort: '9000',
    authType: 'bearer',
    urlPlaceholder: 'http://authentik.local'
  },
  {
    value: 'openwebui',
    label: 'Open WebUI',
    description: 'AI chat interface for LLMs (Ollama, OpenAI, etc.)',
    fields: ['api_key'],
    defaultPort: '8080',
    authType: 'bearer',
    urlPlaceholder: 'http://openwebui.local'
  },
  {
    value: 'ollama',
    label: 'Ollama',
    description: 'Local LLM server for running AI models',
    fields: [],
    defaultPort: '11434',
    authType: 'none',
    urlPlaceholder: 'http://ollama.local'
  },
  {
    value: 'radarr',
    label: 'Radarr',
    description: 'Movie collection manager and downloader',
    fields: ['api_key'],
    defaultPort: '7878',
    authType: 'api_key',
    urlPlaceholder: 'http://radarr.local'
  },
  {
    value: 'sonarr',
    label: 'Sonarr',
    description: 'TV series collection manager and downloader',
    fields: ['api_key'],
    defaultPort: '8989',
    authType: 'api_key',
    urlPlaceholder: 'http://sonarr.local'
  },
  {
    value: 'prowlarr',
    label: 'Prowlarr',
    description: 'Indexer manager for *arr stack',
    fields: ['api_key'],
    defaultPort: '9696',
    authType: 'api_key',
    urlPlaceholder: 'http://prowlarr.local'
  },
  {
    value: 'jackett',
    label: 'Jackett',
    description: 'Torrent indexer proxy',
    fields: ['api_key'],
    defaultPort: '9117',
    authType: 'api_key',
    urlPlaceholder: 'http://jackett.local'
  },
  {
    value: 'deluge',
    label: 'Deluge',
    description: 'BitTorrent client',
    fields: ['password'],
    defaultPort: '8112',
    authType: 'password',
    urlPlaceholder: 'http://deluge.local'
  },
  {
    value: 'komga',
    label: 'Komga',
    description: 'Comic and manga server (API key preferred, or username/password)',
    fields: ['api_key'],
    defaultPort: '25600',
    authType: 'api_key',
    urlPlaceholder: 'http://komga.local'
  },
  {
    value: 'romm',
    label: 'RomM',
    description: 'ROM management system (uses username/password - no API keys)',
    fields: ['username', 'password'],
    defaultPort: '8080',
    authType: 'basic',
    urlPlaceholder: 'http://romm.local'
  },
  {
    value: 'audiobookshelf',
    label: 'Audiobookshelf',
    description: 'Audiobook and podcast server with listening progress tracking',
    fields: ['api_key'],
    defaultPort: '13378',
    authType: 'bearer',
    urlPlaceholder: 'http://audiobookshelf.local'
  },
  {
    value: 'wikijs',
    label: 'Wiki.js',
    description: 'Modern wiki and documentation platform with GraphQL API',
    fields: ['api_key'],
    defaultPort: '3000',
    authType: 'bearer',
    urlPlaceholder: 'http://wiki.local'
  },
  {
    value: 'monitoring',
    label: 'Monitoring System',
    description: 'Custom monitoring service',
    fields: ['api_key'],
    defaultPort: '3001',
    authType: 'api_key',
    urlPlaceholder: 'http://monitor.local'
  },
  {
    value: 'custom',
    label: 'Custom Service',
    description: 'Generic service configuration',
    fields: ['api_key', 'username', 'password'],
    defaultPort: '',
    authType: 'custom',
    urlPlaceholder: 'http://service.local'
  }
];

const ServiceForm: React.FC<ServiceFormProps> = ({
  isOpen,
  onClose,
  onSubmit,
  initialData = {},
  isEditing = false
}) => {
  const { t } = useTranslation('services');
  const [formData, setFormData] = useState<ServiceFormData>({
    name: '',
    service_type: '',
    description: '',
    base_url: '',
    external_url: '',
    port: '',
    api_key: '',
    username: '',
    password: '',
    enabled: true,
    health_check_enabled: true,
    health_check_interval: '300',
    config: {},
    ...initialData
  });

  const [showPassword, setShowPassword] = useState(false);
  const [showApiKey, setShowApiKey] = useState(false);
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});

  const selectedServiceType = SERVICE_TYPES.find(type => type.value === formData.service_type);

  useEffect(() => {
    if (formData.service_type && !formData.port) {
      const serviceType = SERVICE_TYPES.find(type => type.value === formData.service_type);
      if (serviceType && serviceType.defaultPort) {
        setFormData(prev => ({ ...prev, port: serviceType.defaultPort }));
      }
    }
  }, [formData.service_type]);

  const handleChange = (field: keyof ServiceFormData, value: string | boolean) => {
    setFormData(prev => ({ ...prev, [field]: value }));

    // Clear error for this field
    if (errors[field]) {
      setErrors(prev => ({ ...prev, [field]: '' }));
    }
  };

  const handleConfigChange = (key: string, value: string) => {
    setFormData(prev => ({
      ...prev,
      config: { ...prev.config, [key]: value || undefined }
    }));
  };

  const validateForm = (): boolean => {
    const newErrors: Record<string, string> = {};

    if (!formData.name.trim()) {
      newErrors.name = t('form.errors.nameRequired');
    }

    if (!formData.service_type) {
      newErrors.service_type = t('form.errors.typeRequired');
    }

    if (!formData.base_url.trim()) {
      newErrors.base_url = t('form.errors.urlRequired');
    } else {
      try {
        new URL(formData.base_url);
      } catch {
        newErrors.base_url = t('form.errors.urlInvalid');
      }
    }

    if (formData.port && (isNaN(Number(formData.port)) || Number(formData.port) < 1 || Number(formData.port) > 65535)) {
      newErrors.port = t('form.errors.portInvalid');
    }

    // Validate external URL if provided
    if (formData.external_url && formData.external_url.trim()) {
      try {
        new URL(formData.external_url);
      } catch {
        newErrors.external_url = t('form.errors.urlInvalid');
      }
    }

    // Validate auth fields based on service type
    if (selectedServiceType) {
      if (selectedServiceType.fields.includes('api_key') && !formData.api_key.trim()) {
        newErrors.api_key = t('form.errors.apiKeyRequired');
      }
      if (selectedServiceType.fields.includes('username') && !formData.username.trim()) {
        newErrors.username = t('form.errors.usernameRequired');
      }
      if (selectedServiceType.fields.includes('password') && !formData.password.trim()) {
        newErrors.password = t('form.errors.passwordRequired');
      }
    }

    if (formData.health_check_interval && isNaN(Number(formData.health_check_interval))) {
      newErrors.health_check_interval = t('form.errors.intervalInvalid');
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateForm()) {
      return;
    }

    setLoading(true);
    try {
      await onSubmit(formData);
      onClose();
    } catch (error) {
      console.error('Error submitting form:', error);
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-gray-800 rounded-lg w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <div className="sticky top-0 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 p-6">
          <div className="flex items-center justify-between">
            <h3 className="text-xl font-semibold text-gray-900 dark:text-white">
              {isEditing ? t('form.editTitle') : t('form.addTitle')}
            </h3>
            <button
              onClick={onClose}
              className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors text-gray-600 dark:text-gray-400"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          {/* Basic Information */}
          <div className="space-y-4">
            <h4 className="text-lg font-medium text-gray-900 dark:text-white">{t('form.basicInfo')}</h4>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                {t('form.serviceName')} *
              </label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => handleChange('name', e.target.value)}
                className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-white ${
                  errors.name ? 'border-red-500' : 'border-gray-300 dark:border-gray-600'
                }`}
                placeholder={t('form.serviceNamePlaceholder')}
                disabled={loading}
              />
              {errors.name && (
                <p className="mt-1 text-sm text-red-600 flex items-center">
                  <AlertCircle className="w-4 h-4 mr-1" />
                  {errors.name}
                </p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                {t('form.serviceType')} *
              </label>
              <select
                value={formData.service_type}
                onChange={(e) => handleChange('service_type', e.target.value)}
                className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-white ${
                  errors.service_type ? 'border-red-500' : 'border-gray-300 dark:border-gray-600'
                }`}
                disabled={loading}
              >
                <option value="">{t('form.selectServiceType')}</option>
                {SERVICE_TYPES.map((type) => (
                  <option key={type.value} value={type.value}>
                    {type.label}
                  </option>
                ))}
              </select>
              {selectedServiceType && (
                <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
                  {selectedServiceType.description}
                </p>
              )}
              {errors.service_type && (
                <p className="mt-1 text-sm text-red-600 flex items-center">
                  <AlertCircle className="w-4 h-4 mr-1" />
                  {errors.service_type}
                </p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                {t('form.description')}
              </label>
              <textarea
                value={formData.description}
                onChange={(e) => handleChange('description', e.target.value)}
                rows={3}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder={t('form.descriptionPlaceholder')}
                disabled={loading}
              />
            </div>
          </div>

          {/* Connection Settings */}
          <div className="space-y-4">
            <h4 className="text-lg font-medium text-gray-900 dark:text-white">{t('form.connection')}</h4>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="md:col-span-2">
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  {t('form.baseUrl')} *
                </label>
                <input
                  type="url"
                  value={formData.base_url}
                  onChange={(e) => handleChange('base_url', e.target.value)}
                  className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-white ${
                    errors.base_url ? 'border-red-500' : 'border-gray-300 dark:border-gray-600'
                  }`}
                  placeholder={selectedServiceType?.urlPlaceholder || 'http://service.local'}
                  disabled={loading}
                />
                <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
                  {t('form.baseUrlHelp')}
                </p>
                {errors.base_url && (
                  <p className="mt-1 text-sm text-red-600 flex items-center">
                    <AlertCircle className="w-4 h-4 mr-1" />
                    {errors.base_url}
                  </p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  {t('form.port')}
                </label>
                <input
                  type="number"
                  value={formData.port}
                  onChange={(e) => handleChange('port', e.target.value)}
                  className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-white ${
                    errors.port ? 'border-red-500' : 'border-gray-300 dark:border-gray-600'
                  }`}
                  placeholder="8080"
                  min="1"
                  max="65535"
                  disabled={loading}
                />
                {errors.port && (
                  <p className="mt-1 text-sm text-red-600 flex items-center">
                    <AlertCircle className="w-4 h-4 mr-1" />
                    {errors.port}
                  </p>
                )}
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                {t('form.externalUrl')}
                <span title={t('form.externalUrlHelp')}>
                  <HelpCircle className="w-4 h-4 inline ml-1 text-gray-400" />
                </span>
              </label>
              <input
                type="url"
                value={formData.external_url}
                onChange={(e) => handleChange('external_url', e.target.value)}
                className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-white ${
                  errors.external_url ? 'border-red-500' : 'border-gray-300 dark:border-gray-600'
                }`}
                placeholder="https://service.example.com"
                disabled={loading}
              />
              {errors.external_url && (
                <p className="mt-1 text-sm text-red-600 flex items-center">
                  <AlertCircle className="w-4 h-4 mr-1" />
                  {errors.external_url}
                </p>
              )}
              <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
                {t('form.externalUrlHelp')}
              </p>
            </div>
          </div>

          {/* Authentication */}
          {selectedServiceType && selectedServiceType.fields.length > 0 && (
            <div className="space-y-4">
              <h4 className="text-lg font-medium text-gray-900 dark:text-white">{t('form.authentication')}</h4>

              {selectedServiceType.fields.includes('api_key') && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    {t('form.apiKey')} *
                    <span title={t('form.apiKeyHelp')}>
                      <HelpCircle className="w-4 h-4 inline ml-1 text-gray-400" />
                    </span>
                  </label>
                  <div className="relative">
                    <input
                      type={showApiKey ? 'text' : 'password'}
                      value={formData.api_key}
                      onChange={(e) => handleChange('api_key', e.target.value)}
                      className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent pr-10 dark:bg-gray-700 dark:text-white ${
                        errors.api_key ? 'border-red-500' : 'border-gray-300 dark:border-gray-600'
                      }`}
                      placeholder={t('form.apiKeyHelp')}
                      disabled={loading}
                    />
                    <button
                      type="button"
                      onClick={() => setShowApiKey(!showApiKey)}
                      className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
                    >
                      {showApiKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                  {errors.api_key && (
                    <p className="mt-1 text-sm text-red-600 flex items-center">
                      <AlertCircle className="w-4 h-4 mr-1" />
                      {errors.api_key}
                    </p>
                  )}
                </div>
              )}

              {selectedServiceType.fields.includes('username') && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    {t('form.username')} *
                  </label>
                  <input
                    type="text"
                    value={formData.username}
                    onChange={(e) => handleChange('username', e.target.value)}
                    className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-white ${
                      errors.username ? 'border-red-500' : 'border-gray-300 dark:border-gray-600'
                    }`}
                    placeholder={t('form.username')}
                    disabled={loading}
                  />
                  {errors.username && (
                    <p className="mt-1 text-sm text-red-600 flex items-center">
                      <AlertCircle className="w-4 h-4 mr-1" />
                      {errors.username}
                    </p>
                  )}
                </div>
              )}

              {selectedServiceType.fields.includes('password') && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    {t('form.password')} *
                  </label>
                  <div className="relative">
                    <input
                      type={showPassword ? 'text' : 'password'}
                      value={formData.password}
                      onChange={(e) => handleChange('password', e.target.value)}
                      className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent pr-10 dark:bg-gray-700 dark:text-white ${
                        errors.password ? 'border-red-500' : 'border-gray-300 dark:border-gray-600'
                      }`}
                      placeholder={t('form.password')}
                      disabled={loading}
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
                    >
                      {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                  {errors.password && (
                    <p className="mt-1 text-sm text-red-600 flex items-center">
                      <AlertCircle className="w-4 h-4 mr-1" />
                      {errors.password}
                    </p>
                  )}
                </div>
              )}
            </div>
          )}

          {/* WikiJS-specific Settings */}
          {formData.service_type === 'wikijs' && (
            <div className="space-y-4">
              <h4 className="text-lg font-medium text-gray-900 dark:text-white">{t('form.wikijsSettings')}</h4>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  {t('form.defaultLocale')}
                  <span className="ml-1 text-gray-400 font-normal">({t('form.optional')})</span>
                </label>
                <select
                  value={(formData.config?.default_locale as string) || ''}
                  onChange={(e) => handleConfigChange('default_locale', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-white"
                  disabled={loading}
                >
                  <option value="">{t('form.defaultLocaleAuto')}</option>
                  <option value="en">English (en)</option>
                  <option value="fr">Français (fr)</option>
                  <option value="de">Deutsch (de)</option>
                  <option value="es">Español (es)</option>
                  <option value="it">Italiano (it)</option>
                  <option value="pt">Português (pt)</option>
                  <option value="nl">Nederlands (nl)</option>
                  <option value="ru">Русский (ru)</option>
                  <option value="zh">中文 (zh)</option>
                  <option value="ja">日本語 (ja)</option>
                  <option value="ko">한국어 (ko)</option>
                </select>
                <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                  {t('form.defaultLocaleDescription')}
                </p>
              </div>
            </div>
          )}

          {/* Health Check Settings */}
          <div className="space-y-4">
            <h4 className="text-lg font-medium text-gray-900 dark:text-white">{t('form.options')}</h4>

            <div className="flex items-center space-x-3">
              <input
                type="checkbox"
                id="health_check_enabled"
                checked={formData.health_check_enabled}
                onChange={(e) => handleChange('health_check_enabled', e.target.checked)}
                className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                disabled={loading}
              />
              <label htmlFor="health_check_enabled" className="text-sm font-medium text-gray-700 dark:text-gray-300">
                {t('form.healthCheckEnabled')}
              </label>
            </div>

            {formData.health_check_enabled && (
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  {t('form.healthCheckInterval')}
                </label>
                <input
                  type="number"
                  value={formData.health_check_interval}
                  onChange={(e) => handleChange('health_check_interval', e.target.value)}
                  className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-white ${
                    errors.health_check_interval ? 'border-red-500' : 'border-gray-300 dark:border-gray-600'
                  }`}
                  placeholder="300"
                  min="30"
                  disabled={loading}
                />
                {errors.health_check_interval && (
                  <p className="mt-1 text-sm text-red-600 flex items-center">
                    <AlertCircle className="w-4 h-4 mr-1" />
                    {errors.health_check_interval}
                  </p>
                )}
              </div>
            )}

            <div className="flex items-center space-x-3">
              <input
                type="checkbox"
                id="enabled"
                checked={formData.enabled}
                onChange={(e) => handleChange('enabled', e.target.checked)}
                className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                disabled={loading}
              />
              <label htmlFor="enabled" className="text-sm font-medium text-gray-700 dark:text-gray-300">
                {t('form.enabled')}
              </label>
            </div>
          </div>

          {/* Form Actions */}
          <div className="flex justify-end space-x-3 pt-6 border-t border-gray-200 dark:border-gray-700">
            <button
              type="button"
              onClick={onClose}
              className="px-6 py-2 text-gray-700 dark:text-gray-300 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
              disabled={loading}
            >
              {t('form.cancel')}
            </button>
            <button
              type="submit"
              className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              disabled={loading}
            >
              {loading ? t('form.saving') : t('form.save')}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default ServiceForm;