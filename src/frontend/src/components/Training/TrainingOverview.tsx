/**
 * Training Overview - Dashboard-style overview for AI Training
 */

import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  Brain,
  Server,
  Cpu,
  Zap,
  Play,
  CheckCircle,
  FileText,
  TrendingDown,
  TrendingUp,
  Minus,
  AlertCircle,
  Activity,
  Wifi,
  WifiOff,
  ExternalLink,
  ChevronRight,
  Download,
  Settings,
  Upload,
  Loader2,
} from 'lucide-react';
import { api } from '../../lib/api';

// Types
interface Worker {
  id: string;
  name: string;
  url: string;
  status: 'online' | 'offline' | 'busy' | 'error';
  enabled: boolean;
  gpu_available: boolean;
  gpu_names: string[];
  gpu_memory_total_mb: number;
  current_job_id: string | null;
  current_session_id: string | null;
  total_jobs_completed: number;
  last_seen_at: string;
}

interface TrainingStats {
  total_sessions: number;
  active_sessions: number;
  completed_sessions: number;
  failed_sessions: number;
  total_prompts: number;
  validated_prompts: number;
  prompts_by_category: Record<string, number>;
  recent_sessions: RecentSession[];
}

interface TrainingPrompt {
  id: string;
  tags: string[];
}

interface RecentSession {
  id: string;
  name: string;
  status: string;
  base_model: string;
  training_type: string;
  progress_percent: number;
  loss?: number | null;
  started_at?: string | null;
  completed_at?: string | null;
  dataset_size: number;
}

interface OllamaStatus {
  status: string;
  version?: string;
  url: string;
  error?: string;
  models: any[];
  model_count: number;
  total_size_gb: number;
  running_models: any[];
  running_count: number;
}

interface ActiveSessionWithMetrics {
  id: string;
  name: string;
  base_model: string;
  training_type: string;
  status?: string;
  progress_percent: number;
  current_epoch: number;
  total_epochs: number;
  current_step: number;
  total_steps: number;
  loss?: number;
  learning_rate?: number;
  started_at?: string;
  _realtime_metrics?: {
    phase?: string;
    gpu?: {
      gpu_name?: string;
      memory_used_mb?: number;
      memory_total_mb?: number;
      memory_percent?: number;
      utilization_percent?: number;
      temperature_celsius?: number;
      power_watts?: number;
    };
    time?: {
      tokens_per_second?: number;
      step_duration_ms?: number;
    };
    quality?: {
      loss_trend?: string;
      training_health?: string;
      health_message?: string;
    };
    convergence?: {
      best_loss?: number;
    };
  };
}

interface TrainingOverviewProps {
  stats: TrainingStats | null;
  ollamaStatus: OllamaStatus | null;
  activeSessions: ActiveSessionWithMetrics[];
  wsConnected: boolean;
  onViewLogs?: (id: string, name?: string, status?: string) => void;
}

// Stat card component - MCP style (compact)
const StatCard = ({
  title,
  value,
  subtitle,
  color = 'blue',
}: {
  title: string;
  value: string | number;
  subtitle?: string;
  color?: string;
}) => {
  const colorClasses: Record<string, string> = {
    blue: 'text-blue-600 dark:text-blue-400',
    green: 'text-green-600 dark:text-green-400',
    purple: 'text-purple-600 dark:text-purple-400',
    orange: 'text-orange-600 dark:text-orange-400',
    red: 'text-red-600 dark:text-red-400',
    yellow: 'text-yellow-600 dark:text-yellow-400',
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg p-2.5 sm:p-4 shadow">
      <p className="text-xs sm:text-sm text-gray-500 dark:text-gray-400 truncate">{title}</p>
      <p className={`text-lg sm:text-2xl font-bold ${colorClasses[color] || colorClasses.blue}`}>
        {value}
      </p>
      {subtitle && (
        <p className="text-[10px] sm:text-xs text-gray-400 dark:text-gray-500 mt-0.5 sm:mt-1 truncate">{subtitle}</p>
      )}
    </div>
  );
};

