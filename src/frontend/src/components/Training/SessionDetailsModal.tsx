/**
 * Session Details Modal - Displays comprehensive training session summary
 */

import { useState, useEffect } from 'react';
import { apiClient } from '../../lib/api';

interface LossDataPoint {
  step: number;
  loss: number;
}

interface SessionSummary {
  session_id: string;
  name: string;
  status: string;
  base_model: string;
  output_model: string | null;
  training_backend: string;
  started_at: string | null;
  completed_at: string | null;
  duration_seconds: number | null;
  duration_formatted: string;
  total_epochs: number;
  total_steps: number;
  final_step: number;
  progress_percent: number;
  dataset_size: number;
  final_loss: number | null;
  final_learning_rate: number | null;
  error_message: string | null;
  prompts_count: number;
  prompts: Array<{ id: string; name: string; category: string }>;
  hyperparameters: Record<string, unknown>;
  metrics_analysis: {
    total_metrics_points?: number;
    initial_loss?: number;
    final_loss?: number;
    min_loss?: number;
    max_loss?: number;
    avg_loss?: number;
    loss_improvement?: number;
    loss_improvement_percent?: number;
    trend?: string;
  };
  assessment: {
    health: string;
    message: string;
    icon: string;
  };
  loss_history?: LossDataPoint[];
}

interface SessionDetailsModalProps {
  sessionId: string | null;
  isOpen: boolean;
  onClose: () => void;
}

// Status badge colors
function getStatusColor(status: string): string {
  switch (status) {
    case 'completed':
      return 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400';
    case 'failed':
      return 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400';
    case 'running':
    case 'preparing':
      return 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400';
    case 'cancelled':
      return 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300';
    case 'pending':
      return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400';
    default:
      return 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300';
  }
}

// Health indicator colors
function getHealthColor(health: string): string {
  switch (health) {
    case 'excellent':
      return 'text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-900/20';
    case 'good':
      return 'text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/20';
    case 'warning':
      return 'text-yellow-600 dark:text-yellow-400 bg-yellow-50 dark:bg-yellow-900/20';
    case 'critical':
      return 'text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20';
    default:
      return 'text-gray-600 dark:text-gray-400 bg-gray-50 dark:bg-gray-800';
  }
}

