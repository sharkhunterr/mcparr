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
import { useTheme } from '../contexts/ThemeContext';
import { useSettings, type LogLevel } from '../contexts/SettingsContext';
import { api } from '../lib/api';

type TabId = 'appearance' | 'general' | 'logs' | 'notifications' | 'dashboard' | 'backup';

const tabs = [
  { id: 'appearance' as const, label: 'Apparence', icon: Palette },
  { id: 'general' as const, label: 'General', icon: RefreshCw },
  { id: 'logs' as const, label: 'Logs', icon: FileText },
  { id: 'notifications' as const, label: 'Alertes', icon: Bell },
  { id: 'dashboard' as const, label: 'Dashboard', icon: LayoutDashboard },
  { id: 'backup' as const, label: 'Backup', icon: FolderArchive },
];

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

const logLevels: { value: LogLevel; label: string }[] = [
  { value: 'debug', label: 'Debug' },
  { value: 'info', label: 'Info' },
  { value: 'warning', label: 'Warning' },
  { value: 'error', label: 'Error' },
  { value: 'critical', label: 'Critical' },
];

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
  const [activeTab, setActiveTab] = useState<TabId>('appearance');
  const { theme, setTheme } = useTheme();
  const { settings, updateSettings, resetSettings } = useSettings();
  const [showResetConfirm, setShowResetConfirm] = useState(false);

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

  const handleExportSettings = () => {
    const exportData = {
      theme,
      settings,
      exportedAt: new Date().toISOString(),
      version: '1.0',
    };
    const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `mcparr-settings-${new Date().toISOString().split('T')[0]}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleImportSettings = () => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.json';
    input.onchange = (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (file) {
        const reader = new FileReader();
        reader.onload = (event) => {
          try {
            const data = JSON.parse(event.target?.result as string);
            if (data.theme) setTheme(data.theme);
            if (data.settings) updateSettings(data.settings);
          } catch {
            console.error('Invalid settings file');
          }
        };
        reader.readAsText(file);
      }
    };
    input.click();
  };

  const renderAppearanceTab = () => (
    <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 p-4 sm:p-6">
      <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-4">Theme</h3>
      <div className="grid grid-cols-3 gap-3">
        {[
          { value: 'light', label: 'Clair', icon: Sun },
          { value: 'dark', label: 'Sombre', icon: Moon },
          { value: 'system', label: 'Systeme', icon: Monitor },
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

  const renderGeneralTab = () => (
    <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 p-4 sm:p-6 space-y-4">
      <div className="flex items-center justify-between py-2">
        <div>
          <p className="text-sm font-medium text-gray-900 dark:text-white">Actualisation automatique</p>
          <p className="text-xs text-gray-500 dark:text-gray-400">Rafraichir les donnees automatiquement</p>
        </div>
        <Toggle
          enabled={settings.autoRefresh}
          onChange={(value) => updateSettings({ autoRefresh: value })}
        />
      </div>

      {settings.autoRefresh && (
        <div className="flex items-center justify-between py-2">
          <div>
            <p className="text-sm font-medium text-gray-900 dark:text-white">Intervalle</p>
            <p className="text-xs text-gray-500 dark:text-gray-400">Frequence de rafraichissement</p>
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
  );

  const renderLogsTab = () => (
    <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 p-4 sm:p-6 space-y-4">
      <div className="flex items-center justify-between py-2">
        <div>
          <p className="text-sm font-medium text-gray-900 dark:text-white">Niveau de log</p>
          <p className="text-xs text-gray-500 dark:text-gray-400">Filtrer par severite</p>
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
          <p className="text-sm font-medium text-gray-900 dark:text-white">Logs console</p>
          <p className="text-xs text-gray-500 dark:text-gray-400">Afficher dans la console navigateur</p>
        </div>
        <Toggle
          enabled={settings.logToConsole}
          onChange={(value) => updateSettings({ logToConsole: value })}
        />
      </div>

      <div className="flex items-center justify-between py-2">
        <div>
          <p className="text-sm font-medium text-gray-900 dark:text-white">Logs backend</p>
          <p className="text-xs text-gray-500 dark:text-gray-400">Envoyer les logs au serveur</p>
        </div>
        <Toggle
          enabled={settings.logToBackend}
          onChange={(value) => updateSettings({ logToBackend: value })}
        />
      </div>

      {/* Log Levels Preview */}
      <div className="pt-4 border-t border-gray-100 dark:border-gray-700">
        <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">
          Niveaux enregistres avec "{settings.logLevel}":
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
          <p className="text-sm font-medium text-gray-900 dark:text-white">Notifications</p>
          <p className="text-xs text-gray-500 dark:text-gray-400">Activer les notifications</p>
        </div>
        <Toggle
          enabled={settings.notificationsEnabled}
          onChange={(value) => updateSettings({ notificationsEnabled: value })}
        />
      </div>

      <div className="flex items-center justify-between py-2">
        <div>
          <p className="text-sm font-medium text-gray-900 dark:text-white">Sons</p>
          <p className="text-xs text-gray-500 dark:text-gray-400">Jouer un son lors des alertes</p>
        </div>
        <Toggle
          enabled={settings.soundEnabled}
          onChange={(value) => updateSettings({ soundEnabled: value })}
          disabled={!settings.notificationsEnabled}
        />
      </div>

      <div className="flex items-center justify-between py-2">
        <div>
          <p className="text-sm font-medium text-gray-900 dark:text-white">Alertes sur erreur</p>
          <p className="text-xs text-gray-500 dark:text-gray-400">Notifier lors d'erreurs critiques</p>
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
          <p className="text-sm font-medium text-gray-900 dark:text-white">Mode compact</p>
          <p className="text-xs text-gray-500 dark:text-gray-400">Reduire l'espacement</p>
        </div>
        <Toggle
          enabled={settings.dashboardCompactMode}
          onChange={(value) => updateSettings({ dashboardCompactMode: value })}
        />
      </div>

      <div className="flex items-center justify-between py-2">
        <div>
          <p className="text-sm font-medium text-gray-900 dark:text-white">Metriques systeme</p>
          <p className="text-xs text-gray-500 dark:text-gray-400">Afficher CPU, RAM, disque</p>
        </div>
        <Toggle
          enabled={settings.showSystemMetrics}
          onChange={(value) => updateSettings({ showSystemMetrics: value })}
        />
      </div>

      <div className="flex items-center justify-between py-2">
        <div>
          <p className="text-sm font-medium text-gray-900 dark:text-white">Statistiques MCP</p>
          <p className="text-xs text-gray-500 dark:text-gray-400">Afficher les stats du gateway</p>
        </div>
        <Toggle
          enabled={settings.showMcpStats}
          onChange={(value) => updateSettings({ showMcpStats: value })}
        />
      </div>
    </div>
  );

  const backupCategories = [
    { key: 'services' as const, label: 'Services', icon: Server, description: 'Configurations des services (Plex, Authentik, etc.)' },
    { key: 'user_mappings' as const, label: 'User Mappings', icon: Users, description: 'Mappings utilisateurs entre services' },
    { key: 'groups' as const, label: 'Groupes', icon: Shield, description: 'Groupes, membres et permissions MCP' },
    { key: 'site_config' as const, label: 'Configuration', icon: Wrench, description: 'Parametres du site' },
    { key: 'training_prompts' as const, label: 'AI Training', icon: Brain, description: 'Prompts et donnees d\'entrainement' },
  ];

  const renderBackupTab = () => (
    <div className="space-y-6">
      {/* Export Section */}
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 p-4 sm:p-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 rounded-lg bg-blue-100 dark:bg-blue-900/30">
            <Download className="w-5 h-5 text-blue-600 dark:text-blue-400" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-gray-900 dark:text-white">Exporter la configuration</h3>
            <p className="text-xs text-gray-500 dark:text-gray-400">Selectionnez les elements a sauvegarder</p>
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
            {Object.values(exportOptions).filter(Boolean).length} categories selectionnees
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
            Exporter
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
            <h3 className="text-sm font-semibold text-gray-900 dark:text-white">Importer une configuration</h3>
            <p className="text-xs text-gray-500 dark:text-gray-400">Restaurer depuis un fichier de backup</p>
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
                  Version {importFile.version} - {importFile.exported_at ? new Date(importFile.exported_at).toLocaleDateString() : 'Date inconnue'}
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
                <p className="text-sm text-gray-600 dark:text-gray-400">Cliquer pour selectionner un fichier</p>
                <p className="text-xs text-gray-500 dark:text-gray-400">.json uniquement</p>
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
                  <p className="text-sm font-medium text-amber-800 dark:text-amber-200">Mode fusion</p>
                  <p className="text-xs text-amber-600 dark:text-amber-400">Fusionner avec les donnees existantes au lieu de remplacer</p>
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
              Importer la configuration
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
                {importResult.success ? 'Import reussi' : 'Import termine avec des erreurs'}
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
                <p className="text-xs font-medium text-amber-700 dark:text-amber-300 mb-1">Avertissements:</p>
                <ul className="text-xs text-amber-600 dark:text-amber-400 space-y-0.5">
                  {importResult.warnings.slice(0, 5).map((warning, i) => (
                    <li key={i}>• {warning}</li>
                  ))}
                  {importResult.warnings.length > 5 && (
                    <li>... et {importResult.warnings.length - 5} autres</li>
                  )}
                </ul>
              </div>
            )}

            {/* Errors */}
            {importResult.errors.length > 0 && (
              <div className="mt-2">
                <p className="text-xs font-medium text-red-700 dark:text-red-300 mb-1">Erreurs:</p>
                <ul className="text-xs text-red-600 dark:text-red-400 space-y-0.5">
                  {importResult.errors.slice(0, 5).map((error, i) => (
                    <li key={i}>• [{error.type}] {error.name}: {error.error}</li>
                  ))}
                  {importResult.errors.length > 5 && (
                    <li>... et {importResult.errors.length - 5} autres</li>
                  )}
                </ul>
              </div>
            )}
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
            Configuration
          </h1>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
            Parametres de l'application
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleImportSettings}
            className="p-2 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
            title="Importer"
          >
            <Upload className="w-4 h-4" />
          </button>
          <button
            onClick={handleExportSettings}
            className="p-2 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
            title="Exporter"
          >
            <Download className="w-4 h-4" />
          </button>
          <button
            onClick={() => setShowResetConfirm(true)}
            className="p-2 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"
            title="Reinitialiser"
          >
            <RotateCcw className="w-4 h-4" />
          </button>
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
              Reinitialiser les parametres ?
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-6">
              Cette action va restaurer tous les parametres a leurs valeurs par defaut.
            </p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setShowResetConfirm(false)}
                className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
              >
                Annuler
              </button>
              <button
                onClick={() => {
                  resetSettings();
                  setTheme('system');
                  setShowResetConfirm(false);
                }}
                className="px-4 py-2 text-sm font-medium text-white bg-red-600 hover:bg-red-700 rounded-lg transition-colors"
              >
                Reinitialiser
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
