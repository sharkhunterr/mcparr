import { useState } from 'react';
import { Sparkles, ArrowRight, X, Upload, Database, AlertCircle, CheckCircle, Loader2, Server, Users, Shield, Brain, Wrench, Check } from 'lucide-react';
import { useWizard } from '../../contexts/WizardContext';
import { api } from '../../lib/api';

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

interface ImportOptions {
  services: boolean;
  user_mappings: boolean;
  groups: boolean;
  site_config: boolean;
  training_prompts: boolean;
  merge_mode: boolean;
}

export default function WelcomeStep() {
  const { nextStep, skipWizard } = useWizard();
  const [showImport, setShowImport] = useState(false);
  const [importing, setImporting] = useState(false);
  const [importFile, setImportFile] = useState<any>(null);
  const [importFileName, setImportFileName] = useState<string>('');
  const [importOptions, setImportOptions] = useState<ImportOptions>({
    services: true,
    user_mappings: true,
    groups: true,
    site_config: true,
    training_prompts: true,
    merge_mode: false,
  });
  const [importResult, setImportResult] = useState<{
    success: boolean;
    imported: Record<string, number>;
    errors: { type: string; name: string; error: string }[];
    warnings: string[];
  } | null>(null);

  const backupCategories = [
    { key: 'services' as const, label: 'Services', icon: Server },
    { key: 'user_mappings' as const, label: 'Users', icon: Users },
    { key: 'groups' as const, label: 'Groupes', icon: Shield },
    { key: 'site_config' as const, label: 'Config', icon: Wrench },
    { key: 'training_prompts' as const, label: 'AI', icon: Brain },
  ];

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

      // If import successful, automatically move to next step after a short delay
      if (result.success) {
        setTimeout(() => {
          nextStep();
        }, 2000);
      }
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

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center p-4">
      <div className="max-w-3xl w-full">
        {/* Skip button */}
        <div className="flex justify-end mb-4">
          <button
            onClick={skipWizard}
            className="flex items-center gap-2 px-4 py-2 text-sm text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 transition-colors"
          >
            <X className="w-4 h-4" />
            Passer le guide
          </button>
        </div>

        {/* Main card */}
        <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl border border-gray-200 dark:border-gray-700 p-8 md:p-12">
          {/* Icon */}
          <div className="flex justify-center mb-6">
            <div className="p-4 rounded-2xl bg-gradient-to-br from-blue-500 to-indigo-600 shadow-lg">
              <Sparkles className="w-12 h-12 text-white" />
            </div>
          </div>

          {/* Title */}
          <h1 className="text-3xl md:text-4xl font-bold text-center bg-gradient-to-r from-gray-900 to-gray-600 dark:from-white dark:to-gray-300 bg-clip-text text-transparent mb-4">
            Bienvenue sur MCParr
          </h1>

          {/* Subtitle */}
          <p className="text-lg text-center text-gray-600 dark:text-gray-400 mb-8">
            Votre gateway IA pour contrôler votre homelab
          </p>

          {/* Description */}
          <div className="space-y-4 mb-8 text-gray-700 dark:text-gray-300">
            <p className="text-center max-w-2xl mx-auto leading-relaxed">
              MCParr centralise le contrôle de tous vos services homelab via une interface
              conversationnelle alimentée par l'IA.
            </p>
          </div>

          {/* Features grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
            {[
              { emoji: '🔌', text: 'Connexion à vos services' },
              { emoji: '👥', text: 'Mapping utilisateurs' },
              { emoji: '🛡️', text: 'Gestion des permissions' },
              { emoji: '🤖', text: 'Serveur MCP intégré' },
            ].map((item, i) => (
              <div key={i} className="flex items-center gap-3 p-4 bg-gray-50 dark:bg-gray-900/50 rounded-xl">
                <span className="text-2xl">{item.emoji}</span>
                <span className="text-sm font-medium text-gray-700 dark:text-gray-300">{item.text}</span>
              </div>
            ))}
          </div>

          <p className="text-sm text-center text-gray-500 dark:text-gray-400 mb-8">
            Ce guide vous accompagne dans la configuration initiale.
            Vous pourrez modifier tous ces paramètres ultérieurement.
          </p>

          {/* Import Section */}
          {!showImport ? (
            <div className="mb-8">
              <div className="flex flex-col sm:flex-row gap-3 justify-center items-center">
                <button
                  onClick={() => setShowImport(true)}
                  className="flex items-center gap-2 px-6 py-3 bg-green-600 hover:bg-green-700 text-white rounded-xl font-medium transition-all shadow-lg hover:shadow-xl"
                >
                  <Upload className="w-5 h-5" />
                  Importer une configuration
                </button>
                <span className="text-sm text-gray-400">ou</span>
                <button
                  onClick={nextStep}
                  className="flex items-center gap-2 px-8 py-3.5 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white rounded-xl font-medium transition-all shadow-lg hover:shadow-xl"
                >
                  Commencer la configuration
                  <ArrowRight className="w-5 h-5" />
                </button>
              </div>
            </div>
          ) : (
            <div className="mb-8">
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
                  <div className="grid grid-cols-3 sm:grid-cols-5 gap-2 mb-3">
                    {backupCategories.map((cat) => {
                      const Icon = cat.icon;
                      const isChecked = importOptions[cat.key];
                      const hasData = importFile.data?.[cat.key]?.length > 0;

                      return (
                        <button
                          key={cat.key}
                          onClick={() => setImportOptions(prev => ({ ...prev, [cat.key]: !prev[cat.key] }))}
                          disabled={!hasData}
                          className={`flex flex-col items-center gap-1 p-2 rounded-lg border transition-all ${
                            !hasData
                              ? 'border-gray-200 dark:border-gray-700 opacity-50 cursor-not-allowed'
                              : isChecked
                              ? 'border-green-500 bg-green-50 dark:bg-green-900/20'
                              : 'border-gray-200 dark:border-gray-700 hover:border-gray-300'
                          }`}
                        >
                          <Icon className={`w-4 h-4 ${isChecked && hasData ? 'text-green-600' : 'text-gray-400'}`} />
                          <span className={`text-[10px] font-medium ${isChecked && hasData ? 'text-green-700 dark:text-green-300' : 'text-gray-600 dark:text-gray-400'}`}>
                            {cat.label}
                          </span>
                          {hasData && isChecked && <Check className="w-3 h-3 text-green-500" />}
                        </button>
                      );
                    })}
                  </div>

                  {/* Merge Mode Toggle */}
                  <div className="flex items-center justify-between p-2 bg-amber-50 dark:bg-amber-900/20 rounded-lg border border-amber-200 dark:border-amber-800 mb-3">
                    <div className="flex items-center gap-2">
                      <AlertCircle className="w-4 h-4 text-amber-600 dark:text-amber-400" />
                      <div>
                        <p className="text-xs font-medium text-amber-800 dark:text-amber-200">Mode fusion</p>
                        <p className="text-[10px] text-amber-600 dark:text-amber-400">Fusionner avec existant</p>
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
                    className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-green-600 hover:bg-green-700 disabled:bg-gray-400 text-white font-medium rounded-lg transition-colors mb-3"
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
                <div className={`mb-3 p-3 rounded-lg border ${
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
                    <span className={`text-sm font-medium ${importResult.success ? 'text-green-800 dark:text-green-200' : 'text-red-800 dark:text-red-200'}`}>
                      {importResult.success ? 'Import reussi ! Passage a l\'etape suivante...' : 'Import termine avec des erreurs'}
                    </span>
                  </div>

                  {/* Imported counts */}
                  {Object.keys(importResult.imported).length > 0 && (
                    <div className="flex flex-wrap gap-1 mb-2">
                      {Object.entries(importResult.imported).map(([key, count]) => (
                        <span key={key} className="text-[10px] px-1.5 py-0.5 rounded bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300">
                          {key}: {count}
                        </span>
                      ))}
                    </div>
                  )}

                  {/* Errors summary */}
                  {importResult.errors.length > 0 && (
                    <p className="text-xs text-red-600 dark:text-red-400 mt-1">
                      {importResult.errors.length} erreur(s)
                    </p>
                  )}
                </div>
              )}

              {/* Cancel/Continue buttons */}
              <div className="flex gap-2">
                <button
                  onClick={() => {
                    setShowImport(false);
                    setImportFile(null);
                    setImportResult(null);
                  }}
                  className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
                >
                  Annuler
                </button>
                {importResult && !importResult.success && (
                  <button
                    onClick={nextStep}
                    className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
                  >
                    Continuer quand meme
                    <ArrowRight className="w-4 h-4" />
                  </button>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
