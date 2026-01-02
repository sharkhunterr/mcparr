import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Brain,
  RefreshCw,
  BarChart3,
  History,
  FileText,
  Settings,
  Server,
  Play,
  Square,
  Trash2,
  Plus,
  CheckCircle,
  HardDrive,
  Cpu,
  Download,
  Upload,
  Search,
  ChevronDown,
  ChevronUp,
  X,
  Zap,
  Activity,
  Edit,
  Check,
  Monitor,
  Copy,
  Eye,
} from 'lucide-react';
import { WorkerList } from '../components/Workers';
import { api } from '../lib/api';
import { useTrainingWebSocket, type TrainingMetrics } from '../hooks/useTrainingWebSocket';
import SessionDetailsModal from '../components/Training/SessionDetailsModal';
import SessionLogsModal from '../components/Training/SessionLogsModal';
import TrainingOverview from '../components/Training/TrainingOverview';

// Types
interface OllamaModel {
  name: string;
  model: string;
  size: number;
  size_gb: number;
  family: string;
  parameter_size: string;
  quantization_level: string;
  modified_at?: string;
}

interface OllamaStatus {
  status: string;
  version?: string;
  url: string;
  error?: string;
  models: OllamaModel[];
  model_count: number;
  total_size_gb: number;
  running_models: any[];
  running_count: number;
}

interface TrainingSession {
  id: string;
  name: string;
  description?: string;
  base_model: string;
  output_model?: string;
  training_type: string;
  training_backend: string;
  worker_id?: string;
  status: string;
  error_message?: string;
  current_epoch: number;
  total_epochs: number;
  current_step: number;
  total_steps: number;
  progress_percent: number;
  loss?: number;
  learning_rate?: number;
  started_at?: string;
  completed_at?: string;
  estimated_completion?: string;
  gpu_memory_used?: number;
  cpu_usage?: number;
  dataset_size: number;
  created_at: string;
  updated_at: string;
}

interface TrainingPrompt {
  id: string;
  name: string;
  description?: string;
  category: string;
  difficulty: string;
  source: string;
  format: string;
  system_prompt?: string;
  user_input: string;
  expected_output: string;
  // Tool calling support
  tool_call?: {
    name: string;
    arguments: Record<string, unknown>;
  };
  tool_response?: Record<string, unknown>;
  assistant_response?: string;
  tags: string[];
  is_validated: boolean;
  validation_score?: number;
  times_used: number;
  enabled: boolean;
  session_id?: string;
  created_at: string;
  updated_at: string;
}

interface TrainingWorker {
  id: string;
  name: string;
  description?: string;
  url: string;
  status: string;
  enabled: boolean;
  gpu_available: boolean;
  gpu_count: number;
  gpu_names: string[];
  current_job_id?: string;
}

interface TrainingStats {
  total_sessions: number;
  active_sessions: number;
  completed_sessions: number;
  failed_sessions: number;
  total_prompts: number;
  validated_prompts: number;
  prompts_by_category: Record<string, number>;
  recent_sessions: TrainingSession[];
}

interface OllamaMetrics {
  // Ollama metrics
  ollama_status: string;
  ollama_version?: string;
  ollama_url: string;
  models_count: number;
  models_total_size_gb: number;
  running_models_count: number;
  running_models: any[];
  models: {
    name: string;
    size_gb: number;
    family: string;
    parameter_size: string;
    quantization_level: string;
  }[];

  // System metrics
  system_cpu_percent?: number;
  system_memory_used_gb?: number;
  system_memory_total_gb?: number;
  system_memory_percent?: number;
  system_gpu_used_gb?: number;
  system_gpu_total_gb?: number;
  system_gpu_percent?: number;
  system_gpu_name?: string;

  // Training metrics
  training_total_sessions: number;
  training_active_sessions: number;
  training_completed_sessions: number;
  training_total_prompts: number;
  training_prompts_by_category: Record<string, number>;

  error?: string;
}

// Components
const StatusBadge = ({ status }: { status: string }) => {
  const colors: Record<string, string> = {
    pending: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
    preparing: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
    running: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
    completed: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900 dark:text-emerald-200',
    failed: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
    cancelled: 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300',
    paused: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200',
    healthy: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
    unhealthy: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
    not_configured: 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300',
  };

  return (
    <span className={`px-2 py-1 text-xs font-medium rounded-full ${colors[status] || colors.pending}`}>
      {status.replace('_', ' ')}
    </span>
  );
};

// Liste des services disponibles (utilisé dans les formulaires et filtres)
const AVAILABLE_SERVICES = [
  { id: 'plex', label: 'Plex', icon: '🎬', color: 'bg-amber-500' },
  { id: 'tautulli', label: 'Tautulli', icon: '📊', color: 'bg-orange-500' },
  { id: 'overseerr', label: 'Overseerr', icon: '🎯', color: 'bg-violet-500' },
  { id: 'radarr', label: 'Radarr', icon: '🎥', color: 'bg-yellow-500' },
  { id: 'sonarr', label: 'Sonarr', icon: '📺', color: 'bg-sky-500' },
  { id: 'prowlarr', label: 'Prowlarr', icon: '🔍', color: 'bg-pink-500' },
  { id: 'jackett', label: 'Jackett', icon: '🧥', color: 'bg-rose-600' },
  { id: 'deluge', label: 'Deluge', icon: '🌊', color: 'bg-blue-600' },
  { id: 'zammad', label: 'Zammad', icon: '🎫', color: 'bg-teal-500' },
  { id: 'authentik', label: 'Authentik', icon: '🔐', color: 'bg-orange-600' },
  { id: 'komga', label: 'Komga', icon: '📚', color: 'bg-indigo-500' },
  { id: 'romm', label: 'Romm', icon: '🎮', color: 'bg-green-500' },
  { id: 'ollama', label: 'Ollama', icon: '🤖', color: 'bg-purple-500' },
  { id: 'openwebui', label: 'OpenWebUI', icon: '💬', color: 'bg-cyan-500' },
  { id: 'audiobookshelf', label: 'Audiobookshelf', icon: '🎧', color: 'bg-purple-500' },
  { id: 'wikijs', label: 'Wiki.js', icon: '📝', color: 'bg-blue-500' },
  { id: 'system', label: 'Système', icon: '⚙️', color: 'bg-slate-600' },
];

const DifficultyBadge = ({ difficulty }: { difficulty: string }) => {
  const colors: Record<string, string> = {
    basic: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
    intermediate: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
    advanced: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200',
    expert: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
  };

  return (
    <span className={`px-2 py-1 text-xs font-medium rounded-full ${colors[difficulty] || colors.basic}`}>
      {difficulty}
    </span>
  );
};

const ServiceBadge = ({ tags }: { tags: string[] }) => {
  const serviceConfig: Record<string, { color: string; icon: string; label: string }> = {
    plex: { color: 'bg-amber-500 text-white', icon: '🎬', label: 'Plex' },
    tautulli: { color: 'bg-orange-500 text-white', icon: '📊', label: 'Tautulli' },
    overseerr: { color: 'bg-violet-500 text-white', icon: '🎯', label: 'Overseerr' },
    radarr: { color: 'bg-yellow-500 text-black', icon: '🎥', label: 'Radarr' },
    sonarr: { color: 'bg-sky-500 text-white', icon: '📺', label: 'Sonarr' },
    prowlarr: { color: 'bg-pink-500 text-white', icon: '🔍', label: 'Prowlarr' },
    jackett: { color: 'bg-rose-600 text-white', icon: '🧥', label: 'Jackett' },
    system: { color: 'bg-slate-600 text-white', icon: '⚙️', label: 'Système' },
    zammad: { color: 'bg-teal-500 text-white', icon: '🎫', label: 'Zammad' },
    komga: { color: 'bg-indigo-500 text-white', icon: '📚', label: 'Komga' },
    romm: { color: 'bg-green-500 text-white', icon: '🎮', label: 'RomM' },
    authentik: { color: 'bg-orange-600 text-white', icon: '🔐', label: 'Authentik' },
    ollama: { color: 'bg-purple-500 text-white', icon: '🤖', label: 'Ollama' },
    openwebui: { color: 'bg-cyan-500 text-white', icon: '💬', label: 'OpenWebUI' },
    audiobookshelf: { color: 'bg-purple-500 text-white', icon: '🎧', label: 'Audiobookshelf' },
    wikijs: { color: 'bg-blue-500 text-white', icon: '📝', label: 'Wiki.js' },
  };

  // Afficher un badge pour chaque service trouvé dans les tags
  const serviceTags = tags.filter(tag => serviceConfig[tag.toLowerCase()]);

  if (serviceTags.length === 0) return null;

  return (
    <>
      {serviceTags.map(tag => {
        const config = serviceConfig[tag.toLowerCase()];
        return (
          <span key={tag} className={`px-2 py-1 text-xs font-medium rounded-full flex items-center gap-1 ${config.color}`}>
            <span>{config.icon}</span>
            <span>{config.label}</span>
          </span>
        );
      })}
    </>
  );
};

const ProgressBar = ({ value, max, label }: { value: number; max: number; label?: string }) => {
  const percent = max > 0 ? (value / max) * 100 : 0;
  return (
    <div>
      {label && (
        <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400 mb-1">
          <span>{label}</span>
          <span>{percent.toFixed(1)}%</span>
        </div>
      )}
      <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
        <div
          className="bg-blue-500 h-2 rounded-full transition-all duration-300"
          style={{ width: `${Math.min(percent, 100)}%` }}
        />
      </div>
    </div>
  );
};

// Phase display helper (used by TrainingOverview)
export const getPhaseDisplay = (phase: string | undefined) => {
  const phases: Record<string, { label: string; icon: React.ReactNode; color: string }> = {
    preparing: { label: 'Préparation', icon: <Settings className="w-3 h-3 animate-spin" />, color: 'bg-blue-500' },
    downloading: { label: 'Téléchargement modèle', icon: <Download className="w-3 h-3 animate-bounce" />, color: 'bg-cyan-500' },
    training: { label: 'Entraînement', icon: <Brain className="w-3 h-3 animate-pulse" />, color: 'bg-purple-500' },
    exporting: { label: 'Export GGUF', icon: <HardDrive className="w-3 h-3 animate-pulse" />, color: 'bg-orange-500' },
    importing: { label: 'Import Ollama', icon: <Upload className="w-3 h-3 animate-bounce" />, color: 'bg-green-500' },
    completed: { label: 'Terminé', icon: <CheckCircle className="w-3 h-3" />, color: 'bg-emerald-500' },
  };
  return phases[phase || ''] || { label: phase || 'En cours', icon: <Activity className="w-3 h-3 animate-pulse" />, color: 'bg-gray-500' };
};

