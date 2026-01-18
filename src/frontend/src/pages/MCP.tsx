import { useState, useEffect, useCallback, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { Bot, RefreshCw, BarChart3, History, Wrench, Settings, ChevronDown, ChevronRight, Play, X, Loader2, TrendingUp, TrendingDown, Minus, Link2, Workflow, ArrowRight, Square, CircleDot, Calendar, AlertTriangle } from 'lucide-react';
import { useSearchParams } from 'react-router-dom';
import { ToolChainManagement } from '../components/ToolChains';
import { GlobalSearchConfig, GlobalSearchInfoBlock } from '../components/MCP';
import { HelpTooltip } from '../components/common';
import { api, getApiBaseUrl } from '../lib/api';
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

interface McpStatsComparison {
  total: number;
  total_change: number | null;
  average_duration_ms: number;
  duration_change: number | null;
  success_rate: number;
  success_rate_change: number | null;
  completed: number;
  completed_change: number | null;
  failed: number;
  failed_change: number | null;
}

interface McpStats {
  total: number;
  by_status: Record<string, number>;
  by_category: Record<string, number>;
  top_tools: Record<string, number>;
  average_duration_ms: number;
  success_rate: number;
  period_hours: number;
  comparison?: McpStatsComparison;
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
  denied_count?: number;
  granularity?: 'minute' | 'hour' | 'day';
}

interface McpUserStats {
  user_id: string;
  user_display_name: string | null;
  request_count: number;
  avg_duration_ms: number;
  success_count: number;
  failed_count: number;
  denied_count: number;
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
  granularity?: string;
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
    denied: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200',
    cancelled: 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200',
  };

  return (
    <span className={`px-2 py-1 text-xs font-medium rounded-full ${colors[status] || colors.pending}`}>
      {status}
    </span>
  );
};

// Stacked bar chart component for usage with auto-granularity (minute/hour/day)
interface HourlyUsageChartProps {
  data: McpHourlyUsage[];
  startTime: string;
  endTime: string;
  granularity: 'auto' | 'minute' | 'hour' | 'day';
}

