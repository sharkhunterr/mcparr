/**
 * Training Metrics Panel - Displays comprehensive training metrics with visual indicators.
 */

import {
  type TrainingMetrics,
  type LossTrend,
  type TrainingHealth,
  type OverfittingRisk,
} from '../../hooks/useTrainingWebSocket';

interface TrainingMetricsPanelProps {
  metrics: TrainingMetrics;
  showLossChart?: boolean;
  compact?: boolean;
}

// Helper functions
function formatTime(seconds: number): string {
  if (seconds < 60) return `${Math.round(seconds)}s`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${Math.round(seconds % 60)}s`;
  const hours = Math.floor(seconds / 3600);
  const mins = Math.floor((seconds % 3600) / 60);
  return `${hours}h ${mins}m`;
}

function formatNumber(num: number | null, decimals: number = 4): string {
  if (num === null || num === undefined) return '-';
  return num.toFixed(decimals);
}

// Health indicator colors
function getHealthColor(health: TrainingHealth): string {
  switch (health) {
    case 'excellent':
      return 'text-green-500';
    case 'good':
      return 'text-blue-500';
    case 'warning':
      return 'text-yellow-500';
    case 'critical':
      return 'text-red-500';
    default:
      return 'text-gray-500';
  }
}

function getHealthBgColor(health: TrainingHealth): string {
  switch (health) {
    case 'excellent':
      return 'bg-green-100 dark:bg-green-900/30';
    case 'good':
      return 'bg-blue-100 dark:bg-blue-900/30';
    case 'warning':
      return 'bg-yellow-100 dark:bg-yellow-900/30';
    case 'critical':
      return 'bg-red-100 dark:bg-red-900/30';
    default:
      return 'bg-gray-100 dark:bg-gray-800';
  }
}

function getLossTrendIcon(trend: LossTrend): string {
  switch (trend) {
    case 'decreasing':
      return '↓';
    case 'increasing':
      return '↑';
    case 'stable':
      return '→';
    case 'fluctuating':
      return '↕';
    default:
      return '-';
  }
}

function getLossTrendColor(trend: LossTrend): string {
  switch (trend) {
    case 'decreasing':
      return 'text-green-500';
    case 'increasing':
      return 'text-red-500';
    case 'stable':
      return 'text-blue-500';
    case 'fluctuating':
      return 'text-yellow-500';
    default:
      return 'text-gray-500';
  }
}

function getOverfittingColor(risk: OverfittingRisk): string {
  switch (risk) {
    case 'low':
      return 'text-green-500';
    case 'medium':
      return 'text-yellow-500';
    case 'high':
      return 'text-red-500';
    default:
      return 'text-gray-500';
  }
}

// Mini sparkline for loss history
function LossSparkline({ losses }: { losses: number[] }) {
  if (!losses || losses.length < 2) return null;

  const min = Math.min(...losses);
  const max = Math.max(...losses);
  const range = max - min || 1;

  const width = 120;
  const height = 30;
  const padding = 2;

  const points = losses.map((loss, i) => {
    const x = padding + (i / (losses.length - 1)) * (width - 2 * padding);
    const y = height - padding - ((loss - min) / range) * (height - 2 * padding);
    return `${x},${y}`;
  }).join(' ');

  return (
    <svg width={width} height={height} className="inline-block">
      <polyline
        points={points}
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        className="text-blue-500"
      />
    </svg>
  );
}

export function TrainingMetricsPanel({
  metrics,
  showLossChart = true,
  compact = false,
}: TrainingMetricsPanelProps) {
  const { progress, performance, gpu, time, quality, convergence } = metrics;

  if (compact) {
    return (
      <div className="flex items-center gap-4 text-sm">
        {/* Progress */}
        <div className="flex items-center gap-2">
          <span className="text-gray-500">Progress:</span>
          <span className="font-medium">
            {progress.progress_percent.toFixed(1)}%
          </span>
          <span className="text-gray-400">
            (Epoch {progress.current_epoch}/{progress.total_epochs})
          </span>
        </div>

        {/* Loss */}
        {performance.loss !== null && (
          <div className="flex items-center gap-2">
            <span className="text-gray-500">Loss:</span>
            <span className="font-medium">{formatNumber(performance.loss)}</span>
            <span className={getLossTrendColor(quality.loss_trend)}>
              {getLossTrendIcon(quality.loss_trend)}
            </span>
          </div>
        )}

        {/* Health */}
        <div className={`flex items-center gap-1 ${getHealthColor(quality.training_health)}`}>
          <span className="font-medium capitalize">{quality.training_health}</span>
        </div>

        {/* ETA */}
        {time.eta_seconds !== null && (
          <div className="text-gray-500">
            ETA: {formatTime(time.eta_seconds)}
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Health Banner */}
      <div className={`rounded-lg p-3 ${getHealthBgColor(quality.training_health)}`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className={`text-lg font-semibold capitalize ${getHealthColor(quality.training_health)}`}>
              {quality.training_health}
            </span>
            <span className="text-sm text-gray-600 dark:text-gray-300">
              {quality.health_message}
            </span>
          </div>
          <div className="flex items-center gap-4 text-sm">
            <div className="flex items-center gap-1">
              <span className="text-gray-500">Trend:</span>
              <span className={getLossTrendColor(quality.loss_trend)}>
                {getLossTrendIcon(quality.loss_trend)} {quality.loss_trend}
              </span>
            </div>
            <div className="flex items-center gap-1">
              <span className="text-gray-500">Overfit Risk:</span>
              <span className={`capitalize ${getOverfittingColor(quality.overfitting_risk)}`}>
                {quality.overfitting_risk}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Main Metrics Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {/* Progress */}
        <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
          <div className="text-sm text-gray-500 mb-1">Progress</div>
          <div className="text-2xl font-bold">{progress.progress_percent.toFixed(1)}%</div>
          <div className="text-xs text-gray-400 mt-1">
            Step {progress.current_step}/{progress.total_steps}
          </div>
          <div className="text-xs text-gray-400">
            Epoch {progress.current_epoch}/{progress.total_epochs}
          </div>
        </div>

        {/* Loss */}
        <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
          <div className="text-sm text-gray-500 mb-1">Loss</div>
          <div className="flex items-center gap-2">
            <span className="text-2xl font-bold">{formatNumber(performance.loss)}</span>
            <span className={`text-xl ${getLossTrendColor(quality.loss_trend)}`}>
              {getLossTrendIcon(quality.loss_trend)}
            </span>
          </div>
          {showLossChart && performance.loss_history.length > 1 && (
            <div className="mt-2">
              <LossSparkline losses={performance.loss_history} />
            </div>
          )}
          {convergence.best_loss !== null && (
            <div className="text-xs text-gray-400 mt-1">
              Best: {formatNumber(convergence.best_loss)} (step {convergence.best_loss_step})
            </div>
          )}
        </div>

        {/* Time */}
        <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
          <div className="text-sm text-gray-500 mb-1">Time</div>
          <div className="text-2xl font-bold">{formatTime(time.elapsed_seconds)}</div>
          {time.eta_seconds !== null && (
            <div className="text-xs text-gray-400 mt-1">
              ETA: {formatTime(time.eta_seconds)}
            </div>
          )}
          <div className="text-xs text-gray-400">
            {time.tokens_per_second.toFixed(1)} tok/s
          </div>
        </div>

        {/* GPU */}
        {gpu && (
          <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
            <div className="text-sm text-gray-500 mb-1">GPU Memory</div>
            <div className="text-2xl font-bold">
              {gpu.memory_percent !== null ? `${gpu.memory_percent.toFixed(0)}%` : '-'}
            </div>
            <div className="text-xs text-gray-400 mt-1">
              {gpu.memory_used_mb !== null && gpu.memory_total_mb !== null
                ? `${(gpu.memory_used_mb / 1024).toFixed(1)} / ${(gpu.memory_total_mb / 1024).toFixed(1)} GB`
                : '-'}
            </div>
            {gpu.temperature_celsius !== null && (
              <div className="text-xs text-gray-400">
                Temp: {gpu.temperature_celsius}°C
              </div>
            )}
          </div>
        )}
      </div>

      {/* Additional Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3 text-sm">
        <div className="bg-gray-50 dark:bg-gray-800/50 rounded p-2">
          <div className="text-gray-500 text-xs">Learning Rate</div>
          <div className="font-medium">{formatNumber(performance.learning_rate, 6)}</div>
        </div>
        <div className="bg-gray-50 dark:bg-gray-800/50 rounded p-2">
          <div className="text-gray-500 text-xs">Gradient Norm</div>
          <div className="font-medium">{formatNumber(performance.gradient_norm, 4)}</div>
        </div>
        <div className="bg-gray-50 dark:bg-gray-800/50 rounded p-2">
          <div className="text-gray-500 text-xs">Accuracy</div>
          <div className="font-medium">
            {performance.accuracy !== null ? `${(performance.accuracy * 100).toFixed(1)}%` : '-'}
          </div>
        </div>
        <div className="bg-gray-50 dark:bg-gray-800/50 rounded p-2">
          <div className="text-gray-500 text-xs">Tokens Processed</div>
          <div className="font-medium">{progress.tokens_processed.toLocaleString()}</div>
        </div>
        <div className="bg-gray-50 dark:bg-gray-800/50 rounded p-2">
          <div className="text-gray-500 text-xs">Step Duration</div>
          <div className="font-medium">{time.step_duration_ms.toFixed(0)}ms</div>
        </div>
      </div>

      {/* Convergence Info */}
      {convergence.should_early_stop && (
        <div className="bg-yellow-100 dark:bg-yellow-900/30 rounded-lg p-3 text-yellow-800 dark:text-yellow-200">
          <span className="font-medium">Early Stop Recommended:</span>{' '}
          {convergence.early_stop_reason}
        </div>
      )}

      {convergence.epochs_without_improvement > 0 && (
        <div className="text-sm text-gray-500">
          No improvement for {convergence.epochs_without_improvement} epoch(s)
        </div>
      )}
    </div>
  );
}

export default TrainingMetricsPanel;
