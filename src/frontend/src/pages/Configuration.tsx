import { useState, useEffect } from 'react';
import {
  Settings,
  Palette,
  Bell,
  FileText,
  Monitor,
  Moon,
  Sun,
  RotateCcw,
  Check,
  RefreshCw,
  LayoutDashboard,
  Download,
  Upload,
  Database,
  Server,
  Users,
  Shield,
  Brain,
  Wrench,
  AlertCircle,
  CheckCircle,
  Loader2,
  FolderArchive,
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useTheme } from '../contexts/ThemeContext';
import { useSettings, type LogLevel } from '../contexts/SettingsContext';
import { useWizard } from '../contexts/WizardContext';
import { useNavigate } from 'react-router-dom';
import { api } from '../lib/api';

type TabId = 'appearance' | 'general' | 'logs' | 'notifications' | 'dashboard' | 'backup';

interface ExportOptions {
  services: boolean;
  user_mappings: boolean;
  groups: boolean;
  site_config: boolean;
  training_prompts: boolean;
}

interface ImportOptions extends ExportOptions {
  merge_mode: boolean;
}

interface PreviewStats {
  services?: number;
  user_mappings?: number;
  groups?: number;
  group_memberships?: number;
  group_permissions?: number;
  site_config?: number;
  training_prompts?: number;
}

const logLevelValues: LogLevel[] = ['debug', 'info', 'warning', 'error', 'critical'];

// Toggle Switch Component
function Toggle({
  enabled,
  onChange,
  disabled = false,
}: {
  enabled: boolean;
  onChange: (value: boolean) => void;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={() => !disabled && onChange(!enabled)}
      disabled={disabled}
      className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
        disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'
      } ${enabled ? 'bg-blue-600' : 'bg-gray-300 dark:bg-gray-600'}`}
    >
      <span
        className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
          enabled ? 'translate-x-6' : 'translate-x-1'
        }`}
      />
    </button>
  );
}