function formatDate(isoString: string | null): string {
  if (!isoString) return '-';
  const date = new Date(isoString);
  return date.toLocaleString('fr-FR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function formatNumber(num: number | null | undefined, decimals: number = 4): string {
  if (num === null || num === undefined) return '-';
  return num.toFixed(decimals);
}

// Simple SVG Line Chart for Loss Evolution
function LossChart({ data }: { data: LossDataPoint[] }) {
  if (!data || data.length < 2) {
    return (
      <div className="flex items-center justify-center h-32 text-gray-400 dark:text-gray-500 text-sm">
        Pas assez de donnees pour afficher le graphique
      </div>
    );
  }

  const width = 400;
  const height = 120;
  const padding = { top: 10, right: 10, bottom: 25, left: 45 };
  const chartWidth = width - padding.left - padding.right;
  const chartHeight = height - padding.top - padding.bottom;

  // Get min/max values
  const losses = data.map(d => d.loss);
  const steps = data.map(d => d.step);
  const minLoss = Math.min(...losses);
  const maxLoss = Math.max(...losses);
  const minStep = Math.min(...steps);
  const maxStep = Math.max(...steps);

  // Add padding to Y axis
  const yPadding = (maxLoss - minLoss) * 0.1 || 0.1;
  const yMin = Math.max(0, minLoss - yPadding);
  const yMax = maxLoss + yPadding;

  // Scale functions
  const xScale = (step: number) =>
    padding.left + ((step - minStep) / (maxStep - minStep || 1)) * chartWidth;
  const yScale = (loss: number) =>
    padding.top + chartHeight - ((loss - yMin) / (yMax - yMin || 1)) * chartHeight;

  // Create path for the line
  const pathData = data
    .map((d, i) => `${i === 0 ? 'M' : 'L'} ${xScale(d.step)} ${yScale(d.loss)}`)
    .join(' ');

  // Y-axis labels (3 ticks)
  const yTicks = [yMin, (yMin + yMax) / 2, yMax];

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-auto">
      {/* Grid lines */}
      {yTicks.map((tick, i) => (
        <line
          key={i}
          x1={padding.left}
          y1={yScale(tick)}
          x2={width - padding.right}
          y2={yScale(tick)}
          stroke="currentColor"
          strokeOpacity={0.1}
          strokeDasharray="2,2"
        />
      ))}

      {/* Y-axis labels */}
      {yTicks.map((tick, i) => (
        <text
          key={i}
          x={padding.left - 5}
          y={yScale(tick)}
          textAnchor="end"
          dominantBaseline="middle"
          className="fill-gray-500 dark:fill-gray-400"
          fontSize="9"
        >
          {tick.toFixed(2)}
        </text>
      ))}

      {/* X-axis labels */}
      <text
        x={padding.left}
        y={height - 5}
        textAnchor="start"
        className="fill-gray-500 dark:fill-gray-400"
        fontSize="9"
      >
        {minStep}
      </text>
      <text
        x={width - padding.right}
        y={height - 5}
        textAnchor="end"
        className="fill-gray-500 dark:fill-gray-400"
        fontSize="9"
      >
        {maxStep}
      </text>
      <text
        x={width / 2}
        y={height - 5}
        textAnchor="middle"
        className="fill-gray-400 dark:fill-gray-500"
        fontSize="9"
      >
        Steps
      </text>

      {/* Line chart */}
      <path
        d={pathData}
        fill="none"
        stroke="url(#lossGradient)"
        strokeWidth={2}
        strokeLinecap="round"
        strokeLinejoin="round"
      />

      {/* Gradient definition */}
      <defs>
        <linearGradient id="lossGradient" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stopColor="#ef4444" />
          <stop offset="100%" stopColor="#22c55e" />
        </linearGradient>
      </defs>

      {/* Start and end points */}
      <circle
        cx={xScale(data[0].step)}
        cy={yScale(data[0].loss)}
        r={3}
        className="fill-red-500"
      />
      <circle
        cx={xScale(data[data.length - 1].step)}
        cy={yScale(data[data.length - 1].loss)}
        r={3}
        className="fill-green-500"
      />
    </svg>
  );
}

