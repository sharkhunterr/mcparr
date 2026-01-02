import { useState, useEffect, useCallback, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { Bot, RefreshCw, BarChart3, History, Wrench, Settings, ChevronDown, ChevronRight, Play, X, Loader2 } from 'lucide-react';
import { api } from '../lib/api';
import { getServiceColor, getServiceFromToolName } from '../lib/serviceColors';

interface McpRequest {
  id: string;
  tool_name: string;
  tool_category: string | null;
  status: string;
  input_params: Record<string, any> | null;
  output_result: Record<string, any> | null;
  error_message: string | null;
  duration_ms: number | null;
  user_id: string | null;
  user_display_name: string | null;
  service_id: string | null;
  created_at: string;
  completed_at: string | null;
}

interface McpStats {
  total: number;
  by_status: Record<string, number>;
  by_category: Record<string, number>;
  top_tools: Record<string, number>;
  average_duration_ms: number;
  success_rate: number;
  period_hours: number;
}

interface McpToolUsage {
  tool_name: string;
  category: string | null;
  usage_count: number;
  avg_duration_ms: number;
  success_rate: number;
}

interface McpHourlyUsage {
  hour: string;
  count: number;
  success_count?: number;
  failed_count?: number;
}

interface McpUserStats {
  user_id: string;
  user_display_name: string | null;
  request_count: number;
  avg_duration_ms: number;
  success_count: number;
  failed_count: number;
  success_rate: number;
}

interface McpUserServiceStats {
  user_id: string;
  user_display_name: string | null;
  service: string;
  request_count: number;
  success_count: number;
  success_rate: number;
}

interface McpHourlyUserUsage {
  hour: string;
  user_id: string;
  user_display_name: string | null;
  count: number;
}

interface McpTool {
  name: string;
  description: string;
  category: string;
  is_mutation: boolean;
  requires_service: string | null;
  parameters: Array<{
    name: string;
    description: string;
    type: string;
    required: boolean;
    enum?: string[];
    default?: any;
  }>;
}

interface McpToolsResponse {
  total: number;
  categories: Record<string, McpTool[]>;
  tools: McpTool[];
}

interface ToolGroup {
  id: string;
  name: string;
  color?: string;
  icon?: string;
  priority: number;
  is_wildcard: boolean;
}

const StatusBadge = ({ status }: { status: string }) => {
  const colors: Record<string, string> = {
    pending: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
    processing: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
    completed: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
    failed: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
    cancelled: 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200',
  };

  return (
    <span className={`px-2 py-1 text-xs font-medium rounded-full ${colors[status] || colors.pending}`}>
      {status}
    </span>
  );
};

// Stacked bar chart component for hourly usage with success/failure breakdown
const HourlyUsageChart = ({ data, timeRange }: { data: McpHourlyUsage[]; timeRange: number }) => {
  // Generate all hours for the timeRange with 0 values for missing hours
  // Backend uses UTC, so we need to generate UTC hours for matching
  const now = new Date();
  const hours: { hour: string; count: number; success: number; failed: number; label: string }[] = [];

  for (let i = timeRange - 1; i >= 0; i--) {
    const date = new Date(now.getTime() - i * 60 * 60 * 1000);
    // API format: "YYYY-MM-DD HH:00:00" in UTC
    const year = date.getUTCFullYear();
    const month = String(date.getUTCMonth() + 1).padStart(2, '0');
    const day = String(date.getUTCDate()).padStart(2, '0');
    const utcHour = String(date.getUTCHours()).padStart(2, '0');
    const hourKey = `${year}-${month}-${day} ${utcHour}`;

    // Local hour for display
    const localHour = String(date.getHours()).padStart(2, '0');

    const found = data.find(d => d.hour.startsWith(hourKey));
    hours.push({
      hour: hourKey,
      count: found?.count || 0,
      success: found?.success_count || 0,
      failed: found?.failed_count || 0,
      label: `${localHour}:00`  // Display local time in label
    });
  }

  const maxCount = Math.max(...hours.map(h => h.count), 1);
  const chartHeight = 128; // pixels (h-32)

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-medium text-gray-900 dark:text-white">
          Requests Over Time
        </h3>
        <div className="flex items-center gap-3 text-xs">
          <div className="flex items-center gap-1">
            <div className="w-3 h-3 rounded-sm bg-green-500" />
            <span className="text-gray-500 dark:text-gray-400">Success</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-3 h-3 rounded-sm bg-red-500" />
            <span className="text-gray-500 dark:text-gray-400">Failed</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-3 h-3 rounded-sm bg-gray-300 dark:bg-gray-600" />
            <span className="text-gray-500 dark:text-gray-400">No data</span>
          </div>
        </div>
      </div>
      <div className="flex items-end gap-0.5" style={{ height: `${chartHeight}px` }}>
        {hours.map((h, i) => {
          const totalHeight = h.count > 0 ? Math.max((h.count / maxCount) * chartHeight, 8) : 6;
          const successRatio = h.count > 0 ? h.success / h.count : 0;
          const failedRatio = h.count > 0 ? h.failed / h.count : 0;
          const successHeight = totalHeight * successRatio;
          const failedHeight = totalHeight * failedRatio;
          const isLast = i === hours.length - 1;

          return (
            <div
              key={i}
              className="flex-1 flex flex-col items-center justify-end group relative"
              title={`${h.label}: ${h.count} req (${h.success} ok, ${h.failed} err)`}
            >
              {/* Tooltip on hover */}
              <div className="absolute bottom-full mb-2 hidden group-hover:block z-10">
                <div className="bg-gray-900 text-white text-xs rounded px-2 py-1 whitespace-nowrap">
                  {h.label}: {h.count} ({h.success} ✓, {h.failed} ✗)
                </div>
              </div>
              {h.count === 0 ? (
                // No data - gray dot
                <div
                  className={`w-full rounded-sm bg-gray-300 dark:bg-gray-600 ${isLast ? 'opacity-100' : 'opacity-50'}`}
                  style={{ height: '6px' }}
                />
              ) : (
                // Stacked bar: failed on top, success on bottom
                <div className="w-full flex flex-col-reverse">
                  {/* Success (green) - bottom, rounded-t when no failed bar on top */}
                  {successHeight > 0 && (
                    <div
                      className={`w-full rounded-b-sm ${failedHeight === 0 ? 'rounded-t-sm' : ''} ${isLast ? 'bg-green-500' : 'bg-green-400 dark:bg-green-500/80'}`}
                      style={{ height: `${successHeight}px` }}
                    />
                  )}
                  {/* Failed (red) - top */}
                  {failedHeight > 0 && (
                    <div
                      className={`w-full ${successHeight > 0 ? '' : 'rounded-b-sm'} rounded-t-sm ${isLast ? 'bg-red-500' : 'bg-red-400 dark:bg-red-500/80'}`}
                      style={{ height: `${failedHeight}px` }}
                    />
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
      <div className="flex justify-between mt-2 text-xs text-gray-500 dark:text-gray-400">
        <span>{hours[0]?.label || ''}</span>
        <span>{hours[Math.floor(hours.length / 2)]?.label || ''}</span>
        <span>{hours[hours.length - 1]?.label || ''}</span>
      </div>
    </div>
  );
};

const CategoryBadge = ({ category }: { category: string }) => {
  const colors: Record<string, string> = {
    media: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200',
    requests: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
    support: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200',
    system: 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200',
    users: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
  };

  return (
    <span className={`px-2 py-1 text-xs font-medium rounded-full ${colors[category] || colors.system}`}>
      {category}
    </span>
  );
};

// Badge coloré pour identifier le service associé à un outil
const ServiceBadge = ({ toolName, requiresService }: { toolName: string; requiresService?: string | null }) => {
  // Priorité: requires_service > préfixe du nom de l'outil
  const serviceName = requiresService || getServiceFromToolName(toolName);

  if (!serviceName) return null;

  const colors = getServiceColor(serviceName);
  const Icon = colors.icon;

  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-full ${colors.badge} ${colors.badgeDark}`}>
      <Icon className="w-3 h-3" />
      {serviceName}
    </span>
  );
};

const StatCard = ({ title, value, subtitle, color = 'blue' }: {
  title: string;
  value: string | number;
  subtitle?: string;
  color?: string;
}) => (
  <div className="bg-white dark:bg-gray-800 rounded-lg p-2.5 sm:p-4 shadow">
    <p className="text-xs sm:text-sm text-gray-500 dark:text-gray-400 truncate">{title}</p>
    <p className={`text-lg sm:text-2xl font-bold text-${color}-600 dark:text-${color}-400`}>
      {value}
    </p>
    {subtitle && (
      <p className="text-[10px] sm:text-xs text-gray-400 dark:text-gray-500 mt-0.5 sm:mt-1 truncate">{subtitle}</p>
    )}
  </div>
);

// Donut chart component for status breakdown
const StatusDonutChart = ({ data, total }: { data: Record<string, number>; total: number }) => {
  const statusColors: Record<string, { stroke: string; fill: string; label: string }> = {
    completed: { stroke: '#22c55e', fill: 'bg-green-500', label: 'Completed' },
    failed: { stroke: '#ef4444', fill: 'bg-red-500', label: 'Failed' },
    pending: { stroke: '#eab308', fill: 'bg-yellow-500', label: 'Pending' },
    processing: { stroke: '#3b82f6', fill: 'bg-blue-500', label: 'Processing' },
    cancelled: { stroke: '#6b7280', fill: 'bg-gray-500', label: 'Cancelled' },
  };

  const size = 120;
  const strokeWidth = 20;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const center = size / 2;

  // Sort entries so completed is first (largest usually)
  const entries = Object.entries(data).sort((a, b) => {
    const order = ['completed', 'failed', 'pending', 'processing', 'cancelled'];
    return order.indexOf(a[0]) - order.indexOf(b[0]);
  });

  // Calculate segments with cumulative offsets
  const segments = entries.reduce<Array<{ status: string; count: number; offset: number; percentage: number }>>(
    (acc, [status, count]) => {
      const percentage = total > 0 ? count / total : 0;
      const previousOffset = acc.length > 0 ? acc[acc.length - 1].offset + acc[acc.length - 1].percentage : 0;
      acc.push({ status, count, offset: previousOffset, percentage });
      return acc;
    },
    []
  );

  return (
    <div className="flex items-center justify-center gap-6">
      {/* SVG Donut */}
      <div className="relative">
        <svg width={size} height={size} className="transform -rotate-90">
          {/* Background circle */}
          <circle
            cx={center}
            cy={center}
            r={radius}
            fill="none"
            stroke="currentColor"
            strokeWidth={strokeWidth}
            className="text-gray-200 dark:text-gray-700"
          />
          {/* Data segments */}
          {segments.map(({ status, count, offset, percentage }) => {
            if (count === 0) return null;

            const dashLength = circumference * percentage;
            const dashOffset = circumference * offset;

            return (
              <circle
                key={status}
                cx={center}
                cy={center}
                r={radius}
                fill="none"
                stroke={statusColors[status]?.stroke || '#6b7280'}
                strokeWidth={strokeWidth}
                strokeDasharray={`${dashLength} ${circumference - dashLength}`}
                strokeDashoffset={-dashOffset}
                strokeLinecap="butt"
                className="transition-all duration-500"
              />
            );
          })}
        </svg>
        {/* Center text */}
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-2xl font-bold text-gray-900 dark:text-white">{total}</span>
          <span className="text-xs text-gray-500 dark:text-gray-400">total</span>
        </div>
      </div>

      {/* Legend */}
      <div className="flex flex-col gap-2">
        {entries.map(([status, count]) => {
          if (count === 0) return null;
          const percentage = total > 0 ? ((count / total) * 100).toFixed(0) : 0;
          return (
            <div key={status} className="flex items-center gap-2">
              <div className={`w-3 h-3 rounded-full ${statusColors[status]?.fill || 'bg-gray-500'}`} />
              <span className="text-sm text-gray-700 dark:text-gray-300 capitalize">{status}</span>
              <span className="text-sm font-semibold text-gray-900 dark:text-white">{count}</span>
              <span className="text-xs text-gray-500 dark:text-gray-400">({percentage}%)</span>
            </div>
          );
        })}
      </div>
    </div>
  );
};

// Tool Test Modal - Modal for testing MCP tools with dynamic form
const ToolTestModal = ({
  tool,
  isOpen,
  onClose,
}: {
  tool: McpTool | null;
  isOpen: boolean;
  onClose: () => void;
}) => {
  const [params, setParams] = useState<Record<string, any>>({});
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [duration, setDuration] = useState<number | null>(null);
  const { t } = useTranslation('mcp');

  // Initialize params with default values when tool changes
  useEffect(() => {
    if (tool) {
      const initialParams: Record<string, any> = {};
      tool.parameters.forEach((param) => {
        if (param.default !== undefined) {
          initialParams[param.name] = param.default;
        } else if (param.type === 'boolean') {
          initialParams[param.name] = false;
        } else if (param.type === 'integer' || param.type === 'number') {
          initialParams[param.name] = param.required ? '' : '';
        } else if (param.enum && param.enum.length > 0) {
          initialParams[param.name] = param.enum[0];
        } else {
          initialParams[param.name] = '';
        }
      });
      setParams(initialParams);
      setResult(null);
      setError(null);
      setDuration(null);
    }
  }, [tool]);

  const handleParamChange = (name: string, value: any, type: string) => {
    let parsedValue = value;
    if (type === 'integer') {
      parsedValue = value === '' ? '' : parseInt(value, 10);
    } else if (type === 'number') {
      parsedValue = value === '' ? '' : parseFloat(value);
    } else if (type === 'boolean') {
      parsedValue = value === 'true' || value === true;
    }
    setParams((prev) => ({ ...prev, [name]: parsedValue }));
  };

  const handleExecute = async () => {
    if (!tool) return;

    setLoading(true);
    setError(null);
    setResult(null);

    // Build params object, only include non-empty values
    const executeParams: Record<string, any> = {};
    Object.entries(params).forEach(([key, value]) => {
      if (value !== '' && value !== null && value !== undefined) {
        executeParams[key] = value;
      }
    });

    const startTime = Date.now();
    try {
      const response = await api.mcp.executeTool(tool.name, executeParams);
      setDuration(Date.now() - startTime);
      setResult(response);
    } catch (err: any) {
      setDuration(Date.now() - startTime);
      setError(err.message || t('errors.toolExecutionFailed'));
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen || !tool) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex items-center justify-center min-h-screen px-4">
        <div className="fixed inset-0 bg-black bg-opacity-50" onClick={onClose} />
        <div className="relative bg-white dark:bg-gray-800 rounded-lg max-w-3xl w-full p-6 shadow-xl max-h-[90vh] overflow-y-auto">
          {/* Header */}
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-lg font-medium text-gray-900 dark:text-white flex items-center gap-2">
                <Play className="w-5 h-5 text-green-600" />
                {t('tools.testTitle', { name: tool.name })}
              </h3>
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                {tool.description}
              </p>
            </div>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-500 p-1"
            >
              <X className="w-6 h-6" />
            </button>
          </div>

          {/* Parameters Form */}
          {tool.parameters.length > 0 ? (
            <div className="space-y-4 mb-6">
              <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300">
                {t('tools.parameters')}
              </h4>
              {tool.parameters.map((param) => (
                <div key={param.name} className="space-y-1">
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                    {param.name}
                    {param.required && <span className="text-red-500 ml-1">*</span>}
                    <span className="text-xs text-gray-400 ml-2">({param.type})</span>
                  </label>
                  {param.description && (
                    <p className="text-xs text-gray-500 dark:text-gray-400">
                      {param.description}
                    </p>
                  )}
                  {param.type === 'boolean' ? (
                    <select
                      value={params[param.name]?.toString() || 'false'}
                      onChange={(e) => handleParamChange(param.name, e.target.value, param.type)}
                      className="mt-1 block w-full rounded-md border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2"
                    >
                      <option value="false">false</option>
                      <option value="true">true</option>
                    </select>
                  ) : param.enum && param.enum.length > 0 ? (
                    <select
                      value={params[param.name] || ''}
                      onChange={(e) => handleParamChange(param.name, e.target.value, param.type)}
                      className="mt-1 block w-full rounded-md border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2"
                    >
                      {param.enum.map((opt) => (
                        <option key={opt} value={opt}>
                          {opt}
                        </option>
                      ))}
                    </select>
                  ) : (
                    <input
                      type={param.type === 'integer' || param.type === 'number' ? 'number' : 'text'}
                      value={params[param.name] || ''}
                      onChange={(e) => handleParamChange(param.name, e.target.value, param.type)}
                      placeholder={param.default !== undefined ? t('tools.defaultValue', { value: param.default }) : ''}
                      className="mt-1 block w-full rounded-md border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2"
                    />
                  )}
                </div>
              ))}
            </div>
          ) : (
            <div className="mb-6 p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg text-sm text-gray-600 dark:text-gray-400">
              {t('tools.noParameters')}
            </div>
          )}

          {/* Execute Button */}
          <div className="flex justify-end mb-4">
            <button
              onClick={handleExecute}
              disabled={loading}
              className="inline-flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  {t('tools.executing')}
                </>
              ) : (
                <>
                  <Play className="w-4 h-4" />
                  {t('tools.execute')}
                </>
              )}
            </button>
          </div>

          {/* Result / Error */}
          {(result || error) && (
            <div className="border-t dark:border-gray-700 pt-4">
              <div className="flex items-center justify-between mb-2">
                <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  {t('tools.result')}
                </h4>
                {duration !== null && (
                  <span className="text-xs text-gray-500 dark:text-gray-400">
                    {duration}ms
                  </span>
                )}
              </div>
              {error ? (
                <div className="bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 p-4 rounded-lg text-sm">
                  {error}
                </div>
              ) : result ? (
                <pre className="bg-gray-900 dark:bg-black text-gray-100 p-4 rounded-lg text-xs overflow-x-auto max-h-64">
                  {JSON.stringify(result, null, 2)}
                </pre>
              ) : null}
            </div>
          )}

          {/* Footer */}
          <div className="mt-6 flex justify-end">
            <button
              onClick={onClose}
              className="px-4 py-2 bg-gray-200 dark:bg-gray-700 text-gray-900 dark:text-white rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600"
            >
              {t('tools.close')}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

// Color palette for users (modern, distinct colors)
const USER_COLORS = [
  { bg: 'bg-blue-500', hex: '#3b82f6', text: 'text-blue-500' },
  { bg: 'bg-emerald-500', hex: '#10b981', text: 'text-emerald-500' },
  { bg: 'bg-violet-500', hex: '#8b5cf6', text: 'text-violet-500' },
  { bg: 'bg-amber-500', hex: '#f59e0b', text: 'text-amber-500' },
  { bg: 'bg-rose-500', hex: '#f43f5e', text: 'text-rose-500' },
  { bg: 'bg-cyan-500', hex: '#06b6d4', text: 'text-cyan-500' },
  { bg: 'bg-fuchsia-500', hex: '#d946ef', text: 'text-fuchsia-500' },
  { bg: 'bg-lime-500', hex: '#84cc16', text: 'text-lime-500' },
  { bg: 'bg-orange-500', hex: '#f97316', text: 'text-orange-500' },
  { bg: 'bg-teal-500', hex: '#14b8a6', text: 'text-teal-500' },
];

const getUserColor = (index: number) => USER_COLORS[index % USER_COLORS.length];

// User Stats Bar Chart - Horizontal bars with user names
const UserStatsChart = ({ data }: { data: McpUserStats[] }) => {
  const { t } = useTranslation('mcp');
  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center h-40 text-gray-500 dark:text-gray-400 text-sm">
        {t('stats.noData')}
      </div>
    );
  }

  const maxCount = Math.max(...data.map(d => d.request_count), 1);

  return (
    <div className="space-y-3">
      {data.slice(0, 8).map((user, index) => {
        const color = getUserColor(index);
        const percentage = (user.request_count / maxCount) * 100;
        const displayName = user.user_display_name || user.user_id.split('@')[0] || user.user_id.substring(0, 8);

        return (
          <div key={user.user_id} className="group">
            <div className="flex items-center justify-between mb-1">
              <div className="flex items-center gap-2 min-w-0">
                <div className={`w-2 h-2 rounded-full ${color.bg}`} />
                <span className="text-sm font-medium text-gray-900 dark:text-white truncate" title={user.user_id}>
                  {displayName}
                </span>
              </div>
              <div className="flex items-center gap-3 text-xs">
                <span className="tabular-nums text-gray-700 dark:text-gray-300 font-medium">
                  {user.request_count}
                </span>
                <span className={`tabular-nums ${user.success_rate >= 90 ? 'text-green-600 dark:text-green-400' : user.success_rate >= 50 ? 'text-yellow-600 dark:text-yellow-400' : 'text-red-600 dark:text-red-400'}`}>
                  {user.success_rate}%
                </span>
              </div>
            </div>
            <div className="h-2 bg-gray-100 dark:bg-gray-700 rounded-full overflow-hidden">
              <div
                className="h-full rounded-full transition-all duration-500"
                style={{ width: `${percentage}%`, backgroundColor: color.hex }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
};

// User Service Breakdown - Horizontal stacked bars
const UserServiceChart = ({ data }: { data: McpUserServiceStats[] }) => {
  const { t } = useTranslation('mcp');
  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center h-40 text-gray-500 dark:text-gray-400 text-sm">
        {t('stats.noData')}
      </div>
    );
  }

  // Group by user
  const byUser: Record<string, { displayName: string; services: Record<string, number>; total: number }> = {};
  data.forEach(item => {
    if (!byUser[item.user_id]) {
      byUser[item.user_id] = {
        displayName: item.user_display_name || item.user_id.split('@')[0] || item.user_id.substring(0, 8),
        services: {},
        total: 0,
      };
    }
    byUser[item.user_id].services[item.service] = item.request_count;
    byUser[item.user_id].total += item.request_count;
  });

  // Get all unique services
  const allServices = [...new Set(data.map(d => d.service))];
  const maxTotal = Math.max(...Object.values(byUser).map(u => u.total), 1);

  // Sort users by total
  const sortedUsers = Object.entries(byUser).sort((a, b) => b[1].total - a[1].total).slice(0, 6);

  return (
    <div className="space-y-3">
      {sortedUsers.map(([userId, userData]) => {
        const barWidth = (userData.total / maxTotal) * 100;

        return (
          <div key={userId} className="group">
            <div className="flex items-center justify-between mb-1">
              <span className="text-sm font-medium text-gray-900 dark:text-white truncate" title={userId}>
                {userData.displayName}
              </span>
              <span className="text-xs tabular-nums text-gray-600 dark:text-gray-400">
                {userData.total}
              </span>
            </div>
            <div className="h-3 bg-gray-100 dark:bg-gray-700 rounded-full overflow-hidden flex" style={{ width: `${barWidth}%` }}>
              {allServices.map((service) => {
                const count = userData.services[service] || 0;
                if (count === 0) return null;
                const segmentWidth = (count / userData.total) * 100;
                const colors = getServiceColor(service);

                return (
                  <div
                    key={service}
                    className="h-full transition-all first:rounded-l-full last:rounded-r-full"
                    style={{ width: `${segmentWidth}%`, backgroundColor: colors.hex }}
                    title={`${service}: ${count}`}
                  />
                );
              })}
            </div>
          </div>
        );
      })}
      {/* Legend */}
      <div className="flex flex-wrap gap-2 mt-3 pt-3 border-t border-gray-100 dark:border-gray-700">
        {allServices.slice(0, 6).map(service => {
          const colors = getServiceColor(service);
          return (
            <div key={service} className="flex items-center gap-1">
              <div className="w-2 h-2 rounded-full" style={{ backgroundColor: colors.hex }} />
              <span className="text-xs text-gray-600 dark:text-gray-400 capitalize">{service}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
};

// Stacked Bar Chart - Hourly usage by user
const HourlyUserStackedChart = ({ data, timeRange }: { data: McpHourlyUserUsage[]; timeRange: number }) => {
  const { t } = useTranslation('mcp');
  // Get unique users and assign colors
  const users = [...new Set(data.map(d => d.user_id))];
  const userColorMap: Record<string, { displayName: string; color: typeof USER_COLORS[0] }> = {};
  users.forEach((userId, index) => {
    const item = data.find(d => d.user_id === userId);
    userColorMap[userId] = {
      displayName: item?.user_display_name || userId.split('@')[0] || userId.substring(0, 8),
      color: getUserColor(index),
    };
  });

  // Generate hours and aggregate data
  const now = new Date();
  const hours: { hour: string; label: string; byUser: Record<string, number>; total: number }[] = [];

  for (let i = timeRange - 1; i >= 0; i--) {
    const date = new Date(now.getTime() - i * 60 * 60 * 1000);
    const year = date.getUTCFullYear();
    const month = String(date.getUTCMonth() + 1).padStart(2, '0');
    const day = String(date.getUTCDate()).padStart(2, '0');
    const utcHour = String(date.getUTCHours()).padStart(2, '0');
    const hourKey = `${year}-${month}-${day} ${utcHour}`;
    const localHour = String(date.getHours()).padStart(2, '0');

    const hourData: Record<string, number> = {};
    let total = 0;
    data.filter(d => d.hour.startsWith(hourKey)).forEach(d => {
      hourData[d.user_id] = (hourData[d.user_id] || 0) + d.count;
      total += d.count;
    });

    hours.push({ hour: hourKey, label: `${localHour}:00`, byUser: hourData, total });
  }

  const maxCount = Math.max(...hours.map(h => h.total), 1);
  const chartHeight = 140;

  if (users.length === 0) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow">
        <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
          Requêtes par utilisateur (temps)
        </h3>
        <div className="flex items-center justify-center h-32 text-gray-500 dark:text-gray-400 text-sm">
          {t('stats.noData')}
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-medium text-gray-900 dark:text-white">
          Requêtes par utilisateur (temps)
        </h3>
        <div className="flex items-center gap-2 flex-wrap justify-end">
          {users.slice(0, 5).map(userId => (
            <div key={userId} className="flex items-center gap-1">
              <div className={`w-2.5 h-2.5 rounded-full ${userColorMap[userId].color.bg}`} />
              <span className="text-xs text-gray-600 dark:text-gray-400 truncate max-w-[80px]" title={userId}>
                {userColorMap[userId].displayName}
              </span>
            </div>
          ))}
          {users.length > 5 && (
            <span className="text-xs text-gray-400 dark:text-gray-500">+{users.length - 5}</span>
          )}
        </div>
      </div>

      <div className="flex items-end gap-0.5" style={{ height: `${chartHeight}px` }}>
        {hours.map((h, i) => {
          const totalHeight = h.total > 0 ? Math.max((h.total / maxCount) * chartHeight, 8) : 6;
          const isLast = i === hours.length - 1;

          return (
            <div
              key={i}
              className="flex-1 flex flex-col justify-end group relative"
              title={`${h.label}: ${h.total} requêtes`}
            >
              {/* Tooltip */}
              <div className="absolute bottom-full mb-2 hidden group-hover:block z-10 left-1/2 -translate-x-1/2">
                <div className="bg-gray-900 text-white text-xs rounded px-2 py-1 whitespace-nowrap">
                  <div className="font-medium mb-1">{h.label}</div>
                  {Object.entries(h.byUser).map(([userId, count]) => (
                    <div key={userId} className="flex items-center gap-1">
                      <div className={`w-1.5 h-1.5 rounded-full ${userColorMap[userId]?.color.bg || 'bg-gray-400'}`} />
                      <span>{userColorMap[userId]?.displayName || userId}: {count}</span>
                    </div>
                  ))}
                </div>
              </div>

              {h.total === 0 ? (
                <div
                  className={`w-full rounded-sm bg-gray-300 dark:bg-gray-600 ${isLast ? 'opacity-100' : 'opacity-50'}`}
                  style={{ height: '6px' }}
                />
              ) : (
                <div className="w-full flex flex-col-reverse rounded-sm overflow-hidden" style={{ height: `${totalHeight}px` }}>
                  {users.map((userId) => {
                    const count = h.byUser[userId] || 0;
                    if (count === 0) return null;
                    const segmentHeight = (count / h.total) * totalHeight;
                    const color = userColorMap[userId].color;

                    return (
                      <div
                        key={userId}
                        className={`w-full ${isLast ? '' : 'opacity-90'}`}
                        style={{ height: `${segmentHeight}px`, backgroundColor: color.hex }}
                      />
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
      </div>

      <div className="flex justify-between mt-2 text-xs text-gray-500 dark:text-gray-400">
        <span>{hours[0]?.label || ''}</span>
        <span>{hours[Math.floor(hours.length / 2)]?.label || ''}</span>
        <span>{hours[hours.length - 1]?.label || ''}</span>
      </div>
    </div>
  );
};

interface McpServerStatus {
  active: boolean;
  protocol_version: string;
  server_name: string;
  server_version: string;
  tools_count: number;
  enabled_services: string[];
  openapi_url: string;
  docs_url: string;
}

// Descriptions des services pour le prompt système
const SERVICE_DESCRIPTIONS: Record<string, { name: string; description: string }> = {
  system: { name: 'Système', description: 'Monitoring et administration' },
  plex: { name: 'Plex', description: 'Bibliothèque multimédia' },
  tautulli: { name: 'Tautulli', description: 'Monitoring Plex' },
  overseerr: { name: 'Overseerr', description: 'Demandes et disponibilité' },
  openwebui: { name: 'Open WebUI', description: 'Interface IA' },
  radarr: { name: 'Radarr', description: 'Gestion des films' },
  sonarr: { name: 'Sonarr', description: 'Gestion des séries TV' },
  prowlarr: { name: 'Prowlarr', description: 'Indexeurs de torrents' },
  jackett: { name: 'Jackett', description: 'Proxy d\'indexeurs' },
  deluge: { name: 'Deluge', description: 'Client torrent' },
  komga: { name: 'Komga', description: 'Bibliothèque de comics/mangas' },
  romm: { name: 'RomM', description: 'Gestion de ROMs de jeux' },
  audiobookshelf: { name: 'Audiobookshelf', description: 'Livres audio et podcasts' },
  wikijs: { name: 'Wiki.js', description: 'Documentation et wiki' },
  zammad: { name: 'Zammad', description: 'Support et tickets' },
  authentik: { name: 'Authentik', description: 'Authentification SSO' },
  ollama: { name: 'Ollama', description: 'Modèles IA locaux' },
};

// Génère le prompt système dynamiquement basé sur les outils disponibles
const generateSystemPrompt = (tools: McpToolsResponse | null, enabledServices: string[], t: (key: string) => string): string => {
  if (!tools || !tools.tools || tools.tools.length === 0) {
    return `Tu es un assistant intelligent pour la gestion d'un homelab multimédia.

${t('systemPrompt.noTools')}`;
  }

  // Grouper les outils par service
  const toolsByService: Record<string, McpTool[]> = {};

  tools.tools.forEach(tool => {
    // Extraire le service du nom de l'outil (ex: plex_search_media -> plex)
    const serviceName = tool.requires_service || tool.name.split('_')[0];
    if (!toolsByService[serviceName]) {
      toolsByService[serviceName] = [];
    }
    toolsByService[serviceName].push(tool);
  });

  // Construire les sections d'outils
  let toolSections = '';

  // Services activés d'abord
  const sortedServices = Object.keys(toolsByService).sort((a, b) => {
    const aEnabled = enabledServices.includes(a.toLowerCase());
    const bEnabled = enabledServices.includes(b.toLowerCase());
    if (aEnabled && !bEnabled) return -1;
    if (!aEnabled && bEnabled) return 1;
    return a.localeCompare(b);
  });

  sortedServices.forEach(service => {
    const serviceTools = toolsByService[service];
    const serviceInfo = SERVICE_DESCRIPTIONS[service.toLowerCase()];
    const serviceName = serviceInfo?.name || service.charAt(0).toUpperCase() + service.slice(1);
    const serviceDesc = serviceInfo?.description || '';

    toolSections += `\n### ${serviceName}${serviceDesc ? ` (${serviceDesc})` : ''}\n`;

    serviceTools.forEach(tool => {
      const params = tool.parameters
        .filter(p => p.required)
        .map(p => `${p.name}`)
        .join(', ');
      const paramStr = params ? ` (${t('systemPrompt.parameters')}: ${params})` : '';
      toolSections += `- ${tool.name}: ${tool.description}${paramStr}\n`;
    });
  });

  // Générer des exemples basés sur les services activés
  let examples = '';

  if (enabledServices.includes('plex')) {
    examples += `
Question: "${t('examples.plex.q1')}"
→ ${t('examples.plex.a1')}
`;
  }

  if (enabledServices.includes('tautulli')) {
    examples += `
Question: "${t('examples.tautulli.q1')}"
→ ${t('examples.tautulli.a1')}

Question: "${t('examples.tautulli.q2')}"
→ ${t('examples.tautulli.a2')}

Question: "${t('examples.tautulli.q3')}"
→ ${t('examples.tautulli.a3')}

Question: "${t('examples.tautulli.q4')}"
→ ${t('examples.tautulli.a4')}

Question: "${t('examples.tautulli.q5')}"
→ ${t('examples.tautulli.a5')}

Question: "${t('examples.tautulli.q6')}"
→ ${t('examples.tautulli.a6')}

Question: "${t('examples.tautulli.q7')}"
→ ${t('examples.tautulli.a7')}
`;
  }

  if (enabledServices.includes('overseerr')) {
    examples += `
Question: "${t('examples.overseerr.q1')}"
→ ${t('examples.overseerr.a1')}
`;
  }

  if (enabledServices.includes('radarr')) {
    examples += `
Question: "${t('examples.radarr.q1')}"
→ ${t('examples.radarr.a1')}

Question: "${t('examples.radarr.q2')}"
→ ${t('examples.radarr.a2')}

Question: "${t('examples.radarr.q3')}"
→ ${t('examples.radarr.a3')}
`;
  }

  if (enabledServices.includes('sonarr')) {
    examples += `
Question: "${t('examples.sonarr.q1')}"
→ ${t('examples.sonarr.a1')}

Question: "${t('examples.sonarr.q2')}"
→ ${t('examples.sonarr.a2')}
`;
  }

  if (enabledServices.includes('prowlarr')) {
    examples += `
Question: "${t('examples.prowlarr.q1')}"
→ ${t('examples.prowlarr.a1')}

Question: "${t('examples.prowlarr.q2')}"
→ ${t('examples.prowlarr.a2')}

Question: "${t('examples.prowlarr.q3')}"
→ ${t('examples.prowlarr.a3')}
`;
  }

  if (enabledServices.includes('jackett')) {
    examples += `
Question: "${t('examples.jackett.q1')}"
→ ${t('examples.jackett.a1')}

Question: "${t('examples.jackett.q2')}"
→ ${t('examples.jackett.a2')}
`;
  }

  if (enabledServices.includes('komga')) {
    examples += `
Question: "${t('examples.komga.q1')}"
→ ${t('examples.komga.a1')}
`;
  }

  if (enabledServices.includes('romm')) {
    examples += `
Question: "${t('examples.romm.q1')}"
→ ${t('examples.romm.a1')}

Question: "${t('examples.romm.q2')}"
→ ${t('examples.romm.a2')}

Question: "${t('examples.romm.q3')}"
→ ${t('examples.romm.a3')}
`;
  }

  if (enabledServices.includes('zammad')) {
    examples += `
Question: "${t('examples.zammad.q1')}"
→ ${t('examples.zammad.a1')}

Question: "${t('examples.zammad.q2')}"
→ ${t('examples.zammad.a2')}

Question: "${t('examples.zammad.q3')}"
→ ${t('examples.zammad.a3')}

Question: "${t('examples.zammad.q4')}"
→ ${t('examples.zammad.a4')}

Question: "${t('examples.zammad.q5')}"
→ ${t('examples.zammad.a5')}
`;
  }

  if (enabledServices.includes('audiobookshelf')) {
    examples += `
Question: "${t('examples.audiobookshelf.q1')}"
→ ${t('examples.audiobookshelf.a1')}

Question: "${t('examples.audiobookshelf.q2')}"
→ ${t('examples.audiobookshelf.a2')}

Question: "${t('examples.audiobookshelf.q3')}"
→ ${t('examples.audiobookshelf.a3')}

Question: "${t('examples.audiobookshelf.q4')}"
→ ${t('examples.audiobookshelf.a4')}
`;
  }

  if (enabledServices.includes('wikijs')) {
    examples += `
Question: "${t('examples.wikijs.q1')}"
→ ${t('examples.wikijs.a1')}

Question: "${t('examples.wikijs.q2')}"
→ ${t('examples.wikijs.a2')}

Question: "${t('examples.wikijs.q3')}"
→ ${t('examples.wikijs.a3')}

Question: "${t('examples.wikijs.q4')}"
→ ${t('examples.wikijs.a4')}
`;
  }

  if (enabledServices.includes('authentik')) {
    examples += `
Question: "${t('examples.authentik.q1')}"
→ ${t('examples.authentik.a1')}

Question: "${t('examples.authentik.q2')}"
→ ${t('examples.authentik.a2')}

Question: "${t('examples.authentik.q3')}"
→ ${t('examples.authentik.a3')}
`;
  }

  // System tools are always available
  examples += `
Question: "${t('examples.system.q1')}"
→ ${t('examples.system.a1')}

Question: "${t('examples.system.q2')}"
→ ${t('examples.system.a2')}

Question: "${t('examples.system.q3')}"
→ ${t('examples.system.a3')}

Question: "${t('examples.system.q4')}"
→ ${t('examples.system.a4')}

Question: "${t('examples.system.q5')}"
→ ${t('examples.system.a5')}

Question: "${t('examples.system.q6')}"
→ ${t('examples.system.a6')}
`;

  // Règles basées sur les services
  let rules = `
## ${t('systemPrompt.responseFormat')}

1. ${t('systemPrompt.format1')}
2. ${t('systemPrompt.format2')}`;

  if (enabledServices.includes('plex') && enabledServices.includes('overseerr')) {
    rules += `
3. ${t('systemPrompt.format3')}
4. ${t('systemPrompt.format4')}`;
  }

  if (enabledServices.includes('tautulli')) {
    rules += `
5. ${t('systemPrompt.format5')}
6. ${t('systemPrompt.format6')}
7. ${t('systemPrompt.format7')}
8. ${t('systemPrompt.format8')}`;
  }

  if (enabledServices.includes('radarr') || enabledServices.includes('sonarr') || enabledServices.includes('prowlarr') || enabledServices.includes('jackett')) {
    rules += `

## ${t('systemPrompt.indexerTestsTitle')}

${t('systemPrompt.indexerTestsDesc')}
- ${t('systemPrompt.indexerTest1')}
- ${t('systemPrompt.indexerTest2')}
- ${t('systemPrompt.indexerTest3')}
- ${t('systemPrompt.indexerTest4')}

9. ${t('systemPrompt.format9')}
10. ${t('systemPrompt.format10')}
11. ${t('systemPrompt.format11')}`;
  }

  return `Tu es un assistant homelab avec accès à des outils externes.

## ${t('systemPrompt.criticalRules')}

1. ${t('systemPrompt.rule1')}

2. ${t('systemPrompt.rule2')}

3. ${t('systemPrompt.rule3')}

4. ${t('systemPrompt.rule4')}

## ${t('systemPrompt.availableTools')}
${toolSections}
${rules}

## ${t('systemPrompt.usageExamples')}
${examples || t('systemPrompt.noExamples')}

${t('systemPrompt.language')}`;
};

const ConfigurationTab = ({ tools }: { tools: McpToolsResponse | null }) => {
  const { t } = useTranslation('mcp');
  const [copied, setCopied] = useState<string | null>(null);
  const [serverStatus, setServerStatus] = useState<McpServerStatus | null>(null);
  const [_statusLoading, setStatusLoading] = useState(true);
  const [_statusError, setStatusError] = useState<string | null>(null);

  useEffect(() => {
    const fetchStatus = async () => {
      setStatusLoading(true);
      setStatusError(null);
      try {
        const status = await api.mcp.status();
        setServerStatus(status);
      } catch (error) {
        setStatusError('Impossible de se connecter au serveur');
        setServerStatus(null);
      } finally {
        setStatusLoading(false);
      }
    };

    fetchStatus();
    const interval = setInterval(fetchStatus, 30000);
    return () => clearInterval(interval);
  }, []);

  // Générer le prompt dynamiquement
  const systemPrompt = generateSystemPrompt(tools, serverStatus?.enabled_services || [], t);

  const copyToClipboard = async (text: string, id: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(id);
      setTimeout(() => setCopied(null), 2000);
    } catch (err) {
      // Fallback for older browsers
      const textArea = document.createElement('textarea');
      textArea.value = text;
      textArea.style.position = 'fixed';
      textArea.style.left = '-999999px';
      document.body.appendChild(textArea);
      textArea.select();
      try {
        document.execCommand('copy');
        setCopied(id);
        setTimeout(() => setCopied(null), 2000);
      } catch (e) {
        console.error('Failed to copy:', e);
      }
      document.body.removeChild(textArea);
    }
  };

  const backendUrl = window.location.hostname === 'localhost'
    ? 'http://localhost:8002'
    : `http://${window.location.hostname}:8002`;

  // OpenAPI endpoints configuration
  const openApiEndpoints = [
    {
      id: 'all',
      name: t('config.endpoints.all.name'),
      path: '/tools/openapi.json',
      description: t('config.endpoints.all.description'),
      color: 'gray',
      services: ['Tous'],
      recommended: false,
    },
    {
      id: 'system',
      name: t('config.endpoints.system.name'),
      path: '/tools/system/openapi.json',
      description: t('config.endpoints.system.description'),
      color: 'blue',
      services: ['System', 'Zammad', 'Authentik'],
      recommended: true,
    },
    {
      id: 'media',
      name: t('config.endpoints.media.name'),
      path: '/tools/media/openapi.json',
      description: t('config.endpoints.media.description'),
      color: 'purple',
      services: ['Plex', 'Tautulli', 'Overseerr', 'Komga', 'RomM', 'Audiobookshelf'],
      recommended: true,
    },
    {
      id: 'processing',
      name: t('config.endpoints.processing.name'),
      path: '/tools/processing/openapi.json',
      description: t('config.endpoints.processing.description'),
      color: 'orange',
      services: ['Radarr', 'Sonarr', 'Prowlarr', 'Deluge'],
      recommended: true,
    },
    {
      id: 'knowledge',
      name: t('config.endpoints.knowledge.name'),
      path: '/tools/knowledge/openapi.json',
      description: t('config.endpoints.knowledge.description'),
      color: 'green',
      services: ['Wiki.js', 'Open WebUI', 'Ollama'],
      recommended: false,
    },
  ];

  const colorClasses: Record<string, { bg: string; border: string; text: string; badge: string }> = {
    blue: {
      bg: 'bg-blue-50 dark:bg-blue-900/20',
      border: 'border-blue-200 dark:border-blue-800',
      text: 'text-blue-900 dark:text-blue-100',
      badge: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
    },
    purple: {
      bg: 'bg-purple-50 dark:bg-purple-900/20',
      border: 'border-purple-200 dark:border-purple-800',
      text: 'text-purple-900 dark:text-purple-100',
      badge: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200',
    },
    orange: {
      bg: 'bg-orange-50 dark:bg-orange-900/20',
      border: 'border-orange-200 dark:border-orange-800',
      text: 'text-orange-900 dark:text-orange-100',
      badge: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200',
    },
    green: {
      bg: 'bg-green-50 dark:bg-green-900/20',
      border: 'border-green-200 dark:border-green-800',
      text: 'text-green-900 dark:text-green-100',
      badge: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
    },
    gray: {
      bg: 'bg-gray-50 dark:bg-gray-800',
      border: 'border-gray-200 dark:border-gray-700',
      text: 'text-gray-900 dark:text-gray-100',
      badge: 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200',
    },
  };

  return (
    <div className="space-y-6">
      {/* Open WebUI Tool Endpoints */}
      <div className="bg-white dark:bg-gray-800 rounded-lg p-4 sm:p-6 shadow">
        <div className="flex items-center gap-2 mb-4">
          <svg className="w-5 h-5 sm:w-6 sm:h-6 text-blue-600 flex-shrink-0" viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z"/>
          </svg>
          <h3 className="text-base sm:text-lg font-medium text-gray-900 dark:text-white">
            {t('config.openWebUI.title')}
          </h3>
        </div>

        <p className="text-xs sm:text-sm text-gray-600 dark:text-gray-400 mb-4">
          <span className="hidden sm:inline">{t('config.openWebUI.description')}</span>
          <span className="sm:hidden">{t('config.openWebUI.descriptionMobile')}</span>
          <br className="hidden sm:block" />
          <span className="text-blue-600 dark:text-blue-400 block sm:inline mt-1 sm:mt-0">{t('config.openWebUI.performanceTip')}</span>
        </p>

        <div className="grid gap-3">
          {openApiEndpoints.map((endpoint) => {
            const colors = colorClasses[endpoint.color];
            const fullUrl = `${backendUrl}${endpoint.path}`;

            return (
              <div
                key={endpoint.id}
                className={`${colors.bg} ${colors.border} border rounded-lg p-3 sm:p-4`}
              >
                {/* Mobile: Stack layout, Desktop: Side by side */}
                <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3 sm:gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center flex-wrap gap-2 mb-1">
                      <h4 className={`font-medium ${colors.text}`}>
                        {endpoint.name}
                      </h4>
                      {endpoint.recommended && (
                        <span className="px-1.5 py-0.5 text-xs bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300 rounded">
                          {t('config.openWebUI.recommended')}
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">
                      {endpoint.description}
                    </p>
                    <div className="flex flex-wrap gap-1">
                      {endpoint.services.map(service => (
                        <span
                          key={service}
                          className={`px-2 py-0.5 text-xs ${colors.badge} rounded-full`}
                        >
                          {service}
                        </span>
                      ))}
                    </div>
                  </div>
                  {/* Mobile: Full width row, Desktop: Column on right */}
                  <div className="flex flex-row sm:flex-col items-center sm:items-end justify-between sm:justify-start gap-2 pt-2 sm:pt-0 border-t sm:border-t-0 border-gray-200 dark:border-gray-600">
                    <code className="text-xs bg-gray-100 dark:bg-gray-700 px-2 py-1 rounded font-mono truncate max-w-[200px] sm:max-w-none">
                      {endpoint.path}
                    </code>
                    <button
                      onClick={() => copyToClipboard(fullUrl, `endpoint-${endpoint.id}`)}
                      className={`px-3 py-1.5 text-sm font-medium rounded-lg transition-colors whitespace-nowrap ${
                        copied === `endpoint-${endpoint.id}`
                          ? 'bg-green-600 text-white'
                          : 'bg-blue-600 hover:bg-blue-700 text-white'
                      }`}
                    >
                      {copied === `endpoint-${endpoint.id}` ? t('config.openWebUI.copied') : t('config.openWebUI.copyUrl')}
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Quick setup reminder */}
        <div className="mt-4 p-2 sm:p-3 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg">
          <p className="text-xs sm:text-sm text-amber-800 dark:text-amber-200">
            <strong>{t('config.quickSetup.title')}</strong> {t('config.quickSetup.auth')}
            <span className="hidden sm:inline"> •</span><span className="sm:hidden">,</span>
            {t('config.quickSetup.filter')} <code className="bg-amber-100 dark:bg-amber-900 px-1 rounded text-xs">,</code> <span className="text-amber-600 dark:text-amber-400">{t('config.quickSetup.comma')}</span>
          </p>
        </div>

        {/* Important troubleshooting note */}
        <details className="mt-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg group">
          <summary className="p-3 sm:p-4 cursor-pointer list-none flex items-center gap-2 hover:bg-blue-100/50 dark:hover:bg-blue-900/30 rounded-lg">
            <svg className="w-4 h-4 sm:w-5 sm:h-5 text-blue-600 dark:text-blue-400 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
            </svg>
            <span className="font-medium text-sm sm:text-base text-blue-900 dark:text-blue-100">{t('config.troubleshooting.title')}</span>
            <svg className="w-4 h-4 text-blue-400 transition-transform group-open:rotate-180 ml-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </summary>
          <div className="px-3 sm:px-4 pb-3 sm:pb-4 text-xs sm:text-sm text-blue-800 dark:text-blue-200 space-y-2">
            <p>
              {t('config.troubleshooting.description')}
            </p>
            <p><strong>{t('config.troubleshooting.solutionsTitle')}</strong></p>
            <ul className="list-disc list-inside ml-1 sm:ml-2 space-y-1">
              <li>{t('config.troubleshooting.solution1')}</li>
              <li className="break-words">{t('config.troubleshooting.solution2')}</li>
              <li>{t('config.troubleshooting.solution3')}</li>
            </ul>
          </div>
        </details>
      </div>

      {/* System Prompt - Collapsible */}
      <details className="bg-white dark:bg-gray-800 rounded-lg shadow group">
        <summary className="p-3 sm:p-4 cursor-pointer list-none flex items-center justify-between hover:bg-gray-50 dark:hover:bg-gray-700 rounded-lg">
          <div className="flex items-center gap-2 sm:gap-3 min-w-0">
            <svg className="w-4 h-4 sm:w-5 sm:h-5 text-purple-600 flex-shrink-0" viewBox="0 0 24 24" fill="currentColor">
              <path d="M20 2H4c-1.1 0-1.99.9-1.99 2L2 22l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm-2 12H6v-2h12v2zm0-3H6V9h12v2zm0-3H6V6h12v2z"/>
            </svg>
            <div className="min-w-0">
              <h3 className="font-medium text-sm sm:text-base text-gray-900 dark:text-white truncate">
                {t('config.systemPrompt.title')}
              </h3>
              <p className="text-xs sm:text-sm text-gray-500 dark:text-gray-400">
                {serverStatus?.enabled_services?.length || 0} {t('config.systemPrompt.services')} • {tools?.total || 0} {t('config.systemPrompt.tools')}
              </p>
            </div>
          </div>
          <svg className="w-4 h-4 sm:w-5 sm:h-5 text-gray-400 transition-transform group-open:rotate-180 flex-shrink-0 ml-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </summary>
        <div className="p-3 sm:p-4 pt-0 border-t border-gray-100 dark:border-gray-700">
          {serverStatus?.enabled_services && serverStatus.enabled_services.length > 0 && (
            <div className="flex flex-wrap gap-1 mb-3">
              {serverStatus.enabled_services.map(service => {
                const info = SERVICE_DESCRIPTIONS[service.toLowerCase()];
                return (
                  <span
                    key={service}
                    className="px-1.5 sm:px-2 py-0.5 text-xs bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200 rounded-full"
                    title={info?.description || ''}
                  >
                    {info?.name || service}
                  </span>
                );
              })}
            </div>
          )}
          <div className="relative">
            <pre className="bg-gray-900 text-gray-100 p-3 sm:p-4 rounded-lg overflow-x-auto text-xs sm:text-sm whitespace-pre-wrap max-h-60 sm:max-h-80 overflow-y-auto">
              <code>{systemPrompt}</code>
            </pre>
            <button
              onClick={() => copyToClipboard(systemPrompt, 'system-prompt')}
              className={`absolute top-2 right-2 px-2 sm:px-3 py-1 sm:py-1.5 text-xs sm:text-sm font-medium rounded-lg transition-colors ${
                copied === 'system-prompt'
                  ? 'bg-green-600 text-white'
                  : 'bg-purple-600 hover:bg-purple-700 text-white'
              }`}
            >
              {copied === 'system-prompt' ? t('config.systemPrompt.copied') : t('config.systemPrompt.copy')}
            </button>
          </div>
          <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">
            <span className="hidden sm:inline">{t('config.systemPrompt.location')}</span>
            <span className="sm:hidden">{t('config.systemPrompt.locationMobile')}</span>
          </p>
        </div>
      </details>

      {/* Other configurations - Collapsible */}
      <details className="bg-white dark:bg-gray-800 rounded-lg shadow group">
        <summary className="p-3 sm:p-4 cursor-pointer list-none flex items-center justify-between hover:bg-gray-50 dark:hover:bg-gray-700 rounded-lg">
          <div className="flex items-center gap-2 sm:gap-3 min-w-0">
            <svg className="w-4 h-4 sm:w-5 sm:h-5 text-gray-600 flex-shrink-0" viewBox="0 0 24 24" fill="currentColor">
              <path d="M20 4H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zm0 14H4V8h16v10z"/>
            </svg>
            <div className="min-w-0">
              <h3 className="font-medium text-sm sm:text-base text-gray-900 dark:text-white">
                {t('config.otherConfigs.title')}
              </h3>
              <p className="text-xs sm:text-sm text-gray-500 dark:text-gray-400 truncate">
                {t('config.otherConfigs.subtitle')}
              </p>
            </div>
          </div>
          <svg className="w-4 h-4 sm:w-5 sm:h-5 text-gray-400 transition-transform group-open:rotate-180 flex-shrink-0 ml-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </summary>
        <div className="p-3 sm:p-4 pt-0 border-t border-gray-100 dark:border-gray-700 space-y-3 sm:space-y-4">
          {/* API Documentation Link */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
            <div>
              <p className="font-medium text-sm text-gray-900 dark:text-white">{t('config.otherConfigs.apiDocs.title')}</p>
              <p className="text-xs text-gray-500 dark:text-gray-400">{t('config.otherConfigs.apiDocs.description')}</p>
            </div>
            <a
              href={`${backendUrl}/docs`}
              target="_blank"
              rel="noopener noreferrer"
              className="px-3 py-1.5 text-xs sm:text-sm bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium text-center"
            >
              {t('config.otherConfigs.apiDocs.button')}
            </a>
          </div>

          {/* Claude Desktop */}
          <div className="p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
            <p className="font-medium text-sm text-gray-900 dark:text-white mb-2">{t('config.otherConfigs.claudeDesktop.title')}</p>
            <p className="text-xs text-gray-500 dark:text-gray-400 mb-2 break-all">{t('config.otherConfigs.claudeDesktop.description')}
              <code className="bg-gray-200 dark:bg-gray-600 px-1 rounded text-xs">~/.config/Claude/claude_desktop_config.json</code>
            </p>
            <div className="relative">
              <pre className="bg-gray-900 text-gray-100 p-3 rounded text-xs overflow-x-auto">
{`{
  "mcpServers": {
    "mcparr-gateway": {
      "command": "python",
      "args": ["-m", "src.mcp.main"],
      "cwd": "/path/to/ia-homelab/backend"
    }
  }
}`}
              </pre>
              <button
                onClick={() => copyToClipboard(`{
  "mcpServers": {
    "mcparr-gateway": {
      "command": "python",
      "args": ["-m", "src.mcp.main"],
      "cwd": "/path/to/ia-homelab/backend"
    }
  }
}`, 'claude-config')}
                className={`absolute top-1 right-1 px-2 py-1 text-xs rounded transition-colors ${
                  copied === 'claude-config'
                    ? 'bg-green-600 text-white'
                    : 'bg-gray-600 hover:bg-gray-500 text-white'
                }`}
              >
                {copied === 'claude-config' ? t('config.otherConfigs.claudeDesktop.copied') : t('config.otherConfigs.claudeDesktop.copy')}
              </button>
            </div>
          </div>
        </div>
      </details>
    </div>
  );
};

export default function MCP() {
  const { t } = useTranslation('mcp');
  const [activeTab, setActiveTab] = useState<'overview' | 'history' | 'tools' | 'config'>('overview');
  const [stats, setStats] = useState<McpStats | null>(null);
  const [toolUsage, setToolUsage] = useState<McpToolUsage[]>([]);
  const [hourlyUsage, setHourlyUsage] = useState<McpHourlyUsage[]>([]);
  const [userStats, setUserStats] = useState<McpUserStats[]>([]);
  const [userServiceStats, setUserServiceStats] = useState<McpUserServiceStats[]>([]);
  const [hourlyUserUsage, setHourlyUserUsage] = useState<McpHourlyUserUsage[]>([]);
  const [requests, setRequests] = useState<McpRequest[]>([]);
  const [tools, setTools] = useState<McpToolsResponse | null>(null);
  const [toolGroups, setToolGroups] = useState<Record<string, ToolGroup[]>>({});
  const [totalRequests, setTotalRequests] = useState(0);
  const [loading, setLoading] = useState(true);
  const [selectedRequest, setSelectedRequest] = useState<McpRequest | null>(null);
  const [selectedToolToTest, setSelectedToolToTest] = useState<McpTool | null>(null);
  const [timeRange, setTimeRange] = useState(24);
  const [categoryFilter, setCategoryFilter] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [expandedServices, setExpandedServices] = useState<Set<string>>(new Set());

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [statsRes, toolUsageRes, hourlyRes, userStatsRes, userServiceStatsRes, hourlyUserRes, requestsRes, toolsRes, toolGroupsRes] = await Promise.all([
        api.mcp.stats(timeRange).catch(() => null),
        api.mcp.toolUsage(timeRange).catch(() => []),
        api.mcp.hourlyUsage(timeRange).catch(() => []),
        api.mcp.userStats(timeRange).catch(() => []),
        api.mcp.userServiceStats(timeRange).catch(() => []),
        api.mcp.hourlyUsageByUser(timeRange).catch(() => []),
        api.mcp.requests.list({
          limit: 50,
          ...(categoryFilter && { category: categoryFilter }),
          ...(statusFilter && { status: statusFilter }),
        }).catch(() => ({ items: [], total: 0 })),
        api.mcp.tools().catch(() => null),
        api.groups.toolsWithGroups().catch(() => ({ tool_groups: {} })),
      ]);

      if (statsRes) setStats(statsRes);
      setToolUsage(toolUsageRes);
      setHourlyUsage(hourlyRes);
      setUserStats(userStatsRes);
      setUserServiceStats(userServiceStatsRes);
      setHourlyUserUsage(hourlyUserRes);
      setRequests(requestsRes.items || []);
      setTotalRequests(requestsRes.total || 0);
      if (toolsRes) setTools(toolsRes);
      if (toolGroupsRes) setToolGroups(toolGroupsRes.tool_groups || {});
    } catch (error) {
      console.error('Failed to fetch MCP data:', error);
    } finally {
      setLoading(false);
    }
  }, [timeRange, categoryFilter, statusFilter]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Group tools by service instead of category
  const toolsByService = useMemo(() => {
    if (!tools?.tools) return {};

    const grouped: Record<string, McpTool[]> = {};

    tools.tools.forEach((tool) => {
      const serviceName = tool.requires_service || getServiceFromToolName(tool.name) || 'system';
      if (!grouped[serviceName]) {
        grouped[serviceName] = [];
      }
      grouped[serviceName].push(tool);
    });

    // Sort services alphabetically, but put 'system' at the end
    const sortedServices = Object.keys(grouped).sort((a, b) => {
      if (a === 'system') return 1;
      if (b === 'system') return -1;
      return a.localeCompare(b);
    });

    const sorted: Record<string, McpTool[]> = {};
    sortedServices.forEach((service) => {
      sorted[service] = grouped[service];
    });

    return sorted;
  }, [tools]);

  // Calculate usage stats by service
  const usageByService = useMemo(() => {
    if (!toolUsage?.length) return {};

    const byService: Record<string, { count: number; avgDuration: number; successRate: number }> = {};

    toolUsage.forEach((tool) => {
      const serviceName = getServiceFromToolName(tool.tool_name) || 'system';
      if (!byService[serviceName]) {
        byService[serviceName] = { count: 0, avgDuration: 0, successRate: 0 };
      }
      byService[serviceName].count += tool.usage_count;
      byService[serviceName].avgDuration += tool.avg_duration_ms * tool.usage_count;
      byService[serviceName].successRate += tool.success_rate * tool.usage_count;
    });

    // Calculate averages
    Object.keys(byService).forEach((service) => {
      if (byService[service].count > 0) {
        byService[service].avgDuration = Math.round(byService[service].avgDuration / byService[service].count);
        byService[service].successRate = Math.round(byService[service].successRate / byService[service].count);
      }
    });

    return byService;
  }, [toolUsage]);

  // Toggle service expansion
  const toggleService = (serviceName: string) => {
    setExpandedServices((prev) => {
      const next = new Set(prev);
      if (next.has(serviceName)) {
        next.delete(serviceName);
      } else {
        next.add(serviceName);
      }
      return next;
    });
  };

  // Expand/collapse all services
  const toggleAllServices = (expand: boolean) => {
    if (expand) {
      setExpandedServices(new Set(Object.keys(toolsByService)));
    } else {
      setExpandedServices(new Set());
    }
  };

  const formatDuration = (ms: number | null): string => {
    if (ms === null) return '-';
    if (ms < 1000) return `${ms}ms`;
    return `${(ms / 1000).toFixed(2)}s`;
  };

  const formatDate = (date: string): string => {
    return new Date(date).toLocaleString();
  };

  return (
    <div className="p-4 sm:p-6 space-y-4 sm:space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <Bot className="w-6 h-6 sm:w-8 sm:h-8 text-blue-600" />
            MCP Server
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Model Context Protocol - Analytics et historique
          </p>
        </div>
        <div className="flex items-center gap-2">
          <select
            value={timeRange}
            onChange={(e) => setTimeRange(Number(e.target.value))}
            className="px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
          >
            <option value={1}>1h</option>
            <option value={6}>6h</option>
            <option value={24}>24h</option>
            <option value={72}>3j</option>
            <option value={168}>7j</option>
          </select>
          <button
            onClick={fetchData}
            className="p-2 sm:px-4 sm:py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-200 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors flex items-center gap-2"
          >
            <RefreshCw className="w-4 h-4" />
            <span className="hidden sm:inline">{t('refresh')}</span>
          </button>
        </div>
      </div>

      {/* Tab Navigation - Compact horizontal pills */}
      <div className="mb-4 sm:mb-6 overflow-x-auto -mx-4 px-4 sm:mx-0 sm:px-0">
        <nav className="flex gap-1.5 sm:gap-2 min-w-max sm:min-w-0 sm:flex-wrap">
          {[
            { id: 'overview' as const, labelKey: 'statsShort', labelFullKey: 'statsFull', icon: BarChart3 },
            { id: 'history' as const, labelKey: 'historyShort', labelFullKey: 'historyFull', icon: History },
            { id: 'tools' as const, labelKey: 'toolsShort', labelFullKey: 'toolsFull', icon: Wrench },
            { id: 'config' as const, labelKey: 'configShort', labelFullKey: 'configFull', icon: Settings },
          ].map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;

            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                title={t(`tabs.${tab.labelFullKey}`)}
                className={`flex items-center gap-1.5 py-1.5 px-2.5 sm:py-2 sm:px-3 rounded-full font-medium text-xs sm:text-sm transition-all whitespace-nowrap ${
                  isActive
                    ? 'bg-blue-600 text-white shadow-sm'
                    : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
                }`}
              >
                <Icon className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
                <span>{t(`tabs.${tab.labelKey}`)}</span>
              </button>
            );
          })}
        </nav>
      </div>

      {loading ? (
        <div className="text-center py-12 text-gray-500">Loading MCP data...</div>
      ) : (
        <>
          {/* Overview Tab */}
          {activeTab === 'overview' && (
            <div className="space-y-6">
              {/* Stats Grid */}
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-2 sm:gap-4">
                <StatCard
                  title="Total Requests"
                  value={stats?.total || 0}
                  subtitle={`Last ${timeRange}h`}
                  color="blue"
                />
                <StatCard
                  title="Success Rate"
                  value={`${stats?.success_rate || 100}%`}
                  subtitle={`${stats?.by_status?.completed || 0} completed`}
                  color={stats?.success_rate && stats.success_rate < 90 ? 'red' : 'green'}
                />
                <StatCard
                  title="Avg Duration"
                  value={formatDuration(stats?.average_duration_ms || null)}
                  subtitle="Per request"
                  color="purple"
                />
                <StatCard
                  title="Failed"
                  value={stats?.by_status?.failed || 0}
                  subtitle="Errors encountered"
                  color={(stats?.by_status?.failed || 0) > 0 ? 'red' : 'gray'}
                />
              </div>

              {/* Hourly Usage Chart */}
              <HourlyUsageChart data={hourlyUsage} timeRange={timeRange} />

              {/* Tool Usage & Categories */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Top Tools */}
                <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow">
                  <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
                    Top Tools
                  </h3>
                  {toolUsage.length > 0 ? (
                    <div className="space-y-2">
                      {toolUsage.slice(0, 10).map((tool, index) => {
                        const serviceName = getServiceFromToolName(tool.tool_name) || 'system';
                        const colors = getServiceColor(serviceName);
                        const maxUsage = Math.max(...toolUsage.map(t => t.usage_count));
                        const percentage = (tool.usage_count / maxUsage) * 100;

                        return (
                        <div key={tool.tool_name} className="group">
                          <div className="flex items-center gap-3">
                            {/* Rank */}
                            <span className="text-xs font-medium text-gray-400 w-4">{index + 1}</span>
                            {/* Color dot */}
                            <span className={`w-2 h-2 rounded-full ${colors.dot}`} title={serviceName} />
                            {/* Tool name */}
                            <span className="text-sm text-gray-900 dark:text-white flex-1 truncate" title={tool.tool_name}>
                              {tool.tool_name.replace(`${serviceName}_`, '')}
                            </span>
                            {/* Stats */}
                            <span className="text-xs tabular-nums text-gray-500 dark:text-gray-400">
                              {tool.usage_count}
                            </span>
                            <span className={`text-xs tabular-nums ${tool.success_rate >= 90 ? 'text-green-600 dark:text-green-400' : tool.success_rate >= 50 ? 'text-yellow-600 dark:text-yellow-400' : 'text-red-600 dark:text-red-400'}`}>
                              {tool.success_rate}%
                            </span>
                          </div>
                          {/* Progress bar */}
                          <div className="ml-7 mt-1 h-1 bg-gray-100 dark:bg-gray-700 rounded-full overflow-hidden">
                            <div
                              className="h-full rounded-full transition-all"
                              style={{ width: `${percentage}%`, backgroundColor: colors.hex }}
                            />
                          </div>
                        </div>
                        );
                      })}
                    </div>
                  ) : (
                    <p className="text-gray-500 dark:text-gray-400">No tool usage data</p>
                  )}
                </div>

                {/* By Service */}
                <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow">
                  <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
                    Par Service
                  </h3>
                  {Object.keys(usageByService).length > 0 ? (
                    <div className="space-y-3">
                      {Object.entries(usageByService)
                        .sort((a, b) => b[1].count - a[1].count)
                        .map(([serviceName, serviceStats]) => {
                          const colors = getServiceColor(serviceName);
                          const Icon = colors.icon;
                          const totalUsage = Object.values(usageByService).reduce((sum, s) => sum + s.count, 0);
                          const percentage = totalUsage > 0 ? (serviceStats.count / totalUsage) * 100 : 0;

                          return (
                            <div key={serviceName} className="flex items-center gap-3">
                              {/* Icon with color background */}
                              <div className={`p-1.5 rounded-lg ${colors.bg}`}>
                                <Icon className={`w-4 h-4 ${colors.text}`} />
                              </div>
                              {/* Service info + bar */}
                              <div className="flex-1 min-w-0">
                                <div className="flex items-center justify-between mb-1">
                                  <span className="text-sm font-medium text-gray-900 dark:text-white capitalize">
                                    {serviceName}
                                  </span>
                                  <div className="flex items-center gap-2">
                                    <span className="text-xs tabular-nums text-gray-600 dark:text-gray-400">
                                      {serviceStats.count}
                                    </span>
                                    <span className={`text-xs tabular-nums ${serviceStats.successRate >= 90 ? 'text-green-600 dark:text-green-400' : serviceStats.successRate >= 50 ? 'text-yellow-600 dark:text-yellow-400' : 'text-red-600 dark:text-red-400'}`}>
                                      {serviceStats.successRate}%
                                    </span>
                                  </div>
                                </div>
                                <div className="w-full bg-gray-100 dark:bg-gray-700 rounded-full h-1.5 overflow-hidden">
                                  <div
                                    className="h-full rounded-full transition-all"
                                    style={{ width: `${percentage}%`, backgroundColor: colors.hex }}
                                  />
                                </div>
                              </div>
                            </div>
                          );
                        })}
                    </div>
                  ) : (
                    <p className="text-gray-500 dark:text-gray-400">{t('stats.noUsageData')}</p>
                  )}
                </div>
              </div>

              {/* Bottom row: Status donut + Performance metrics + Quick stats */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {/* Status Donut - Compact */}
                <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow">
                  <h3 className="text-sm font-medium text-gray-900 dark:text-white mb-3">
                    Par Status
                  </h3>
                  {stats?.by_status && Object.keys(stats.by_status).length > 0 ? (
                    <StatusDonutChart data={stats.by_status} total={stats.total} />
                  ) : (
                    <div className="flex items-center justify-center h-24">
                      <p className="text-sm text-gray-500 dark:text-gray-400">{t('stats.noData')}</p>
                    </div>
                  )}
                </div>

                {/* Performance by Service - Bar chart style */}
                <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow">
                  <h3 className="text-sm font-medium text-gray-900 dark:text-white mb-3">
                    Durée moyenne par service
                  </h3>
                  {toolUsage.length > 0 ? (
                    <div className="space-y-2">
                      {(() => {
                        // Calculate avg duration per service
                        const serviceAvgDuration: Record<string, { total: number; count: number }> = {};
                        toolUsage.forEach(tool => {
                          const serviceName = getServiceFromToolName(tool.tool_name) || 'other';
                          if (!serviceAvgDuration[serviceName]) {
                            serviceAvgDuration[serviceName] = { total: 0, count: 0 };
                          }
                          serviceAvgDuration[serviceName].total += tool.avg_duration_ms * tool.usage_count;
                          serviceAvgDuration[serviceName].count += tool.usage_count;
                        });

                        const serviceDurations = Object.entries(serviceAvgDuration)
                          .map(([name, data]) => ({
                            name,
                            avgMs: data.count > 0 ? data.total / data.count : 0
                          }))
                          .sort((a, b) => b.avgMs - a.avgMs)
                          .slice(0, 5);

                        const maxDuration = Math.max(...serviceDurations.map(s => s.avgMs), 1);

                        return serviceDurations.map(service => {
                          const colors = getServiceColor(service.name);
                          const percentage = (service.avgMs / maxDuration) * 100;
                          return (
                            <div key={service.name} className="flex items-center gap-2">
                              <span className="text-xs text-gray-600 dark:text-gray-400 w-16 truncate capitalize">
                                {service.name}
                              </span>
                              <div className="flex-1 h-4 bg-gray-100 dark:bg-gray-700 rounded overflow-hidden">
                                <div
                                  className="h-full rounded transition-all"
                                  style={{ width: `${percentage}%`, backgroundColor: colors.hex }}
                                />
                              </div>
                              <span className="text-xs font-mono text-gray-700 dark:text-gray-300 w-14 text-right">
                                {service.avgMs >= 1000
                                  ? `${(service.avgMs / 1000).toFixed(1)}s`
                                  : `${Math.round(service.avgMs)}ms`}
                              </span>
                            </div>
                          );
                        });
                      })()}
                    </div>
                  ) : (
                    <div className="flex items-center justify-center h-24">
                      <p className="text-sm text-gray-500 dark:text-gray-400">{t('stats.noData')}</p>
                    </div>
                  )}
                </div>

                {/* Quick Stats Cards */}
                <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow">
                  <h3 className="text-sm font-medium text-gray-900 dark:text-white mb-3">
                    Highlights
                  </h3>
                  <div className="space-y-3">
                    {/* Most used tool */}
                    {toolUsage.length > 0 && (
                      <div className="flex items-center gap-3 p-2 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                        <div className="p-1.5 bg-blue-100 dark:bg-blue-800 rounded">
                          <BarChart3 className="w-4 h-4 text-blue-600 dark:text-blue-400" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-xs text-gray-500 dark:text-gray-400">Plus utilisé</p>
                          <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
                            {toolUsage[0]?.tool_name.replace(/^(plex_|tautulli_|overseerr_|zammad_|komga_|ollama_|openwebui_)/, '')}
                          </p>
                        </div>
                        <span className="text-sm font-bold text-blue-600 dark:text-blue-400">
                          {toolUsage[0]?.usage_count}
                        </span>
                      </div>
                    )}

                    {/* Fastest tool */}
                    {toolUsage.length > 0 && (
                      <div className="flex items-center gap-3 p-2 bg-green-50 dark:bg-green-900/20 rounded-lg">
                        <div className="p-1.5 bg-green-100 dark:bg-green-800 rounded">
                          <RefreshCw className="w-4 h-4 text-green-600 dark:text-green-400" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-xs text-gray-500 dark:text-gray-400">Plus rapide</p>
                          <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
                            {[...toolUsage].sort((a, b) => a.avg_duration_ms - b.avg_duration_ms)[0]?.tool_name.replace(/^(plex_|tautulli_|overseerr_|zammad_|komga_|ollama_|openwebui_)/, '')}
                          </p>
                        </div>
                        <span className="text-sm font-bold text-green-600 dark:text-green-400">
                          {Math.round([...toolUsage].sort((a, b) => a.avg_duration_ms - b.avg_duration_ms)[0]?.avg_duration_ms || 0)}ms
                        </span>
                      </div>
                    )}

                    {/* Error rate highlight */}
                    {stats && (
                      <div className={`flex items-center gap-3 p-2 rounded-lg ${
                        stats.success_rate >= 95
                          ? 'bg-emerald-50 dark:bg-emerald-900/20'
                          : stats.success_rate >= 80
                            ? 'bg-yellow-50 dark:bg-yellow-900/20'
                            : 'bg-red-50 dark:bg-red-900/20'
                      }`}>
                        <div className={`p-1.5 rounded ${
                          stats.success_rate >= 95
                            ? 'bg-emerald-100 dark:bg-emerald-800'
                            : stats.success_rate >= 80
                              ? 'bg-yellow-100 dark:bg-yellow-800'
                              : 'bg-red-100 dark:bg-red-800'
                        }`}>
                          <History className={`w-4 h-4 ${
                            stats.success_rate >= 95
                              ? 'text-emerald-600 dark:text-emerald-400'
                              : stats.success_rate >= 80
                                ? 'text-yellow-600 dark:text-yellow-400'
                                : 'text-red-600 dark:text-red-400'
                          }`} />
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-xs text-gray-500 dark:text-gray-400">Fiabilité</p>
                          <p className="text-sm font-medium text-gray-900 dark:text-white">
                            {stats.success_rate >= 95 ? 'Excellente' : stats.success_rate >= 80 ? 'Correcte' : 'À surveiller'}
                          </p>
                        </div>
                        <span className={`text-sm font-bold ${
                          stats.success_rate >= 95
                            ? 'text-emerald-600 dark:text-emerald-400'
                            : stats.success_rate >= 80
                              ? 'text-yellow-600 dark:text-yellow-400'
                              : 'text-red-600 dark:text-red-400'
                        }`}>
                          {stats.success_rate}%
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {/* User Statistics Section */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* User Stats Chart */}
                <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow">
                  <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
                    Requêtes par utilisateur
                  </h3>
                  <UserStatsChart data={userStats} />
                </div>

                {/* User Service Breakdown */}
                <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow">
                  <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
                    Services par utilisateur
                  </h3>
                  <UserServiceChart data={userServiceStats} />
                </div>
              </div>

              {/* Hourly Usage by User - Stacked Chart */}
              <HourlyUserStackedChart data={hourlyUserUsage} timeRange={timeRange} />
            </div>
          )}

          {/* History Tab */}
          {activeTab === 'history' && (
            <div className="space-y-4">
              {/* Filters */}
              <div className="flex gap-4 bg-white dark:bg-gray-800 p-4 rounded-lg shadow">
                <select
                  value={categoryFilter}
                  onChange={(e) => setCategoryFilter(e.target.value)}
                  className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                >
                  <option value="">All Categories</option>
                  <option value="media">Media</option>
                  <option value="requests">Requests</option>
                  <option value="support">Support</option>
                  <option value="system">System</option>
                  <option value="users">Users</option>
                </select>
                <select
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                  className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                >
                  <option value="">All Statuses</option>
                  <option value="pending">Pending</option>
                  <option value="processing">Processing</option>
                  <option value="completed">Completed</option>
                  <option value="failed">Failed</option>
                </select>
                <span className="ml-auto text-sm text-gray-500 self-center">
                  {totalRequests} total requests
                </span>
              </div>

              {/* Request List - Mobile: Card view, Desktop: Table view */}
              {/* Mobile Cards */}
              <div className="sm:hidden space-y-3">
                {requests.length > 0 ? (
                  requests.map((request) => (
                    <div
                      key={request.id}
                      className="bg-white dark:bg-gray-800 rounded-lg shadow p-4"
                      onClick={() => setSelectedRequest(request)}
                    >
                      <div className="flex items-start justify-between mb-2">
                        <div className="min-w-0 flex-1">
                          <span className="text-sm font-medium text-gray-900 dark:text-white block truncate">
                            {request.tool_name}
                          </span>
                          <span className="text-xs text-gray-500">
                            {new Date(request.created_at).toLocaleString()}
                          </span>
                        </div>
                        <StatusBadge status={request.status} />
                      </div>
                      <div className="flex items-center gap-2 flex-wrap">
                        <ServiceBadge toolName={request.tool_name} />
                        {request.tool_category && <CategoryBadge category={request.tool_category} />}
                        {request.user_display_name && (
                          <span className="text-xs text-gray-500">par {request.user_display_name}</span>
                        )}
                        <span className="text-xs text-gray-400 ml-auto">
                          {formatDuration(request.duration_ms)}
                        </span>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="text-center py-12 text-gray-500 dark:text-gray-400">
                    {t('history.noRequests')}
                  </div>
                )}
              </div>

              {/* Desktop Table */}
              <div className="hidden sm:block bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden">
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                    <thead className="bg-gray-50 dark:bg-gray-700">
                      <tr>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                          Outil
                        </th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                          Service
                        </th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                          User
                        </th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                          Statut
                        </th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                          Duree
                        </th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                          Date
                        </th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">

                        </th>
                      </tr>
                    </thead>
                    <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                      {requests.length > 0 ? (
                        requests.map((request) => (
                          <tr key={request.id} className="hover:bg-gray-50 dark:hover:bg-gray-700">
                            <td className="px-4 py-3 whitespace-nowrap">
                              <span className="text-sm font-medium text-gray-900 dark:text-white">
                                {request.tool_name}
                              </span>
                            </td>
                            <td className="px-4 py-3 whitespace-nowrap">
                              <ServiceBadge toolName={request.tool_name} />
                            </td>
                            <td className="px-4 py-3 whitespace-nowrap">
                              {request.user_id ? (
                                <span className="text-sm text-gray-900 dark:text-white" title={request.user_id}>
                                  {request.user_display_name || (request.user_id.includes('@') ? request.user_id.split('@')[0] : request.user_id.substring(0, 8))}
                                </span>
                              ) : (
                                <span className="text-sm text-gray-400 dark:text-gray-500">-</span>
                              )}
                            </td>
                            <td className="px-4 py-3 whitespace-nowrap">
                              <StatusBadge status={request.status} />
                            </td>
                            <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                              {formatDuration(request.duration_ms)}
                            </td>
                            <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                              {formatDate(request.created_at)}
                            </td>
                            <td className="px-4 py-3 whitespace-nowrap">
                              <button
                                onClick={() => setSelectedRequest(request)}
                                className="text-blue-600 hover:text-blue-900 dark:text-blue-400 dark:hover:text-blue-300 text-sm"
                              >
                                Details
                              </button>
                            </td>
                          </tr>
                        ))
                      ) : (
                        <tr>
                          <td colSpan={7} className="px-4 py-12 text-center text-gray-500 dark:text-gray-400">
                            {t('history.noRequests')}
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* Tools Tab */}
          {activeTab === 'tools' && (
            <div className="space-y-4">
              {/* Controls */}
              <div className="flex items-center justify-between bg-white dark:bg-gray-800 rounded-lg p-4 shadow">
                <div className="text-sm text-gray-600 dark:text-gray-400">
                  {t('tools.toolsAvailable', { count: tools?.total || 0, services: Object.keys(toolsByService).length })}
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => toggleAllServices(true)}
                    className="px-3 py-1.5 text-xs font-medium text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700"
                  >
                    {t('tools.expandAll')}
                  </button>
                  <button
                    onClick={() => toggleAllServices(false)}
                    className="px-3 py-1.5 text-xs font-medium text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700"
                  >
                    {t('tools.collapseAll')}
                  </button>
                </div>
              </div>

              {/* Services List */}
              {Object.keys(toolsByService).length > 0 ? (
                Object.entries(toolsByService).map(([serviceName, serviceTools]) => {
                  const colors = getServiceColor(serviceName);
                  const Icon = colors.icon;
                  const isExpanded = expandedServices.has(serviceName);

                  return (
                    <div
                      key={serviceName}
                      className={`rounded-lg shadow overflow-hidden border ${colors.border}`}
                    >
                      {/* Service Header - Clickable */}
                      <button
                        onClick={() => toggleService(serviceName)}
                        className={`w-full flex items-center justify-between p-4 ${colors.bg} hover:opacity-90 transition-opacity`}
                      >
                        <div className="flex items-center gap-3">
                          <div className={`p-2 rounded-lg ${colors.badge} ${colors.badgeDark}`}>
                            <Icon className="w-5 h-5" />
                          </div>
                          <div className="text-left">
                            <h3 className={`font-semibold capitalize ${colors.text}`}>
                              {serviceName}
                            </h3>
                            <p className="text-sm text-gray-500 dark:text-gray-400">
                              {serviceTools.length} outil{serviceTools.length !== 1 ? 's' : ''}
                            </p>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          {isExpanded ? (
                            <ChevronDown className="w-5 h-5 text-gray-500" />
                          ) : (
                            <ChevronRight className="w-5 h-5 text-gray-500" />
                          )}
                        </div>
                      </button>

                      {/* Tools Grid - Collapsible */}
                      {isExpanded && (
                        <div className="p-4 bg-white dark:bg-gray-800">
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            {serviceTools.map((tool) => (
                              <div
                                key={tool.name}
                                className={`border rounded-lg p-4 ${colors.border}`}
                              >
                                <div className="flex items-start justify-between">
                                  <div className="flex-1 min-w-0">
                                    <h4 className="font-medium text-gray-900 dark:text-white">
                                      {tool.name}
                                    </h4>
                                    <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                                      {tool.description}
                                    </p>
                                    {/* Group Labels */}
                                    {toolGroups[tool.name] && toolGroups[tool.name].length > 0 && (
                                      <div className="flex flex-wrap gap-1 mt-2">
                                        {toolGroups[tool.name].map((group) => (
                                          <span
                                            key={group.id}
                                            className="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium"
                                            style={{
                                              backgroundColor: `${group.color || '#6366f1'}15`,
                                              color: group.color || '#6366f1',
                                              border: `1px solid ${group.color || '#6366f1'}30`
                                            }}
                                            title={`Accès via groupe ${group.name}`}
                                          >
                                            {group.name}
                                          </span>
                                        ))}
                                      </div>
                                    )}
                                  </div>
                                  <div className="flex flex-col gap-1 items-end ml-2">
                                    {tool.is_mutation && (
                                      <span className="px-2 py-1 text-xs bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200 rounded flex-shrink-0">
                                        Mutation
                                      </span>
                                    )}
                                    <button
                                      onClick={() => setSelectedToolToTest(tool)}
                                      className="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium text-green-700 dark:text-green-400 bg-green-50 dark:bg-green-900/30 hover:bg-green-100 dark:hover:bg-green-900/50 rounded transition-colors"
                                    >
                                      <Play className="w-3 h-3" />
                                      {t('tools.test')}
                                    </button>
                                  </div>
                                </div>
                                {tool.parameters.length > 0 && (
                                  <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700">
                                    <p className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-2">
                                      {t('tools.parameters')}:
                                    </p>
                                    <div className="space-y-1">
                                      {tool.parameters.map((param) => (
                                        <div key={param.name} className="flex items-center text-xs">
                                          <span className={`font-mono ${param.required ? 'text-red-600 dark:text-red-400' : 'text-gray-600 dark:text-gray-400'}`}>
                                            {param.name}
                                            {param.required && '*'}
                                          </span>
                                          <span className="text-gray-400 dark:text-gray-500 ml-2">
                                            ({param.type})
                                          </span>
                                        </div>
                                      ))}
                                    </div>
                                  </div>
                                )}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })
              ) : (
                <div className="text-center py-12 text-gray-500">{t('tools.noTools')}</div>
              )}
            </div>
          )}

          {/* Configuration Tab */}
          {activeTab === 'config' && <ConfigurationTab tools={tools} />}
        </>
      )}

      {/* Request Details Modal */}
      {selectedRequest && (
        <div className="fixed inset-0 z-50 overflow-y-auto">
          <div className="flex items-center justify-center min-h-screen px-4">
            <div className="fixed inset-0 bg-black bg-opacity-50" onClick={() => setSelectedRequest(null)} />
            <div className="relative bg-white dark:bg-gray-800 rounded-lg max-w-2xl w-full p-6 shadow-xl">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-medium text-gray-900 dark:text-white">
                  Request Details
                </h3>
                <button
                  onClick={() => setSelectedRequest(null)}
                  className="text-gray-400 hover:text-gray-500"
                >
                  <span className="text-2xl">&times;</span>
                </button>
              </div>

              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm text-gray-500 dark:text-gray-400">Tool</p>
                    <p className="font-medium text-gray-900 dark:text-white">{selectedRequest.tool_name}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-500 dark:text-gray-400">Category</p>
                    {selectedRequest.tool_category && <CategoryBadge category={selectedRequest.tool_category} />}
                  </div>
                  <div>
                    <p className="text-sm text-gray-500 dark:text-gray-400">User</p>
                    <p className="text-gray-900 dark:text-white" title={selectedRequest.user_id || undefined}>
                      {selectedRequest.user_display_name || selectedRequest.user_id || '-'}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-500 dark:text-gray-400">Status</p>
                    <StatusBadge status={selectedRequest.status} />
                  </div>
                  <div>
                    <p className="text-sm text-gray-500 dark:text-gray-400">Duration</p>
                    <p className="text-gray-900 dark:text-white">{formatDuration(selectedRequest.duration_ms)}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-500 dark:text-gray-400">Created</p>
                    <p className="text-gray-900 dark:text-white">{formatDate(selectedRequest.created_at)}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-500 dark:text-gray-400">Completed</p>
                    <p className="text-gray-900 dark:text-white">
                      {selectedRequest.completed_at ? formatDate(selectedRequest.completed_at) : '-'}
                    </p>
                  </div>
                </div>

                {selectedRequest.input_params && Object.keys(selectedRequest.input_params).length > 0 && (
                  <div>
                    <p className="text-sm text-gray-500 dark:text-gray-400 mb-2">Input Parameters</p>
                    <pre className="bg-gray-50 dark:bg-gray-900 p-3 rounded-lg text-xs overflow-x-auto">
                      {JSON.stringify(selectedRequest.input_params, null, 2)}
                    </pre>
                  </div>
                )}

                {selectedRequest.output_result && (
                  <div>
                    <p className="text-sm text-gray-500 dark:text-gray-400 mb-2">Result</p>
                    <pre className="bg-gray-50 dark:bg-gray-900 p-3 rounded-lg text-xs overflow-x-auto max-h-48">
                      {JSON.stringify(selectedRequest.output_result, null, 2)}
                    </pre>
                  </div>
                )}

                {selectedRequest.error_message && (
                  <div>
                    <p className="text-sm text-gray-500 dark:text-gray-400 mb-2">Error</p>
                    <p className="text-red-600 dark:text-red-400 text-sm bg-red-50 dark:bg-red-900/20 p-3 rounded-lg">
                      {selectedRequest.error_message}
                    </p>
                  </div>
                )}
              </div>

              <div className="mt-6 flex justify-end">
                <button
                  onClick={() => setSelectedRequest(null)}
                  className="px-4 py-2 bg-gray-200 dark:bg-gray-700 text-gray-900 dark:text-white rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tool Test Modal */}
      <ToolTestModal
        tool={selectedToolToTest}
        isOpen={selectedToolToTest !== null}
        onClose={() => setSelectedToolToTest(null)}
      />
    </div>
  );
}