export default function Configuration() {
  const { t } = useTranslation('configuration');
  const { t: tCommon } = useTranslation('common');
  const [activeTab, setActiveTab] = useState<TabId>('appearance');
  const { theme, setTheme } = useTheme();
  const { settings, updateSettings, resetSettings } = useSettings();
  const { resetWizard } = useWizard();
  const navigate = useNavigate();
  const [showResetConfirm, setShowResetConfirm] = useState(false);

  const tabs = [
    { id: 'appearance' as const, label: t('tabs.appearance'), icon: Palette },
    { id: 'general' as const, label: t('tabs.general'), icon: RefreshCw },
    { id: 'logs' as const, label: t('tabs.logs'), icon: FileText },
    { id: 'notifications' as const, label: t('tabs.notifications'), icon: Bell },
    { id: 'dashboard' as const, label: t('tabs.dashboard'), icon: LayoutDashboard },
    { id: 'backup' as const, label: t('tabs.backup'), icon: FolderArchive },
  ];

  const logLevels: { value: LogLevel; label: string }[] = logLevelValues.map(value => ({
    value,
    label: t(`logs.levels.${value}`)
  }));

  const backupCategories = [
    { key: 'services' as const, label: t('backup.categories.services.label'), icon: Server, description: t('backup.categories.services.description') },
    { key: 'user_mappings' as const, label: t('backup.categories.user_mappings.label'), icon: Users, description: t('backup.categories.user_mappings.description') },
    { key: 'groups' as const, label: t('backup.categories.groups.label'), icon: Shield, description: t('backup.categories.groups.description') },
    { key: 'site_config' as const, label: t('backup.categories.site_config.label'), icon: Wrench, description: t('backup.categories.site_config.description') },
    { key: 'training_prompts' as const, label: t('backup.categories.training_prompts.label'), icon: Brain, description: t('backup.categories.training_prompts.description') },
  ];

  // Backup states
  const [exportOptions, setExportOptions] = useState<ExportOptions>({
    services: true,
    user_mappings: true,
    groups: true,
    site_config: true,
    training_prompts: true,
  });
  const [importOptions, setImportOptions] = useState<ImportOptions>({
    services: true,
    user_mappings: true,
    groups: true,
    site_config: true,
    training_prompts: true,
    merge_mode: false,
  });
  const [previewStats, setPreviewStats] = useState<PreviewStats>({});
  const [loadingPreview, setLoadingPreview] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState<{
    success: boolean;
    imported: Record<string, number>;
    errors: { type: string; name: string; error: string }[];
    warnings: string[];
  } | null>(null);
  const [importFile, setImportFile] = useState<any>(null);
  const [importFileName, setImportFileName] = useState<string>('');
  const [showResetAllConfirm, setShowResetAllConfirm] = useState(false);
  const [resetting, setResetting] = useState(false);
  const [showWizardAfterReset, setShowWizardAfterReset] = useState(true);

  // Fetch preview stats when backup tab is selected or options change
  useEffect(() => {
    if (activeTab === 'backup') {
      fetchPreviewStats();
    }
  }, [activeTab, exportOptions]);

  const fetchPreviewStats = async () => {
    setLoadingPreview(true);
    try {
      const stats = await api.backup.preview(exportOptions);
      setPreviewStats(stats);
    } catch (error) {
      console.error('Failed to fetch preview stats:', error);
    } finally {
      setLoadingPreview(false);
    }
  };

  const handleFullExport = async () => {
    setExporting(true);
    try {
      const response = await api.backup.export(exportOptions);
      const blob = new Blob([JSON.stringify(response, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `mcparr-backup-${new Date().toISOString().split('T')[0]}.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Export failed:', error);
    } finally {
      setExporting(false);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setImportFileName(file.name);
      const reader = new FileReader();
      reader.onload = (event) => {
        try {
          const data = JSON.parse(event.target?.result as string);
          setImportFile(data);
          setImportResult(null);
        } catch {
          console.error('Invalid backup file');
          setImportFile(null);
        }
      };
      reader.readAsText(file);
    }
  };

  const handleFullImport = async () => {
    if (!importFile) return;

    setImporting(true);
    try {
      const result = await api.backup.import({
        version: importFile.version || '1.0',
        data: importFile.data,
        options: importOptions,
      });
      setImportResult(result);
    } catch (error) {
      console.error('Import failed:', error);
      setImportResult({
        success: false,
        imported: {},
        errors: [{ type: 'system', name: 'import', error: String(error) }],
        warnings: [],
      });
    } finally {
      setImporting(false);
    }
  };

  const handleResetAll = async () => {
    setResetting(true);
    try {
      // Call API to reset all data
      const result = await api.backup.resetAll();
      console.log('Reset result:', result);

      // Show success message
      alert(t('backup.reset.successMessage'));

      // Redirect to wizard or reload page
      if (showWizardAfterReset) {
        resetWizard();
        navigate('/wizard');
      } else {
        window.location.reload();
      }
    } catch (error) {
      console.error('Reset failed:', error);
      alert(t('backup.reset.errorMessage', { error: error instanceof Error ? error.message : 'Unknown error' }));
    } finally {
      setResetting(false);
      setShowResetAllConfirm(false);
    }
  };

  const renderAppearanceTab = () => (
    <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 p-4 sm:p-6">
      <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-4">{t('appearance.title')}</h3>
      <div className="grid grid-cols-3 gap-3">
        {[
          { value: 'light', label: t('appearance.themeOptions.light'), icon: Sun },
          { value: 'dark', label: t('appearance.themeOptions.dark'), icon: Moon },
          { value: 'system', label: t('appearance.themeOptions.system'), icon: Monitor },
        ].map((option) => (
          <button
            key={option.value}
            onClick={() => setTheme(option.value as 'light' | 'dark' | 'system')}
            className={`relative flex flex-col items-center gap-2 p-4 rounded-xl border-2 transition-all ${
              theme === option.value
                ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
            }`}
          >
            <option.icon
              className={`w-6 h-6 ${
                theme === option.value ? 'text-blue-600 dark:text-blue-400' : 'text-gray-500 dark:text-gray-400'
              }`}
            />
            <span
              className={`text-sm font-medium ${
                theme === option.value ? 'text-blue-600 dark:text-blue-400' : 'text-gray-700 dark:text-gray-300'
              }`}
            >
              {option.label}
            </span>
            {theme === option.value && (
              <Check className="w-4 h-4 text-blue-500 absolute top-2 right-2" />
            )}
          </button>
        ))}
      </div>
    </div>
  );

  const handleResetWizard = () => {
    if (window.confirm(t('general.wizard.confirmMessage'))) {
      resetWizard();
      navigate('/wizard');
    }
  };

  const renderGeneralTab = () => (
    <div className="space-y-6">
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 p-4 sm:p-6 space-y-4">
        <div className="flex items-center justify-between py-2">
          <div>
            <p className="text-sm font-medium text-gray-900 dark:text-white">{t('general.language.label')}</p>
            <p className="text-xs text-gray-500 dark:text-gray-400">{t('general.language.description')}</p>
          </div>
          <select
            value={settings.language}
            onChange={(e) => updateSettings({ language: e.target.value as 'fr' | 'en' })}
            className="px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
          >
            <option value="fr">{t('general.language.options.fr')}</option>
            <option value="en">{t('general.language.options.en')}</option>
          </select>
        </div>

        <div className="flex items-center justify-between py-2">
          <div>
            <p className="text-sm font-medium text-gray-900 dark:text-white">{t('general.autoRefresh.label')}</p>
            <p className="text-xs text-gray-500 dark:text-gray-400">{t('general.autoRefresh.description')}</p>
          </div>
          <Toggle
            enabled={settings.autoRefresh}
            onChange={(value) => updateSettings({ autoRefresh: value })}
          />
        </div>

        {settings.autoRefresh && (
          <div className="flex items-center justify-between py-2">
            <div>
              <p className="text-sm font-medium text-gray-900 dark:text-white">{t('general.refreshInterval.label')}</p>
              <p className="text-xs text-gray-500 dark:text-gray-400">{t('general.refreshInterval.description')}</p>
            </div>
            <select
              value={settings.refreshInterval}
              onChange={(e) => updateSettings({ refreshInterval: Number(e.target.value) })}
              className="px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            >
              <option value={5}>5s</option>
              <option value={10}>10s</option>
              <option value={30}>30s</option>
              <option value={60}>1min</option>
            </select>
          </div>
        )}
      </div>

      {/* Wizard section */}
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 p-4 sm:p-6">
        <div className="flex items-start justify-between">
          <div>
            <p className="text-sm font-medium text-gray-900 dark:text-white">{t('general.wizard.label')}</p>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              {t('general.wizard.description')}
            </p>
          </div>
          <button
            onClick={handleResetWizard}
            className="flex items-center gap-2 px-3 py-1.5 text-sm text-blue-600 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded-lg transition-colors"
          >
            <RotateCcw className="w-4 h-4" />
            {t('general.wizard.resetButton')}
          </button>
        </div>
      </div>
    </div>
  );

  const renderLogsTab = () => (
    <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 p-4 sm:p-6 space-y-4">
      <div className="flex items-center justify-between py-2">
        <div>
          <p className="text-sm font-medium text-gray-900 dark:text-white">{t('logs.logLevel.label')}</p>
          <p className="text-xs text-gray-500 dark:text-gray-400">{t('logs.logLevel.description')}</p>
        </div>
        <select
          value={settings.logLevel}
          onChange={(e) => updateSettings({ logLevel: e.target.value as LogLevel })}
          className="px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
        >
          {logLevels.map((level) => (
            <option key={level.value} value={level.value}>
              {level.label}
            </option>
          ))}
        </select>
      </div>

      <div className="flex items-center justify-between py-2">
        <div>
          <p className="text-sm font-medium text-gray-900 dark:text-white">{t('logs.logToConsole.label')}</p>
          <p className="text-xs text-gray-500 dark:text-gray-400">{t('logs.logToConsole.description')}</p>
        </div>
        <Toggle
          enabled={settings.logToConsole}
          onChange={(value) => updateSettings({ logToConsole: value })}
        />
      </div>

      <div className="flex items-center justify-between py-2">
        <div>
          <p className="text-sm font-medium text-gray-900 dark:text-white">{t('logs.logToBackend.label')}</p>
          <p className="text-xs text-gray-500 dark:text-gray-400">{t('logs.logToBackend.description')}</p>
        </div>
        <Toggle
          enabled={settings.logToBackend}
          onChange={(value) => updateSettings({ logToBackend: value })}
        />
      </div>

      {/* Log Levels Preview */}
      <div className="pt-4 border-t border-gray-100 dark:border-gray-700">
        <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">
          {t('logs.levelsPreview', { level: settings.logLevel })}
        </p>
        <div className="flex flex-wrap gap-2">
          {logLevels.map((level) => {
            const isIncluded = logLevels.findIndex((l) => l.value === level.value) >=
              logLevels.findIndex((l) => l.value === settings.logLevel);
            return (
              <span
                key={level.value}
                className={`px-2 py-1 text-xs rounded-full ${
                  isIncluded
                    ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300'
                    : 'bg-gray-100 dark:bg-gray-700 text-gray-400 line-through'
                }`}
              >
                {level.label}
              </span>
            );
          })}
        </div>
      </div>
    </div>
  );

  const renderNotificationsTab = () => (
    <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 p-4 sm:p-6 space-y-4">
      <div className="flex items-center justify-between py-2">
        <div>
          <p className="text-sm font-medium text-gray-900 dark:text-white">{t('notifications.enabled.label')}</p>
          <p className="text-xs text-gray-500 dark:text-gray-400">{t('notifications.enabled.description')}</p>
        </div>
        <Toggle
          enabled={settings.notificationsEnabled}
          onChange={(value) => updateSettings({ notificationsEnabled: value })}
        />
      </div>

      <div className="flex items-center justify-between py-2">
        <div>
          <p className="text-sm font-medium text-gray-900 dark:text-white">{t('notifications.sound.label')}</p>
          <p className="text-xs text-gray-500 dark:text-gray-400">{t('notifications.sound.description')}</p>
        </div>
        <Toggle
          enabled={settings.soundEnabled}
          onChange={(value) => updateSettings({ soundEnabled: value })}
          disabled={!settings.notificationsEnabled}
        />
      </div>

      <div className="flex items-center justify-between py-2">
        <div>
          <p className="text-sm font-medium text-gray-900 dark:text-white">{t('notifications.alertOnError.label')}</p>
          <p className="text-xs text-gray-500 dark:text-gray-400">{t('notifications.alertOnError.description')}</p>
        </div>
        <Toggle
          enabled={settings.alertOnError}
          onChange={(value) => updateSettings({ alertOnError: value })}
          disabled={!settings.notificationsEnabled}
        />
      </div>
    </div>
  );

  const renderDashboardTab = () => (
    <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 p-4 sm:p-6 space-y-4">
      <div className="flex items-center justify-between py-2">
        <div>
          <p className="text-sm font-medium text-gray-900 dark:text-white">{t('dashboard.compactMode.label')}</p>
          <p className="text-xs text-gray-500 dark:text-gray-400">{t('dashboard.compactMode.description')}</p>
        </div>
        <Toggle
          enabled={settings.dashboardCompactMode}
          onChange={(value) => updateSettings({ dashboardCompactMode: value })}
        />
      </div>

      <div className="flex items-center justify-between py-2">
        <div>
          <p className="text-sm font-medium text-gray-900 dark:text-white">{t('dashboard.systemMetrics.label')}</p>
          <p className="text-xs text-gray-500 dark:text-gray-400">{t('dashboard.systemMetrics.description')}</p>
        </div>
        <Toggle
          enabled={settings.showSystemMetrics}
          onChange={(value) => updateSettings({ showSystemMetrics: value })}
        />
      </div>

      <div className="flex items-center justify-between py-2">
        <div>
          <p className="text-sm font-medium text-gray-900 dark:text-white">{t('dashboard.mcpStats.label')}</p>
          <p className="text-xs text-gray-500 dark:text-gray-400">{t('dashboard.mcpStats.description')}</p>
        </div>
        <Toggle
          enabled={settings.showMcpStats}
          onChange={(value) => updateSettings({ showMcpStats: value })}
        />
      </div>
    </div>
  );

  const renderBackupTab = () => (
    <div className="space-y-6">
      {/* Export Section */}
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 p-4 sm:p-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 rounded-lg bg-blue-100 dark:bg-blue-900/30">
            <Download className="w-5 h-5 text-blue-600 dark:text-blue-400" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-gray-900 dark:text-white">{t('backup.export.title')}</h3>
            <p className="text-xs text-gray-500 dark:text-gray-400">{t('backup.export.description')}</p>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 mb-4">
          {backupCategories.map((cat) => {
            const Icon = cat.icon;
            const isChecked = exportOptions[cat.key];
            const count = previewStats[cat.key] ?? 0;

            return (
              <button
                key={cat.key}
                onClick={() => setExportOptions(prev => ({ ...prev, [cat.key]: !prev[cat.key] }))}
                className={`relative flex items-start gap-3 p-3 rounded-lg border-2 transition-all text-left ${
                  isChecked
                    ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                    : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
                }`}
              >
                <div className={`p-1.5 rounded-md ${isChecked ? 'bg-blue-100 dark:bg-blue-900/50' : 'bg-gray-100 dark:bg-gray-700'}`}>
                  <Icon className={`w-4 h-4 ${isChecked ? 'text-blue-600 dark:text-blue-400' : 'text-gray-500 dark:text-gray-400'}`} />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className={`text-sm font-medium ${isChecked ? 'text-blue-700 dark:text-blue-300' : 'text-gray-700 dark:text-gray-300'}`}>
                      {cat.label}
                    </span>
                    {loadingPreview ? (
                      <Loader2 className="w-3 h-3 text-gray-400 animate-spin" />
                    ) : (
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400">
                        {count}
                      </span>
                    )}
                  </div>
                  <p className="text-[10px] text-gray-500 dark:text-gray-400 mt-0.5 truncate">{cat.description}</p>
                </div>
                {isChecked && (
                  <Check className="w-4 h-4 text-blue-500 absolute top-2 right-2" />
                )}
              </button>
            );
          })}
        </div>

        <div className="flex items-center justify-between pt-3 border-t border-gray-100 dark:border-gray-700">
          <div className="text-xs text-gray-500 dark:text-gray-400">
            {t('backup.export.categoriesSelected', { count: Object.values(exportOptions).filter(Boolean).length })}
          </div>
          <button
            onClick={handleFullExport}
            disabled={exporting || Object.values(exportOptions).every(v => !v)}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white text-sm font-medium rounded-lg transition-colors"
          >
            {exporting ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Download className="w-4 h-4" />
            )}
            {t('backup.export.button')}
          </button>
        </div>
      </div>

      {/* Import Section */}
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 p-4 sm:p-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 rounded-lg bg-green-100 dark:bg-green-900/30">
            <Upload className="w-5 h-5 text-green-600 dark:text-green-400" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-gray-900 dark:text-white">{t('backup.import.title')}</h3>
            <p className="text-xs text-gray-500 dark:text-gray-400">{t('backup.import.description')}</p>
          </div>
        </div>

        {/* File Upload */}
        <div className="mb-4">
          <label className="flex flex-col items-center justify-center w-full h-32 border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-lg cursor-pointer hover:border-green-500 dark:hover:border-green-500 transition-colors bg-gray-50 dark:bg-gray-900/50">
            <input
              type="file"
              accept=".json"
              onChange={handleFileSelect}
              className="hidden"
            />
            {importFile ? (
              <div className="text-center">
                <Database className="w-8 h-8 text-green-500 mx-auto mb-2" />
                <p className="text-sm font-medium text-gray-900 dark:text-white">{importFileName}</p>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  {t('backup.import.version', { version: importFile.version })} - {importFile.exported_at ? new Date(importFile.exported_at).toLocaleDateString() : t('backup.import.dateUnknown')}
                </p>
                {importFile.stats && (
                  <div className="flex flex-wrap gap-1 mt-2 justify-center">
                    {Object.entries(importFile.stats).map(([key, value]) => (
                      <span key={key} className="text-[10px] px-1.5 py-0.5 rounded bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300">
                        {key}: {value as number}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ) : (
              <div className="text-center">
                <Upload className="w-8 h-8 text-gray-400 mx-auto mb-2" />
                <p className="text-sm text-gray-600 dark:text-gray-400">{t('backup.import.selectFile')}</p>
                <p className="text-xs text-gray-500 dark:text-gray-400">{t('backup.import.fileType')}</p>
              </div>
            )}
          </label>
        </div>

        {/* Import Options */}
        {importFile && (
          <>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 mb-4">
              {backupCategories.map((cat) => {
                const Icon = cat.icon;
                const isChecked = importOptions[cat.key];
                const hasData = importFile.data?.[cat.key]?.length > 0;

                return (
                  <button
                    key={cat.key}
                    onClick={() => setImportOptions(prev => ({ ...prev, [cat.key]: !prev[cat.key] }))}
                    disabled={!hasData}
                    className={`flex items-center gap-2 p-2 rounded-lg border transition-all ${
                      !hasData
                        ? 'border-gray-200 dark:border-gray-700 opacity-50 cursor-not-allowed'
                        : isChecked
                        ? 'border-green-500 bg-green-50 dark:bg-green-900/20'
                        : 'border-gray-200 dark:border-gray-700 hover:border-gray-300'
                    }`}
                  >
                    <Icon className={`w-4 h-4 ${isChecked && hasData ? 'text-green-600' : 'text-gray-400'}`} />
                    <span className={`text-xs font-medium ${isChecked && hasData ? 'text-green-700 dark:text-green-300' : 'text-gray-600 dark:text-gray-400'}`}>
                      {cat.label}
                    </span>
                    {hasData && isChecked && <Check className="w-3 h-3 text-green-500 ml-auto" />}
                  </button>
                );
              })}
            </div>

            {/* Merge Mode Toggle */}
            <div className="flex items-center justify-between p-3 bg-amber-50 dark:bg-amber-900/20 rounded-lg border border-amber-200 dark:border-amber-800 mb-4">
              <div className="flex items-center gap-2">
                <AlertCircle className="w-4 h-4 text-amber-600 dark:text-amber-400" />
                <div>
                  <p className="text-sm font-medium text-amber-800 dark:text-amber-200">{t('backup.import.mergeMode.label')}</p>
                  <p className="text-xs text-amber-600 dark:text-amber-400">{t('backup.import.mergeMode.description')}</p>
                </div>
              </div>
              <Toggle
                enabled={importOptions.merge_mode}
                onChange={(value) => setImportOptions(prev => ({ ...prev, merge_mode: value }))}
              />
            </div>

            <button
              onClick={handleFullImport}
              disabled={importing || Object.entries(importOptions).filter(([k]) => k !== 'merge_mode').every(([, v]) => !v)}
              className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-green-600 hover:bg-green-700 disabled:bg-gray-400 text-white font-medium rounded-lg transition-colors"
            >
              {importing ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Upload className="w-4 h-4" />
              )}
              {t('backup.import.button')}
            </button>
          </>
        )}

        {/* Import Result */}
        {importResult && (
          <div className={`mt-4 p-4 rounded-lg border ${
            importResult.success
              ? 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800'
              : 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800'
          }`}>
            <div className="flex items-center gap-2 mb-2">
              {importResult.success ? (
                <CheckCircle className="w-5 h-5 text-green-600 dark:text-green-400" />
              ) : (
                <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400" />
              )}
              <span className={`font-medium ${importResult.success ? 'text-green-800 dark:text-green-200' : 'text-red-800 dark:text-red-200'}`}>
                {importResult.success ? t('backup.import.result.success') : t('backup.import.result.error')}
              </span>
            </div>

            {/* Imported counts */}
            {Object.keys(importResult.imported).length > 0 && (
              <div className="flex flex-wrap gap-2 mb-2">
                {Object.entries(importResult.imported).map(([key, count]) => (
                  <span key={key} className="text-xs px-2 py-1 rounded bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300">
                    {key}: {count}
                  </span>
                ))}
              </div>
            )}

            {/* Warnings */}
            {importResult.warnings.length > 0 && (
              <div className="mt-2">
                <p className="text-xs font-medium text-amber-700 dark:text-amber-300 mb-1">{t('backup.import.result.warnings')}</p>
                <ul className="text-xs text-amber-600 dark:text-amber-400 space-y-0.5">
                  {importResult.warnings.slice(0, 5).map((warning, i) => (
                    <li key={i}>• {warning}</li>
                  ))}
                  {importResult.warnings.length > 5 && (
                    <li>{t('backup.import.result.andMore', { count: importResult.warnings.length - 5 })}</li>
                  )}
                </ul>
              </div>
            )}

            {/* Errors */}
            {importResult.errors.length > 0 && (
              <div className="mt-2">
                <p className="text-xs font-medium text-red-700 dark:text-red-300 mb-1">{t('backup.import.result.errors')}</p>
                <ul className="text-xs text-red-600 dark:text-red-400 space-y-0.5">
                  {importResult.errors.slice(0, 5).map((error, i) => (
                    <li key={i}>• [{error.type}] {error.name}: {error.error}</li>
                  ))}
                  {importResult.errors.length > 5 && (
                    <li>{t('backup.import.result.andMore', { count: importResult.errors.length - 5 })}</li>
                  )}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Reset All Section */}
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-red-200 dark:border-red-800 p-4 sm:p-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 rounded-lg bg-red-100 dark:bg-red-900/30">
            <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-gray-900 dark:text-white">{t('backup.reset.title')}</h3>
            <p className="text-xs text-gray-500 dark:text-gray-400">{t('backup.reset.description')}</p>
          </div>
        </div>

        <div className="bg-red-50 dark:bg-red-900/20 rounded-lg p-4 mb-4">
          <p className="text-sm text-red-800 dark:text-red-200 mb-2 font-medium">
            {t('backup.reset.warningTitle')}
          </p>
          <p className="text-xs text-red-700 dark:text-red-300">
            {t('backup.reset.warningDescription')}
          </p>
          <ul className="text-xs text-red-700 dark:text-red-300 mt-2 space-y-1 ml-4">
            <li>• {t('backup.reset.warningItems.services')}</li>
            <li>• {t('backup.reset.warningItems.userMappings')}</li>
            <li>• {t('backup.reset.warningItems.groups')}</li>
            <li>• {t('backup.reset.warningItems.training')}</li>
            <li>• {t('backup.reset.warningItems.siteConfig')}</li>
          </ul>
          <p className="text-xs text-red-700 dark:text-red-300 mt-2 font-medium">
            {t('backup.reset.warningFooter')}
          </p>
        </div>

        {!showResetAllConfirm ? (
          <button
            onClick={() => setShowResetAllConfirm(true)}
            className="w-full px-4 py-3 bg-red-600 hover:bg-red-700 text-white font-medium rounded-lg transition-colors flex items-center justify-center gap-2"
          >
            <AlertCircle className="w-5 h-5" />
            {t('backup.reset.button')}
          </button>
        ) : (
          <div className="space-y-3">
            <div className="bg-amber-50 dark:bg-amber-900/20 rounded-lg p-3 border border-amber-200 dark:border-amber-800">
              <p className="text-sm text-amber-800 dark:text-amber-200 font-medium mb-2">
                {t('backup.reset.confirmTitle')}
              </p>
              <p className="text-xs text-amber-700 dark:text-amber-300">
                {t('backup.reset.confirmDescription')}
              </p>
            </div>

            {/* Option to show wizard after reset */}
            <label className="flex items-center gap-2 cursor-pointer p-3 rounded-lg bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800">
              <input
                type="checkbox"
                checked={showWizardAfterReset}
                onChange={(e) => setShowWizardAfterReset(e.target.checked)}
                className="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500 dark:focus:ring-blue-600 dark:ring-offset-gray-800 focus:ring-2 dark:bg-gray-700 dark:border-gray-600"
              />
              <span className="text-sm text-blue-800 dark:text-blue-200">
                {t('backup.reset.showWizard')}
              </span>
            </label>

            <div className="flex gap-2">
              <button
                onClick={() => setShowResetAllConfirm(false)}
                disabled={resetting}
                className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors disabled:opacity-50"
              >
                {tCommon('actions.cancel')}
              </button>
              <button
                onClick={handleResetAll}
                disabled={resetting}
                className="flex-1 px-4 py-2 bg-red-600 hover:bg-red-700 text-white font-medium rounded-lg transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {resetting ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    {t('backup.reset.deleting')}
                  </>
                ) : (
                  <>
                    <AlertCircle className="w-4 h-4" />
                    {t('backup.reset.confirmButton')}
                  </>
                )}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );

  const renderTabContent = () => {
    switch (activeTab) {
      case 'appearance':
        return renderAppearanceTab();
      case 'general':
        return renderGeneralTab();
      case 'logs':
        return renderLogsTab();
      case 'notifications':
        return renderNotificationsTab();
      case 'dashboard':
        return renderDashboardTab();
      case 'backup':
        return renderBackupTab();
      default:
        return null;
    }
  };

  return (
    <div className="p-4 sm:p-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <Settings className="w-6 h-6 sm:w-8 sm:h-8 text-blue-600" />
            {t('title')}
          </h1>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
            {t('description')}
          </p>
        </div>
      </div>

      {/* Tab Navigation - Same style as Users (horizontal pills) */}
      <div className="mb-4 sm:mb-6 overflow-x-auto -mx-4 px-4 sm:mx-0 sm:px-0">
        <nav className="flex gap-1.5 sm:gap-2 min-w-max sm:min-w-0 sm:flex-wrap">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;

            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-1.5 py-1.5 px-2.5 sm:py-2 sm:px-3 rounded-full font-medium text-xs sm:text-sm transition-all whitespace-nowrap ${
                  isActive
                    ? 'bg-blue-600 text-white shadow-sm'
                    : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
                }`}
              >
                <Icon className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </nav>
      </div>

      {/* Tab Content */}
      <div className="space-y-6">
        {renderTabContent()}
      </div>

      {/* Reset Confirmation Modal */}
      {showResetConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-xl p-6 max-w-md w-full mx-4">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
              {t('reset.title')}
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-6">
              {t('reset.description')}
            </p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setShowResetConfirm(false)}
                className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
              >
                {tCommon('actions.cancel')}
              </button>
              <button
                onClick={() => {
                  resetSettings();
                  setTheme('system');
                  setShowResetConfirm(false);
                }}
                className="px-4 py-2 text-sm font-medium text-white bg-red-600 hover:bg-red-700 rounded-lg transition-colors"
              >
                {t('reset.button')}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