// Worker card component
const WorkerCard = ({ worker }: { worker: Worker }) => {
  const statusColors = {
    online: 'bg-green-500',
    offline: 'bg-gray-400',
    busy: 'bg-yellow-500',
    error: 'bg-red-500',
  };

  const statusLabels = {
    online: 'En ligne',
    offline: 'Hors ligne',
    busy: 'Occupe',
    error: 'Erreur',
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl p-4 shadow-sm border border-gray-100 dark:border-gray-700">
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3">
          <div className={`p-2 rounded-lg ${worker.gpu_available ? 'bg-orange-100 dark:bg-orange-900/30' : 'bg-gray-100 dark:bg-gray-700'}`}>
            <Cpu className={`w-5 h-5 ${worker.gpu_available ? 'text-orange-600 dark:text-orange-400' : 'text-gray-500'}`} />
          </div>
          <div>
            <h4 className="font-medium text-gray-900 dark:text-white">{worker.name}</h4>
            <p className="text-xs text-gray-500 dark:text-gray-400">{worker.url}</p>
          </div>
        </div>
        <div className="flex items-center gap-1.5">
          <span className={`w-2 h-2 rounded-full ${statusColors[worker.status]}`} />
          <span className="text-xs text-gray-500 dark:text-gray-400">{statusLabels[worker.status]}</span>
        </div>
      </div>

      {worker.gpu_available && worker.gpu_names.length > 0 && (
        <div className="bg-gray-50 dark:bg-gray-900/50 rounded-lg p-3 mb-3">
          <div className="flex items-center gap-2 mb-2">
            <Zap className="w-4 h-4 text-orange-500" />
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
              {worker.gpu_names[0]}
            </span>
          </div>
          {worker.gpu_memory_total_mb > 0 && (
            <p className="text-xs text-gray-500 dark:text-gray-400">
              {(worker.gpu_memory_total_mb / 1024).toFixed(1)} GB VRAM
            </p>
          )}
        </div>
      )}

      <div className="flex items-center justify-between text-sm">
        <div className="flex items-center gap-1 text-gray-500 dark:text-gray-400">
          <CheckCircle className="w-4 h-4 text-green-500" />
          <span>{worker.total_jobs_completed} jobs</span>
        </div>
        {worker.current_job_id && (
          <span className="text-xs px-2 py-0.5 bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-300 rounded-full">
            En cours
          </span>
        )}
      </div>
    </div>
  );
};

// Service colors for stacked bar
const SERVICE_COLORS: Record<string, { bg: string; text: string }> = {
  homeassistant: { bg: 'bg-cyan-500', text: 'text-cyan-600 dark:text-cyan-400' },
  ollama: { bg: 'bg-purple-500', text: 'text-purple-600 dark:text-purple-400' },
  filesystem: { bg: 'bg-green-500', text: 'text-green-600 dark:text-green-400' },
  docker: { bg: 'bg-blue-500', text: 'text-blue-600 dark:text-blue-400' },
  git: { bg: 'bg-orange-500', text: 'text-orange-600 dark:text-orange-400' },
  memory: { bg: 'bg-pink-500', text: 'text-pink-600 dark:text-pink-400' },
  browser: { bg: 'bg-yellow-500', text: 'text-yellow-600 dark:text-yellow-400' },
  puppeteer: { bg: 'bg-indigo-500', text: 'text-indigo-600 dark:text-indigo-400' },
  plex: { bg: 'bg-amber-500', text: 'text-amber-600 dark:text-amber-400' },
  tautulli: { bg: 'bg-rose-500', text: 'text-rose-600 dark:text-rose-400' },
  overseerr: { bg: 'bg-emerald-500', text: 'text-emerald-600 dark:text-emerald-400' },
  radarr: { bg: 'bg-orange-500', text: 'text-orange-600 dark:text-orange-400' },
  sonarr: { bg: 'bg-sky-500', text: 'text-sky-600 dark:text-sky-400' },
  prowlarr: { bg: 'bg-violet-500', text: 'text-violet-600 dark:text-violet-400' },
  jackett: { bg: 'bg-fuchsia-500', text: 'text-fuchsia-600 dark:text-fuchsia-400' },
  bazarr: { bg: 'bg-lime-500', text: 'text-lime-600 dark:text-lime-400' },
  lidarr: { bg: 'bg-teal-500', text: 'text-teal-600 dark:text-teal-400' },
  zammad: { bg: 'bg-red-500', text: 'text-red-600 dark:text-red-400' },
  authentik: { bg: 'bg-orange-600', text: 'text-orange-700 dark:text-orange-400' },
  proxmox: { bg: 'bg-slate-500', text: 'text-slate-600 dark:text-slate-400' },
  system: { bg: 'bg-gray-500', text: 'text-gray-600 dark:text-gray-400' },
  komga: { bg: 'bg-red-400', text: 'text-red-500 dark:text-red-400' },
  romm: { bg: 'bg-blue-400', text: 'text-blue-500 dark:text-blue-400' },
  deluge: { bg: 'bg-blue-600', text: 'text-blue-700 dark:text-blue-400' },
  openwebui: { bg: 'bg-purple-400', text: 'text-purple-500 dark:text-purple-400' },
};