// Sessions Tab
const SessionsTab = ({
  sessions,
  loading,
  onCreate,
  onStart,
  onCancel,
  onDelete,
  onDuplicate,
  onManagePrompts,
  onViewDetails,
  onViewLogs,
}: {
  sessions: TrainingSession[];
  loading: boolean;
  onCreate: () => void;
  onStart: (id: string) => void;
  onCancel: (id: string) => void;
  onDelete: (id: string) => void;
  onDuplicate: (id: string) => void;
  onManagePrompts: (session: TrainingSession) => void;
  onViewDetails: (id: string) => void;
  onViewLogs: (id: string, name?: string, status?: string) => void;
}) => {
  const [expandedSession, setExpandedSession] = useState<string | null>(null);
  const { t } = useTranslation('training');

  const formatDate = (date: string | undefined): string => {
    if (!date) return '-';
    return new Date(date).toLocaleString();
  };

  return (
    <div className="space-y-4">
      {/* Actions */}
      <div className="flex items-center justify-between bg-white dark:bg-gray-800 p-4 rounded-lg shadow">
        <span className="text-sm text-gray-500">
          {sessions.length} session{sessions.length !== 1 ? 's' : ''}
        </span>
        <button
          onClick={onCreate}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center gap-2"
        >
          <Plus className="w-4 h-4" />
          Nouvelle session
        </button>
      </div>

      {/* Sessions List */}
      {loading ? (
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
        </div>
      ) : sessions.length > 0 ? (
        <div className="space-y-3">
          {sessions.map((session) => (
            <div
              key={session.id}
              className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden"
            >
              <div
                className="p-4 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
                onClick={() => setExpandedSession(expandedSession === session.id ? null : session.id)}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3 flex-1 min-w-0">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <h4 className="font-medium text-gray-900 dark:text-white truncate">
                          {session.name}
                        </h4>
                        <StatusBadge status={session.status} />
                      </div>
                      <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                        {session.base_model} - {session.training_type}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {session.status === 'running' && (
                      <div className="text-right mr-4">
                        <p className="text-sm font-medium text-blue-600 dark:text-blue-400">
                          {session.progress_percent.toFixed(1)}%
                        </p>
                        <p className="text-xs text-gray-400">
                          Epoch {session.current_epoch}/{session.total_epochs}
                        </p>
                      </div>
                    )}
                    {expandedSession === session.id ? (
                      <ChevronUp className="w-5 h-5 text-gray-400" />
                    ) : (
                      <ChevronDown className="w-5 h-5 text-gray-400" />
                    )}
                  </div>
                </div>

                {/* Progress bar for running sessions */}
                {session.status === 'running' && (
                  <div className="mt-3">
                    <ProgressBar
                      value={session.current_epoch}
                      max={session.total_epochs}
                    />
                  </div>
                )}
              </div>

              {/* Expanded details */}
              {expandedSession === session.id && (
                <div className="px-4 pb-4 border-t border-gray-200 dark:border-gray-700">
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4">
                    <div>
                      <p className="text-xs text-gray-500 dark:text-gray-400">Créé le</p>
                      <p className="text-sm text-gray-900 dark:text-white">{formatDate(session.created_at)}</p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-500 dark:text-gray-400">Démarré le</p>
                      <p className="text-sm text-gray-900 dark:text-white">{formatDate(session.started_at)}</p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-500 dark:text-gray-400">Epochs</p>
                      <p className="text-sm text-gray-900 dark:text-white">
                        {session.current_epoch} / {session.total_epochs}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-500 dark:text-gray-400">Dataset</p>
                      <p className="text-sm text-gray-900 dark:text-white">{session.dataset_size} prompts</p>
                    </div>
                  </div>

                  {session.loss !== null && session.loss !== undefined && (
                    <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-4">
                      <div className="flex items-center gap-2">
                        <Cpu className="w-4 h-4 text-gray-400" />
                        <div>
                          <p className="text-xs text-gray-500">Loss</p>
                          <p className="text-sm font-medium">{session.loss.toFixed(4)}</p>
                        </div>
                      </div>
                      {session.gpu_memory_used && (
                        <div className="flex items-center gap-2">
                          <HardDrive className="w-4 h-4 text-gray-400" />
                          <div>
                            <p className="text-xs text-gray-500">GPU Memory</p>
                            <p className="text-sm font-medium">{session.gpu_memory_used.toFixed(1)} GB</p>
                          </div>
                        </div>
                      )}
                    </div>
                  )}

                  {session.error_message && (
                    <div className="mt-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
                      <p className="text-sm text-red-800 dark:text-red-200">{session.error_message}</p>
                    </div>
                  )}

                  {session.description && (
                    <p className="mt-4 text-sm text-gray-600 dark:text-gray-300">{session.description}</p>
                  )}

                  {/* Actions */}
                  <div className="mt-4 flex gap-2 flex-wrap">
                    {session.status === 'pending' && (
                      <>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            onManagePrompts(session);
                          }}
                          className="px-3 py-1.5 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 flex items-center gap-1"
                        >
                          <Edit className="w-3.5 h-3.5" />
                          Gérer les prompts ({session.dataset_size})
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            onStart(session.id);
                          }}
                          disabled={session.dataset_size === 0}
                          className="px-3 py-1.5 bg-green-600 text-white text-sm rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1"
                          title={session.dataset_size === 0 ? 'Ajoutez des prompts avant de démarrer' : ''}
                        >
                          <Play className="w-3.5 h-3.5" />
                          Démarrer
                        </button>
                      </>
                    )}
                    {['running', 'preparing'].includes(session.status) && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onCancel(session.id);
                        }}
                        className="px-3 py-1.5 bg-orange-600 text-white text-sm rounded-lg hover:bg-orange-700 flex items-center gap-1"
                      >
                        <Square className="w-3.5 h-3.5" />
                        {t('sessions.cancel')}
                      </button>
                    )}
                    {!['running', 'preparing'].includes(session.status) && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onDelete(session.id);
                        }}
                        className="px-3 py-1.5 bg-red-600 text-white text-sm rounded-lg hover:bg-red-700 flex items-center gap-1"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                        {t('sessions.delete')}
                      </button>
                    )}
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onDuplicate(session.id);
                      }}
                      className="px-3 py-1.5 bg-gray-600 text-white text-sm rounded-lg hover:bg-gray-700 flex items-center gap-1"
                    >
                      <Copy className="w-3.5 h-3.5" />
                      Dupliquer
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onViewDetails(session.id);
                      }}
                      className="px-3 py-1.5 bg-purple-600 text-white text-sm rounded-lg hover:bg-purple-700 flex items-center gap-1"
                    >
                      <Eye className="w-3.5 h-3.5" />
                      Details
                    </button>
                    {['completed', 'failed', 'cancelled'].includes(session.status) && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onViewLogs(session.id, session.name, session.status);
                        }}
                        className="px-3 py-1.5 bg-gray-500 text-white text-sm rounded-lg hover:bg-gray-600 flex items-center gap-1"
                      >
                        <FileText className="w-3.5 h-3.5" />
                        Logs
                      </button>
                    )}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      ) : (
        <div className="text-center py-12 bg-white dark:bg-gray-800 rounded-lg shadow">
          <Brain className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <p className="text-gray-500 dark:text-gray-400">{t('sessions.noSessions')}</p>
          <p className="text-sm text-gray-400 dark:text-gray-500 mt-1">
            Créez une nouvelle session pour commencer
          </p>
        </div>
      )}
    </div>
  );
};

// Fonction utilitaire pour détecter les services d'un prompt à partir de ses tags
const detectServices = (prompt: TrainingPrompt): string[] => {
  const knownServices = ['plex', 'tautulli', 'overseerr', 'radarr', 'sonarr', 'prowlarr', 'jackett', 'system', 'zammad'];
  return prompt.tags.filter(tag => knownServices.includes(tag.toLowerCase())).map(t => t.toLowerCase());
};