export default function SessionDetailsModal({
  sessionId,
  isOpen,
  onClose,
}: SessionDetailsModalProps) {
  const [summary, setSummary] = useState<SessionSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen || !sessionId) return;

    const fetchData = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await apiClient.get<SessionSummary>(`/api/training/sessions/${sessionId}/summary`);
        setSummary(data);
      } catch (err: unknown) {
        setError((err as Error).message || 'Failed to load session details');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [isOpen, sessionId]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/50 transition-opacity"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="flex min-h-full items-center justify-center p-4">
        <div className="relative bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-3xl w-full max-h-[90vh] overflow-hidden">
          {/* Header */}
          <div className="flex items-center justify-between px-6 py-4 border-b dark:border-gray-700">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
              Details de la session
            </h2>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* Content */}
          <div className="px-6 py-4 overflow-y-auto max-h-[calc(90vh-120px)]">
            {loading && (
              <div className="flex items-center justify-center py-12">
                <div className="animate-spin rounded-full h-8 w-8 border-2 border-blue-500 border-t-transparent"></div>
              </div>
            )}

            {error && (
              <div className="bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 p-4 rounded-lg">
                {error}
              </div>
            )}

            {summary && !loading && (
              <div className="space-y-6">
                {/* Assessment Banner */}
                <div className={`p-4 rounded-lg ${getHealthColor(summary.assessment.health)}`}>
                  <div className="flex items-center gap-3">
                    <span className="text-2xl">{summary.assessment.icon}</span>
                    <div>
                      <p className="font-medium">{summary.assessment.message}</p>
                    </div>
                  </div>
                </div>

                {/* Basic Info */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">
                      Nom
                    </h3>
                    <p className="text-gray-900 dark:text-white font-medium">{summary.name}</p>
                  </div>
                  <div>
                    <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">
                      Status
                    </h3>
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(summary.status)}`}>
                      {summary.status}
                    </span>
                  </div>
                  <div>
                    <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">
                      Modele de base
                    </h3>
                    <p className="text-gray-900 dark:text-white text-sm font-mono">
                      {summary.base_model}
                    </p>
                  </div>
                  <div>
                    <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">
                      Modele de sortie
                    </h3>
                    <p className="text-gray-900 dark:text-white text-sm font-mono">
                      {summary.output_model || '-'}
                    </p>
                  </div>
                </div>

                {/* Timing */}
                <div className="bg-gray-50 dark:bg-gray-900/50 rounded-lg p-4">
                  <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">
                    Timing
                  </h3>
                  <div className="grid grid-cols-3 gap-4 text-sm">
                    <div>
                      <p className="text-gray-500 dark:text-gray-400">Debut</p>
                      <p className="text-gray-900 dark:text-white font-medium">
                        {formatDate(summary.started_at)}
                      </p>
                    </div>
                    <div>
                      <p className="text-gray-500 dark:text-gray-400">Fin</p>
                      <p className="text-gray-900 dark:text-white font-medium">
                        {formatDate(summary.completed_at)}
                      </p>
                    </div>
                    <div>
                      <p className="text-gray-500 dark:text-gray-400">Duree</p>
                      <p className="text-gray-900 dark:text-white font-medium">
                        {summary.duration_formatted}
                      </p>
                    </div>
                  </div>
                </div>

                {/* Progress */}
                <div className="bg-gray-50 dark:bg-gray-900/50 rounded-lg p-4">
                  <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">
                    Progression
                  </h3>
                  <div className="grid grid-cols-4 gap-4 text-sm">
                    <div>
                      <p className="text-gray-500 dark:text-gray-400">Epochs</p>
                      <p className="text-gray-900 dark:text-white font-medium">
                        {summary.total_epochs}
                      </p>
                    </div>
                    <div>
                      <p className="text-gray-500 dark:text-gray-400">Steps</p>
                      <p className="text-gray-900 dark:text-white font-medium">
                        {summary.final_step} / {summary.total_steps}
                      </p>
                    </div>
                    <div>
                      <p className="text-gray-500 dark:text-gray-400">Progres</p>
                      <p className="text-gray-900 dark:text-white font-medium">
                        {summary.progress_percent.toFixed(1)}%
                      </p>
                    </div>
                    <div>
                      <p className="text-gray-500 dark:text-gray-400">Prompts</p>
                      <p className="text-gray-900 dark:text-white font-medium">
                        {summary.prompts_count}
                      </p>
                    </div>
                  </div>
                </div>

                {/* Metrics */}
                {summary.metrics_analysis && Object.keys(summary.metrics_analysis).length > 0 && (
                  <div className="bg-gray-50 dark:bg-gray-900/50 rounded-lg p-4">
                    <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">
                      Metriques
                    </h3>
                    <div className="grid grid-cols-3 gap-4 text-sm">
                      <div>
                        <p className="text-gray-500 dark:text-gray-400">Loss initial</p>
                        <p className="text-gray-900 dark:text-white font-mono">
                          {formatNumber(summary.metrics_analysis.initial_loss)}
                        </p>
                      </div>
                      <div>
                        <p className="text-gray-500 dark:text-gray-400">Loss final</p>
                        <p className="text-gray-900 dark:text-white font-mono">
                          {formatNumber(summary.metrics_analysis.final_loss)}
                        </p>
                      </div>
                      <div>
                        <p className="text-gray-500 dark:text-gray-400">Amelioration</p>
                        <p className={`font-mono font-medium ${
                          (summary.metrics_analysis.loss_improvement_percent || 0) > 0
                            ? 'text-green-600 dark:text-green-400'
                            : (summary.metrics_analysis.loss_improvement_percent || 0) < 0
                            ? 'text-red-600 dark:text-red-400'
                            : 'text-gray-900 dark:text-white'
                        }`}>
                          {summary.metrics_analysis.loss_improvement_percent !== undefined
                            ? `${summary.metrics_analysis.loss_improvement_percent > 0 ? '+' : ''}${summary.metrics_analysis.loss_improvement_percent.toFixed(1)}%`
                            : '-'}
                        </p>
                      </div>
                      <div>
                        <p className="text-gray-500 dark:text-gray-400">Loss min</p>
                        <p className="text-gray-900 dark:text-white font-mono">
                          {formatNumber(summary.metrics_analysis.min_loss)}
                        </p>
                      </div>
                      <div>
                        <p className="text-gray-500 dark:text-gray-400">Loss max</p>
                        <p className="text-gray-900 dark:text-white font-mono">
                          {formatNumber(summary.metrics_analysis.max_loss)}
                        </p>
                      </div>
                      <div>
                        <p className="text-gray-500 dark:text-gray-400">Tendance</p>
                        <p className={`font-medium ${
                          summary.metrics_analysis.trend === 'decreasing'
                            ? 'text-green-600 dark:text-green-400'
                            : summary.metrics_analysis.trend === 'increasing'
                            ? 'text-red-600 dark:text-red-400'
                            : 'text-gray-900 dark:text-white'
                        }`}>
                          {summary.metrics_analysis.trend === 'decreasing' && 'En baisse'}
                          {summary.metrics_analysis.trend === 'increasing' && 'En hausse'}
                          {summary.metrics_analysis.trend === 'stable' && 'Stable'}
                          {!summary.metrics_analysis.trend && '-'}
                        </p>
                      </div>
                    </div>
                  </div>
                )}

                {/* Loss Evolution Chart */}
                {summary.loss_history && summary.loss_history.length > 0 && (
                  <div className="bg-gray-50 dark:bg-gray-900/50 rounded-lg p-4">
                    <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">
                      Evolution du Loss
                    </h3>
                    <LossChart data={summary.loss_history} />
                  </div>
                )}

                {/* Error Message */}
                {summary.error_message && (
                  <div className="bg-red-50 dark:bg-red-900/20 rounded-lg p-4">
                    <h3 className="text-sm font-semibold text-red-700 dark:text-red-400 mb-2">
                      Erreur
                    </h3>
                    <p className="text-red-600 dark:text-red-300 text-sm font-mono whitespace-pre-wrap">
                      {summary.error_message}
                    </p>
                  </div>
                )}

                {/* Hyperparameters */}
                {summary.hyperparameters && Object.keys(summary.hyperparameters).length > 0 && (
                  <div className="bg-gray-50 dark:bg-gray-900/50 rounded-lg p-4">
                    <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">
                      Hyperparametres
                    </h3>
                    <div className="grid grid-cols-2 gap-2 text-sm">
                      {Object.entries(summary.hyperparameters).map(([key, value]) => (
                        <div key={key} className="flex justify-between">
                          <span className="text-gray-500 dark:text-gray-400">{key}</span>
                          <span className="text-gray-900 dark:text-white font-mono">
                            {typeof value === 'number' ? value.toFixed(6).replace(/\.?0+$/, '') : String(value)}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="flex justify-end px-6 py-4 border-t dark:border-gray-700">
            <button
              onClick={onClose}
              className="px-4 py-2 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
            >
              Fermer
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