const DEFAULT_COLORS = [
  { bg: 'bg-blue-500', text: 'text-blue-600 dark:text-blue-400' },
  { bg: 'bg-purple-500', text: 'text-purple-600 dark:text-purple-400' },
  { bg: 'bg-green-500', text: 'text-green-600 dark:text-green-400' },
  { bg: 'bg-orange-500', text: 'text-orange-600 dark:text-orange-400' },
  { bg: 'bg-pink-500', text: 'text-pink-600 dark:text-pink-400' },
  { bg: 'bg-cyan-500', text: 'text-cyan-600 dark:text-cyan-400' },
  { bg: 'bg-yellow-500', text: 'text-yellow-600 dark:text-yellow-400' },
];

const getServiceColor = (serviceName: string, index: number) => {
  const lowerName = serviceName.toLowerCase();
  if (SERVICE_COLORS[lowerName]) {
    return SERVICE_COLORS[lowerName];
  }
  return DEFAULT_COLORS[index % DEFAULT_COLORS.length];
};

// Horizontal stacked bar chart for prompts by service
const ServiceStackedBar = ({ data, total }: { data: Record<string, number>; total: number }) => {
  const sortedServices = Object.entries(data).sort((a, b) => b[1] - a[1]);

  if (sortedServices.length === 0) {
    return (
      <div className="text-center py-4 text-gray-500 dark:text-gray-400 text-sm">
        Aucune donnée
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {/* Stacked Bar */}
      <div className="h-5 rounded-full overflow-hidden flex bg-gray-100 dark:bg-gray-700">
        {sortedServices.map(([serviceName, count], index) => {
          const color = getServiceColor(serviceName, index);
          const percentage = total > 0 ? (count / total) * 100 : 0;

          return (
            <div
              key={serviceName}
              className={`${color.bg} h-full transition-all duration-300 hover:opacity-80`}
              style={{ width: `${percentage}%` }}
              title={`${serviceName}: ${count} (${percentage.toFixed(1)}%)`}
            />
          );
        })}
      </div>

      {/* Legend */}
      <div className="flex flex-wrap gap-x-4 gap-y-1.5">
        {sortedServices.map(([serviceName, count], index) => {
          const color = getServiceColor(serviceName, index);
          const percentage = total > 0 ? (count / total) * 100 : 0;

          return (
            <div key={serviceName} className="flex items-center gap-1.5 text-xs">
              <span className={`w-2.5 h-2.5 rounded-full ${color.bg}`} />
              <span className="text-gray-600 dark:text-gray-400 capitalize">{serviceName}</span>
              <span className="font-medium text-gray-900 dark:text-white">{count}</span>
              <span className="text-gray-400 dark:text-gray-500">({percentage.toFixed(0)}%)</span>
            </div>
          );
        })}
      </div>
    </div>
  );
};

// Sessions history mini chart
const SessionsHistoryChart = ({ sessions }: { sessions: RecentSession[] }) => {
  if (!sessions || sessions.length === 0) return null;

  const maxLoss = Math.max(...sessions.filter(s => s.loss != null).map(s => s.loss!), 2);

  return (
    <div className="flex items-end gap-1 h-16">
      {sessions.slice(0, 10).reverse().map((session) => {
        const height = session.loss != null ? Math.max((session.loss / maxLoss) * 100, 10) : 10;
        const color = session.status === 'completed' ? 'bg-green-500' :
                      session.status === 'failed' ? 'bg-red-500' : 'bg-yellow-500';
        return (
          <div
            key={session.id}
            className="flex-1 flex flex-col items-center justify-end"
            title={`${session.name}: Loss ${session.loss?.toFixed(4) || 'N/A'}`}
          >
            <div
              className={`w-full ${color} rounded-t-sm transition-all hover:opacity-80`}
              style={{ height: `${height}%` }}
            />
          </div>
        );
      })}
    </div>
  );
};

// Pipeline steps configuration
const PIPELINE_STEPS = [
  { id: 'preparing', label: 'Preparation', icon: Settings },
  { id: 'downloading', label: 'Pull Model', icon: Download },
  { id: 'training', label: 'Training', icon: Brain },
  { id: 'exporting', label: 'Export GGUF', icon: FileText },
  { id: 'importing', label: 'Import Ollama', icon: Upload },
  { id: 'completed', label: 'Termine', icon: CheckCircle },
];

// Pipeline steps component
const PipelineSteps = ({ currentPhase }: { currentPhase?: string }) => {
  const getStepStatus = (stepId: string): 'completed' | 'active' | 'pending' => {
    if (!currentPhase) return 'pending';

    const currentIndex = PIPELINE_STEPS.findIndex(s => s.id === currentPhase);
    const stepIndex = PIPELINE_STEPS.findIndex(s => s.id === stepId);

    if (currentPhase === 'completed' || currentPhase === 'failed') {
      // All steps completed (or failed)
      return currentPhase === 'completed' ? 'completed' : (stepIndex < currentIndex ? 'completed' : 'pending');
    }

    if (stepIndex < currentIndex) return 'completed';
    if (stepIndex === currentIndex) return 'active';
    return 'pending';
  };

  return (
    <div className="flex items-center justify-between gap-1 mb-4">
      {PIPELINE_STEPS.map((step, index) => {
        const status = getStepStatus(step.id);
        const Icon = step.icon;
        const isLast = index === PIPELINE_STEPS.length - 1;

        return (
          <div key={step.id} className="flex items-center flex-1">
            <div className="flex flex-col items-center">
              <div className={`
                w-8 h-8 rounded-full flex items-center justify-center transition-all
                ${status === 'completed' ? 'bg-green-500 text-white' : ''}
                ${status === 'active' ? 'bg-purple-500 text-white ring-2 ring-purple-300 dark:ring-purple-700' : ''}
                ${status === 'pending' ? 'bg-gray-200 dark:bg-gray-700 text-gray-400 dark:text-gray-500' : ''}
              `}>
                {status === 'active' ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : status === 'completed' ? (
                  <CheckCircle className="w-4 h-4" />
                ) : (
                  <Icon className="w-4 h-4" />
                )}
              </div>
              <span className={`
                text-[10px] mt-1 text-center leading-tight whitespace-nowrap
                ${status === 'active' ? 'text-purple-600 dark:text-purple-400 font-medium' : ''}
                ${status === 'completed' ? 'text-green-600 dark:text-green-400' : ''}
                ${status === 'pending' ? 'text-gray-400 dark:text-gray-500' : ''}
              `}>
                {step.label}
              </span>
            </div>
            {!isLast && (
              <div className={`
                flex-1 h-0.5 mx-1 mb-4 transition-all
                ${status === 'completed' ? 'bg-green-500' : 'bg-gray-200 dark:bg-gray-700'}
              `} />
            )}
          </div>
        );
      })}
    </div>
  );
};

// Loss trend indicator component
const LossTrendIndicator = ({ trend }: { trend?: string }) => {
  if (!trend) return null;

  const getTrendInfo = (trend: string) => {
    switch (trend) {
      case 'decreasing':
      case 'decreasing_fast':
        return { icon: TrendingDown, color: 'text-green-400', label: 'En baisse' };
      case 'increasing':
      case 'increasing_fast':
        return { icon: TrendingUp, color: 'text-red-400', label: 'En hausse' };
      case 'stable':
      case 'plateauing':
        return { icon: Minus, color: 'text-yellow-400', label: 'Stable' };
      default:
        return { icon: Minus, color: 'text-gray-400', label: '-' };
    }
  };

  const { icon: Icon, color, label } = getTrendInfo(trend);

  return (
    <div className={`flex items-center gap-1 ${color}`}>
      <Icon className="w-4 h-4" />
      <span className="text-xs">{label}</span>
    </div>
  );
};

// Active training card
const ActiveTrainingCard = ({ session, onViewLogs }: { session: ActiveSessionWithMetrics; onViewLogs?: (id: string, name?: string, status?: string) => void }) => {
  const formatDuration = (startedAt: string | undefined) => {
    if (!startedAt) return '-';
    const start = new Date(startedAt);
    const now = new Date();
    const diffMs = now.getTime() - start.getTime();
    const hours = Math.floor(diffMs / (1000 * 60 * 60));
    const minutes = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));
    const seconds = Math.floor((diffMs % (1000 * 60)) / 1000);
    if (hours > 0) return `${hours}h ${minutes}m`;
    if (minutes > 0) return `${minutes}m ${seconds}s`;
    return `${seconds}s`;
  };

  const getLossColor = (loss: number | undefined) => {
    if (loss === undefined) return 'text-gray-500';
    if (loss < 0.5) return 'text-green-500';
    if (loss < 1.0) return 'text-yellow-500';
    if (loss < 2.0) return 'text-orange-500';
    return 'text-red-500';
  };

  const lossTrend = session._realtime_metrics?.quality?.loss_trend;

  // Health color for dark mode compatible display
  const getHealthColorDark = (health: string | undefined) => {
    switch (health) {
      case 'excellent': return 'text-green-500';
      case 'good': return 'text-blue-500';
      case 'warning': return 'text-yellow-500';
      case 'critical': return 'text-red-500';
      default: return 'text-gray-500';
    }
  };

  const currentPhase = session._realtime_metrics?.phase;

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl p-5 shadow-sm border border-gray-100 dark:border-gray-700">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <div>
            <h4 className="font-semibold text-lg text-gray-900 dark:text-white">{session.name}</h4>
            <p className="text-sm text-gray-500 dark:text-gray-400">{session.base_model}</p>
          </div>
          {onViewLogs && (
            <button
              onClick={() => onViewLogs(session.id, session.name, session.status)}
              className="p-1.5 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors"
              title="Voir les logs en direct"
            >
              <FileText className="w-4 h-4" />
            </button>
          )}
        </div>
        <div className="text-right">
          <p className="text-3xl font-bold text-purple-600 dark:text-purple-400">{session.progress_percent.toFixed(1)}%</p>
          <p className="text-xs text-gray-500 dark:text-gray-400">{formatDuration(session.started_at)}</p>
        </div>
      </div>

      {/* Pipeline Steps */}
      <PipelineSteps currentPhase={currentPhase} />

      {/* Progress bar */}
      <div className="mb-4">
        <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
          <div
            className="bg-purple-500 h-2 rounded-full transition-all"
            style={{ width: `${Math.min(session.progress_percent, 100)}%` }}
          />
        </div>
        <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400 mt-1">
          <span>Epoch {session.current_epoch}/{session.total_epochs}</span>
          <span>Step {session.current_step}/{session.total_steps}</span>
        </div>
      </div>

      {/* Metrics grid */}
      <div className="grid grid-cols-4 gap-3">
        <div className="bg-gray-50 dark:bg-gray-900/50 rounded-lg p-2 text-center">
          <div className="flex items-center justify-center gap-1">
            <p className="text-xs text-gray-500 dark:text-gray-400">Loss</p>
            <LossTrendIndicator trend={lossTrend} />
          </div>
          <p className={`text-lg font-bold ${session.loss !== undefined ? getLossColor(session.loss) : 'text-gray-900 dark:text-white'}`}>
            {session.loss?.toFixed(4) || '-'}
          </p>
        </div>
        <div className="bg-gray-50 dark:bg-gray-900/50 rounded-lg p-2 text-center">
          <p className="text-xs text-gray-500 dark:text-gray-400">LR</p>
          <p className="text-lg font-bold text-gray-900 dark:text-white">
            {session.learning_rate ? session.learning_rate.toExponential(1) : '-'}
          </p>
        </div>
        <div className="bg-gray-50 dark:bg-gray-900/50 rounded-lg p-2 text-center">
          <p className="text-xs text-gray-500 dark:text-gray-400">Vitesse</p>
          <p className="text-lg font-bold text-gray-900 dark:text-white">
            {session._realtime_metrics?.time?.tokens_per_second?.toFixed(0) || '-'} tok/s
          </p>
        </div>
        <div className="bg-gray-50 dark:bg-gray-900/50 rounded-lg p-2 text-center">
          <p className="text-xs text-gray-500 dark:text-gray-400">Sante</p>
          <p className={`text-lg font-bold capitalize ${getHealthColorDark(session._realtime_metrics?.quality?.training_health)}`}>
            {session._realtime_metrics?.quality?.training_health || '-'}
          </p>
        </div>
      </div>

      {/* GPU metrics - Always show */}
      <div className="mt-3 bg-gray-50 dark:bg-gray-900/50 rounded-lg p-3">
        <div className="flex items-center gap-2 mb-2">
          <Zap className="w-4 h-4 text-orange-500" />
          <span className="text-sm text-gray-700 dark:text-gray-300">
            {session._realtime_metrics?.gpu?.gpu_name || 'GPU'}
          </span>
        </div>
        <div className="grid grid-cols-4 gap-3 text-sm">
          <div>
            <p className="text-xs text-gray-500 dark:text-gray-400">Utilisation</p>
            <p className="font-medium text-gray-900 dark:text-white">
              {session._realtime_metrics?.gpu?.utilization_percent?.toFixed(0) ?? '-'}%
            </p>
          </div>
          <div>
            <p className="text-xs text-gray-500 dark:text-gray-400">VRAM</p>
            <p className="font-medium text-gray-900 dark:text-white">
              {session._realtime_metrics?.gpu?.memory_percent?.toFixed(0) ?? '-'}%
            </p>
          </div>
          <div>
            <p className="text-xs text-gray-500 dark:text-gray-400">Temp</p>
            <p className={`font-medium ${
              (session._realtime_metrics?.gpu?.temperature_celsius ?? 0) > 80 ? 'text-red-500' :
              (session._realtime_metrics?.gpu?.temperature_celsius ?? 0) > 70 ? 'text-yellow-500' : 'text-gray-900 dark:text-white'
            }`}>
              {session._realtime_metrics?.gpu?.temperature_celsius ?? '-'}°C
            </p>
          </div>
          <div>
            <p className="text-xs text-gray-500 dark:text-gray-400">Power</p>
            <p className="font-medium text-gray-900 dark:text-white">
              {session._realtime_metrics?.gpu?.power_watts?.toFixed(0) ?? '-'}W
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