// Models Tab - Liste et gestion des modèles Ollama
const ModelsTab = ({
  models,
  loading,
  onRefresh,
  runningModels = [],
}: {
  models: OllamaModel[];
  loading: boolean;
  onRefresh: () => void;
  runningModels?: { name: string }[];
}) => {
  const [deleting, setDeleting] = useState<string | null>(null);
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [loadingModel, setLoadingModel] = useState<string | null>(null);
  const { t } = useTranslation('training');

  const isModelRunning = (modelName: string) => {
    return runningModels.some(m => m.name === modelName || m.name.startsWith(modelName + ':'));
  };

  const handleToggleLoad = async (modelName: string) => {
    setLoadingModel(modelName);
    try {
      if (isModelRunning(modelName)) {
        await api.training.ollama.unloadModel(modelName);
      } else {
        await api.training.ollama.loadModel(modelName);
      }
      onRefresh();
    } catch (error) {
      console.error('Failed to toggle model load:', error);
    } finally {
      setLoadingModel(null);
    }
  };

  const handleDelete = async (modelName: string) => {
    setDeleting(modelName);
    try {
      await api.training.ollama.deleteModel(modelName);
      onRefresh();
    } catch (error) {
      console.error('Failed to delete model:', error);
    } finally {
      setDeleting(null);
      setConfirmDelete(null);
    }
  };

  const filteredModels = models.filter(model =>
    model.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    model.family?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    return date.toLocaleDateString('fr-FR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const totalSize = models.reduce((acc, m) => acc + (m.size_gb || 0), 0);

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row gap-3 sm:items-center sm:justify-between">
        <div className="flex items-center gap-3">
          <div className="relative flex-1 sm:w-64">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              placeholder={t('models.searchPlaceholder')}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-4 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-purple-500"
            />
          </div>
        </div>
        <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
          <Brain className="w-4 h-4" />
          <span>{models.length} modèles</span>
          <span className="text-gray-300 dark:text-gray-600">•</span>
          <HardDrive className="w-4 h-4" />
          <span>{totalSize.toFixed(1)} GB</span>
        </div>
      </div>

      {/* Models List */}
      {loading ? (
        <div className="text-center py-12 text-gray-500">{t('models.loading')}</div>
      ) : filteredModels.length === 0 ? (
        <div className="bg-white dark:bg-gray-800 rounded-lg p-8 text-center">
          <Brain className="w-12 h-12 mx-auto text-gray-300 dark:text-gray-600 mb-3" />
          <p className="text-gray-500 dark:text-gray-400">
            {searchQuery ? t('models.noModelsFound') : t('models.noModels')}
          </p>
        </div>
      ) : (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-50 dark:bg-gray-900/50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Modèle
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider hidden sm:table-cell">
                  Famille
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider hidden md:table-cell">
                  Paramètres
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Taille
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider hidden lg:table-cell">
                  Modifié
                </th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
              {filteredModels.map((model) => (
                <tr key={model.name} className="hover:bg-gray-50 dark:hover:bg-gray-700/50">
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <div className="relative">
                        <Brain className="w-5 h-5 text-purple-500 flex-shrink-0" />
                        {isModelRunning(model.name) && (
                          <span className="absolute -top-0.5 -right-0.5 w-2 h-2 bg-green-500 rounded-full" title="Chargé en mémoire" />
                        )}
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <p className="font-medium text-gray-900 dark:text-white text-sm">
                            {model.name}
                          </p>
                          {isModelRunning(model.name) && (
                            <span className="px-1.5 py-0.5 text-xs bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400 rounded">
                              Chargé
                            </span>
                          )}
                        </div>
                        {model.quantization_level && (
                          <span className="text-xs text-gray-500 dark:text-gray-400">
                            {model.quantization_level}
                          </span>
                        )}
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-300 hidden sm:table-cell">
                    {model.family || '-'}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-300 hidden md:table-cell">
                    {model.parameter_size || '-'}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-300">
                    {model.size_gb?.toFixed(1) || '-'} GB
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-500 dark:text-gray-400 hidden lg:table-cell">
                    {formatDate(model.modified_at)}
                  </td>
                  <td className="px-4 py-3 text-right">
                    {confirmDelete === model.name ? (
                      <div className="flex items-center justify-end gap-2">
                        <span className="text-xs text-red-600 dark:text-red-400">{t('models.confirmQuestion')}</span>
                        <button
                          onClick={() => handleDelete(model.name)}
                          disabled={deleting === model.name}
                          className="p-1.5 text-white bg-red-500 rounded hover:bg-red-600 disabled:opacity-50"
                        >
                          {deleting === model.name ? (
                            <RefreshCw className="w-4 h-4 animate-spin" />
                          ) : (
                            <Check className="w-4 h-4" />
                          )}
                        </button>
                        <button
                          onClick={() => setConfirmDelete(null)}
                          className="p-1.5 text-gray-600 dark:text-gray-400 bg-gray-200 dark:bg-gray-700 rounded hover:bg-gray-300 dark:hover:bg-gray-600"
                        >
                          <X className="w-4 h-4" />
                        </button>
                      </div>
                    ) : (
                      <div className="flex items-center justify-end gap-1">
                        {/* Load/Unload button */}
                        <button
                          onClick={() => handleToggleLoad(model.name)}
                          disabled={loadingModel === model.name}
                          className={`p-1.5 rounded transition-colors ${
                            isModelRunning(model.name)
                              ? 'text-green-500 hover:text-orange-500 hover:bg-orange-50 dark:hover:bg-orange-900/20'
                              : 'text-gray-400 hover:text-green-500 hover:bg-green-50 dark:hover:bg-green-900/20'
                          }`}
                          title={isModelRunning(model.name) ? t('models.unload') : t('models.load')}
                        >
                          {loadingModel === model.name ? (
                            <RefreshCw className="w-4 h-4 animate-spin" />
                          ) : isModelRunning(model.name) ? (
                            <Zap className="w-4 h-4" />
                          ) : (
                            <Play className="w-4 h-4" />
                          )}
                        </button>
                        {/* Delete button */}
                        <button
                          onClick={() => setConfirmDelete(model.name)}
                          className="p-1.5 text-gray-400 hover:text-red-500 dark:hover:text-red-400 transition-colors"
                          title={t('models.delete')}
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

// Prompts Tab
const PromptsTab = ({
  prompts,
  loading,
  searchQuery,
  setSearchQuery,
  serviceFilter,
  setServiceFilter,
  onCreate,
  onImport,
  onExport,
  onSeed,
  onValidate,
  onDelete,
  onEdit,
}: {
  prompts: TrainingPrompt[];
  loading: boolean;
  searchQuery: string;
  setSearchQuery: (query: string) => void;
  serviceFilter: string;
  setServiceFilter: (service: string) => void;
  onCreate: () => void;
  onImport: () => void;
  onExport: () => void;
  onSeed: (reset: boolean) => void;
  onValidate: (id: string) => void;
  onDelete: (id: string) => void;
  onEdit: (prompt: TrainingPrompt) => void;
}) => {
  const [expandedPrompt, setExpandedPrompt] = useState<string | null>(null);
  const { t } = useTranslation('training');

  // Filtrer les prompts par service côté client
  const filteredPrompts = serviceFilter
    ? prompts.filter(p => detectServices(p).includes(serviceFilter))
    : prompts;

  // Compter les prompts par service
  const serviceCounts = prompts.reduce((acc, p) => {
    const services = detectServices(p);
    services.forEach(service => {
      acc[service] = (acc[service] || 0) + 1;
    });
    return acc;
  }, {} as Record<string, number>);

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="bg-white dark:bg-gray-800 p-4 rounded-lg shadow flex flex-wrap gap-4 items-center">
        <div className="flex-1 min-w-[200px] relative">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder={t('prompts.search')}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
          />
        </div>
        <select
          value={serviceFilter}
          onChange={(e) => setServiceFilter(e.target.value)}
          className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
        >
          <option value="">Tous les services ({prompts.length})</option>
          <option value="plex">🎬 Plex ({serviceCounts['plex'] || 0})</option>
          <option value="tautulli">📊 Tautulli ({serviceCounts['tautulli'] || 0})</option>
          <option value="overseerr">🎯 Overseerr ({serviceCounts['overseerr'] || 0})</option>
          <option value="radarr">🎥 Radarr ({serviceCounts['radarr'] || 0})</option>
          <option value="sonarr">📺 Sonarr ({serviceCounts['sonarr'] || 0})</option>
          <option value="prowlarr">🔍 Prowlarr ({serviceCounts['prowlarr'] || 0})</option>
          <option value="jackett">🧥 Jackett ({serviceCounts['jackett'] || 0})</option>
          <option value="system">⚙️ Système ({serviceCounts['system'] || 0})</option>
          <option value="zammad">🎫 Zammad ({serviceCounts['zammad'] || 0})</option>
        </select>
        <div className="flex items-center gap-2">
          <button
            onClick={() => onSeed(true)}
            className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 flex items-center gap-2"
            title={t('prompts.deleteAll')}
          >
            <Zap className="w-4 h-4" />
            Reset Prompts
          </button>
          <button
            onClick={onImport}
            className="px-4 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 flex items-center gap-2"
          >
            <Upload className="w-4 h-4" />
            Importer
          </button>
          <button
            onClick={onExport}
            className="px-4 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 flex items-center gap-2"
          >
            <Download className="w-4 h-4" />
            Exporter
          </button>
          <button
            onClick={onCreate}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center gap-2"
          >
            <Plus className="w-4 h-4" />
            Nouveau
          </button>
        </div>
      </div>

      {/* Prompts List */}
      {loading ? (
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
        </div>
      ) : filteredPrompts.length > 0 ? (
        <div className="space-y-3">
          {filteredPrompts.map((prompt) => (
            <div
              key={prompt.id}
              className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden"
            >
              <div
                className="p-4 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
                onClick={() => setExpandedPrompt(expandedPrompt === prompt.id ? null : prompt.id)}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3 flex-1 min-w-0">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <h4 className="font-medium text-gray-900 dark:text-white truncate">
                          {prompt.name}
                        </h4>
                        <ServiceBadge tags={prompt.tags} />
                        <DifficultyBadge difficulty={prompt.difficulty} />
                        {prompt.is_validated && (
                          <CheckCircle className="w-4 h-4 text-green-500" />
                        )}
                      </div>
                      <p className="text-sm text-gray-500 dark:text-gray-400 mt-1 truncate">
                        {prompt.user_input.substring(0, 100)}...
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-gray-400">
                      {prompt.times_used} utilisations
                    </span>
                    {expandedPrompt === prompt.id ? (
                      <ChevronUp className="w-5 h-5 text-gray-400" />
                    ) : (
                      <ChevronDown className="w-5 h-5 text-gray-400" />
                    )}
                  </div>
                </div>
              </div>

              {/* Expanded details */}
              {expandedPrompt === prompt.id && (
                <div className="px-4 pb-4 border-t border-gray-200 dark:border-gray-700 space-y-4">
                  {prompt.system_prompt && (
                    <div className="mt-4">
                      <p className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                        System Prompt
                      </p>
                      <pre className="text-sm bg-gray-50 dark:bg-gray-900 p-3 rounded-lg overflow-x-auto whitespace-pre-wrap">
                        {prompt.system_prompt}
                      </pre>
                    </div>
                  )}

                  <div>
                    <p className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                      Input utilisateur
                    </p>
                    <pre className="text-sm bg-gray-50 dark:bg-gray-900 p-3 rounded-lg overflow-x-auto whitespace-pre-wrap">
                      {prompt.user_input}
                    </pre>
                  </div>

                  {/* Tool calling display */}
                  {prompt.tool_call && (
                    <div className="space-y-3 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
                      <p className="text-xs font-semibold text-blue-700 dark:text-blue-300">Tool Call</p>
                      <pre className="text-sm bg-white dark:bg-gray-900 p-2 rounded overflow-x-auto">
                        {JSON.stringify(prompt.tool_call, null, 2)}
                      </pre>
                    </div>
                  )}

                  {prompt.tool_response && (
                    <div className="space-y-2 p-3 bg-green-50 dark:bg-green-900/20 rounded-lg border border-green-200 dark:border-green-800">
                      <p className="text-xs font-semibold text-green-700 dark:text-green-300">Tool Response</p>
                      <pre className="text-sm bg-white dark:bg-gray-900 p-2 rounded overflow-x-auto max-h-32">
                        {JSON.stringify(prompt.tool_response, null, 2)}
                      </pre>
                    </div>
                  )}

                  {prompt.assistant_response ? (
                    <div className="space-y-2 p-3 bg-purple-50 dark:bg-purple-900/20 rounded-lg border border-purple-200 dark:border-purple-800">
                      <p className="text-xs font-semibold text-purple-700 dark:text-purple-300">Réponse finale</p>
                      <pre className="text-sm bg-white dark:bg-gray-900 p-2 rounded overflow-x-auto whitespace-pre-wrap max-h-48">
                        {prompt.assistant_response}
                      </pre>
                    </div>
                  ) : (
                    <div>
                      <p className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                        Sortie attendue
                      </p>
                      <pre className="text-sm bg-gray-50 dark:bg-gray-900 p-3 rounded-lg overflow-x-auto whitespace-pre-wrap max-h-48">
                        {prompt.expected_output}
                      </pre>
                    </div>
                  )}

                  <div className="flex gap-2">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onEdit(prompt);
                      }}
                      className="px-3 py-1.5 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 flex items-center gap-1"
                    >
                      <Edit className="w-3.5 h-3.5" />
                      {t('prompts.edit')}
                    </button>
                    {!prompt.is_validated && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onValidate(prompt.id);
                        }}
                        className="px-3 py-1.5 bg-green-600 text-white text-sm rounded-lg hover:bg-green-700 flex items-center gap-1"
                      >
                        <CheckCircle className="w-3.5 h-3.5" />
                        Valider
                      </button>
                    )}
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onDelete(prompt.id);
                      }}
                      className="px-3 py-1.5 bg-red-600 text-white text-sm rounded-lg hover:bg-red-700 flex items-center gap-1"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                      {t('prompts.delete')}
                    </button>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      ) : (
        <div className="text-center py-12 bg-white dark:bg-gray-800 rounded-lg shadow">
          <FileText className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <p className="text-gray-500 dark:text-gray-400">{t('prompts.noPrompts')}</p>
          <p className="text-sm text-gray-400 dark:text-gray-500 mt-1">
            Ajoutez des prompts pour entraîner vos modèles
          </p>
        </div>
      )}
    </div>
  );
};

// Session Creation Modal
const SessionModal = ({
  isOpen,
  onClose,
  onSubmit,
  models,
  allPrompts,
}: {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: any, promptIds: string[]) => Promise<void>;
  models: OllamaModel[];
  allPrompts: TrainingPrompt[];
}) => {
  const [step, setStep] = useState<1 | 2>(1);
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    base_model: '',
    training_backend: 'ollama_modelfile' as 'ollama_modelfile' | 'unsloth',
    worker_id: '',
    total_epochs: 3,
    batch_size: 2,
    learning_rate: 0.0002,
    overwrite_existing: false,
    base_adapter_path: '' as string,  // For incremental training from existing LoRA adapter
  });

  // HuggingFace models for GPU fine-tuning (Unsloth)
  const huggingfaceModels = [
    { name: 'unsloth/llama-3.2-3b-instruct-bnb-4bit', size: '3B', description: 'Llama 3.2 3B - Rapide, faible VRAM' },
    { name: 'unsloth/llama-3.2-1b-instruct-bnb-4bit', size: '1B', description: 'Llama 3.2 1B - Très rapide, minimal' },
    { name: 'unsloth/Llama-3.1-8B-Instruct-bnb-4bit', size: '8B', description: 'Llama 3.1 8B - Meilleure qualité' },
    { name: 'unsloth/mistral-7b-instruct-v0.3-bnb-4bit', size: '7B', description: 'Mistral 7B - Excellent rapport qualité/taille' },
    { name: 'unsloth/Phi-3.5-mini-instruct-bnb-4bit', size: '3.8B', description: 'Phi 3.5 Mini - Microsoft, compact' },
    { name: 'unsloth/gemma-2-2b-it-bnb-4bit', size: '2B', description: 'Gemma 2 2B - Google, léger' },
  ];
  const [workers, setWorkers] = useState<TrainingWorker[]>([]);
  const [loadingWorkers, setLoadingWorkers] = useState(false);
  const { t } = useTranslation('training');

  // LoRA adapters for incremental training
  interface LoraAdapter {
    adapter_name: string;
    model_name?: string;
    session_id?: string;
    session_name?: string;
    prompts_count?: number;
    created_at?: string;
    size_mb?: number;
    path: string;
    parent_adapter?: string;
  }
  const [loraAdapters, setLoraAdapters] = useState<LoraAdapter[]>([]);
  const [loadingAdapters, setLoadingAdapters] = useState(false);

  // Fetch available workers when modal opens
  useEffect(() => {
    if (isOpen) {
      setLoadingWorkers(true);
      api.workers.list(true)
        .then((data) => setWorkers(data || []))
        .catch(() => setWorkers([]))
        .finally(() => setLoadingWorkers(false));
    }
  }, [isOpen]);

  // Fetch LoRA adapters from selected worker
  useEffect(() => {
    if (formData.worker_id && formData.training_backend === 'unsloth') {
      const selectedWorker = workers.find(w => w.id === formData.worker_id);
      if (selectedWorker?.url) {
        setLoadingAdapters(true);
        fetch(`${selectedWorker.url}/api/adapters`)
          .then(res => res.json())
          .then(data => setLoraAdapters(data.adapters || []))
          .catch(() => setLoraAdapters([]))
          .finally(() => setLoadingAdapters(false));
      }
    } else {
      setLoraAdapters([]);
    }
  }, [formData.worker_id, formData.training_backend, workers]);
  const [selectedPrompts, setSelectedPrompts] = useState<Set<string>>(new Set());
  const [serviceFilter, setServiceFilter] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const detectServices = (prompt: TrainingPrompt): string[] => {
    const serviceKeywords = ['plex', 'tautulli', 'overseerr', 'radarr', 'sonarr', 'prowlarr', 'jackett', 'zammad', 'system'];
    return prompt.tags.filter(tag => serviceKeywords.includes(tag.toLowerCase()));
  };

  const filteredPrompts = allPrompts.filter((prompt) => {
    if (!prompt.enabled) return false;
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      if (!prompt.name.toLowerCase().includes(query) &&
          !prompt.user_input.toLowerCase().includes(query)) {
        return false;
      }
    }
    if (serviceFilter) {
      const services = detectServices(prompt);
      if (!services.includes(serviceFilter)) return false;
    }
    return true;
  });

  const togglePrompt = (promptId: string) => {
    const newSelected = new Set(selectedPrompts);
    if (newSelected.has(promptId)) {
      newSelected.delete(promptId);
    } else {
      newSelected.add(promptId);
    }
    setSelectedPrompts(newSelected);
  };

  const selectAll = () => setSelectedPrompts(new Set(filteredPrompts.map(p => p.id)));
  const selectNone = () => setSelectedPrompts(new Set());

  const resetForm = () => {
    setStep(1);
    setFormData({
      name: '',
      description: '',
      base_model: '',
      training_backend: 'ollama_modelfile',
      worker_id: '',
      total_epochs: 3,
      batch_size: 2,
      learning_rate: 0.0002,
      overwrite_existing: false,
      base_adapter_path: '',
    });
    setSelectedPrompts(new Set());
    setServiceFilter('');
    setSearchQuery('');
  };

  const handleClose = () => {
    resetForm();
    onClose();
  };

  const handleSubmit = async () => {
    setSubmitting(true);
    try {
      // Structure the data as expected by the backend API
      const sessionData = {
        name: formData.name,
        description: formData.description,
        base_model: formData.base_model,
        training_backend: formData.training_backend,
        worker_id: formData.worker_id || null,
        total_epochs: formData.total_epochs,
        hyperparameters: {
          batch_size: formData.batch_size,
          learning_rate: formData.learning_rate,
          overwrite_existing: formData.overwrite_existing,
        },
        // For incremental training: path to existing LoRA adapter
        base_adapter_path: formData.base_adapter_path || null,
      };
      await onSubmit(sessionData, Array.from(selectedPrompts));
      handleClose();
    } catch (error) {
      console.error('Failed to create session:', error);
    } finally {
      setSubmitting(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-4xl max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
          <div>
            <h3 className="text-lg font-medium text-gray-900 dark:text-white">
              Nouvelle session d'entraînement
            </h3>
            <div className="flex items-center gap-2 mt-1">
              <span className={`px-2 py-0.5 text-xs rounded-full ${step === 1 ? 'bg-blue-600 text-white' : 'bg-gray-200 dark:bg-gray-600 text-gray-600 dark:text-gray-300'}`}>
                1. Configuration
              </span>
              <span className="text-gray-400">→</span>
              <span className={`px-2 py-0.5 text-xs rounded-full ${step === 2 ? 'bg-blue-600 text-white' : 'bg-gray-200 dark:bg-gray-600 text-gray-600 dark:text-gray-300'}`}>
                2. Sélection des prompts
              </span>
            </div>
          </div>
          <button onClick={handleClose} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Step 1: Configuration */}
        {step === 1 && (
          <div className="p-4 space-y-4 overflow-y-auto">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Nom *</label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                placeholder="Ma session d'entraînement"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Description</label>
              <textarea
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                rows={2}
                placeholder="Description optionnelle..."
              />
            </div>
            {/* Training Method Selection - MOVED BEFORE MODEL SELECTION */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Méthode d'entraînement</label>
              <div className="space-y-2">
                <label className={`flex items-start p-3 border rounded-lg cursor-pointer transition-colors ${
                  formData.training_backend === 'ollama_modelfile'
                    ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                    : 'hover:bg-gray-50 dark:hover:bg-gray-700 border-gray-300 dark:border-gray-600'
                }`}>
                  <input
                    type="radio"
                    name="training_backend"
                    value="ollama_modelfile"
                    checked={formData.training_backend === 'ollama_modelfile'}
                    onChange={() => setFormData({ ...formData, training_backend: 'ollama_modelfile', base_model: '' })}
                    className="mt-1 mr-3"
                  />
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-gray-900 dark:text-white">Modelfile (rapide)</span>
                      <span className="px-2 py-0.5 text-xs bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300 rounded">
                        Recommandé
                      </span>
                    </div>
                    <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                      Crée un modèle Ollama avec les exemples intégrés. Pas de GPU requis.
                    </p>
                  </div>
                </label>
                <label className={`flex items-start p-3 border rounded-lg cursor-pointer transition-colors ${
                  formData.training_backend === 'unsloth'
                    ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                    : 'hover:bg-gray-50 dark:hover:bg-gray-700 border-gray-300 dark:border-gray-600'
                }`}>
                  <input
                    type="radio"
                    name="training_backend"
                    value="unsloth"
                    checked={formData.training_backend === 'unsloth'}
                    onChange={() => setFormData({ ...formData, training_backend: 'unsloth', base_model: '' })}
                    className="mt-1 mr-3"
                  />
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-gray-900 dark:text-white">Fine-tuning GPU (Unsloth)</span>
                      <span className="px-2 py-0.5 text-xs bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300 rounded flex items-center gap-1">
                        <Zap className="w-3 h-3" /> GPU requis
                      </span>
                    </div>
                    <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                      Fine-tuning LoRA sur worker GPU distant. Meilleurs résultats.
                    </p>
                  </div>
                </label>
              </div>
            </div>

            {/* Model Selection - changes based on training backend */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                {formData.training_backend === 'unsloth' ? 'Modèle de base *' : 'Modèle Ollama *'}
              </label>
              {formData.training_backend === 'unsloth' ? (
                <select
                  value={formData.base_adapter_path || formData.base_model}
                  onChange={(e) => {
                    const value = e.target.value;
                    // Check if selected value is an adapter path (starts with /)
                    if (value.startsWith('/')) {
                      // Find the adapter to get its base model
                      const adapter = loraAdapters.find(a => a.path === value);
                      setFormData({
                        ...formData,
                        base_adapter_path: value,
                        // Use the adapter's original base model, or keep current
                        base_model: adapter?.model_name || formData.base_model,
                      });
                    } else {
                      // Regular HuggingFace model selected
                      setFormData({
                        ...formData,
                        base_model: value,
                        base_adapter_path: '',
                      });
                    }
                  }}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                >
                  <option value="">Sélectionner un modèle</option>
                  {loraAdapters.length > 0 && (
                    <optgroup label="🔄 Modèles entraînés (entraînement incrémental)">
                      {loraAdapters.map((adapter) => (
                        <option key={adapter.path} value={adapter.path}>
                          {adapter.session_name || adapter.adapter_name} ({adapter.prompts_count || '?'} prompts, {adapter.size_mb?.toFixed(1) || '?'} MB)
                        </option>
                      ))}
                    </optgroup>
                  )}
                  <optgroup label="📦 Modèles HuggingFace (nouvel entraînement)">
                    {huggingfaceModels.map((model) => (
                      <option key={model.name} value={model.name}>
                        {model.description} ({model.size})
                      </option>
                    ))}
                  </optgroup>
                </select>
              ) : (
                <select
                  value={formData.base_model}
                  onChange={(e) => setFormData({ ...formData, base_model: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                >
                  <option value="">Sélectionner un modèle Ollama</option>
                  {models.map((model) => (
                    <option key={model.name} value={model.name}>
                      {model.name} ({model.size_gb.toFixed(1)} GB)
                    </option>
                  ))}
                </select>
              )}
              {formData.training_backend === 'unsloth' && (
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                  {loadingAdapters ? (
                    <span className="flex items-center gap-1">
                      <RefreshCw className="w-3 h-3 animate-spin" />
                      {t('form.loadingAdapters')}
                    </span>
                  ) : formData.base_adapter_path ? (
                    <span className="text-blue-500 dark:text-blue-400">
                      ⚡ Entraînement incrémental : les nouveaux prompts s'ajouteront aux connaissances existantes
                    </span>
                  ) : (
                    'Modèles optimisés 4-bit pour GTX 1080 Ti (11GB VRAM)'
                  )}
                </p>
              )}
            </div>

            {/* Overwrite existing model option */}
            <div className="flex items-start gap-3 p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
              <input
                type="checkbox"
                id="overwrite_existing"
                checked={formData.overwrite_existing}
                onChange={(e) => setFormData({ ...formData, overwrite_existing: e.target.checked })}
                className="mt-1"
              />
              <label htmlFor="overwrite_existing" className="cursor-pointer">
                <span className="font-medium text-gray-900 dark:text-white">Écraser le modèle existant</span>
                <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                  Si un modèle avec le même nom existe déjà dans Ollama, il sera remplacé.
                  Sinon, une erreur se produira si le nom est déjà pris.
                </p>
              </label>
            </div>

            {/* Worker Selection */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Worker d'entraînement</label>
              {loadingWorkers ? (
                <div className="flex items-center gap-2 p-3 text-gray-500 dark:text-gray-400">
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  {t('workers.loading')}
                </div>
              ) : workers.length === 0 ? (
                <div className="p-3 border border-gray-300 dark:border-gray-600 rounded-lg">
                  <div className="flex items-center gap-2 text-gray-500 dark:text-gray-400">
                    <Server className="w-4 h-4" />
                    <span>{t('workers.noWorkers')}</span>
                  </div>
                  <p className="text-sm text-gray-400 dark:text-gray-500 mt-1">
                    Configurez un worker dans les paramètres pour activer l'entraînement.
                  </p>
                </div>
              ) : (
                <div className="space-y-2">
                  {workers.map((worker) => {
                    const isOnline = worker.status === 'online';
                    const hasGpu = worker.gpu_available;
                    const isDisabled = !isOnline || !worker.enabled;

                    return (
                      <label
                        key={worker.id}
                        className={`flex items-center p-3 border rounded-lg cursor-pointer transition-colors ${
                          isDisabled
                            ? 'opacity-50 cursor-not-allowed border-gray-200 dark:border-gray-700'
                            : formData.worker_id === worker.id
                              ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                              : 'hover:bg-gray-50 dark:hover:bg-gray-700 border-gray-300 dark:border-gray-600'
                        }`}
                      >
                        <input
                          type="radio"
                          name="worker_id"
                          value={worker.id}
                          checked={formData.worker_id === worker.id}
                          onChange={(e) => setFormData({ ...formData, worker_id: e.target.value })}
                          disabled={isDisabled}
                          className="mr-3"
                        />
                        <div className="flex-1">
                          <div className="flex items-center gap-2">
                            {hasGpu ? (
                              <Zap className="w-4 h-4 text-yellow-500" />
                            ) : (
                              <Server className="w-4 h-4 text-blue-500" />
                            )}
                            <span className="font-medium text-gray-900 dark:text-white">{worker.name}</span>
                            {isOnline ? (
                              hasGpu ? (
                                <span className="px-2 py-0.5 text-xs bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300 rounded">
                                  GPU: {worker.gpu_names?.[0] || 'Disponible'}
                                </span>
                              ) : (
                                <span className="px-2 py-0.5 text-xs bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300 rounded">
                                  CPU only
                                </span>
                              )
                            ) : (
                              <span className="px-2 py-0.5 text-xs bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300 rounded">
                                Hors ligne
                              </span>
                            )}
                            {worker.current_job_id && (
                              <span className="px-2 py-0.5 text-xs bg-orange-100 text-orange-700 dark:bg-orange-900 dark:text-orange-300 rounded flex items-center gap-1">
                                <Activity className="w-3 h-3" /> Occupé
                              </span>
                            )}
                          </div>
                          {worker.description && (
                            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                              {worker.description}
                            </p>
                          )}
                        </div>
                      </label>
                    );
                  })}
                </div>
              )}
            </div>
            <div className="grid grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Epochs</label>
                <input
                  type="number"
                  min="1"
                  value={formData.total_epochs}
                  onChange={(e) => setFormData({ ...formData, total_epochs: parseInt(e.target.value) || 1 })}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Batch size</label>
                <input
                  type="number"
                  min="1"
                  value={formData.batch_size}
                  onChange={(e) => setFormData({ ...formData, batch_size: parseInt(e.target.value) || 1 })}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Learning rate</label>
                <input
                  type="number"
                  step="0.00001"
                  min="0"
                  value={formData.learning_rate}
                  onChange={(e) => setFormData({ ...formData, learning_rate: parseFloat(e.target.value) || 0.0001 })}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                />
              </div>
            </div>
          </div>
        )}

        {/* Step 2: Prompt Selection */}
        {step === 2 && (
          <div className="flex-1 flex flex-col overflow-hidden">
            {/* Filters */}
            <div className="p-4 border-b border-gray-200 dark:border-gray-700 space-y-3">
              <div className="flex items-center gap-3">
                <div className="relative flex-1">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                  <input
                    type="text"
                    placeholder={t('prompts.searchPlaceholder')}
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-full pl-9 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm"
                  />
                </div>
                <select
                  value={serviceFilter}
                  onChange={(e) => setServiceFilter(e.target.value)}
                  className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm"
                >
                  <option value="">Tous les services</option>
                  {AVAILABLE_SERVICES.map((service) => (
                    <option key={service.id} value={service.id}>
                      {service.icon} {service.label}
                    </option>
                  ))}
                </select>
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <button onClick={selectAll} className="text-sm text-blue-600 hover:text-blue-700 dark:text-blue-400">
                    Tout sélectionner
                  </button>
                  <span className="text-gray-300 dark:text-gray-600">|</span>
                  <button onClick={selectNone} className="text-sm text-gray-500 hover:text-gray-600 dark:text-gray-400">
                    Tout désélectionner
                  </button>
                </div>
                <span className="text-sm text-gray-500 dark:text-gray-400">
                  {selectedPrompts.size} sélectionné{selectedPrompts.size !== 1 ? 's' : ''} / {filteredPrompts.length}
                </span>
              </div>
            </div>

            {/* Prompts List */}
            <div className="flex-1 overflow-y-auto p-4">
              {filteredPrompts.length > 0 ? (
                <div className="space-y-2">
                  {filteredPrompts.map((prompt) => {
                    const services = detectServices(prompt);
                    const isSelected = selectedPrompts.has(prompt.id);
                    return (
                      <div
                        key={prompt.id}
                        onClick={() => togglePrompt(prompt.id)}
                        className={`p-3 rounded-lg border cursor-pointer transition-all ${
                          isSelected
                            ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                            : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
                        }`}
                      >
                        <div className="flex items-start gap-3">
                          <div className={`mt-0.5 w-5 h-5 rounded border flex items-center justify-center ${
                            isSelected ? 'bg-blue-600 border-blue-600 text-white' : 'border-gray-300 dark:border-gray-600'
                          }`}>
                            {isSelected && <Check className="w-3.5 h-3.5" />}
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 flex-wrap">
                              <span className="font-medium text-gray-900 dark:text-white text-sm">{prompt.name}</span>
                              {services.map((service) => {
                                const svc = AVAILABLE_SERVICES.find(s => s.id === service);
                                return svc ? (
                                  <span key={service} className={`px-1.5 py-0.5 text-xs rounded ${svc.color} text-white`}>
                                    {svc.icon}
                                  </span>
                                ) : null;
                              })}
                            </div>
                            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 line-clamp-1">{prompt.user_input}</p>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="text-center py-12">
                  <FileText className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-4" />
                  <p className="text-gray-500 dark:text-gray-400">{t('prompts.noPromptsFound')}</p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Footer */}
        <div className="flex items-center justify-between p-4 border-t border-gray-200 dark:border-gray-700">
          <div>
            {step === 2 && (
              <span className="text-sm text-gray-500 dark:text-gray-400">
                {selectedPrompts.size} prompt{selectedPrompts.size !== 1 ? 's' : ''} pour l'entraînement
              </span>
            )}
          </div>
          <div className="flex gap-3">
            {step === 1 ? (
              <>
                <button
                  onClick={handleClose}
                  className="px-4 py-2 text-gray-700 dark:text-gray-300 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700"
                >
                  {t('sessions.cancel')}
                </button>
                <button
                  onClick={() => setStep(2)}
                  disabled={!formData.name || !formData.base_model}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2"
                >
                  Suivant
                  <ChevronDown className="w-4 h-4 rotate-[-90deg]" />
                </button>
              </>
            ) : (
              <>
                <button
                  onClick={() => setStep(1)}
                  className="px-4 py-2 text-gray-700 dark:text-gray-300 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 flex items-center gap-2"
                >
                  <ChevronDown className="w-4 h-4 rotate-90" />
                  Retour
                </button>
                <button
                  onClick={handleSubmit}
                  disabled={submitting || selectedPrompts.size === 0}
                  className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 flex items-center gap-2"
                >
                  {submitting ? (
                    <>
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                      {t('prompts.creating')}
                    </>
                  ) : (
                    <>
                      <Check className="w-4 h-4" />
                      {t('prompts.createMultiple', { count: selectedPrompts.size })}
                    </>
                  )}
                </button>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
// Prompt Creation/Edit Modal
const PromptModal = ({
  isOpen,
  onClose,
  onSubmit,
  availableServices,
  editingPrompt,
}: {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: any) => Promise<void>;
  availableServices: { id: string; label: string; icon: string; color: string }[];
  editingPrompt?: TrainingPrompt | null;
}) => {
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    difficulty: 'basic',
    system_prompt: 'Tu es un assistant IA homelab. Utilise les outils MCP pour répondre aux demandes.',
    user_input: '',
    expected_output: '',
    // Tool calling support
    tool_call_name: '',
    tool_call_arguments: '',
    tool_response: '',
    assistant_response: '',
    services: [] as string[],
  });
  const [submitting, setSubmitting] = useState(false);
  const [useToolCalling, setUseToolCalling] = useState(false);
  const { t } = useTranslation('training');

  // Populate form when editing
  useEffect(() => {
    if (editingPrompt) {
      setFormData({
        name: editingPrompt.name,
        description: editingPrompt.description || '',
        difficulty: editingPrompt.difficulty,
        system_prompt: editingPrompt.system_prompt || 'Tu es un assistant IA homelab. Utilise les outils MCP pour répondre aux demandes.',
        user_input: editingPrompt.user_input,
        expected_output: editingPrompt.expected_output,
        tool_call_name: editingPrompt.tool_call?.name || '',
        tool_call_arguments: editingPrompt.tool_call?.arguments ? JSON.stringify(editingPrompt.tool_call.arguments, null, 2) : '',
        tool_response: editingPrompt.tool_response ? JSON.stringify(editingPrompt.tool_response, null, 2) : '',
        assistant_response: editingPrompt.assistant_response || '',
        services: editingPrompt.tags || [],
      });
      setUseToolCalling(!!editingPrompt.tool_call);
    } else {
      // Reset form for new prompt
      setFormData({
        name: '',
        description: '',
        difficulty: 'basic',
        system_prompt: 'Tu es un assistant IA homelab. Utilise les outils MCP pour répondre aux demandes.',
        user_input: '',
        expected_output: '',
        tool_call_name: '',
        tool_call_arguments: '',
        tool_response: '',
        assistant_response: '',
        services: [],
      });
      setUseToolCalling(false);
    }
  }, [editingPrompt, isOpen]);

  if (!isOpen) return null;

  const toggleService = (serviceId: string) => {
    setFormData(prev => ({
      ...prev,
      services: prev.services.includes(serviceId)
        ? prev.services.filter(s => s !== serviceId)
        : [...prev.services, serviceId]
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (formData.services.length === 0) {
      alert('Veuillez sélectionner au moins un service');
      return;
    }
    setSubmitting(true);
    try {
      // Build the submission data (without category - using tags for services)
      const submitData: any = {
        name: formData.name,
        description: formData.description,
        category: 'homelab', // Default category (required by backend but not user-facing)
        difficulty: formData.difficulty,
        system_prompt: formData.system_prompt,
        user_input: formData.user_input,
        tags: formData.services,
      };

      // Add ID if editing
      if (editingPrompt) {
        submitData.id = editingPrompt.id;
      }

      // Handle tool calling fields
      if (useToolCalling && formData.tool_call_name && formData.tool_response && formData.assistant_response) {
        // Parse tool call arguments
        let parsedArgs = {};
        try {
          if (formData.tool_call_arguments.trim()) {
            parsedArgs = JSON.parse(formData.tool_call_arguments);
          }
        } catch {
          alert(t('form.jsonValidationError'));
          setSubmitting(false);
          return;
        }

        // Parse tool response
        let parsedResponse = {};
        try {
          parsedResponse = JSON.parse(formData.tool_response);
        } catch {
          alert(t('form.jsonResponseError'));
          setSubmitting(false);
          return;
        }

        submitData.tool_call = {
          name: formData.tool_call_name,
          arguments: parsedArgs,
        };
        submitData.tool_response = parsedResponse;
        submitData.assistant_response = formData.assistant_response;
        submitData.expected_output = formData.assistant_response; // For backwards compatibility
      } else {
        submitData.expected_output = formData.expected_output;
      }

      await onSubmit(submitData);
      onClose();
    } catch (error) {
      console.error('Failed to save prompt:', error);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-2xl mx-4 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
          <h3 className="text-lg font-medium text-gray-900 dark:text-white">
            {editingPrompt ? t('prompts.editPrompt') : t('prompts.newPrompt')}
          </h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300">
            <X className="w-5 h-5" />
          </button>
        </div>
        <form onSubmit={handleSubmit} className="p-4 space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{t('form.nameRequired')}</label>
              <input
                type="text"
                required
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                placeholder={t('form.namePlaceholder')}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Difficulté</label>
              <select
                value={formData.difficulty}
                onChange={(e) => setFormData({ ...formData, difficulty: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              >
                <option value="basic">Basique</option>
                <option value="intermediate">Intermédiaire</option>
                <option value="advanced">Avancé</option>
              </select>
            </div>
          </div>

          {/* Services Selection */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">{t('form.servicesRequired')}</label>
            <div className="flex flex-wrap gap-2">
              {availableServices.map((service) => (
                <button
                  key={service.id}
                  type="button"
                  onClick={() => toggleService(service.id)}
                  className={`px-3 py-1.5 rounded-full text-sm font-medium flex items-center gap-1.5 transition-all ${
                    formData.services.includes(service.id)
                      ? `${service.color} text-white ring-2 ring-offset-2 ring-${service.color.replace('bg-', '')}`
                      : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
                  }`}
                >
                  <span>{service.icon}</span>
                  <span>{service.label}</span>
                </button>
              ))}
            </div>
            {formData.services.length === 0 && (
              <p className="text-xs text-red-500 mt-1">{t('prompts.selectAtLeastOne')}</p>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Description</label>
            <input
              type="text"
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              placeholder="Description du prompt"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">System Prompt</label>
            <textarea
              value={formData.system_prompt}
              onChange={(e) => setFormData({ ...formData, system_prompt: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white font-mono text-sm"
              rows={3}
              placeholder="Instructions système pour le modèle..."
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Input utilisateur *</label>
            <textarea
              required
              value={formData.user_input}
              onChange={(e) => setFormData({ ...formData, user_input: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white font-mono text-sm"
              rows={3}
              placeholder="Question ou demande de l'utilisateur..."
            />
          </div>
          {/* Tool Calling Toggle */}
          <div className="flex items-center gap-3 py-2 border-t border-gray-200 dark:border-gray-700">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={useToolCalling}
                onChange={(e) => setUseToolCalling(e.target.checked)}
                className="w-4 h-4 text-blue-600 rounded border-gray-300 focus:ring-blue-500"
              />
              <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                Utiliser Tool Calling
              </span>
            </label>
            <span className="text-xs text-gray-500 dark:text-gray-400">
              (apprend au modèle à appeler des outils ET utiliser les résultats)
            </span>
          </div>

          {useToolCalling ? (
            <>
              {/* Tool Call Section */}
              <div className="space-y-4 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
                <h4 className="text-sm font-semibold text-blue-700 dark:text-blue-300">Tool Call (Appel d'outil)</h4>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Nom du tool *</label>
                    <input
                      type="text"
                      required
                      value={formData.tool_call_name}
                      onChange={(e) => setFormData({ ...formData, tool_call_name: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white font-mono text-sm"
                      placeholder="ex: system_get_health"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Arguments (JSON)</label>
                    <input
                      type="text"
                      value={formData.tool_call_arguments}
                      onChange={(e) => setFormData({ ...formData, tool_call_arguments: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white font-mono text-sm"
                      placeholder='ex: {"service": "ollama"}'
                    />
                  </div>
                </div>
              </div>

              {/* Tool Response Section */}
              <div className="space-y-2 p-4 bg-green-50 dark:bg-green-900/20 rounded-lg border border-green-200 dark:border-green-800">
                <label className="block text-sm font-semibold text-green-700 dark:text-green-300">Réponse du Tool (JSON) *</label>
                <textarea
                  required
                  value={formData.tool_response}
                  onChange={(e) => setFormData({ ...formData, tool_response: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white font-mono text-sm"
                  rows={4}
                  placeholder='{"status": "healthy", "version": "0.1.0", "services": [...]}'
                />
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  Réponse réaliste que le tool retournerait (utilisée pour l'entraînement)
                </p>
              </div>

              {/* Final Assistant Response */}
              <div className="space-y-2 p-4 bg-purple-50 dark:bg-purple-900/20 rounded-lg border border-purple-200 dark:border-purple-800">
                <label className="block text-sm font-semibold text-purple-700 dark:text-purple-300">Réponse finale de l'assistant *</label>
                <textarea
                  required
                  value={formData.assistant_response}
                  onChange={(e) => setFormData({ ...formData, assistant_response: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white font-mono text-sm"
                  rows={4}
                  placeholder="Le système est en bonne santé. Ollama version 0.1.0 est opérationnel avec 3 services actifs..."
                />
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  Comment l'assistant doit synthétiser et présenter les données du tool
                </p>
              </div>
            </>
          ) : (
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Sortie attendue *</label>
              <textarea
                required
                value={formData.expected_output}
                onChange={(e) => setFormData({ ...formData, expected_output: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white font-mono text-sm"
                rows={4}
                placeholder="Réponse attendue du modèle..."
              />
            </div>
          )}

          <div className="flex justify-end gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-gray-700 dark:text-gray-300 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700"
            >
              {t('prompts.cancel')}
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              {submitting
                ? (editingPrompt ? t('prompts.saving') : t('prompts.creating'))
                : (editingPrompt ? t('prompts.save') : t('prompts.create'))}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

// Session Prompts Selection Modal
const SessionPromptsModal = ({
  isOpen,
  onClose,
  session,
  allPrompts,
  onSave,
}: {
  isOpen: boolean;
  onClose: () => void;
  session: TrainingSession;
  allPrompts: TrainingPrompt[];
  onSave: (sessionId: string, promptIds: string[]) => Promise<void>;
}) => {
  const [selectedPrompts, setSelectedPrompts] = useState<Set<string>>(new Set());
  const [serviceFilter, setServiceFilter] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [saving, setSaving] = useState(false);
  const [_sessionPrompts, setSessionPrompts] = useState<TrainingPrompt[]>([]);
  const [loadingSessionPrompts, setLoadingSessionPrompts] = useState(true);
  const { t } = useTranslation('training');

  // Load current session prompts on open
  useEffect(() => {
    if (isOpen && session) {
      setLoadingSessionPrompts(true);
      api.training.sessions.getPrompts(session.id)
        .then((prompts: TrainingPrompt[]) => {
          setSessionPrompts(prompts);
          setSelectedPrompts(new Set(prompts.map(p => p.id)));
        })
        .catch(console.error)
        .finally(() => setLoadingSessionPrompts(false));
    }
  }, [isOpen, session?.id]);

  const detectServices = (prompt: TrainingPrompt): string[] => {
    const serviceKeywords = ['plex', 'tautulli', 'overseerr', 'radarr', 'sonarr', 'prowlarr', 'jackett', 'zammad', 'system'];
    return prompt.tags.filter(tag => serviceKeywords.includes(tag.toLowerCase()));
  };

  const filteredPrompts = allPrompts.filter((prompt) => {
    if (!prompt.enabled) return false;
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      if (!prompt.name.toLowerCase().includes(query) &&
          !prompt.user_input.toLowerCase().includes(query)) {
        return false;
      }
    }
    if (serviceFilter) {
      const services = detectServices(prompt);
      if (!services.includes(serviceFilter)) return false;
    }
    return true;
  });

  const togglePrompt = (promptId: string) => {
    const newSelected = new Set(selectedPrompts);
    if (newSelected.has(promptId)) {
      newSelected.delete(promptId);
    } else {
      newSelected.add(promptId);
    }
    setSelectedPrompts(newSelected);
  };

  const selectAll = () => {
    const allIds = new Set(filteredPrompts.map(p => p.id));
    setSelectedPrompts(allIds);
  };

  const selectNone = () => {
    setSelectedPrompts(new Set());
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await onSave(session.id, Array.from(selectedPrompts));
      onClose();
    } catch (error) {
      console.error('Failed to save prompts:', error);
    } finally {
      setSaving(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-4xl max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
          <div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
              Sélection des prompts
            </h3>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Session: {session.name}
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded-lg"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Filters */}
        <div className="p-4 border-b border-gray-200 dark:border-gray-700 space-y-3">
          <div className="flex items-center gap-3">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                placeholder={t('prompts.searchPlaceholder')}
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-9 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm"
              />
            </div>
            <select
              value={serviceFilter}
              onChange={(e) => setServiceFilter(e.target.value)}
              className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm"
            >
              <option value="">Tous les services</option>
              {AVAILABLE_SERVICES.map((service) => (
                <option key={service.id} value={service.id}>
                  {service.icon} {service.label}
                </option>
              ))}
            </select>
          </div>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <button
                onClick={selectAll}
                className="text-sm text-blue-600 hover:text-blue-700 dark:text-blue-400"
              >
                Tout sélectionner
              </button>
              <span className="text-gray-300 dark:text-gray-600">|</span>
              <button
                onClick={selectNone}
                className="text-sm text-gray-500 hover:text-gray-600 dark:text-gray-400"
              >
                Tout désélectionner
              </button>
            </div>
            <span className="text-sm text-gray-500 dark:text-gray-400">
              {selectedPrompts.size} sélectionné{selectedPrompts.size !== 1 ? 's' : ''} / {filteredPrompts.length} affiché{filteredPrompts.length !== 1 ? 's' : ''}
            </span>
          </div>
        </div>

        {/* Prompts List */}
        <div className="flex-1 overflow-y-auto p-4">
          {loadingSessionPrompts ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
            </div>
          ) : filteredPrompts.length > 0 ? (
            <div className="space-y-2">
              {filteredPrompts.map((prompt) => {
                const services = detectServices(prompt);
                const isSelected = selectedPrompts.has(prompt.id);
                return (
                  <div
                    key={prompt.id}
                    onClick={() => togglePrompt(prompt.id)}
                    className={`p-3 rounded-lg border cursor-pointer transition-all ${
                      isSelected
                        ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                        : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
                    }`}
                  >
                    <div className="flex items-start gap-3">
                      <div className={`mt-0.5 w-5 h-5 rounded border flex items-center justify-center ${
                        isSelected
                          ? 'bg-blue-600 border-blue-600 text-white'
                          : 'border-gray-300 dark:border-gray-600'
                      }`}>
                        {isSelected && <Check className="w-3.5 h-3.5" />}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="font-medium text-gray-900 dark:text-white text-sm">
                            {prompt.name}
                          </span>
                          {services.map((service) => {
                            const svc = AVAILABLE_SERVICES.find(s => s.id === service);
                            return svc ? (
                              <span
                                key={service}
                                className={`px-1.5 py-0.5 text-xs rounded ${svc.color} text-white`}
                              >
                                {svc.icon}
                              </span>
                            ) : null;
                          })}
                        </div>
                        <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 line-clamp-1">
                          {prompt.user_input}
                        </p>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="text-center py-12">
              <FileText className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-4" />
              <p className="text-gray-500 dark:text-gray-400">{t('prompts.noPromptsFound')}</p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between p-4 border-t border-gray-200 dark:border-gray-700">
          <span className="text-sm text-gray-500 dark:text-gray-400">
            {selectedPrompts.size} prompt{selectedPrompts.size !== 1 ? 's' : ''} sera{selectedPrompts.size !== 1 ? 'ont' : ''} utilisé{selectedPrompts.size !== 1 ? 's' : ''} pour l'entraînement
          </span>
          <div className="flex gap-3">
            <button
              onClick={onClose}
              className="px-4 py-2 text-gray-700 dark:text-gray-300 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700"
            >
              {t('prompts.cancel')}
            </button>
            <button
              onClick={handleSave}
              disabled={saving}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2"
            >
              {saving ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                  {t('prompts.saving')}
                </>
              ) : (
                <>
                  <Check className="w-4 h-4" />
                  {t('prompts.saveMultiple', { count: selectedPrompts.size })}
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

// Main Component
export default function Training() {
  const { t } = useTranslation('training');
  const [activeTab, setActiveTab] = useState<'overview' | 'sessions' | 'prompts' | 'workers' | 'models'>('overview');
  const [ollamaStatus, setOllamaStatus] = useState<OllamaStatus | null>(null);
  const [_ollamaMetrics, _setOllamaMetrics] = useState<OllamaMetrics | null>(null);
  const [stats, setStats] = useState<TrainingStats | null>(null);
  const [sessions, setSessions] = useState<TrainingSession[]>([]);
  const [prompts, setPrompts] = useState<TrainingPrompt[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [serviceFilter, setServiceFilter] = useState('');
  const [showSessionModal, setShowSessionModal] = useState(false);
  const [showPromptModal, setShowPromptModal] = useState(false);
  const [showPromptsSelectionModal, setShowPromptsSelectionModal] = useState(false);
  const [selectedSessionForPrompts, setSelectedSessionForPrompts] = useState<TrainingSession | null>(null);
  const [showDetailsModal, setShowDetailsModal] = useState(false);
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null);
  const [showLogsModal, setShowLogsModal] = useState(false);
  const [selectedLogsSessionId, setSelectedLogsSessionId] = useState<string | null>(null);
  const [selectedLogsSessionName, setSelectedLogsSessionName] = useState<string | undefined>(undefined);
  const [selectedLogsSessionStatus, setSelectedLogsSessionStatus] = useState<string | undefined>(undefined);
  const [editingPrompt, setEditingPrompt] = useState<TrainingPrompt | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // WebSocket for real-time training metrics
  const {
    connected: wsConnected,
    connect: wsConnect,
    subscribeToSession,
    unsubscribeFromSession,
  } = useTrainingWebSocket({
    autoConnect: false,
    onSessionUpdate: (update) => {
      // Update local session state with real-time metrics
      setSessions(prev => prev.map(session => {
        if (session.id === update.session_id && update.data) {
          const metrics = update.data;
          return {
            ...session,
            progress_percent: metrics.progress?.progress_percent ?? session.progress_percent,
            current_epoch: metrics.progress?.current_epoch ?? session.current_epoch,
            total_epochs: metrics.progress?.total_epochs ?? session.total_epochs,
            current_step: metrics.progress?.current_step ?? session.current_step,
            total_steps: metrics.progress?.total_steps ?? session.total_steps,
            loss: metrics.performance?.loss ?? session.loss,
            learning_rate: metrics.performance?.learning_rate ?? session.learning_rate,
            gpu_memory_used: metrics.gpu?.memory_used_mb ? metrics.gpu.memory_used_mb / 1024 : session.gpu_memory_used,
            cpu_usage: session.cpu_usage,
            // Store full metrics for display
            _realtime_metrics: metrics,
          } as TrainingSession & { _realtime_metrics?: TrainingMetrics };
        }
        return session;
      }));

      // Update stats based on update type
      if (update.update_type === 'completed' || update.update_type === 'failed' || update.update_type === 'cancelled') {
        // Refresh data when a session ends
        fetchData();
      }
    },
  });

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [statusRes, metricsRes, statsRes, sessionsRes, promptsRes] = await Promise.all([
        api.training.ollama.status().catch(() => null),
        api.training.ollama.metrics().catch(() => null),
        api.training.stats().catch(() => null),
        api.training.sessions.list().catch(() => []),
        api.training.prompts.list({
          ...(searchQuery && { search: searchQuery }),
        }).catch(() => []),
      ]);

      if (statusRes) setOllamaStatus(statusRes);
      if (metricsRes) _setOllamaMetrics(metricsRes);
      if (statsRes) setStats(statsRes);
      setSessions(sessionsRes);
      setPrompts(promptsRes);
    } catch (error) {
      console.error('Failed to fetch training data:', error);
    } finally {
      setLoading(false);
    }
  }, [searchQuery]);

  useEffect(() => {
    fetchData();
  }, []);

  // Connect WebSocket and subscribe to active sessions when they exist
  useEffect(() => {
    const activeSessions = sessions.filter(s => s.status === 'running' || s.status === 'preparing');

    if (activeSessions.length > 0 && !wsConnected) {
      wsConnect();
    }

    // Subscribe to each active session
    if (wsConnected) {
      activeSessions.forEach(session => {
        subscribeToSession(session.id, 2); // 2 second update interval
      });
    }

    // Cleanup: unsubscribe when sessions complete
    return () => {
      activeSessions.forEach(session => {
        unsubscribeFromSession(session.id);
      });
    };
  }, [sessions, wsConnected, wsConnect, subscribeToSession, unsubscribeFromSession]);

  // Light polling for stats only (not full data) when sessions are active - every 30 seconds
  useEffect(() => {
    if (stats?.active_sessions && stats.active_sessions > 0) {
      const interval = setInterval(async () => {
        // Only refresh stats and sessions list, not the entire page
        try {
          const [statsRes, sessionsRes] = await Promise.all([
            api.training.stats().catch(() => null),
            api.training.sessions.list().catch(() => []),
          ]);
          if (statsRes) setStats(statsRes);
          if (sessionsRes) {
            // Merge new session data with existing realtime metrics
            setSessions(prev => {
              return sessionsRes.map((newSession: TrainingSession) => {
                const existing = prev.find(s => s.id === newSession.id);
                if (existing && (existing as any)._realtime_metrics) {
                  return { ...newSession, _realtime_metrics: (existing as any)._realtime_metrics };
                }
                return newSession;
              });
            });
          }
        } catch (error) {
          console.error('Failed to refresh stats:', error);
        }
      }, 30000); // 30 second polling for session list updates
      return () => clearInterval(interval);
    }
  }, [stats?.active_sessions]);

  const handleStartSession = async (id: string) => {
    try {
      // Find the session to get its configured backend
      const session = sessions.find(s => s.id === id);
      const backend = (session?.training_backend || 'ollama_modelfile') as 'ollama_modelfile' | 'unsloth';
      await api.training.sessions.start(id, backend);
      fetchData();
    } catch (error) {
      console.error('Failed to start session:', error);
    }
  };

  const handleCancelSession = async (id: string) => {
    try {
      await api.training.sessions.cancel(id);
      fetchData();
    } catch (error) {
      console.error('Failed to cancel session:', error);
    }
  };

  const handleDeleteSession = async (id: string) => {
    if (!confirm('Êtes-vous sûr de vouloir supprimer cette session ?')) return;
    try {
      await api.training.sessions.delete(id);
      fetchData();
    } catch (error) {
      console.error('Failed to delete session:', error);
    }
  };

  const handleDuplicateSession = async (id: string) => {
    try {
      await api.training.sessions.duplicate(id);
      fetchData();
    } catch (error) {
      console.error('Failed to duplicate session:', error);
    }
  };

  const handleManageSessionPrompts = (session: TrainingSession) => {
    setSelectedSessionForPrompts(session);
    setShowPromptsSelectionModal(true);
  };

  const handleViewSessionDetails = (sessionId: string) => {
    setSelectedSessionId(sessionId);
    setShowDetailsModal(true);
  };

  const handleViewSessionLogs = (sessionId: string, sessionName?: string, sessionStatus?: string) => {
    setSelectedLogsSessionId(sessionId);
    setSelectedLogsSessionName(sessionName);
    setSelectedLogsSessionStatus(sessionStatus);
    setShowLogsModal(true);
  };

  const handleSaveSessionPrompts = async (sessionId: string, promptIds: string[]) => {
    await api.training.sessions.setPrompts(sessionId, promptIds);
    fetchData();
  };

  const handleValidatePrompt = async (id: string) => {
    try {
      await api.training.prompts.validate(id);
      fetchData();
    } catch (error) {
      console.error('Failed to validate prompt:', error);
    }
  };

  const handleDeletePrompt = async (id: string) => {
    if (!confirm('Êtes-vous sûr de vouloir supprimer ce prompt ?')) return;
    try {
      await api.training.prompts.delete(id);
      fetchData();
    } catch (error) {
      console.error('Failed to delete prompt:', error);
    }
  };

  const handleCreateSession = async (data: any, promptIds: string[]) => {
    // Create session
    const session = await api.training.sessions.create(data);
    // Associate prompts
    if (promptIds.length > 0 && session?.id) {
      await api.training.sessions.setPrompts(session.id, promptIds);
    }
    fetchData();
  };

  const handleSavePrompt = async (data: any) => {
    if (data.id) {
      // Update existing prompt
      await api.training.prompts.update(data.id, data);
    } else {
      // Create new prompt
      await api.training.prompts.create(data);
    }
    setEditingPrompt(null);
    fetchData();
  };

  const handleEditPrompt = (prompt: TrainingPrompt) => {
    setEditingPrompt(prompt);
    setShowPromptModal(true);
  };

  const handleImportPrompts = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    try {
      const text = await file.text();
      const prompts = JSON.parse(text);
      await api.training.prompts.import(Array.isArray(prompts) ? prompts : [prompts]);
      fetchData();
      alert('Prompts importés avec succès');
    } catch (error) {
      console.error('Failed to import prompts:', error);
      alert(t('errors.importFailed'));
    }
    e.target.value = '';
  };

  const handleExportPrompts = async () => {
    try {
      const data = await api.training.prompts.export({});
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `prompts-export-${new Date().toISOString().split('T')[0]}.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Failed to export prompts:', error);
      alert(t('errors.exportFailed'));
    }
  };

  const handleSeedPrompts = async (reset: boolean = false) => {
    if (reset && !confirm('Ceci va supprimer TOUS les prompts existants et les remplacer par les prompts par défaut. Continuer ?')) {
      return;
    }
    try {
      const result = await api.training.prompts.seed(reset);
      alert(`${result.message}`);
      fetchData();
    } catch (error) {
      console.error('Failed to seed prompts:', error);
      alert(t('errors.loadHomelabFailed'));
    }
  };

  return (
    <div className="p-4 sm:p-6 space-y-4 sm:space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <Brain className="w-6 h-6 sm:w-8 sm:h-8 text-purple-600" />
            Training IA
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Entraînement et fine-tuning avec Ollama
          </p>
        </div>
        <button
          onClick={fetchData}
          className="p-2 sm:px-4 sm:py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-200 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors flex items-center gap-2"
        >
          <RefreshCw className="w-4 h-4" />
          <span className="hidden sm:inline">{t('refresh')}</span>
        </button>
      </div>

      {/* Tab Navigation - Compact horizontal pills */}
      <div className="mb-4 sm:mb-6 overflow-x-auto -mx-4 px-4 sm:mx-0 sm:px-0">
        <nav className="flex gap-1.5 sm:gap-2 min-w-max sm:min-w-0 sm:flex-wrap">
          {[
            { id: 'overview' as const, label: 'Stats', labelFull: 'Vue générale', icon: BarChart3 },
            { id: 'sessions' as const, label: 'Sessions', labelFull: 'Sessions d\'entraînement', icon: History },
            { id: 'prompts' as const, label: 'Prompts', labelFull: 'Prompts d\'entraînement', icon: FileText },
            { id: 'workers' as const, label: 'Workers', labelFull: 'Workers GPU', icon: Monitor },
            { id: 'models' as const, label: 'Models', labelFull: 'Modèles Ollama', icon: Brain },
          ].map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;

            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                title={tab.labelFull}
                className={`flex items-center gap-1.5 py-1.5 px-2.5 sm:py-2 sm:px-3 rounded-full font-medium text-xs sm:text-sm transition-all whitespace-nowrap ${
                  isActive
                    ? 'bg-purple-600 text-white shadow-sm'
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
      {loading && activeTab === 'overview' ? (
        <div className="text-center py-12 text-gray-500">{t('models.loading')}</div>
      ) : (
        <>
          {activeTab === 'overview' && (
            <TrainingOverview
              stats={stats}
              ollamaStatus={ollamaStatus}
              activeSessions={sessions.filter(s => s.status === 'running' || s.status === 'preparing')}
              wsConnected={wsConnected}
              onViewLogs={handleViewSessionLogs}
            />
          )}

          {activeTab === 'sessions' && (
            <SessionsTab
              sessions={sessions}
              loading={loading}
              onCreate={() => setShowSessionModal(true)}
              onStart={handleStartSession}
              onCancel={handleCancelSession}
              onDelete={handleDeleteSession}
              onDuplicate={handleDuplicateSession}
              onManagePrompts={handleManageSessionPrompts}
              onViewDetails={handleViewSessionDetails}
              onViewLogs={handleViewSessionLogs}
            />
          )}

          {activeTab === 'prompts' && (
            <PromptsTab
              prompts={prompts}
              loading={loading}
              searchQuery={searchQuery}
              setSearchQuery={setSearchQuery}
              serviceFilter={serviceFilter}
              setServiceFilter={setServiceFilter}
              onCreate={() => {
                setEditingPrompt(null);
                setShowPromptModal(true);
              }}
              onImport={handleImportPrompts}
              onExport={handleExportPrompts}
              onSeed={handleSeedPrompts}
              onValidate={handleValidatePrompt}
              onDelete={handleDeletePrompt}
              onEdit={handleEditPrompt}
            />
          )}

          {activeTab === 'workers' && (
            <WorkerList />
          )}

          {activeTab === 'models' && (
            <ModelsTab
              models={ollamaStatus?.models || []}
              loading={loading}
              onRefresh={fetchData}
              runningModels={ollamaStatus?.running_models || []}
            />
          )}

        </>
      )}

      {/* Session Creation Modal */}
      <SessionModal
        isOpen={showSessionModal}
        onClose={() => setShowSessionModal(false)}
        onSubmit={handleCreateSession}
        models={ollamaStatus?.models || []}
        allPrompts={prompts}
      />

      {/* Prompt Creation/Edit Modal */}
      <PromptModal
        isOpen={showPromptModal}
        onClose={() => {
          setShowPromptModal(false);
          setEditingPrompt(null);
        }}
        onSubmit={handleSavePrompt}
        availableServices={AVAILABLE_SERVICES}
        editingPrompt={editingPrompt}
      />

      {selectedSessionForPrompts && (
        <SessionPromptsModal
          isOpen={showPromptsSelectionModal}
          onClose={() => {
            setShowPromptsSelectionModal(false);
            setSelectedSessionForPrompts(null);
          }}
          session={selectedSessionForPrompts}
          allPrompts={prompts}
          onSave={handleSaveSessionPrompts}
        />
      )}

      {/* Session Details Modal */}
      <SessionDetailsModal
        isOpen={showDetailsModal}
        sessionId={selectedSessionId}
        onClose={() => {
          setShowDetailsModal(false);
          setSelectedSessionId(null);
        }}
      />

      {/* Session Logs Modal */}
      <SessionLogsModal
        isOpen={showLogsModal}
        sessionId={selectedLogsSessionId}
        sessionName={selectedLogsSessionName}
        sessionStatus={selectedLogsSessionStatus}
        onClose={() => {
          setShowLogsModal(false);
          setSelectedLogsSessionId(null);
          setSelectedLogsSessionName(undefined);
          setSelectedLogsSessionStatus(undefined);
        }}
      />

      {/* Hidden file input for import */}
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileChange}
        accept=".json"
        className="hidden"
      />
    </div>
  );
}