const HourlyUsageChart = ({ data, startTime, endTime, granularity: selectedGranularity }: HourlyUsageChartProps) => {
  const { t } = useTranslation('mcp');

  // Calculate period in hours
  const start = new Date(startTime);
  const end = new Date(endTime);
  const periodHours = (end.getTime() - start.getTime()) / (1000 * 60 * 60);

  // Use granularity from API data if available, otherwise calculate based on selection
  // This ensures frontend slots match the backend's actual grouping
  const actualGranularity = data.length > 0 && data[0].granularity
    ? data[0].granularity as 'minute' | 'hour' | 'day'
    : selectedGranularity === 'auto'
      ? (periodHours <= 1 ? 'minute' : periodHours <= 72 ? 'hour' : 'day')
      : selectedGranularity;

  // Calculate expected number of slots to check if it's too many
  const expectedSlots = actualGranularity === 'minute'
    ? periodHours * 60
    : actualGranularity === 'hour'
      ? periodHours
      : periodHours / 24;

  // Max slots to render (to avoid performance issues)
  // 750 allows 30 days at hour granularity (30 * 24 = 720)
  const MAX_SLOTS = 750;
  const tooManySlots = expectedSlots > MAX_SLOTS;

  // Generate all time slots for the period (using UTC to match backend)
  const generateTimeSlots = (): string[] => {
    // If too many slots, don't generate (will show warning instead)
    if (tooManySlots) return [];

    const slots: string[] = [];
    const current = new Date(start);

    // Round to the appropriate granularity (in UTC)
    if (actualGranularity === 'minute') {
      current.setUTCSeconds(0, 0);
    } else if (actualGranularity === 'hour') {
      current.setUTCMinutes(0, 0, 0);
    } else {
      current.setUTCHours(0, 0, 0, 0);
    }

    while (current <= end) {
      const year = current.getUTCFullYear();
      const month = String(current.getUTCMonth() + 1).padStart(2, '0');
      const day = String(current.getUTCDate()).padStart(2, '0');
      const hour = String(current.getUTCHours()).padStart(2, '0');
      const minute = String(current.getUTCMinutes()).padStart(2, '0');

      if (actualGranularity === 'minute') {
        slots.push(`${year}-${month}-${day} ${hour}:${minute}:00`);
        current.setUTCMinutes(current.getUTCMinutes() + 1);
      } else if (actualGranularity === 'hour') {
        slots.push(`${year}-${month}-${day} ${hour}:00:00`);
        current.setUTCHours(current.getUTCHours() + 1);
      } else {
        slots.push(`${year}-${month}-${day} 00:00:00`);
        current.setUTCDate(current.getUTCDate() + 1);
      }
    }
    return slots;
  };

  // Create lookup from data
  const dataLookup = new Map(data.map(d => [d.hour, d]));
  const allSlots = generateTimeSlots();

  // Format label based on granularity
  const formatLabel = (hourStr: string): string => {
    const [datePart, timePart] = hourStr.split(' ');
    const [, month, day] = datePart.split('-');
    const [hour, minute] = (timePart || '00:00:00').split(':');

    if (actualGranularity === 'day') {
      return `${day}/${month}`;
    } else if (actualGranularity === 'minute') {
      return `${hour}:${minute}`;
    } else {
      // Hour granularity - show date if data spans multiple days
      if (periodHours > 24) {
        return `${day}/${month} ${hour}h`;
      }
      return `${hour}:00`;
    }
  };

  // Build hours array with all slots (filled or empty)
  const hours = allSlots.map(slot => {
    const d = dataLookup.get(slot);
    return {
      key: slot,
      count: d?.count || 0,
      success: d?.success_count || 0,
      failed: d?.failed_count || 0,
      denied: d?.denied_count || 0,
      label: formatLabel(slot)
    };
  });

  const maxCount = Math.max(...hours.map(h => h.count), 1);
  const chartHeight = 128; // pixels (h-32)

  // Show warning if too many slots
  if (tooManySlots) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-medium text-gray-900 dark:text-white">
            {t('stats.requestsOverTime')}
          </h3>
        </div>
        <div className="flex flex-col items-center justify-center py-8 text-center">
          <div className="text-amber-500 dark:text-amber-400 mb-2">
            <AlertTriangle className="w-8 h-8 mx-auto" />
          </div>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            {t('stats.tooManyDataPoints', { count: Math.round(expectedSlots), max: MAX_SLOTS })}
          </p>
          <p className="text-xs text-gray-500 dark:text-gray-500 mt-1">
            {t('stats.reduceGranularityOrPeriod')}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-medium text-gray-900 dark:text-white">
          {t('stats.requestsOverTime')}
        </h3>
        <div className="flex items-center gap-3 text-xs">
          <div className="flex items-center gap-1">
            <div className="w-3 h-3 rounded-sm bg-green-500" />
            <span className="text-gray-500 dark:text-gray-400">{t('stats.success')}</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-3 h-3 rounded-sm bg-red-500" />
            <span className="text-gray-500 dark:text-gray-400">{t('stats.failed')}</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-3 h-3 rounded-sm bg-orange-500" />
            <span className="text-gray-500 dark:text-gray-400">{t('status.denied')}</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-3 h-3 rounded-sm bg-gray-300 dark:bg-gray-600" />
            <span className="text-gray-500 dark:text-gray-400">{t('stats.noDataForPeriod')}</span>
          </div>
        </div>
      </div>
      <div className="flex items-end gap-0.5" style={{ height: `${chartHeight}px` }}>
        {hours.map((h, i) => {
          const totalHeight = h.count > 0 ? Math.max((h.count / maxCount) * chartHeight, 8) : 6;
          const successRatio = h.count > 0 ? h.success / h.count : 0;
          const failedRatio = h.count > 0 ? h.failed / h.count : 0;
          const deniedRatio = h.count > 0 ? h.denied / h.count : 0;
          const successHeight = totalHeight * successRatio;
          const failedHeight = totalHeight * failedRatio;
          const deniedHeight = totalHeight * deniedRatio;
          const isLast = i === hours.length - 1;
          const hasTopSegment = failedHeight > 0 || deniedHeight > 0;

          return (
            <div
              key={i}
              className="flex-1 flex flex-col items-center justify-end group relative"
              title={`${h.label}: ${h.count} req (${h.success} ok, ${h.failed} err, ${h.denied} denied)`}
            >
              {/* Tooltip on hover */}
              <div className="absolute bottom-full mb-2 hidden group-hover:block z-10">
                <div className="bg-gray-900 text-white text-xs rounded px-2 py-1 whitespace-nowrap">
                  {h.label}: {h.count} ({h.success} ✓, {h.failed} ✗, {h.denied} ⊘)
                </div>
              </div>
              {h.count === 0 ? (
                // No data - gray bar
                <div
                  className={`w-full rounded-sm bg-gray-300 dark:bg-gray-600 ${isLast ? 'opacity-100' : 'opacity-50'}`}
                  style={{ height: '6px' }}
                />
              ) : (
                // Stacked bar: failed on top, denied in middle, success on bottom
                <div className="w-full flex flex-col-reverse">
                  {/* Success (green) - bottom */}
                  {successHeight > 0 && (
                    <div
                      className={`w-full rounded-b-sm ${!hasTopSegment ? 'rounded-t-sm' : ''} ${isLast ? 'bg-green-500' : 'bg-green-400 dark:bg-green-500/80'}`}
                      style={{ height: `${successHeight}px` }}
                    />
                  )}
                  {/* Denied (orange) - middle */}
                  {deniedHeight > 0 && (
                    <div
                      className={`w-full ${successHeight === 0 ? 'rounded-b-sm' : ''} ${failedHeight === 0 ? 'rounded-t-sm' : ''} ${isLast ? 'bg-orange-500' : 'bg-orange-400 dark:bg-orange-500/80'}`}
                      style={{ height: `${deniedHeight}px` }}
                    />
                  )}
                  {/* Failed (red) - top */}
                  {failedHeight > 0 && (
                    <div
                      className={`w-full ${successHeight === 0 && deniedHeight === 0 ? 'rounded-b-sm' : ''} rounded-t-sm ${isLast ? 'bg-red-500' : 'bg-red-400 dark:bg-red-500/80'}`}
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

// Trend indicator component
const TrendIndicator = ({
  change,
  inverted = false,
  isAbsolute = false,
}: {
  change: number | null | undefined;
  inverted?: boolean; // true means decrease is good
  isAbsolute?: boolean; // true for absolute change (like success rate points)
}) => {
  if (change === null || change === undefined) return null;

  const isPositive = change > 0;
  const isNeutral = change === 0;
  const isGood = inverted ? !isPositive : isPositive;

  if (isNeutral) {
    return (
      <span className="inline-flex items-center gap-0.5 text-[9px] sm:text-[10px] text-gray-400">
        <Minus className="w-3 h-3" />
        0{isAbsolute ? 'pt' : '%'}
      </span>
    );
  }

  return (
    <span className={`inline-flex items-center gap-0.5 text-[9px] sm:text-[10px] ${
      isGood ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'
    }`}>
      {isPositive ? (
        <TrendingUp className="w-3 h-3" />
      ) : (
        <TrendingDown className="w-3 h-3" />
      )}
      {isPositive ? '+' : ''}{isAbsolute ? change.toFixed(1) : change.toFixed(0)}{isAbsolute ? 'pt' : '%'}
    </span>
  );
};

const StatCard = ({ title, value, subtitle, color = 'blue', change, changeInverted, changeAbsolute }: {
  title: string;
  value: string | number;
  subtitle?: string;
  color?: string;
  change?: number | null;
  changeInverted?: boolean;
  changeAbsolute?: boolean;
}) => (
  <div className="bg-white dark:bg-gray-800 rounded-lg p-2.5 sm:p-4 shadow">
    <p className="text-xs sm:text-sm text-gray-500 dark:text-gray-400 truncate">{title}</p>
    <div className="flex items-center gap-2">
      <p className={`text-lg sm:text-2xl font-bold text-${color}-600 dark:text-${color}-400`}>
        {value}
      </p>
      <TrendIndicator change={change} inverted={changeInverted} isAbsolute={changeAbsolute} />
    </div>
    {subtitle && (
      <p className="text-[10px] sm:text-xs text-gray-400 dark:text-gray-500 mt-0.5 sm:mt-1 truncate">{subtitle}</p>
    )}
  </div>
);

// Donut chart component for status breakdown
const StatusDonutChart = ({ data, total }: { data: Record<string, number>; total: number }) => {
  const { t } = useTranslation('mcp');
  const statusColors: Record<string, { stroke: string; fill: string }> = {
    completed: { stroke: '#22c55e', fill: 'bg-green-500' },
    failed: { stroke: '#ef4444', fill: 'bg-red-500' },
    denied: { stroke: '#f97316', fill: 'bg-orange-500' },
    pending: { stroke: '#eab308', fill: 'bg-yellow-500' },
    processing: { stroke: '#3b82f6', fill: 'bg-blue-500' },
    cancelled: { stroke: '#6b7280', fill: 'bg-gray-500' },
  };

  const size = 120;
  const strokeWidth = 20;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const center = size / 2;

  // Sort entries so completed is first (largest usually)
  const entries = Object.entries(data).sort((a, b) => {
    const order = ['completed', 'failed', 'denied', 'pending', 'processing', 'cancelled'];
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
          <span className="text-xs text-gray-500 dark:text-gray-400">{t('stats.total')}</span>
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
              <span className="text-sm text-gray-700 dark:text-gray-300">{t(`status.${status}`)}</span>
              <span className="text-sm font-semibold text-gray-900 dark:text-white">{count}</span>
              <span className="text-xs text-gray-500 dark:text-gray-400">({percentage}%)</span>
            </div>
          );
        })}
      </div>
    </div>
  );
};

// Chain Badge - Shows chain info for requests that triggered next tools
const ChainBadge = ({
  request,
  onChainClick,
}: {
  request: McpRequest;
  onChainClick?: () => void;
}) => {
  const { t } = useTranslation('mcp');
  const chainContext = request.output_result?.chain_context;
  const nextTools = request.output_result?.next_tools_to_call;

  if (!chainContext && (!nextTools || nextTools.length === 0)) return null;

  const position = chainContext?.position || 'start';
  const chains = chainContext?.chains || [];
  const chainName = chains[0]?.name;
  const chainColor = chains[0]?.color || '#8b5cf6';
  const stepNumber = chainContext?.step_number;

  // Position-specific styling
  const positionIcons = {
    start: <Play className="w-3 h-3" />,
    middle: <CircleDot className="w-3 h-3" />,
    end: <Square className="w-3 h-3" />,
  };

  const positionLabels = {
    start: t('history.chainStart'),
    middle: t('history.chainMiddle'),
    end: t('history.chainEnd'),
  };

  return (
    <button
      onClick={(e) => {
        e.stopPropagation();
        onChainClick?.();
      }}
      className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium transition-colors hover:opacity-80"
      style={{
        backgroundColor: `${chainColor}20`,
        color: chainColor,
      }}
      title={`${positionLabels[position as keyof typeof positionLabels] || position}${stepNumber ? ` (${t('history.step')} ${stepNumber})` : ''} - ${chainName || t('history.chainTriggered')}`}
    >
      {positionIcons[position as keyof typeof positionIcons]}
      {stepNumber && (
        <>
          <ArrowRight className="w-3 h-3" />
          <span>{stepNumber}</span>
        </>
      )}
    </button>
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

  return (
    <div className="space-y-3">
      {data.slice(0, 8).map((user, index) => {
        const color = getUserColor(index);
        const displayName = user.user_display_name || user.user_id.split('@')[0] || user.user_id.substring(0, 8);

        // Calculate percentages within the user's total (bar is always full width)
        const total = user.request_count || 1;
        const successPct = (user.success_count / total) * 100;
        const deniedPct = ((user.denied_count || 0) / total) * 100;
        const failedPct = (user.failed_count / total) * 100;

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
            {/* Full-width bar with stacked segments */}
            <div className="h-2 bg-gray-100 dark:bg-gray-700 rounded-full overflow-hidden flex">
              {/* Success segment - green */}
              {successPct > 0 && (
                <div
                  className="h-full bg-green-500 transition-all duration-500"
                  style={{ width: `${successPct}%` }}
                  title={`${t('stats.completed')}: ${user.success_count}`}
                />
              )}
              {/* Denied segment - orange */}
              {deniedPct > 0 && (
                <div
                  className="h-full bg-orange-500 transition-all duration-500"
                  style={{ width: `${deniedPct}%` }}
                  title={`${t('stats.denied')}: ${user.denied_count || 0}`}
                />
              )}
              {/* Failed segment - red */}
              {failedPct > 0 && (
                <div
                  className="h-full bg-red-500 transition-all duration-500"
                  style={{ width: `${failedPct}%` }}
                  title={`${t('stats.failed')}: ${user.failed_count}`}
                />
              )}
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

  // Sort users by total
  const sortedUsers = Object.entries(byUser).sort((a, b) => b[1].total - a[1].total).slice(0, 6);

  return (
    <div className="space-y-3">
      {sortedUsers.map(([userId, userData]) => (
          <div key={userId} className="group">
            <div className="flex items-center justify-between mb-1">
              <span className="text-sm font-medium text-gray-900 dark:text-white truncate" title={userId}>
                {userData.displayName}
              </span>
              <span className="text-xs tabular-nums text-gray-600 dark:text-gray-400">
                {userData.total}
              </span>
            </div>
            <div className="h-3 bg-gray-100 dark:bg-gray-700 rounded-full overflow-hidden flex w-full">
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
        ))}
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
interface HourlyUserStackedChartProps {
  data: McpHourlyUserUsage[];
  startTime: string;
  endTime: string;
  granularity: 'auto' | 'minute' | 'hour' | 'day';
}

const HourlyUserStackedChart = ({ data, startTime, endTime, granularity: selectedGranularity }: HourlyUserStackedChartProps) => {
  const { t } = useTranslation('mcp');

  // Calculate period in hours
  const start = new Date(startTime);
  const end = new Date(endTime);
  const periodHours = (end.getTime() - start.getTime()) / (1000 * 60 * 60);

  // Determine actual granularity
  const actualGranularity = selectedGranularity === 'auto'
    ? (periodHours <= 1 ? 'minute' : periodHours <= 72 ? 'hour' : 'day')
    : selectedGranularity;

  // Calculate expected slots and check limit
  const expectedSlots = actualGranularity === 'minute'
    ? periodHours * 60
    : actualGranularity === 'hour'
      ? periodHours
      : periodHours / 24;
  const MAX_SLOTS = 750;
  const tooManySlots = expectedSlots > MAX_SLOTS;

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

  // Generate all time slots (using UTC to match backend)
  const generateTimeSlots = (): string[] => {
    if (tooManySlots) return [];
    const slots: string[] = [];
    const current = new Date(start);

    if (actualGranularity === 'minute') {
      current.setUTCSeconds(0, 0);
    } else if (actualGranularity === 'hour') {
      current.setUTCMinutes(0, 0, 0);
    } else {
      current.setUTCHours(0, 0, 0, 0);
    }

    while (current <= end) {
      const year = current.getUTCFullYear();
      const month = String(current.getUTCMonth() + 1).padStart(2, '0');
      const day = String(current.getUTCDate()).padStart(2, '0');
      const hour = String(current.getUTCHours()).padStart(2, '0');
      const minute = String(current.getUTCMinutes()).padStart(2, '0');

      if (actualGranularity === 'minute') {
        slots.push(`${year}-${month}-${day} ${hour}:${minute}:00`);
        current.setUTCMinutes(current.getUTCMinutes() + 1);
      } else if (actualGranularity === 'hour') {
        slots.push(`${year}-${month}-${day} ${hour}:00:00`);
        current.setUTCHours(current.getUTCHours() + 1);
      } else {
        slots.push(`${year}-${month}-${day} 00:00:00`);
        current.setUTCDate(current.getUTCDate() + 1);
      }
    }
    return slots;
  };

  const allSlots = generateTimeSlots();

  // Format label based on granularity
  const formatLabel = (hourStr: string): string => {
    const [datePart, timePart] = hourStr.split(' ');
    const [, month, day] = datePart.split('-');
    const [hour, minute] = (timePart || '00:00:00').split(':');

    if (actualGranularity === 'day') {
      return `${day}/${month}`;
    } else if (actualGranularity === 'minute') {
      return `${hour}:${minute}`;
    } else {
      if (periodHours > 24) {
        return `${day}/${month} ${hour}h`;
      }
      return `${hour}:00`;
    }
  };

  // Group data by time bucket
  const dataByHour: Record<string, { byUser: Record<string, number>; total: number }> = {};
  data.forEach(d => {
    if (!dataByHour[d.hour]) {
      dataByHour[d.hour] = { byUser: {}, total: 0 };
    }
    dataByHour[d.hour].byUser[d.user_id] = (dataByHour[d.hour].byUser[d.user_id] || 0) + d.count;
    dataByHour[d.hour].total += d.count;
  });

  // Build hours array with all slots
  const hours = allSlots.map(slot => ({
    hour: slot,
    label: formatLabel(slot),
    byUser: dataByHour[slot]?.byUser || {},
    total: dataByHour[slot]?.total || 0
  }));

  const maxCount = Math.max(...hours.map(h => h.total), 1);
  const chartHeight = 140;

  // Show warning if too many slots
  if (tooManySlots) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow">
        <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
          {t('stats.requestsByUser')}
        </h3>
        <div className="flex flex-col items-center justify-center py-8 text-center">
          <div className="text-amber-500 dark:text-amber-400 mb-2">
            <AlertTriangle className="w-8 h-8 mx-auto" />
          </div>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            {t('stats.tooManyDataPoints', { count: Math.round(expectedSlots), max: MAX_SLOTS })}
          </p>
          <p className="text-xs text-gray-500 dark:text-gray-500 mt-1">
            {t('stats.reduceGranularityOrPeriod')}
          </p>
        </div>
      </div>
    );
  }

  if (users.length === 0 && hours.every(h => h.total === 0)) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow">
        <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
          {t('stats.requestsByUser')}
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
          {t('stats.requestsByUser')}
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

// Descriptions des services pour le prompt système - avec mots-clés pour meilleure sélection d'outil
const SERVICE_DESCRIPTIONS: Record<string, { name: string; description: string }> = {
  system: { name: 'Système', description: 'Monitoring serveur, CPU, mémoire, disque, logs, alertes' },
  plex: { name: 'Plex', description: 'Films et séries TV en streaming VIDÉO (regarder des vidéos)' },
  tautulli: { name: 'Tautulli', description: 'Statistiques Plex: qui regarde quoi, historique de visionnage' },
  overseerr: { name: 'Overseerr', description: 'Demander un film ou série TV non disponible' },
  openwebui: { name: 'Open WebUI', description: 'Interface IA, modèles LLM' },
  radarr: { name: 'Radarr', description: 'Télécharger/ajouter des FILMS, file d\'attente films' },
  sonarr: { name: 'Sonarr', description: 'Télécharger/ajouter des SÉRIES TV, file d\'attente séries' },
  prowlarr: { name: 'Prowlarr', description: 'Indexeurs torrents centralisés, recherche sur indexeurs' },
  jackett: { name: 'Jackett', description: 'Proxy indexeurs torrents alternatif' },
  deluge: { name: 'Deluge', description: 'Torrents actifs, téléchargements en cours, vitesse' },
  komga: { name: 'Komga', description: 'Comics, mangas, BD, bandes dessinées (LECTURE de BD)' },
  romm: { name: 'RomM', description: 'ROMs de jeux vidéo rétro, émulateurs, jeux retro gaming' },
  audiobookshelf: { name: 'Audiobookshelf', description: 'LIVRES AUDIO, audiobooks, podcasts, ÉCOUTER (PAS vidéo!)' },
  wikijs: { name: 'Wiki.js', description: 'Documentation, wiki, tutoriels, pages de documentation' },
  zammad: { name: 'Zammad', description: 'Tickets de support, problèmes, demandes d\'aide' },
  authentik: { name: 'Authentik', description: 'Utilisateurs SSO, groupes, authentification' },
  ollama: { name: 'Ollama', description: 'Modèles IA locaux, LLM' },
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

  // Générer le guide de sélection d'outils dynamiquement
  let toolSelectionGuide = `\n## ${t('systemPrompt.toolSelectionGuide')}\n\n${t('systemPrompt.toolSelectionIntro')}\n\n`;
  toolSelectionGuide += `| ${t('systemPrompt.contentType')} | ${t('systemPrompt.serviceToUse')} | ${t('systemPrompt.toolToUse')} |\n`;
  toolSelectionGuide += `|---|---|---|\n`;

  // Ajouter les lignes pour chaque service activé
  if (enabledServices.includes('audiobookshelf')) {
    toolSelectionGuide += `| ${t('systemPrompt.toolSelection.audiobook.content')} | ${t('systemPrompt.toolSelection.audiobook.service')} | ${t('systemPrompt.toolSelection.audiobook.tool')} |\n`;
  }
  if (enabledServices.includes('plex')) {
    toolSelectionGuide += `| ${t('systemPrompt.toolSelection.video.content')} | ${t('systemPrompt.toolSelection.video.service')} | ${t('systemPrompt.toolSelection.video.tool')} |\n`;
  }
  if (enabledServices.includes('komga')) {
    toolSelectionGuide += `| ${t('systemPrompt.toolSelection.comic.content')} | ${t('systemPrompt.toolSelection.comic.service')} | ${t('systemPrompt.toolSelection.comic.tool')} |\n`;
  }
  if (enabledServices.includes('romm')) {
    toolSelectionGuide += `| ${t('systemPrompt.toolSelection.game.content')} | ${t('systemPrompt.toolSelection.game.service')} | ${t('systemPrompt.toolSelection.game.tool')} |\n`;
  }
  if (enabledServices.includes('zammad')) {
    toolSelectionGuide += `| ${t('systemPrompt.toolSelection.ticket.content')} | ${t('systemPrompt.toolSelection.ticket.service')} | ${t('systemPrompt.toolSelection.ticket.tool')} |\n`;
  }
  if (enabledServices.includes('wikijs')) {
    toolSelectionGuide += `| ${t('systemPrompt.toolSelection.wiki.content')} | ${t('systemPrompt.toolSelection.wiki.service')} | ${t('systemPrompt.toolSelection.wiki.tool')} |\n`;
  }
  if (enabledServices.includes('deluge')) {
    toolSelectionGuide += `| ${t('systemPrompt.toolSelection.torrent.content')} | ${t('systemPrompt.toolSelection.torrent.service')} | ${t('systemPrompt.toolSelection.torrent.tool')} |\n`;
  }
  if (enabledServices.includes('radarr')) {
    toolSelectionGuide += `| ${t('systemPrompt.toolSelection.movieDownload.content')} | ${t('systemPrompt.toolSelection.movieDownload.service')} | ${t('systemPrompt.toolSelection.movieDownload.tool')} |\n`;
  }
  if (enabledServices.includes('sonarr')) {
    toolSelectionGuide += `| ${t('systemPrompt.toolSelection.seriesDownload.content')} | ${t('systemPrompt.toolSelection.seriesDownload.service')} | ${t('systemPrompt.toolSelection.seriesDownload.tool')} |\n`;
  }
  if (enabledServices.includes('tautulli')) {
    toolSelectionGuide += `| ${t('systemPrompt.toolSelection.plexStats.content')} | ${t('systemPrompt.toolSelection.plexStats.service')} | ${t('systemPrompt.toolSelection.plexStats.tool')} |\n`;
  }
  if (enabledServices.includes('overseerr')) {
    toolSelectionGuide += `| ${t('systemPrompt.toolSelection.request.content')} | ${t('systemPrompt.toolSelection.request.service')} | ${t('systemPrompt.toolSelection.request.tool')} |\n`;
  }
  if (enabledServices.includes('authentik')) {
    toolSelectionGuide += `| ${t('systemPrompt.toolSelection.sso.content')} | ${t('systemPrompt.toolSelection.sso.service')} | ${t('systemPrompt.toolSelection.sso.tool')} |\n`;
  }

  // System prompt simplifié - l'IA utilise list_available_tools pour découvrir les outils
  return `${t('systemPrompt.simple.intro')}

${t('systemPrompt.simple.rules')}

${t('systemPrompt.language')}`;
};

const ConfigurationTab = ({ tools }: { tools: McpToolsResponse | null }) => {
  const { t } = useTranslation('mcp');
  const [copied, setCopied] = useState<string | null>(null);
  const [serverStatus, setServerStatus] = useState<McpServerStatus | null>(null);
  const [_statusLoading, setStatusLoading] = useState(true);
  const [_statusError, setStatusError] = useState<string | null>(null);

  // Auto-configuration state
  const [autoConfigLoading, setAutoConfigLoading] = useState(false);
  const [autoConfigResult, setAutoConfigResult] = useState<{
    success: boolean;
    message: string;
    configured_groups?: string[];
    total_tools?: number;
    errors?: string[];
  } | null>(null);
  const [mcparrExternalUrl, setMcparrExternalUrl] = useState('');
  // Endpoint mode: 'all' = single endpoint, 'group' = per category, 'service' = per service, 'serviceGroup' = custom service groups
  const [endpointMode, setEndpointMode] = useState<'all' | 'group' | 'service' | 'serviceGroup'>('group');
  // Groups match backend OPENWEBUI_TOOL_GROUPS keys (for 'group' mode)
  const [selectedGroups, setSelectedGroups] = useState<Record<string, boolean>>({
    media: true,
    books: true,
    download: true,
    games: true,
    system: true,
    knowledge: false,
    auth: true,
  });
  // Services for 'service' mode
  const [selectedServices, setSelectedServices] = useState<Record<string, boolean>>({
    plex: true,
    tautulli: true,
    overseerr: true,
    radarr: true,
    sonarr: true,
    prowlarr: true,
    jackett: false,
    deluge: true,
    komga: true,
    audiobookshelf: true,
    romm: true,
    system: true,
    zammad: true,
    openwebui: false,
    wikijs: false,
    authentik: true,
  });
  // Custom service groups for 'serviceGroup' mode
  const [customServiceGroups, setCustomServiceGroups] = useState<Array<{ id: string; name: string; service_types: string[] }>>([]);
  const [selectedServiceGroups, setSelectedServiceGroups] = useState<Record<string, boolean>>({});
  const [serviceGroupsLoading, setServiceGroupsLoading] = useState(false);
  const [useFunctionFilters, setUseFunctionFilters] = useState(true);

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

  // Fetch custom service groups when mode changes to 'serviceGroup'
  useEffect(() => {
    if (endpointMode === 'serviceGroup') {
      const fetchServiceGroups = async () => {
        setServiceGroupsLoading(true);
        try {
          const response = await api.serviceGroups.list(true); // Only enabled groups
          const groups = response.groups || [];
          setCustomServiceGroups(groups);
          // Initialize selection - all groups selected by default
          const initialSelection: Record<string, boolean> = {};
          groups.forEach((group: { id: string }) => {
            initialSelection[group.id] = true;
          });
          setSelectedServiceGroups(initialSelection);
        } catch (error) {
          console.error('Failed to fetch service groups:', error);
          setCustomServiceGroups([]);
        } finally {
          setServiceGroupsLoading(false);
        }
      };
      fetchServiceGroups();
    }
  }, [endpointMode]);

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

  const backendUrl = getApiBaseUrl();

  // Auto-configure Open WebUI handler
  const handleAutoConfigureOpenWebUI = async () => {
    if (!mcparrExternalUrl.trim()) {
      setAutoConfigResult({
        success: false,
        message: t('config.autoConfig.errorNoUrl'),
        errors: [t('config.autoConfig.errorNoUrlDetail')],
      });
      return;
    }

    // Build request body based on endpoint mode
    const requestBody: {
      mcparr_external_url: string;
      endpoint_mode: string;
      use_function_filters: boolean;
      groups?: string[];
      services?: string[];
      service_group_ids?: string[];
    } = {
      mcparr_external_url: mcparrExternalUrl.trim(),
      endpoint_mode: endpointMode,
      use_function_filters: useFunctionFilters,
    };

    if (endpointMode === 'group') {
      const groupsToConfig = Object.entries(selectedGroups)
        .filter(([, enabled]) => enabled)
        .map(([group]) => group);

      if (groupsToConfig.length === 0) {
        setAutoConfigResult({
          success: false,
          message: t('config.autoConfig.errorNoCategory'),
          errors: [t('config.autoConfig.errorNoCategoryDetail')],
        });
        return;
      }
      requestBody.groups = groupsToConfig;
    } else if (endpointMode === 'service') {
      const servicesToConfig = Object.entries(selectedServices)
        .filter(([, enabled]) => enabled)
        .map(([service]) => service);

      if (servicesToConfig.length === 0) {
        setAutoConfigResult({
          success: false,
          message: t('config.autoConfig.errorNoService'),
          errors: [t('config.autoConfig.errorNoServiceDetail')],
        });
        return;
      }
      requestBody.services = servicesToConfig;
    } else if (endpointMode === 'serviceGroup') {
      const serviceGroupIds = Object.entries(selectedServiceGroups)
        .filter(([, enabled]) => enabled)
        .map(([groupId]) => groupId);

      if (serviceGroupIds.length === 0) {
        setAutoConfigResult({
          success: false,
          message: t('config.autoConfig.errorNoServiceGroup'),
          errors: [t('config.autoConfig.errorNoServiceGroupDetail')],
        });
        return;
      }
      requestBody.service_group_ids = serviceGroupIds;
    }
    // For 'all' mode, no groups/services needed

    setAutoConfigLoading(true);
    setAutoConfigResult(null);

    try {
      const response = await fetch(`${backendUrl}/tools/configure_openwebui`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody),
      });

      const data = await response.json();
      setAutoConfigResult(data);
    } catch (error) {
      setAutoConfigResult({
        success: false,
        message: t('config.autoConfig.errorNetwork'),
        errors: [String(error)],
      });
    } finally {
      setAutoConfigLoading(false);
    }
  };

  // Check if Open WebUI service is configured
  const isOpenWebUIConfigured = serverStatus?.enabled_services?.some(
    (s) => s.toLowerCase() === 'openwebui' || s.toLowerCase() === 'open_webui'
  ) ?? false;

  return (
    <div className="space-y-6">
      {/* Section 1: Auto-configuration for Open WebUI */}
      <div className="bg-white dark:bg-gray-800 rounded-lg p-4 sm:p-6 shadow">
        <div className="flex items-center gap-2 mb-4">
          <svg className="w-5 h-5 sm:w-6 sm:h-6 text-teal-600 flex-shrink-0" viewBox="0 0 24 24" fill="currentColor">
            <path d="M19.35 10.04C18.67 6.59 15.64 4 12 4 9.11 4 6.6 5.64 5.35 8.04 2.34 8.36 0 10.91 0 14c0 3.31 2.69 6 6 6h13c2.76 0 5-2.24 5-5 0-2.64-2.05-4.78-4.65-4.96zM14 13v4h-4v-4H7l5-5 5 5h-3z"/>
          </svg>
          <h3 className="text-base sm:text-lg font-medium text-gray-900 dark:text-white">
            {t('config.autoConfig.title')}
          </h3>
          <div className="flex-1" />
          <HelpTooltip topicId="config" />
        </div>

        {!isOpenWebUIConfigured ? (
          /* Not available message */
          <div className="p-4 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg">
            <p className="font-medium text-amber-800 dark:text-amber-200 mb-1">
              {t('config.autoConfig.notAvailable')}
            </p>
            <p className="text-sm text-amber-600 dark:text-amber-400">
              {t('config.autoConfig.notAvailableDetail')}
            </p>
          </div>
        ) : (
          /* Auto-configuration form */
          <div className="space-y-4">
            <p className="text-xs sm:text-sm text-gray-600 dark:text-gray-400">
              {t('config.autoConfig.description')}
            </p>

            {/* 1. Endpoint mode select - FIRST */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                {t('config.autoConfig.endpointMode.label')}
              </label>
              <select
                value={endpointMode}
                onChange={(e) => setEndpointMode(e.target.value as 'all' | 'group' | 'service' | 'serviceGroup')}
                className="w-full sm:w-auto px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-teal-500 focus:border-transparent"
              >
                <option value="group">{t('config.autoConfig.endpointMode.group')}</option>
                <option value="serviceGroup">{t('config.autoConfig.endpointMode.serviceGroup')}</option>
                <option value="service">{t('config.autoConfig.endpointMode.service')}</option>
                <option value="all">{t('config.autoConfig.endpointMode.all')}</option>
              </select>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                {t(`config.autoConfig.endpointMode.${endpointMode}Help`)}
              </p>
            </div>

            {/* 2. Conditional selection based on mode */}
            {endpointMode === 'group' && (
              <div className="p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg border border-gray-200 dark:border-gray-600">
                <p className="text-xs font-medium text-gray-700 dark:text-gray-300 mb-2">
                  {t('config.autoConfig.selectCategories')}
                </p>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                  {[
                    { id: 'media', label: t('config.autoConfig.groups.media') },
                    { id: 'books', label: t('config.autoConfig.groups.books') },
                    { id: 'download', label: t('config.autoConfig.groups.download') },
                    { id: 'games', label: t('config.autoConfig.groups.games') },
                    { id: 'system', label: t('config.autoConfig.groups.system') },
                    { id: 'knowledge', label: t('config.autoConfig.groups.knowledge') },
                    { id: 'auth', label: t('config.autoConfig.groups.auth') },
                  ].map((group) => (
                    <label
                      key={group.id}
                      className={`flex items-center gap-2 p-2 rounded-lg cursor-pointer transition-colors ${
                        selectedGroups[group.id]
                          ? 'bg-teal-100 dark:bg-teal-900/30 border border-teal-300 dark:border-teal-700'
                          : 'bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-600 hover:bg-gray-100 dark:hover:bg-gray-700'
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={selectedGroups[group.id]}
                        onChange={(e) => setSelectedGroups(prev => ({
                          ...prev,
                          [group.id]: e.target.checked
                        }))}
                        className="w-4 h-4 text-teal-600 bg-gray-100 border-gray-300 rounded focus:ring-teal-500"
                      />
                      <span className={`text-xs font-medium ${
                        selectedGroups[group.id] ? 'text-teal-800 dark:text-teal-200' : 'text-gray-600 dark:text-gray-400'
                      }`}>
                        {group.label}
                      </span>
                    </label>
                  ))}
                </div>
              </div>
            )}

            {endpointMode === 'service' && (
              <div className="p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg border border-gray-200 dark:border-gray-600">
                <p className="text-xs font-medium text-gray-700 dark:text-gray-300 mb-2">
                  {t('config.autoConfig.selectServices')}
                </p>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                  {[
                    { id: 'plex', label: 'Plex' },
                    { id: 'tautulli', label: 'Tautulli' },
                    { id: 'overseerr', label: 'Overseerr' },
                    { id: 'radarr', label: 'Radarr' },
                    { id: 'sonarr', label: 'Sonarr' },
                    { id: 'prowlarr', label: 'Prowlarr' },
                    { id: 'jackett', label: 'Jackett' },
                    { id: 'deluge', label: 'Deluge' },
                    { id: 'komga', label: 'Komga' },
                    { id: 'audiobookshelf', label: 'Audiobookshelf' },
                    { id: 'romm', label: 'RomM' },
                    { id: 'system', label: 'System' },
                    { id: 'zammad', label: 'Zammad' },
                    { id: 'openwebui', label: 'Open WebUI' },
                    { id: 'wikijs', label: 'Wiki.js' },
                    { id: 'authentik', label: 'Authentik' },
                  ].map((service) => (
                    <label
                      key={service.id}
                      className={`flex items-center gap-2 p-2 rounded-lg cursor-pointer transition-colors ${
                        selectedServices[service.id]
                          ? 'bg-teal-100 dark:bg-teal-900/30 border border-teal-300 dark:border-teal-700'
                          : 'bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-600 hover:bg-gray-100 dark:hover:bg-gray-700'
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={selectedServices[service.id]}
                        onChange={(e) => setSelectedServices(prev => ({
                          ...prev,
                          [service.id]: e.target.checked
                        }))}
                        className="w-4 h-4 text-teal-600 bg-gray-100 border-gray-300 rounded focus:ring-teal-500"
                      />
                      <span className={`text-xs font-medium ${
                        selectedServices[service.id] ? 'text-teal-800 dark:text-teal-200' : 'text-gray-600 dark:text-gray-400'
                      }`}>
                        {service.label}
                      </span>
                    </label>
                  ))}
                </div>
              </div>
            )}

            {endpointMode === 'serviceGroup' && (
              <div className="p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg border border-gray-200 dark:border-gray-600">
                <p className="text-xs font-medium text-gray-700 dark:text-gray-300 mb-2">
                  {t('config.autoConfig.selectServiceGroups')}
                </p>
                {serviceGroupsLoading ? (
                  <div className="flex items-center justify-center py-4">
                    <Loader2 className="w-5 h-5 animate-spin text-teal-600" />
                    <span className="ml-2 text-sm text-gray-500">{t('common:loading')}</span>
                  </div>
                ) : customServiceGroups.length === 0 ? (
                  <div className="text-center py-4">
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                      {t('config.autoConfig.noServiceGroups')}
                    </p>
                    <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">
                      {t('config.autoConfig.noServiceGroupsHint')}
                    </p>
                  </div>
                ) : (
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    {customServiceGroups.map((group) => (
                      <label
                        key={group.id}
                        className={`flex items-center gap-2 p-2 rounded-lg cursor-pointer transition-colors ${
                          selectedServiceGroups[group.id]
                            ? 'bg-teal-100 dark:bg-teal-900/30 border border-teal-300 dark:border-teal-700'
                            : 'bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-600 hover:bg-gray-100 dark:hover:bg-gray-700'
                        }`}
                      >
                        <input
                          type="checkbox"
                          checked={selectedServiceGroups[group.id] || false}
                          onChange={(e) => setSelectedServiceGroups(prev => ({
                            ...prev,
                            [group.id]: e.target.checked
                          }))}
                          className="w-4 h-4 text-teal-600 bg-gray-100 border-gray-300 rounded focus:ring-teal-500"
                        />
                        <div className="flex-1 min-w-0">
                          <span className={`text-xs font-medium block truncate ${
                            selectedServiceGroups[group.id] ? 'text-teal-800 dark:text-teal-200' : 'text-gray-600 dark:text-gray-400'
                          }`}>
                            {group.name}
                          </span>
                          <span className="text-[10px] text-gray-400 dark:text-gray-500">
                            {group.service_types.length} {t('config.autoConfig.servicesInGroup')}
                          </span>
                        </div>
                      </label>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* 3. Function filters checkbox */}
            <label className="flex items-start gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={useFunctionFilters}
                onChange={(e) => setUseFunctionFilters(e.target.checked)}
                className="w-4 h-4 mt-0.5 text-teal-600 bg-gray-100 border-gray-300 rounded focus:ring-teal-500"
              />
              <div>
                <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  {t('config.autoConfig.useFunctionFilters')}
                </span>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  {t('config.autoConfig.useFunctionFiltersHelp')}
                </p>
              </div>
            </label>

            {/* 4. URL input + button */}
            <div className="flex flex-col sm:flex-row gap-2">
              <input
                type="url"
                placeholder={t('config.autoConfig.urlPlaceholder')}
                value={mcparrExternalUrl}
                onChange={(e) => setMcparrExternalUrl(e.target.value)}
                className="flex-1 px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white placeholder-gray-400 focus:ring-2 focus:ring-teal-500 focus:border-transparent"
              />
              <button
                onClick={handleAutoConfigureOpenWebUI}
                disabled={autoConfigLoading || (endpointMode === 'group' && Object.values(selectedGroups).every(v => !v)) || (endpointMode === 'service' && Object.values(selectedServices).every(v => !v)) || (endpointMode === 'serviceGroup' && Object.values(selectedServiceGroups).every(v => !v))}
                className="px-4 py-2 text-sm font-medium text-white bg-teal-600 hover:bg-teal-700 disabled:bg-teal-400 disabled:cursor-not-allowed rounded-lg transition-colors flex items-center justify-center gap-2 whitespace-nowrap"
              >
                {autoConfigLoading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    {t('config.autoConfig.configuring')}
                  </>
                ) : (
                  <>
                    <Play className="w-4 h-4" />
                    {t('config.autoConfig.button')}
                  </>
                )}
              </button>
            </div>

            {/* Result message */}
            {autoConfigResult && (
              <div className={`p-3 rounded-lg ${
                autoConfigResult.success
                  ? 'bg-green-100 dark:bg-green-900/30 border border-green-300 dark:border-green-700'
                  : 'bg-red-100 dark:bg-red-900/30 border border-red-300 dark:border-red-700'
              }`}>
                <p className={`text-sm font-medium ${
                  autoConfigResult.success ? 'text-green-800 dark:text-green-200' : 'text-red-800 dark:text-red-200'
                }`}>
                  {autoConfigResult.message}
                </p>
                {autoConfigResult.success && autoConfigResult.configured_groups && (
                  <p className="text-xs text-green-600 dark:text-green-400 mt-1">
                    {t('config.autoConfig.successDetail', {
                      groups: autoConfigResult.configured_groups.length,
                      tools: autoConfigResult.total_tools,
                    })}
                  </p>
                )}
                {autoConfigResult.errors && autoConfigResult.errors.length > 0 && (
                  <ul className="text-xs text-red-600 dark:text-red-400 mt-1 list-disc list-inside">
                    {autoConfigResult.errors.map((error, i) => (
                      <li key={i}>{error}</li>
                    ))}
                  </ul>
                )}
              </div>
            )}

            <p className="text-xs text-gray-500 dark:text-gray-400">
              {t('config.autoConfig.requirement')}
            </p>
          </div>
        )}
      </div>

      {/* Section 2: Compact Endpoints Reference */}
      <details className="bg-white dark:bg-gray-800 rounded-lg shadow group">
        <summary className="p-3 sm:p-4 cursor-pointer list-none flex items-center justify-between hover:bg-gray-50 dark:hover:bg-gray-700 rounded-lg">
          <div className="flex items-center gap-2 sm:gap-3 min-w-0">
            <svg className="w-4 h-4 sm:w-5 sm:h-5 text-blue-600 flex-shrink-0" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z"/>
            </svg>
            <div className="min-w-0">
              <h3 className="font-medium text-sm sm:text-base text-gray-900 dark:text-white">
                {t('config.endpointsRef.title')}
              </h3>
              <p className="text-xs text-gray-500 dark:text-gray-400 truncate">
                {t('config.endpointsRef.description')}
              </p>
            </div>
          </div>
          <svg className="w-4 h-4 sm:w-5 sm:h-5 text-gray-400 transition-transform group-open:rotate-180 flex-shrink-0 ml-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </summary>
        <div className="p-3 sm:p-4 pt-0 border-t border-gray-100 dark:border-gray-700 space-y-3">
          {/* All tools endpoint */}
          <div className="flex items-center justify-between gap-2 p-2 bg-gray-50 dark:bg-gray-700 rounded-lg">
            <div className="min-w-0">
              <span className="text-sm font-medium text-gray-700 dark:text-gray-300">{t('config.endpointsRef.allTools')}</span>
              <code className="ml-2 text-xs text-gray-500 dark:text-gray-400">/tools/openapi.json</code>
            </div>
            <button
              onClick={() => copyToClipboard(`${backendUrl}/tools/openapi.json`, 'endpoint-all')}
              className={`px-2 py-1 text-xs font-medium rounded transition-colors ${
                copied === 'endpoint-all' ? 'bg-green-600 text-white' : 'bg-blue-600 hover:bg-blue-700 text-white'
              }`}
            >
              {copied === 'endpoint-all' ? t('config.openWebUI.copied') : t('config.openWebUI.copyUrl')}
            </button>
          </div>

          {/* Category endpoints */}
          <div className="space-y-1">
            <p className="text-xs font-medium text-gray-600 dark:text-gray-400 mb-2">{t('config.endpointsRef.byCategory')}</p>
            {[
              { id: 'system', path: '/tools/system/openapi.json', color: 'blue' },
              { id: 'media', path: '/tools/media/openapi.json', color: 'purple' },
              { id: 'processing', path: '/tools/processing/openapi.json', color: 'orange' },
              { id: 'knowledge', path: '/tools/knowledge/openapi.json', color: 'green' },
            ].map((ep) => (
              <div key={ep.id} className="flex items-center justify-between gap-2 p-2 bg-gray-50 dark:bg-gray-700 rounded">
                <div className="flex items-center gap-2 min-w-0">
                  <span className={`w-2 h-2 rounded-full bg-${ep.color}-500 flex-shrink-0`}></span>
                  <span className="text-xs font-medium text-gray-700 dark:text-gray-300">{t(`config.endpoints.${ep.id}.name`)}</span>
                  <code className="text-xs text-gray-500 dark:text-gray-400 truncate">{ep.path}</code>
                </div>
                <button
                  onClick={() => copyToClipboard(`${backendUrl}${ep.path}`, `endpoint-${ep.id}`)}
                  className={`px-2 py-1 text-xs font-medium rounded transition-colors flex-shrink-0 ${
                    copied === `endpoint-${ep.id}` ? 'bg-green-600 text-white' : 'bg-gray-600 hover:bg-gray-700 text-white'
                  }`}
                >
                  {copied === `endpoint-${ep.id}` ? t('config.openWebUI.copied') : t('config.openWebUI.copyUrl')}
                </button>
              </div>
            ))}
          </div>

          {/* Quick tip */}
          <p className="text-xs text-blue-600 dark:text-blue-400">
            {t('config.endpointsRef.tip')}
          </p>

          {/* Troubleshooting */}
          <details className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
            <summary className="p-2 cursor-pointer list-none flex items-center gap-2 hover:bg-blue-100/50 dark:hover:bg-blue-900/30 rounded-lg text-sm">
              <svg className="w-4 h-4 text-blue-600 dark:text-blue-400 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
              </svg>
              <span className="font-medium text-blue-900 dark:text-blue-100">{t('config.troubleshooting.title')}</span>
            </summary>
            <div className="px-3 pb-3 text-xs text-blue-800 dark:text-blue-200 space-y-1">
              <p>{t('config.troubleshooting.description')}</p>
              <ul className="list-disc list-inside ml-1 space-y-0.5">
                <li>{t('config.troubleshooting.solution1')}</li>
                <li>{t('config.troubleshooting.solution2')}</li>
                <li>{t('config.troubleshooting.solution3')}</li>
              </ul>
            </div>
          </details>
        </div>
      </details>

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

      {/* Global Search Configuration */}
      <GlobalSearchConfig />
    </div>
  );
};

// ============================================================================
// DATE RANGE PICKER COMPONENT
// ============================================================================

interface DateRangePickerProps {
  startDate: Date | null;
  endDate: Date | null;
  onApply: (start: Date, end: Date) => void;
  onClear: () => void;
  presetValue: number;
  onPresetChange: (hours: number) => void;
}

const DateRangePicker = ({ startDate, endDate, onApply, onClear, presetValue, onPresetChange }: DateRangePickerProps) => {
  const { t } = useTranslation('mcp');
  const [isOpen, setIsOpen] = useState(false);
  const [tempStart, setTempStart] = useState<string>('');
  const [tempEnd, setTempEnd] = useState<string>('');

  // Format date for datetime-local input
  const formatDateForInput = (date: Date) => {
    const pad = (n: number) => n.toString().padStart(2, '0');
    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
  };

  // Initialize temp values when opening
  const handleOpen = () => {
    if (startDate && endDate) {
      setTempStart(formatDateForInput(startDate));
      setTempEnd(formatDateForInput(endDate));
    } else {
      // Default to last 24h
      const end = new Date();
      const start = new Date(end.getTime() - 24 * 60 * 60 * 1000);
      setTempStart(formatDateForInput(start));
      setTempEnd(formatDateForInput(end));
    }
    setIsOpen(true);
  };

  const handleApply = () => {
    if (tempStart && tempEnd) {
      onApply(new Date(tempStart), new Date(tempEnd));
      setIsOpen(false);
    }
  };

  const handlePresetClick = (preset: string) => {
    const now = new Date();
    let start: Date;
    let end: Date = now;

    switch (preset) {
      case 'today':
        start = new Date(now.getFullYear(), now.getMonth(), now.getDate());
        break;
      case 'yesterday':
        start = new Date(now.getFullYear(), now.getMonth(), now.getDate() - 1);
        end = new Date(now.getFullYear(), now.getMonth(), now.getDate());
        break;
      case 'last7days':
        start = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
        break;
      case 'last30days':
        start = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
        break;
      case 'thisMonth':
        start = new Date(now.getFullYear(), now.getMonth(), 1);
        break;
      case 'lastMonth':
        start = new Date(now.getFullYear(), now.getMonth() - 1, 1);
        end = new Date(now.getFullYear(), now.getMonth(), 0, 23, 59, 59);
        break;
      default:
        return;
    }

    setTempStart(formatDateForInput(start));
    setTempEnd(formatDateForInput(end));
  };

  const isCustom = startDate !== null && endDate !== null;

  // Format display text
  const getDisplayText = () => {
    if (isCustom && startDate && endDate) {
      const formatShort = (d: Date) => d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
      return `${formatShort(startDate)} - ${formatShort(endDate)}`;
    }
    return null;
  };

  return (
    <div className="relative">
      {/* Combined select + custom button + date display */}
      <div className="flex items-center gap-2">
        {/* Preset dropdown */}
        <select
          value={isCustom ? 'custom' : presetValue}
          onChange={(e) => {
            const val = e.target.value;
            if (val === 'custom') {
              handleOpen();
            } else {
              onClear();
              onPresetChange(Number(val));
            }
          }}
          className="px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white flex-shrink-0"
        >
          <option value={1}>{t('stats.timeRange1h')}</option>
          <option value={6}>{t('stats.timeRange6h')}</option>
          <option value={24}>{t('stats.timeRange24h')}</option>
          <option value={72}>{t('stats.timeRange3d')}</option>
          <option value={168}>{t('stats.timeRange7d')}</option>
          <option value="custom">{t('stats.timeRangeCustom')}</option>
        </select>

        {/* Calendar button for custom range */}
        <button
          onClick={handleOpen}
          className={`p-2 text-sm border rounded-lg flex items-center gap-1 transition-colors ${
            isCustom
              ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400'
              : 'border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-600'
          }`}
          title={getDisplayText() || t('stats.dateRange.custom')}
        >
          <Calendar className="w-4 h-4" />
        </button>

        {/* Clear button when custom range is active */}
        {isCustom && (
          <button
            onClick={onClear}
            className="p-2 text-sm text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
            title={t('stats.dateRange.clear')}
          >
            <X className="w-4 h-4" />
          </button>
        )}

        {/* Custom range display - inline to the right */}
        {isCustom && (
          <span className="text-xs text-gray-500 dark:text-gray-400 whitespace-nowrap ml-1">
            {getDisplayText()}
          </span>
        )}
      </div>

      {/* Popup modal */}
      {isOpen && (
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 z-40"
            onClick={() => setIsOpen(false)}
          />

          {/* Modal */}
          <div className="absolute top-full left-0 mt-2 z-50 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg p-4 min-w-[320px]">
            {/* Presets */}
            <div className="mb-4">
              <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-2">
                {t('stats.dateRange.preset')}
              </label>
              <div className="grid grid-cols-3 gap-1">
                {['today', 'yesterday', 'last7days', 'last30days', 'thisMonth', 'lastMonth'].map(preset => (
                  <button
                    key={preset}
                    onClick={() => handlePresetClick(preset)}
                    className="px-2 py-1 text-xs border border-gray-200 dark:border-gray-600 rounded hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                  >
                    {t(`stats.dateRange.${preset}`)}
                  </button>
                ))}
              </div>
            </div>

            {/* Custom inputs */}
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                  {t('stats.dateRange.from')}
                </label>
                <input
                  type="datetime-local"
                  value={tempStart}
                  onChange={(e) => setTempStart(e.target.value)}
                  className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                  {t('stats.dateRange.to')}
                </label>
                <input
                  type="datetime-local"
                  value={tempEnd}
                  onChange={(e) => setTempEnd(e.target.value)}
                  className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                />
              </div>
            </div>

            {/* Actions */}
            <div className="flex justify-end gap-2 mt-4 pt-3 border-t border-gray-200 dark:border-gray-700">
              <button
                onClick={() => setIsOpen(false)}
                className="px-3 py-1.5 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200"
              >
                {t('stats.dateRange.cancel')}
              </button>
              <button
                onClick={handleApply}
                disabled={!tempStart || !tempEnd}
                className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {t('stats.dateRange.apply')}
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default function MCP() {
  const { t } = useTranslation('mcp');
  const [searchParams] = useSearchParams();
  const initialTab = (searchParams.get('tab') as 'overview' | 'history' | 'tools' | 'interactions' | 'config') || 'overview';
  const [activeTab, setActiveTab] = useState<'overview' | 'history' | 'tools' | 'interactions' | 'config'>(initialTab);
  const [stats, setStats] = useState<McpStats | null>(null);
  const [toolUsage, setToolUsage] = useState<McpToolUsage[]>([]);
  const [hourlyUsage, setHourlyUsage] = useState<McpHourlyUsage[]>([]);
  const [userStats, setUserStats] = useState<McpUserStats[]>([]);
  const [userServiceStats, setUserServiceStats] = useState<McpUserServiceStats[]>([]);
  const [hourlyUserUsage, setHourlyUserUsage] = useState<McpHourlyUserUsage[]>([]);
  const [requests, setRequests] = useState<McpRequest[]>([]);
  const [tools, setTools] = useState<McpToolsResponse | null>(null);
  const [toolGroups, setToolGroups] = useState<Record<string, ToolGroup[]>>({});
  const [, setTotalRequests] = useState(0);
  const [loading, setLoading] = useState(true);
  const [selectedRequest, setSelectedRequest] = useState<McpRequest | null>(null);
  const [selectedToolToTest, setSelectedToolToTest] = useState<McpTool | null>(null);
  const [timeRange, setTimeRange] = useState(24);
  const [customStartDate, setCustomStartDate] = useState<Date | null>(null);
  const [customEndDate, setCustomEndDate] = useState<Date | null>(null);
  const [chartGranularity, setChartGranularity] = useState<'auto' | 'minute' | 'hour' | 'day'>('auto');
  const [serviceFilter, setServiceFilter] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [expandedServices, setExpandedServices] = useState<Set<string>>(new Set());

  // Calculate effective time range based on custom dates or preset
  const getEffectiveTimeRange = useCallback(() => {
    if (customStartDate && customEndDate) {
      return {
        start_time: customStartDate.toISOString(),
        end_time: customEndDate.toISOString(),
        hours: Math.ceil((customEndDate.getTime() - customStartDate.getTime()) / (60 * 60 * 1000)),
      };
    }
    return {
      start_time: new Date(Date.now() - timeRange * 60 * 60 * 1000).toISOString(),
      end_time: new Date().toISOString(),
      hours: timeRange,
    };
  }, [customStartDate, customEndDate, timeRange]);

  const fetchData = useCallback(async () => {
    setLoading(true);
    const { start_time, end_time, hours } = getEffectiveTimeRange();
    // Pass granularity to API (undefined for 'auto' lets backend decide)
    const apiGranularity = chartGranularity === 'auto' ? undefined : chartGranularity;
    try {
      const [statsRes, toolUsageRes, hourlyRes, userStatsRes, userServiceStatsRes, hourlyUserRes, requestsRes, toolsRes, toolGroupsRes] = await Promise.all([
        api.mcp.statsWithComparison(hours, start_time, end_time).catch(() => null),
        api.mcp.toolUsage(hours, start_time, end_time).catch(() => []),
        api.mcp.hourlyUsage(hours, start_time, end_time, apiGranularity).catch(() => []),
        api.mcp.userStats(hours, start_time, end_time).catch(() => []),
        api.mcp.userServiceStats(hours, start_time, end_time).catch(() => []),
        api.mcp.hourlyUsageByUser(hours, start_time, end_time, apiGranularity).catch(() => []),
        api.mcp.requests.list({
          limit: hours > 24 ? 200 : 100,
          start_time,
          end_time,
          ...(serviceFilter && { service: serviceFilter }),
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
  }, [getEffectiveTimeRange, serviceFilter, statusFilter, chartGranularity]);

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
      <div>
        <h1 className="text-xl sm:text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
          <Bot className="w-6 h-6 sm:w-8 sm:h-8 text-teal-600" />
          MCP Server
        </h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          {t('subtitle')}
        </p>
      </div>

      {/* Tab Navigation - Compact horizontal pills */}
      <div className="mb-4 sm:mb-6 overflow-x-auto -mx-4 px-4 sm:mx-0 sm:px-0">
        <nav className="flex gap-1.5 sm:gap-2 min-w-max sm:min-w-0 sm:flex-wrap">
          {[
            { id: 'overview' as const, labelKey: 'statsShort', labelFullKey: 'statsFull', icon: BarChart3 },
            { id: 'history' as const, labelKey: 'historyShort', labelFullKey: 'historyFull', icon: History },
            { id: 'tools' as const, labelKey: 'toolsShort', labelFullKey: 'toolsFull', icon: Wrench },
            { id: 'interactions' as const, labelKey: 'interactionsShort', labelFullKey: 'interactionsFull', icon: Link2 },
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
                    ? 'bg-teal-600 text-white shadow-sm'
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
        <div className="text-center py-12 text-gray-500">{t('stats.loading')}</div>
      ) : (
        <>
          {/* Overview Tab */}
          {activeTab === 'overview' && (
            <div className="space-y-6">
              {/* Actions bar in card container */}
              <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-3 sm:p-4">
                <div className="flex flex-row gap-2 sm:gap-3 items-center">
                  {/* Refresh button - icon only on all screens */}
                  <button
                    onClick={fetchData}
                    className="p-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-600 flex items-center transition-colors flex-shrink-0"
                  >
                    <RefreshCw className="w-4 h-4" />
                  </button>

                  {/* Time range filter with DateRangePicker */}
                  <DateRangePicker
                    startDate={customStartDate}
                    endDate={customEndDate}
                    onApply={(start, end) => {
                      setCustomStartDate(start);
                      setCustomEndDate(end);
                    }}
                    onClear={() => {
                      setCustomStartDate(null);
                      setCustomEndDate(null);
                    }}
                    presetValue={timeRange}
                    onPresetChange={setTimeRange}
                  />

                  {/* Granularity selector */}
                  <select
                    value={chartGranularity}
                    onChange={(e) => setChartGranularity(e.target.value as 'auto' | 'minute' | 'hour' | 'day')}
                    className="px-2 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white flex-shrink-0"
                    title={t('stats.granularity.title')}
                  >
                    <option value="auto">{t('stats.granularity.auto')}</option>
                    <option value="minute">{t('stats.granularity.minute')}</option>
                    <option value="hour">{t('stats.granularity.hour')}</option>
                    <option value="day">{t('stats.granularity.day')}</option>
                  </select>

                  {/* Spacer */}
                  <div className="flex-1" />

                  {/* Help button */}
                  <HelpTooltip topicId="stats" />
                </div>
              </div>
              {/* Stats Grid */}
              <div className="grid grid-cols-2 lg:grid-cols-5 gap-2 sm:gap-4">
                <StatCard
                  title={t('stats.totalRequests')}
                  value={stats?.total || 0}
                  subtitle={t('stats.lastHours', { hours: timeRange })}
                  color="blue"
                  change={stats?.comparison?.total_change}
                />
                <StatCard
                  title={t('stats.successRate')}
                  value={`${stats?.success_rate || 100}%`}
                  subtitle={t('stats.completed', { count: stats?.by_status?.completed || 0 })}
                  color={stats?.success_rate && stats.success_rate < 90 ? 'red' : 'green'}
                  change={stats?.comparison?.success_rate_change}
                />
                <StatCard
                  title={t('stats.avgDuration')}
                  value={formatDuration(stats?.average_duration_ms || null)}
                  subtitle={t('stats.perRequest')}
                  color="purple"
                  change={stats?.comparison?.duration_change}
                  changeInverted={true}
                />
                <StatCard
                  title={t('stats.denied')}
                  value={stats?.by_status?.denied || 0}
                  subtitle={t('stats.accessDenied')}
                  color={(stats?.by_status?.denied || 0) > 0 ? 'orange' : 'gray'}
                  change={stats?.comparison?.denied_change}
                  changeInverted={true}
                />
                <StatCard
                  title={t('stats.failed')}
                  value={stats?.by_status?.failed || 0}
                  subtitle={t('stats.errorsEncountered')}
                  color={(stats?.by_status?.failed || 0) > 0 ? 'red' : 'gray'}
                  change={stats?.comparison?.failed_change}
                  changeInverted={true}
                />
              </div>

              {/* Hourly Usage Chart */}
              <HourlyUsageChart
                data={hourlyUsage}
                startTime={getEffectiveTimeRange().start_time}
                endTime={getEffectiveTimeRange().end_time}
                granularity={chartGranularity}
              />

              {/* Tool Usage & Categories */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Top Tools */}
                <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow">
                  <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
                    {t('stats.topTools')}
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
                    <p className="text-gray-500 dark:text-gray-400">{t('stats.noToolUsageData')}</p>
                  )}
                </div>

                {/* By Service */}
                <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow">
                  <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
                    {t('stats.byService')}
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
                    {t('stats.byStatus')}
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
                    {t('stats.avgDurationByService')}
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
                    {t('stats.highlights')}
                  </h3>
                  <div className="space-y-3">
                    {/* Most used tool */}
                    {toolUsage.length > 0 && (
                      <div className="flex items-center gap-3 p-2 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                        <div className="p-1.5 bg-blue-100 dark:bg-blue-800 rounded">
                          <BarChart3 className="w-4 h-4 text-blue-600 dark:text-blue-400" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-xs text-gray-500 dark:text-gray-400">{t('stats.mostUsed')}</p>
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
                          <p className="text-xs text-gray-500 dark:text-gray-400">{t('stats.fastest')}</p>
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
                          <p className="text-xs text-gray-500 dark:text-gray-400">{t('stats.reliability')}</p>
                          <p className="text-sm font-medium text-gray-900 dark:text-white">
                            {stats.success_rate >= 95 ? t('stats.excellent') : stats.success_rate >= 80 ? t('stats.good') : t('stats.needsAttention')}
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
                    {t('stats.requestsByUser')}
                  </h3>
                  <UserStatsChart data={userStats} />
                </div>

                {/* User Service Breakdown */}
                <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow">
                  <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
                    {t('stats.servicesByUser')}
                  </h3>
                  <UserServiceChart data={userServiceStats} />
                </div>
              </div>

              {/* Hourly Usage by User - Stacked Chart */}
              <HourlyUserStackedChart
                data={hourlyUserUsage}
                startTime={getEffectiveTimeRange().start_time}
                endTime={getEffectiveTimeRange().end_time}
                granularity={chartGranularity}
              />
            </div>
          )}

          {/* History Tab */}
          {activeTab === 'history' && (
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
              <div className="p-3 sm:p-4">
                {/* Actions bar with filters - single row layout matching UserMappingList */}
                <div className="flex flex-row gap-2 sm:gap-3 items-center mb-4">
                  {/* Refresh button - icon only on all screens */}
                  <button
                    onClick={fetchData}
                    className="p-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-600 flex items-center transition-colors flex-shrink-0"
                  >
                    <RefreshCw className="w-4 h-4" />
                  </button>

                  {/* Time range filter with DateRangePicker */}
                  <DateRangePicker
                    startDate={customStartDate}
                    endDate={customEndDate}
                    onApply={(start, end) => {
                      setCustomStartDate(start);
                      setCustomEndDate(end);
                    }}
                    onClear={() => {
                      setCustomStartDate(null);
                      setCustomEndDate(null);
                    }}
                    presetValue={timeRange}
                    onPresetChange={setTimeRange}
                  />

                  {/* Service filter */}
                  <select
                    value={serviceFilter}
                    onChange={(e) => setServiceFilter(e.target.value)}
                    className="hidden sm:block px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white flex-shrink-0"
                  >
                    <option value="">{t('history.filters.allServices')}</option>
                    {Object.keys(toolsByService).map((service) => (
                      <option key={service} value={service}>
                        {service.charAt(0).toUpperCase() + service.slice(1)}
                      </option>
                    ))}
                  </select>

                  {/* Status filter */}
                  <select
                    value={statusFilter}
                    onChange={(e) => setStatusFilter(e.target.value)}
                    className="hidden sm:block px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white flex-shrink-0"
                  >
                    <option value="">{t('history.filters.allStatuses')}</option>
                    <option value="pending">{t('status.pending')}</option>
                    <option value="processing">{t('status.processing')}</option>
                    <option value="completed">{t('status.completed')}</option>
                    <option value="failed">{t('status.failed')}</option>
                    <option value="denied">{t('status.denied')}</option>
                    <option value="cancelled">{t('status.cancelled')}</option>
                  </select>

                  {/* Spacer to push help to right */}
                  <div className="flex-1" />

                  {/* Help button */}
                  <HelpTooltip topicId="history" />
                </div>

              {/* Request List - Mobile: Card view, Desktop: Table view */}
              {/* Mobile Cards */}
              <div className="sm:hidden space-y-2">
                {requests.length > 0 ? (
                  requests.map((request) => (
                    <div
                      key={request.id}
                      className="p-3 rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700/50 cursor-pointer"
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
                        <ChainBadge request={request} onChainClick={() => setSelectedRequest(request)} />
                        {request.user_display_name && (
                          <span className="text-xs text-gray-500">{t('history.by')} {request.user_display_name}</span>
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
              <div className="hidden sm:block overflow-hidden">
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
                          {t('tabs.interactionsShort')}
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
                    <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
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
                              <ChainBadge request={request} onChainClick={() => setSelectedRequest(request)} />
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
                                {t('history.requestDetail.viewDetails')}
                              </button>
                            </td>
                          </tr>
                        ))
                      ) : (
                        <tr>
                          <td colSpan={8} className="px-4 py-12 text-center text-gray-500 dark:text-gray-400">
                            {t('history.noRequests')}
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
              </div>
            </div>
          )}

          {/* Tools Tab */}
          {activeTab === 'tools' && (
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
              <div className="p-3 sm:p-4">
                {/* Actions bar - single row layout matching History tab */}
                <div className="flex flex-row gap-2 sm:gap-3 items-center mb-4">
                  {/* Refresh button - icon only on all screens */}
                  <button
                    onClick={fetchData}
                    className="p-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-600 flex items-center transition-colors flex-shrink-0"
                  >
                    <RefreshCw className="w-4 h-4" />
                  </button>

                  {/* Expand All button */}
                  <button
                    onClick={() => toggleAllServices(true)}
                    className="flex px-3 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-600 items-center gap-2 transition-colors flex-shrink-0"
                  >
                    {t('tools.expandAll')}
                  </button>

                  {/* Collapse All button */}
                  <button
                    onClick={() => toggleAllServices(false)}
                    className="flex px-3 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-600 items-center gap-2 transition-colors flex-shrink-0"
                  >
                    {t('tools.collapseAll')}
                  </button>

                  {/* Tools count info - visible on md+ */}
                  <div className="text-sm text-gray-600 dark:text-gray-400 hidden md:block">
                    {t('tools.toolsAvailable', { count: tools?.total || 0, services: Object.keys(toolsByService).length })}
                  </div>

                  {/* Spacer to push help to the right */}
                  <div className="flex-1" />

                  {/* Help button */}
                  <HelpTooltip topicId="tools" />
                </div>

                {/* Global Search Info Block */}
                <GlobalSearchInfoBlock
                  onConfigure={() => setActiveTab('config')}
                  className="mb-4"
                />

              {/* Services List */}
              <div className="space-y-3">
              {Object.keys(toolsByService).length > 0 ? (
                Object.entries(toolsByService).map(([serviceName, serviceTools]) => {
                  const colors = getServiceColor(serviceName);
                  const Icon = colors.icon;
                  const isExpanded = expandedServices.has(serviceName);

                  return (
                    <div
                      key={serviceName}
                      className={`rounded-lg overflow-hidden border ${colors.border}`}
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
              </div>
            </div>
          )}

          {/* Interactions Tab (Tool Chains) */}
          {activeTab === 'interactions' && (
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 h-[calc(100vh-280px)] min-h-[500px]">
              <ToolChainManagement />
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
                  {t('history.requestDetail.title')}
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
                    <p className="text-sm text-gray-500 dark:text-gray-400">{t('history.requestDetail.tool')}</p>
                    <p className="font-medium text-gray-900 dark:text-white">{selectedRequest.tool_name}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-500 dark:text-gray-400">{t('history.requestDetail.category')}</p>
                    {selectedRequest.tool_category && <CategoryBadge category={selectedRequest.tool_category} />}
                  </div>
                  <div>
                    <p className="text-sm text-gray-500 dark:text-gray-400">{t('history.requestDetail.user')}</p>
                    <p className="text-gray-900 dark:text-white" title={selectedRequest.user_id || undefined}>
                      {selectedRequest.user_display_name || selectedRequest.user_id || '-'}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-500 dark:text-gray-400">{t('history.requestDetail.status')}</p>
                    <StatusBadge status={selectedRequest.status} />
                  </div>
                  <div>
                    <p className="text-sm text-gray-500 dark:text-gray-400">{t('history.requestDetail.duration')}</p>
                    <p className="text-gray-900 dark:text-white">{formatDuration(selectedRequest.duration_ms)}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-500 dark:text-gray-400">{t('history.requestDetail.created')}</p>
                    <p className="text-gray-900 dark:text-white">{formatDate(selectedRequest.created_at)}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-500 dark:text-gray-400">{t('history.requestDetail.completed')}</p>
                    <p className="text-gray-900 dark:text-white">
                      {selectedRequest.completed_at ? formatDate(selectedRequest.completed_at) : '-'}
                    </p>
                  </div>
                </div>

                {selectedRequest.input_params && Object.keys(selectedRequest.input_params).length > 0 && (
                  <div>
                    <p className="text-sm text-gray-500 dark:text-gray-400 mb-2">{t('history.requestDetail.inputParams')}</p>
                    <pre className="bg-gray-50 dark:bg-gray-900 p-3 rounded-lg text-xs overflow-x-auto">
                      {JSON.stringify(selectedRequest.input_params, null, 2)}
                    </pre>
                  </div>
                )}

                {selectedRequest.output_result && (
                  <div>
                    <p className="text-sm text-gray-500 dark:text-gray-400 mb-2">{t('history.requestDetail.result')}</p>
                    <pre className="bg-gray-50 dark:bg-gray-900 p-3 rounded-lg text-xs overflow-x-auto max-h-48">
                      {JSON.stringify(selectedRequest.output_result, null, 2)}
                    </pre>
                  </div>
                )}

                {/* Tool Chain Info */}
                {(selectedRequest.output_result?.chain_context ||
                  (selectedRequest.output_result?.next_tools_to_call &&
                   selectedRequest.output_result.next_tools_to_call.length > 0)) && (
                  <div className="border-t dark:border-gray-700 pt-4">
                    {/* Chain Header with badges */}
                    {selectedRequest.output_result?.chain_context && (() => {
                      const position = selectedRequest.output_result.chain_context.position || 'start';
                      const sourceTool = selectedRequest.output_result.chain_context.source_tool;

                      const positionConfig = {
                        start: {
                          icon: <Play className="w-3 h-3" />,
                          label: t('history.chainStart'),
                          bgClass: 'bg-green-100 dark:bg-green-900/30',
                          textClass: 'text-green-700 dark:text-green-300',
                        },
                        middle: {
                          icon: <CircleDot className="w-3 h-3" />,
                          label: t('history.chainMiddle'),
                          bgClass: 'bg-blue-100 dark:bg-blue-900/30',
                          textClass: 'text-blue-700 dark:text-blue-300',
                        },
                        end: {
                          icon: <Square className="w-3 h-3" />,
                          label: t('history.chainEnd'),
                          bgClass: 'bg-orange-100 dark:bg-orange-900/30',
                          textClass: 'text-orange-700 dark:text-orange-300',
                        },
                      };

                      const config = positionConfig[position as keyof typeof positionConfig] || positionConfig.start;

                      return (
                        <div className="flex items-center gap-2 mb-3 flex-wrap">
                          {/* Position Badge */}
                          <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${config.bgClass} ${config.textClass}`}>
                            {config.icon}
                            {config.label}
                          </span>

                          {/* Source Tool Badge (for middle/end positions) */}
                          {(position === 'middle' || position === 'end') && sourceTool && (
                            <span className="inline-flex items-center gap-1 px-2 py-1 bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 rounded-full text-xs">
                              <ArrowRight className="w-3 h-3 rotate-180" />
                              {sourceTool}
                            </span>
                          )}

                          {/* Chain Links */}
                          {selectedRequest.output_result.chain_context.chains?.map((chain: any) => (
                            <a
                              key={chain.id}
                              href={`#chains`}
                              onClick={(e) => {
                                e.preventDefault();
                                setSelectedRequest(null);
                                setActiveTab('interactions');
                              }}
                              className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium transition-colors hover:opacity-80"
                              style={{
                                backgroundColor: `${chain.color || '#8b5cf6'}20`,
                                color: chain.color || '#8b5cf6',
                              }}
                              title={t('history.viewChain')}
                            >
                              <Workflow className="w-3 h-3" />
                              {chain.name}
                              <Link2 className="w-3 h-3" />
                            </a>
                          ))}
                        </div>
                      );
                    })()}

                    {/* Next Tools */}
                    {selectedRequest.output_result?.next_tools_to_call &&
                     selectedRequest.output_result.next_tools_to_call.length > 0 && (() => {
                      // Get color from chain_context (at root level)
                      const chainColor = selectedRequest.output_result.chain_context?.chains?.[0]?.color || '#8b5cf6';

                      return (
                        <div className="space-y-2">
                          <p className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">
                            {t('history.nextTools')}
                          </p>
                          <div className="space-y-2">
                            {selectedRequest.output_result.next_tools_to_call.map((nextTool: any, index: number) => (
                              <div
                                key={index}
                                className="flex items-center gap-2 p-2 rounded-lg"
                                style={{ backgroundColor: `${chainColor}10` }}
                              >
                                <ArrowRight className="w-4 h-4 flex-shrink-0" style={{ color: chainColor }} />

                                {/* Tool Badge */}
                                <span
                                  className="inline-flex items-center gap-1 px-2 py-1 rounded text-xs font-medium"
                                  style={{
                                    backgroundColor: `${chainColor}20`,
                                    color: chainColor,
                                  }}
                                >
                                  {nextTool.tool}
                                </span>

                                {/* Service Badge */}
                                <span className="text-xs px-2 py-0.5 bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 rounded">
                                  {nextTool.service_name}
                                </span>

                                {/* Reason */}
                                {nextTool.reason && (
                                  <span className="text-xs text-gray-500 dark:text-gray-400 truncate flex-1" title={nextTool.reason}>
                                    {nextTool.reason}
                                  </span>
                                )}
                              </div>
                            ))}
                          </div>
                        </div>
                      );
                    })()}
                  </div>
                )}

                {selectedRequest.error_message && (
                  <div>
                    <p className="text-sm text-gray-500 dark:text-gray-400 mb-2">{t('history.requestDetail.error')}</p>
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
                  {t('history.requestDetail.close')}
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