// Main component
export default function TrainingOverview({
  stats,
  ollamaStatus,
  activeSessions,
  wsConnected,
  onViewLogs,
}: TrainingOverviewProps) {
  const [workers, setWorkers] = useState<Worker[]>([]);
  const [loadingWorkers, setLoadingWorkers] = useState(true);
  const [promptsByService, setPromptsByService] = useState<Record<string, number>>({});
  const [loadingPrompts, setLoadingPrompts] = useState(true);

  useEffect(() => {
    const fetchWorkers = async () => {
      try {
        const res = await api.workers.list();
        setWorkers(res || []);
      } catch (error) {
        console.error('Failed to fetch workers:', error);
      } finally {
        setLoadingWorkers(false);
      }
    };
    fetchWorkers();
  }, []);

  // Fetch prompts to calculate service distribution
  useEffect(() => {
    const fetchPrompts = async () => {
      try {
        const res = await api.training.prompts.list();
        // API returns array directly, not {prompts: [...]}
        const prompts = Array.isArray(res) ? res : (res?.prompts || []);

        // Known service names to filter tags
        const serviceNames = [
          'prowlarr', 'radarr', 'sonarr', 'lidarr', 'readarr', 'bazarr',
          'tautulli', 'overseerr', 'ombi', 'plex', 'jellyfin', 'emby',
          'komga', 'zammad', 'system', 'ollama', 'homeassistant', 'unifi',
          'proxmox', 'portainer', 'docker', 'traefik', 'nginx'
        ];

        // Count prompts by service tags (only count known services)
        const serviceCount: Record<string, number> = {};
        prompts.forEach((prompt: TrainingPrompt) => {
          if (prompt.tags && Array.isArray(prompt.tags)) {
            // Find the first tag that matches a known service
            const serviceTags = prompt.tags.filter((tag: string) =>
              serviceNames.includes(tag.toLowerCase())
            );
            // Count each service tag found
            serviceTags.forEach((tag: string) => {
              const normalizedTag = tag.toLowerCase();
              serviceCount[normalizedTag] = (serviceCount[normalizedTag] || 0) + 1;
            });
          }
        });

        setPromptsByService(serviceCount);
      } catch (error) {
        console.error('Failed to fetch prompts:', error);
      } finally {
        setLoadingPrompts(false);
      }
    };
    fetchPrompts();
  }, []);

  const successRate = stats?.total_sessions
    ? ((stats.completed_sessions / stats.total_sessions) * 100).toFixed(0)
    : '0';

  return (
    <div className="space-y-6">
      {/* Active Training Sessions */}
      {activeSessions.length > 0 && (
        <div>
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
              <Play className="w-5 h-5 text-green-500 animate-pulse" />
              Entrainement en cours
            </h3>
            <span className={`flex items-center gap-1 text-xs px-2 py-1 rounded-full ${
              wsConnected ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300' :
                           'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300'
            }`}>
              {wsConnected ? <Wifi className="w-3 h-3" /> : <WifiOff className="w-3 h-3" />}
              {wsConnected ? 'Live' : 'Offline'}
            </span>
          </div>
          <div className="space-y-4">
            {activeSessions.map((session) => (
              <ActiveTrainingCard key={session.id} session={session} onViewLogs={onViewLogs} />
            ))}
          </div>
        </div>
      )}

      {/* Stats Row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Sessions"
          value={stats?.total_sessions || 0}
          subtitle={`${stats?.active_sessions || 0} actives`}
          color="blue"
        />
        <StatCard
          title="Prompts"
          value={stats?.total_prompts || 0}
          subtitle={`${stats?.validated_prompts || 0} valides`}
          color="purple"
        />
        <StatCard
          title="Taux de succes"
          value={`${successRate}%`}
          subtitle={`${stats?.completed_sessions || 0} completees`}
          color={stats?.failed_sessions && stats.failed_sessions > 0 ? 'orange' : 'green'}
        />
        <StatCard
          title="Workers"
          value={workers.filter(w => w.status === 'online').length}
          subtitle={`${workers.length} configures`}
          color="orange"
        />
      </div>

      {/* Workers and Ollama Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Workers */}
        <div className="bg-white dark:bg-gray-800 rounded-xl p-5 shadow-sm border border-gray-100 dark:border-gray-700">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-gray-900 dark:text-white flex items-center gap-2">
              <Server className="w-5 h-5 text-orange-500" />
              Training Workers
            </h3>
            <Link
              to="/training?tab=workers"
              className="text-sm text-blue-600 dark:text-blue-400 hover:underline flex items-center gap-1"
            >
              Gerer <ChevronRight className="w-4 h-4" />
            </Link>
          </div>
          {loadingWorkers ? (
            <div className="space-y-3">
              {[1, 2].map(i => (
                <div key={i} className="h-24 bg-gray-100 dark:bg-gray-700 rounded-lg animate-pulse" />
              ))}
            </div>
          ) : workers.length > 0 ? (
            <div className="space-y-3">
              {workers.slice(0, 3).map((worker) => (
                <WorkerCard key={worker.id} worker={worker} />
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-gray-500 dark:text-gray-400">
              <Server className="w-10 h-10 mx-auto mb-2 opacity-50" />
              <p>Aucun worker configure</p>
              <Link to="/training?tab=workers" className="text-sm text-blue-600 dark:text-blue-400 hover:underline mt-2 inline-block">
                Ajouter un worker
              </Link>
            </div>
          )}
        </div>

        {/* Ollama Status */}
        <div className="bg-white dark:bg-gray-800 rounded-xl p-5 shadow-sm border border-gray-100 dark:border-gray-700">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-gray-900 dark:text-white flex items-center gap-2">
              <Brain className="w-5 h-5 text-purple-500" />
              Ollama Server
            </h3>
            <span className={`px-2 py-1 text-xs rounded-full ${
              ollamaStatus?.status === 'healthy'
                ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300'
                : ollamaStatus?.status === 'not_configured'
                ? 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-300'
                : 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300'
            }`}>
              {ollamaStatus?.status === 'healthy' ? 'Connecte' :
               ollamaStatus?.status === 'not_configured' ? 'Non configure' : 'Erreur'}
            </span>
          </div>

          {ollamaStatus?.status === 'healthy' ? (
            <div className="space-y-4">
              <div className="grid grid-cols-3 gap-3">
                <div className="bg-gray-50 dark:bg-gray-900/50 rounded-lg p-3 text-center">
                  <p className="text-2xl font-bold text-gray-900 dark:text-white">{ollamaStatus.model_count}</p>
                  <p className="text-xs text-gray-500 dark:text-gray-400">Modeles</p>
                </div>
                <div className="bg-gray-50 dark:bg-gray-900/50 rounded-lg p-3 text-center">
                  <p className="text-2xl font-bold text-gray-900 dark:text-white">{ollamaStatus.total_size_gb.toFixed(1)}</p>
                  <p className="text-xs text-gray-500 dark:text-gray-400">GB Total</p>
                </div>
                <div className="bg-gray-50 dark:bg-gray-900/50 rounded-lg p-3 text-center">
                  <p className="text-2xl font-bold text-gray-900 dark:text-white">{ollamaStatus.running_count}</p>
                  <p className="text-xs text-gray-500 dark:text-gray-400">Actifs</p>
                </div>
              </div>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                Version: {ollamaStatus.version} - {ollamaStatus.url}
              </p>
            </div>
          ) : ollamaStatus?.status === 'not_configured' ? (
            <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4">
              <div className="flex items-start gap-3">
                <AlertCircle className="w-5 h-5 text-yellow-600 dark:text-yellow-400 flex-shrink-0" />
                <div>
                  <p className="text-sm text-yellow-800 dark:text-yellow-200">Ollama non configure</p>
                  <Link
                    to="/services"
                    className="inline-flex items-center gap-1 mt-2 text-sm text-yellow-700 dark:text-yellow-300 hover:underline"
                  >
                    Configurer <ExternalLink className="w-3 h-3" />
                  </Link>
                </div>
              </div>
            </div>
          ) : (
            <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
              <p className="text-sm text-red-800 dark:text-red-200">
                {ollamaStatus?.error || 'Connexion echouee'}
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Prompts and Sessions Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Prompts by Service */}
        <div className="bg-white dark:bg-gray-800 rounded-xl p-5 shadow-sm border border-gray-100 dark:border-gray-700">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-gray-900 dark:text-white flex items-center gap-2">
              <FileText className="w-5 h-5 text-purple-500" />
              Prompts par service
            </h3>
            <Link
              to="/training?tab=prompts"
              className="text-sm text-blue-600 dark:text-blue-400 hover:underline flex items-center gap-1"
            >
              Voir tout <ChevronRight className="w-4 h-4" />
            </Link>
          </div>
          {loadingPrompts ? (
            <div className="space-y-3">
              {[1, 2, 3].map(i => (
                <div key={i} className="h-8 bg-gray-100 dark:bg-gray-700 rounded animate-pulse" />
              ))}
            </div>
          ) : Object.keys(promptsByService).length > 0 ? (
            <ServiceStackedBar data={promptsByService} total={Object.values(promptsByService).reduce((a, b) => a + b, 0)} />
          ) : (
            <div className="text-center py-8 text-gray-500 dark:text-gray-400">
              <FileText className="w-10 h-10 mx-auto mb-2 opacity-50" />
              <p>Aucun prompt</p>
            </div>
          )}
        </div>

        {/* Recent Sessions */}
        <div className="bg-white dark:bg-gray-800 rounded-xl p-5 shadow-sm border border-gray-100 dark:border-gray-700">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-gray-900 dark:text-white flex items-center gap-2">
              <Activity className="w-5 h-5 text-blue-500" />
              Sessions recentes
            </h3>
            <Link
              to="/training?tab=sessions"
              className="text-sm text-blue-600 dark:text-blue-400 hover:underline flex items-center gap-1"
            >
              Voir tout <ChevronRight className="w-4 h-4" />
            </Link>
          </div>

          {stats?.recent_sessions && stats.recent_sessions.length > 0 ? (
            <div className="space-y-4">
              {/* Mini chart */}
              <div className="bg-gray-50 dark:bg-gray-900/50 rounded-lg p-3">
                <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">Evolution du Loss (10 dernieres)</p>
                <SessionsHistoryChart sessions={stats.recent_sessions} />
              </div>

              {/* List */}
              <div className="space-y-2">
                {stats.recent_sessions.slice(0, 4).map((session) => (
                  <div
                    key={session.id}
                    className="flex items-center justify-between p-2 bg-gray-50 dark:bg-gray-900/50 rounded-lg"
                  >
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-sm text-gray-900 dark:text-white truncate">
                        {session.name}
                      </p>
                      <p className="text-xs text-gray-500 dark:text-gray-400">
                        {session.dataset_size} prompts - Loss: {session.loss?.toFixed(4) || 'N/A'}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      {['completed', 'failed', 'cancelled'].includes(session.status) && onViewLogs && (
                        <button
                          onClick={() => onViewLogs(session.id, session.name, session.status)}
                          className="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
                          title="Voir les logs"
                        >
                          <FileText className="w-4 h-4" />
                        </button>
                      )}
                      <span className={`px-2 py-0.5 text-xs rounded-full ${
                        session.status === 'completed'
                          ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300'
                          : session.status === 'failed'
                          ? 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300'
                          : 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-300'
                      }`}>
                        {session.status}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="text-center py-8 text-gray-500 dark:text-gray-400">
              <Activity className="w-10 h-10 mx-auto mb-2 opacity-50" />
              <p>Aucune session</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
