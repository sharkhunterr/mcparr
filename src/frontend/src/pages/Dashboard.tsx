import { useState, useEffect, useCallback } from 'react';
import {
  LayoutDashboard,
  Cpu,
  HardDrive,
  MemoryStick,
  Clock,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Bot,
  Users,
  RefreshCw,
  Wifi,
  WifiOff,
  Film,
  Shield,
  Eye,
  Zap,
  Server,
  ArrowRight,
  Activity,
  FileText,
  Wrench,
  Brain,
  Sparkles
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { api, apiClient } from '../lib/api';
import { getServiceColor, getServiceFromToolName } from '../lib/serviceColors';
import { Link } from 'react-router-dom';
import { useSettings } from '../contexts/SettingsContext';

interface SystemMetrics {
  cpu_usage: number;
  cpu_load_avg: number;
  memory_usage: number;
  memory_used: number;
  memory_total: number;
  disk_usage: number;
  disk_used: number;
  disk_total: number;
  network_bytes_sent: number;
  network_bytes_recv: number;
  services_running: number;
  services_total: number;
  uptime: number;
}

interface ServiceHealth {
  id: string;
  name: string;
  service_type: string;
  status: string;
  enabled: boolean;
  healthy: boolean;
  last_test_at: string | null;
  last_error: string | null;
}

interface McpStats {
  total: number;
  success_rate: number;
  average_duration_ms: number;
  by_status: Record<string, number>;
  by_category: Record<string, number>;
  top_tools: Record<string, number>;
  period_hours: number;
}

interface AlertStats {
  total: number;
  active: number;
  by_severity: Record<string, number>;
}

interface HourlyUsage {
  hour: string;
  count: number;
  success_count?: number;
  failed_count?: number;
}

interface LogStats {
  total: number;
  by_level: Record<string, number>;
  by_source: Record<string, number>;
  error_rate: number;
  period_hours: number;
}

interface TrainingStats {
  total_sessions: number;
  active_sessions: number;
  completed_sessions: number;
  failed_sessions: number;
  total_prompts: number;
  validated_prompts: number;
  prompts_by_category: Record<string, number>;
}

interface TrainingWorker {
  id: string;
  name: string;
  status: string;
  enabled: boolean;
  gpu_available: boolean;
  gpu_names: string[];
  gpu_memory_total_mb: number;
  current_job_id: string | null;
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

interface Group {
  id: string;
  name: string;
  description: string;
  color: string;
  priority: number;
  enabled: boolean;
  member_count: number;
  tool_count: number;
}

interface UserMapping {
  id: string;
  central_user_id: string;
  central_username: string;
  service_config: {
    service_type: string;
  };
}

// Helper functions
const formatUptime = (seconds: number): string => {
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  if (days > 0) return `${days}j ${hours}h`;
  if (hours > 0) return `${hours}h ${minutes}m`;
  return `${minutes}m`;
};

const formatBytes = (bytes: number): string => {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
};

const getServiceIcon = (type: string) => {
  switch (type.toLowerCase()) {
    case 'plex': return Film;
    case 'authentik': return Shield;
    case 'tautulli': return Eye;
    case 'overseerr': return Zap;
    case 'openwebui': return Bot;
    default: return Server;
  }
};

const getServiceColors = (type: string) => {
  const colors = getServiceColor(type);
  return {
    bg: colors.bg,
    text: colors.text,
    border: colors.border
  };
};

// Progress bar component
const ProgressBar = ({ value, color }: { value: number; color: 'blue' | 'green' | 'purple' | 'orange' | 'red' | 'yellow' }) => {
  const colorClasses = {
    blue: 'bg-blue-500',
    green: 'bg-green-500',
    purple: 'bg-purple-500',
    orange: 'bg-orange-500',
    red: 'bg-red-500',
    yellow: 'bg-yellow-500',
  };

  return (
    <div className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
      <div
        className={`h-full ${colorClasses[color]} transition-all duration-500`}
        style={{ width: `${Math.min(value, 100)}%` }}
      />
    </div>
  );
};

// Mini stacked bar chart for MCP hourly usage with success/failure breakdown
const MiniBarChart = ({ data, hoursCount = 12 }: { data: HourlyUsage[]; hoursCount?: number }) => {
  // Generate hours with 0 values for missing hours
  // Backend uses UTC, so we need to generate UTC hours for matching
  const now = new Date();
  const hours: { hour: string; count: number; success: number; failed: number; label: string }[] = [];

  for (let i = hoursCount - 1; i >= 0; i--) {
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
      label: localHour + 'h'  // Display local time
    });
  }

  const maxCount = Math.max(...hours.map(h => h.count), 1);
  const maxHeight = 40; // pixels

  return (
    <div className="flex items-end gap-0.5" style={{ height: `${maxHeight}px` }}>
      {hours.map((h, i) => {
        const totalHeight = h.count > 0 ? Math.max((h.count / maxCount) * maxHeight, 6) : 4;
        const successRatio = h.count > 0 ? h.success / h.count : 0;
        const failedRatio = h.count > 0 ? h.failed / h.count : 0;
        const successHeight = totalHeight * successRatio;
        const failedHeight = totalHeight * failedRatio;
        const isLast = i === hours.length - 1;

        return (
          <div
            key={i}
            className="flex-1 flex flex-col items-center justify-end"
            title={`${h.label}: ${h.count} req (${h.success} ok, ${h.failed} err)`}
          >
            {h.count === 0 ? (
              // No data - gray dot
              <div
                className={`w-full rounded-sm bg-gray-300 dark:bg-gray-600 ${isLast ? 'opacity-100' : 'opacity-60'}`}
                style={{ height: '4px' }}
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
  );
};

export default function Dashboard() {
  const { t } = useTranslation('dashboard');
  const { t: tCommon } = useTranslation('common');
  const { settings } = useSettings();
  const [metrics, setMetrics] = useState<SystemMetrics | null>(null);
  const [services, setServices] = useState<ServiceHealth[]>([]);
  const [mcpStats, setMcpStats] = useState<McpStats | null>(null);
  const [mcpHourlyUsage, setMcpHourlyUsage] = useState<HourlyUsage[]>([]);
  const [alertStats, setAlertStats] = useState<AlertStats | null>(null);
  const [logStats, setLogStats] = useState<LogStats | null>(null);
  const [trainingStats, setTrainingStats] = useState<TrainingStats | null>(null);
  const [trainingWorkers, setTrainingWorkers] = useState<TrainingWorker[]>([]);
  const [promptsByService, setPromptsByService] = useState<Record<string, number>>({});
  const [mcpUserStats, setMcpUserStats] = useState<McpUserStats[]>([]);
  const [userMappingsCount, setUserMappingsCount] = useState<number>(0);
  const [userMappings, setUserMappings] = useState<UserMapping[]>([]);
  const [groups, setGroups] = useState<Group[]>([]);
  const [loading, setLoading] = useState(true);
  const [autoRefresh, setAutoRefresh] = useState(settings.autoRefresh);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  // Sync autoRefresh with settings changes
  useEffect(() => {
    setAutoRefresh(settings.autoRefresh);
  }, [settings.autoRefresh]);

  const fetchData = useCallback(async () => {
    try {
      const [metricsRes, servicesRes, mcpStatsRes, alertStatsRes, mappingsRes, hourlyUsageRes, logStatsRes, trainingStatsRes, groupsRes, mcpUserStatsRes, workersRes, promptsRes] = await Promise.all([
        api.system.currentMetrics().catch(() => null),
        api.services.list().catch(() => []),
        api.mcp.stats(24).catch(() => null),
        api.alerts.stats(24).catch(() => null),
        apiClient.get('/api/users/').catch(() => ({ mappings: [], total: 0 })),
        api.mcp.hourlyUsage(24).catch(() => []),
        api.logs.stats(24).catch(() => null),
        api.training.stats().catch(() => null),
        api.groups.list().catch(() => ({ groups: [], total: 0 })),
        api.mcp.userStats(24).catch(() => []),
        api.workers.list().catch(() => []),
        api.training.prompts.list().catch(() => []),
      ]);

      if (metricsRes) setMetrics(metricsRes);

      if (Array.isArray(servicesRes)) {
        const healthPromises = servicesRes.map(async (service: any) => {
          try {
            const health = await apiClient.get(`/api/services/${service.id}/health`);
            return { ...health, service_type: service.service_type };
          } catch {
            return {
              id: service.id,
              name: service.name,
              service_type: service.service_type,
              status: service.status,
              enabled: service.enabled,
              healthy: false,
              last_test_at: null,
              last_error: 'Unable to fetch health',
            };
          }
        });
        const healthResults = await Promise.all(healthPromises);
        setServices(healthResults);
      }

      if (mcpStatsRes) setMcpStats(mcpStatsRes);
      if (alertStatsRes) setAlertStats(alertStatsRes);
      if (logStatsRes) setLogStats(logStatsRes);
      if (trainingStatsRes) setTrainingStats(trainingStatsRes);
      if (Array.isArray(hourlyUsageRes)) {
        setMcpHourlyUsage(hourlyUsageRes);
      }
      if (mappingsRes && typeof mappingsRes.total === 'number') {
        setUserMappingsCount(mappingsRes.total);
        if (mappingsRes.mappings) setUserMappings(mappingsRes.mappings);
      } else if (mappingsRes?.mappings) {
        setUserMappingsCount(mappingsRes.mappings.length);
        setUserMappings(mappingsRes.mappings);
      }
      if (groupsRes?.groups) {
        setGroups(groupsRes.groups);
      }
      if (Array.isArray(mcpUserStatsRes)) {
        setMcpUserStats(mcpUserStatsRes);
      }
      if (Array.isArray(workersRes)) {
        setTrainingWorkers(workersRes);
      }

      // Process prompts to count by service tags
      if (promptsRes) {
        const prompts = Array.isArray(promptsRes) ? promptsRes : (promptsRes?.prompts || []);

        // Get service names from configured services
        const configuredServiceNames = Array.isArray(servicesRes)
          ? servicesRes.map((s: { name: string }) => s.name.toLowerCase())
          : [];

        // Common service names to look for in tags
        const knownServiceNames = [
          'prowlarr', 'radarr', 'sonarr', 'lidarr', 'readarr', 'bazarr',
          'tautulli', 'overseerr', 'ombi', 'plex', 'jellyfin', 'emby',
          'komga', 'zammad', 'system', 'ollama', 'homeassistant', 'unifi',
          'proxmox', 'portainer', 'docker', 'traefik', 'nginx', 'authentik',
          ...configuredServiceNames
        ];

        const serviceCount: Record<string, number> = {};
        prompts.forEach((prompt: { tags?: string[] }) => {
          if (prompt.tags && Array.isArray(prompt.tags)) {
            const serviceTags = prompt.tags.filter((tag: string) =>
              knownServiceNames.includes(tag.toLowerCase())
            );
            serviceTags.forEach((tag: string) => {
              const normalizedTag = tag.toLowerCase();
              serviceCount[normalizedTag] = (serviceCount[normalizedTag] || 0) + 1;
            });
          }
        });

        setPromptsByService(serviceCount);
      }

      setLastUpdated(new Date());
    } catch (error) {
      console.error('Failed to fetch dashboard data:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  useEffect(() => {
    if (autoRefresh) {
      const intervalMs = settings.refreshInterval * 1000;
      const interval = setInterval(fetchData, intervalMs);
      return () => clearInterval(interval);
    }
  }, [autoRefresh, fetchData, settings.refreshInterval]);

  const healthyServices = services.filter(s => s.healthy && s.enabled).length;
  const enabledServices = services.filter(s => s.enabled).length;
  const cpuColor = (metrics?.cpu_usage || 0) > 80 ? 'red' : (metrics?.cpu_usage || 0) > 60 ? 'yellow' : 'blue';
  const memColor = (metrics?.memory_usage || 0) > 80 ? 'red' : (metrics?.memory_usage || 0) > 60 ? 'yellow' : 'green';
  const diskColor = (metrics?.disk_usage || 0) > 80 ? 'red' : (metrics?.disk_usage || 0) > 60 ? 'yellow' : 'purple';

  if (loading) {
    return (
      <div className="p-4 sm:p-6 space-y-4">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded w-48"></div>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {[1, 2, 3, 4].map(i => (
              <div key={i} className="h-24 bg-gray-200 dark:bg-gray-700 rounded-lg"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-4 sm:p-6 space-y-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <LayoutDashboard className="w-6 h-6 sm:w-7 sm:h-7 text-blue-600" />
            {t('title')}
          </h1>
        </div>

        <div className="flex items-center gap-2">
          {lastUpdated && (
            <span className="text-xs text-gray-500 dark:text-gray-400 flex items-center gap-1">
              {autoRefresh ? (
                <Wifi className="w-3 h-3 text-green-500" />
              ) : (
                <WifiOff className="w-3 h-3 text-gray-400" />
              )}
              {lastUpdated.toLocaleTimeString()}
            </span>
          )}
          <label className="flex items-center gap-1 text-xs text-gray-600 dark:text-gray-400">
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
              className="rounded border-gray-300 text-blue-600 focus:ring-blue-500 w-3 h-3"
            />
            {t('autoRefresh')}
          </label>
          <button
            onClick={fetchData}
            className="p-1.5 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* System Metrics Row */}
      {settings.showSystemMetrics && (
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {/* CPU */}
        <div className="bg-white dark:bg-gray-800 rounded-xl p-4 shadow-sm border border-gray-100 dark:border-gray-700">
          <div className="flex items-center mb-3">
            <div className={`p-2 rounded-lg ${cpuColor === 'red' ? 'bg-red-100 dark:bg-red-900/30' : cpuColor === 'yellow' ? 'bg-yellow-100 dark:bg-yellow-900/30' : 'bg-blue-100 dark:bg-blue-900/30'}`}>
              <Cpu className={`w-5 h-5 ${cpuColor === 'red' ? 'text-red-600 dark:text-red-400' : cpuColor === 'yellow' ? 'text-yellow-600 dark:text-yellow-400' : 'text-blue-600 dark:text-blue-400'}`} />
            </div>
            <div className="ml-3 flex-1">
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">{t('cpu')}</p>
              <p className="text-xl font-semibold text-gray-900 dark:text-white">
                {metrics?.cpu_usage.toFixed(0) || 0}<span className="text-base text-gray-500 dark:text-gray-400">%</span>
              </p>
            </div>
          </div>
          <ProgressBar value={metrics?.cpu_usage || 0} color={cpuColor as 'blue' | 'yellow' | 'red'} />
        </div>

        {/* Memory */}
        <div className="bg-white dark:bg-gray-800 rounded-xl p-4 shadow-sm border border-gray-100 dark:border-gray-700">
          <div className="flex items-center mb-3">
            <div className={`p-2 rounded-lg ${memColor === 'red' ? 'bg-red-100 dark:bg-red-900/30' : memColor === 'yellow' ? 'bg-yellow-100 dark:bg-yellow-900/30' : 'bg-green-100 dark:bg-green-900/30'}`}>
              <MemoryStick className={`w-5 h-5 ${memColor === 'red' ? 'text-red-600 dark:text-red-400' : memColor === 'yellow' ? 'text-yellow-600 dark:text-yellow-400' : 'text-green-600 dark:text-green-400'}`} />
            </div>
            <div className="ml-3 flex-1">
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">{t('memory')}</p>
              <p className="text-xl font-semibold text-gray-900 dark:text-white">
                {metrics?.memory_usage.toFixed(0) || 0}<span className="text-base text-gray-500 dark:text-gray-400">%</span>
              </p>
            </div>
          </div>
          <ProgressBar value={metrics?.memory_usage || 0} color={memColor as 'green' | 'yellow' | 'red'} />
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
            {formatBytes(metrics?.memory_used || 0)} / {formatBytes(metrics?.memory_total || 0)}
          </p>
        </div>

        {/* Disk */}
        <div className="bg-white dark:bg-gray-800 rounded-xl p-4 shadow-sm border border-gray-100 dark:border-gray-700">
          <div className="flex items-center mb-3">
            <div className={`p-2 rounded-lg ${diskColor === 'red' ? 'bg-red-100 dark:bg-red-900/30' : diskColor === 'yellow' ? 'bg-yellow-100 dark:bg-yellow-900/30' : 'bg-purple-100 dark:bg-purple-900/30'}`}>
              <HardDrive className={`w-5 h-5 ${diskColor === 'red' ? 'text-red-600 dark:text-red-400' : diskColor === 'yellow' ? 'text-yellow-600 dark:text-yellow-400' : 'text-purple-600 dark:text-purple-400'}`} />
            </div>
            <div className="ml-3 flex-1">
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">{t('disk')}</p>
              <p className="text-xl font-semibold text-gray-900 dark:text-white">
                {metrics?.disk_usage.toFixed(0) || 0}<span className="text-base text-gray-500 dark:text-gray-400">%</span>
              </p>
            </div>
          </div>
          <ProgressBar value={metrics?.disk_usage || 0} color={diskColor as 'purple' | 'yellow' | 'red'} />
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
            {formatBytes(metrics?.disk_used || 0)} / {formatBytes(metrics?.disk_total || 0)}
          </p>
        </div>

        {/* Uptime */}
        <div className="bg-white dark:bg-gray-800 rounded-xl p-4 shadow-sm border border-gray-100 dark:border-gray-700">
          <div className="flex items-center">
            <div className="p-2 rounded-lg bg-orange-100 dark:bg-orange-900/30">
              <Clock className="w-5 h-5 text-orange-600 dark:text-orange-400" />
            </div>
            <div className="ml-3 flex-1">
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">{t('uptime')}</p>
              <p className="text-xl font-semibold text-gray-900 dark:text-white">
                {formatUptime(metrics?.uptime || 0)}
              </p>
            </div>
          </div>
          <div className="mt-3 flex items-center gap-1.5">
            <CheckCircle className="w-4 h-4 text-green-500" />
            <span className="text-xs text-green-600 dark:text-green-400">{t('systemActive')}</span>
          </div>
        </div>
      </div>
      )}

      {/* Services - Modern pills */}
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 p-4">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Server className="w-4 h-4 text-blue-500" />
            <span className="font-semibold text-sm text-gray-900 dark:text-white">{t('services.title')}</span>
            <span className="text-xs px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400">
              {t('services.healthy', { healthy: healthyServices, enabled: enabledServices })}
            </span>
          </div>
          <Link to="/services" className="text-xs text-blue-600 hover:text-blue-700 flex items-center gap-1">
            {tCommon('actions.manage')} <ArrowRight className="w-3 h-3" />
          </Link>
        </div>
        <div className="flex flex-wrap gap-2">
          {services.length > 0 ? (
            services.map((service) => {
              const Icon = getServiceIcon(service.service_type);
              const colors = getServiceColors(service.service_type);
              const isHealthy = service.enabled && service.healthy;
              const isDisabled = !service.enabled;

              return (
                <div
                  key={service.id}
                  className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full border transition-all ${
                    isDisabled
                      ? 'bg-gray-50 dark:bg-gray-900/50 border-gray-200 dark:border-gray-700 opacity-50'
                      : isHealthy
                      ? `${colors.bg} ${colors.border}`
                      : 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800'
                  }`}
                >
                  <Icon className={`w-3.5 h-3.5 ${isDisabled ? 'text-gray-400' : isHealthy ? colors.text : 'text-red-500'}`} />
                  <span className={`text-xs font-medium ${isDisabled ? 'text-gray-400' : 'text-gray-900 dark:text-white'}`}>
                    {service.name}
                  </span>
                  {isDisabled ? (
                    <span className="text-[10px] text-gray-400">{t('services.off')}</span>
                  ) : isHealthy ? (
                    <CheckCircle className="w-3 h-3 text-green-500" />
                  ) : (
                    <XCircle className="w-3 h-3 text-red-500" />
                  )}
                </div>
              );
            })
          ) : (
            <p className="text-xs text-gray-500 dark:text-gray-400">{t('services.noServices')}</p>
          )}
        </div>
      </div>

      {/* Bottom Grid: MCP Gateway + Top Tools | Users */}
      {settings.showMcpStats && (
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* MCP Gateway + Top Tools Combined */}
        <div className="lg:col-span-2 bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 p-4">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Bot className="w-4 h-4 text-violet-500" />
              <span className="font-semibold text-sm text-gray-900 dark:text-white">{t('mcp.title')}</span>
              <span className="text-xs text-gray-500 dark:text-gray-400">({t('observability.period')})</span>
            </div>
            <Link to="/mcp" className="text-xs text-blue-600 hover:text-blue-700 flex items-center gap-1">
              {tCommon('actions.manage')} <ArrowRight className="w-3 h-3" />
            </Link>
          </div>

          {/* Stats Row */}
          <div className="flex items-center gap-6 mb-4">
            <div className="flex items-center gap-5">
              <div>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">{mcpStats?.total ?? 0}</p>
                <p className="text-xs text-gray-500 dark:text-gray-400">{t('mcp.requests')}</p>
              </div>
              <div>
                <p className="text-2xl font-bold text-green-600 dark:text-green-400">
                  {mcpStats?.total ? `${Math.round(mcpStats.success_rate)}%` : '—'}
                </p>
                <p className="text-xs text-gray-500 dark:text-gray-400">{t('mcp.success')}</p>
              </div>
              <div>
                <p className="text-2xl font-bold text-gray-700 dark:text-gray-300">
                  {mcpStats?.average_duration_ms ? `${Math.round(mcpStats.average_duration_ms)}` : '—'}
                </p>
                <p className="text-xs text-gray-500 dark:text-gray-400">{t('mcp.avgDuration')}</p>
              </div>
            </div>
            <div className="flex-1 min-w-0">
              <MiniBarChart data={mcpHourlyUsage} hoursCount={24} />
            </div>
          </div>

          {/* Usage by Service - Stacked Bar */}
          <div className="border-t border-gray-100 dark:border-gray-700 pt-3">
            <div className="flex items-center gap-2 mb-3">
              <Wrench className="w-3.5 h-3.5 text-gray-400" />
              <span className="text-xs font-medium text-gray-500 dark:text-gray-400">{t('mcp.byService')}</span>
            </div>
            {mcpStats?.top_tools && Object.keys(mcpStats.top_tools).length > 0 ? (
              (() => {
                // Aggregate by service
                const serviceUsage: Record<string, number> = {};
                Object.entries(mcpStats.top_tools).forEach(([tool, count]) => {
                  const serviceName = getServiceFromToolName(tool) || 'system';
                  serviceUsage[serviceName] = (serviceUsage[serviceName] || 0) + count;
                });

                // Sort by count descending
                const sortedServices = Object.entries(serviceUsage)
                  .sort(([, a], [, b]) => b - a);
                const totalCount = Object.values(serviceUsage).reduce((a, b) => a + b, 0);

                return (
                  <div className="space-y-3">
                    {/* Stacked Bar */}
                    <div className="h-4 rounded-full overflow-hidden flex bg-gray-100 dark:bg-gray-700">
                      {sortedServices.map(([serviceName, count]) => {
                        const colors = getServiceColor(serviceName);
                        const percentage = (count / totalCount) * 100;

                        return (
                          <div
                            key={serviceName}
                            className="h-full transition-all hover:opacity-80 cursor-pointer relative group"
                            style={{ width: `${percentage}%`, backgroundColor: colors.hex }}
                            title={`${serviceName}: ${count} (${percentage.toFixed(1)}%)`}
                          >
                            {/* Tooltip on hover */}
                            <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1 px-2 py-1 bg-gray-900 text-white text-xs rounded opacity-0 group-hover:opacity-100 pointer-events-none whitespace-nowrap z-10">
                              {serviceName}: {count}
                            </div>
                          </div>
                        );
                      })}
                    </div>

                    {/* Legend */}
                    <div className="flex flex-wrap gap-x-4 gap-y-1">
                      {sortedServices.map(([serviceName, count]) => {
                        const colors = getServiceColor(serviceName);

                        return (
                          <div key={serviceName} className="flex items-center gap-1.5">
                            <span
                              className="w-2.5 h-2.5 rounded-sm flex-shrink-0"
                              style={{ backgroundColor: colors.hex }}
                            />
                            <span className="text-xs text-gray-600 dark:text-gray-400 capitalize">
                              {serviceName}
                            </span>
                            <span className="text-xs tabular-nums text-gray-400 dark:text-gray-500">
                              {count}
                            </span>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                );
              })()
            ) : (
              <p className="text-xs text-gray-500 dark:text-gray-400 text-center py-2">{t('mcp.noRequests')}</p>
            )}
          </div>

          {/* Usage by User - Stacked Bar */}
          <div className="border-t border-gray-100 dark:border-gray-700 pt-3 mt-3">
            <div className="flex items-center gap-2 mb-3">
              <Users className="w-3.5 h-3.5 text-gray-400" />
              <span className="text-xs font-medium text-gray-500 dark:text-gray-400">{t('mcp.byUser')}</span>
            </div>
            {mcpUserStats.length > 0 ? (
              (() => {
                // User colors palette
                const userColors = [
                  { bg: 'bg-blue-500', hex: '#3b82f6' },
                  { bg: 'bg-emerald-500', hex: '#10b981' },
                  { bg: 'bg-violet-500', hex: '#8b5cf6' },
                  { bg: 'bg-amber-500', hex: '#f59e0b' },
                  { bg: 'bg-rose-500', hex: '#f43f5e' },
                  { bg: 'bg-cyan-500', hex: '#06b6d4' },
                  { bg: 'bg-fuchsia-500', hex: '#d946ef' },
                  { bg: 'bg-lime-500', hex: '#84cc16' },
                ];

                const sortedUsers = [...mcpUserStats].sort((a, b) => b.request_count - a.request_count);
                const totalCount = sortedUsers.reduce((sum, u) => sum + u.request_count, 0);

                return (
                  <div className="space-y-3">
                    {/* Stacked Bar */}
                    <div className="h-4 rounded-full overflow-hidden flex bg-gray-100 dark:bg-gray-700">
                      {sortedUsers.map((user, index) => {
                        const color = userColors[index % userColors.length];
                        const percentage = (user.request_count / totalCount) * 100;
                        const displayName = user.user_display_name || user.user_id.split('@')[0];

                        return (
                          <div
                            key={user.user_id}
                            className="h-full transition-all hover:opacity-80 cursor-pointer relative group"
                            style={{ width: `${percentage}%`, backgroundColor: color.hex }}
                            title={`${displayName}: ${user.request_count} (${percentage.toFixed(1)}%)`}
                          >
                            {/* Tooltip on hover */}
                            <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1 px-2 py-1 bg-gray-900 text-white text-xs rounded opacity-0 group-hover:opacity-100 pointer-events-none whitespace-nowrap z-10">
                              {displayName}: {user.request_count}
                            </div>
                          </div>
                        );
                      })}
                    </div>

                    {/* Legend */}
                    <div className="flex flex-wrap gap-x-4 gap-y-1">
                      {sortedUsers.map((user, index) => {
                        const color = userColors[index % userColors.length];
                        const displayName = user.user_display_name || user.user_id.split('@')[0];

                        return (
                          <div key={user.user_id} className="flex items-center gap-1.5">
                            <span
                              className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                              style={{ backgroundColor: color.hex }}
                            />
                            <span className="text-xs text-gray-600 dark:text-gray-400">
                              {displayName}
                            </span>
                            <span className="text-xs tabular-nums text-gray-400 dark:text-gray-500">
                              {user.request_count}
                            </span>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                );
              })()
            ) : (
              <p className="text-xs text-gray-500 dark:text-gray-400 text-center py-2">{t('mcp.noUsers')}</p>
            )}
          </div>
        </div>

        {/* Users & Groups Block */}
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 p-4">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Users className="w-4 h-4 text-blue-500" />
              <span className="font-semibold text-sm text-gray-900 dark:text-white">{t('users.title')}</span>
            </div>
            <Link to="/users" className="text-xs text-blue-600 hover:text-blue-700 flex items-center gap-1">
              {tCommon('actions.manage')} <ArrowRight className="w-3 h-3" />
            </Link>
          </div>

          {/* Stats Row */}
          <div className="grid grid-cols-3 gap-2 mb-3">
            <div className="text-center p-2 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
              <p className="text-xl font-bold text-blue-600 dark:text-blue-400">
                {new Set(userMappings.map(m => m.central_user_id)).size}
              </p>
              <p className="text-[10px] text-gray-600 dark:text-gray-400">{t('users.totalUsers')}</p>
            </div>
            <div className="text-center p-2 bg-purple-50 dark:bg-purple-900/20 rounded-lg">
              <p className="text-xl font-bold text-purple-600 dark:text-purple-400">{groups.length}</p>
              <p className="text-[10px] text-gray-600 dark:text-gray-400">{t('users.totalGroups')}</p>
            </div>
            <div className="text-center p-2 bg-green-50 dark:bg-green-900/20 rounded-lg">
              <p className="text-xl font-bold text-green-600 dark:text-green-400">{userMappingsCount}</p>
              <p className="text-[10px] text-gray-600 dark:text-gray-400">{t('users.totalMappings')}</p>
            </div>
          </div>

          {/* Groups List */}
          {groups.length > 0 ? (
            <div className="space-y-1.5">
              <p className="text-[10px] uppercase tracking-wider text-gray-500 dark:text-gray-400 font-medium mb-1">{t('users.mcpGroups')}</p>
              {groups.slice(0, 4).map(group => (
                <div
                  key={group.id}
                  className="flex items-center gap-2.5 p-2 bg-gray-50 dark:bg-gray-900/50 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800/50 transition-colors"
                >
                  <div
                    className="w-2.5 h-2.5 rounded-full flex-shrink-0 ring-2 ring-white dark:ring-gray-800 shadow-sm"
                    style={{ backgroundColor: group.color || '#6b7280' }}
                  />
                  <span className="text-xs font-medium text-gray-900 dark:text-white truncate flex-1">
                    {group.name}
                  </span>
                  <div className="flex items-center gap-1.5 flex-shrink-0">
                    <span className="text-[10px] px-1.5 py-0.5 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded font-medium">
                      {t('users.userCount', { count: group.member_count })}
                    </span>
                    <span className="text-[10px] px-1.5 py-0.5 bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 rounded font-medium">
                      {t('users.toolCount', { count: group.tool_count })}
                    </span>
                  </div>
                </div>
              ))}
              {groups.length > 4 && (
                <p className="text-[10px] text-gray-400 dark:text-gray-500 text-center pt-1">
                  {t('users.moreGroups', { count: groups.length - 4 })}
                </p>
              )}
            </div>
          ) : (
            <div className="text-center py-4">
              <p className="text-xs text-gray-500 dark:text-gray-400">{t('users.noGroups')}</p>
              <Link to="/users" className="text-xs text-blue-600 hover:text-blue-700 mt-1 inline-block">
                {t('users.createGroup')}
              </Link>
            </div>
          )}
        </div>
      </div>
      )}

      {/* Second Row: AI Training (expanded) | Observability (compact) */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* AI Training - Expanded Block with Charts */}
        <div className="lg:col-span-2 bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 p-4">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <div className="p-1.5 rounded-lg bg-violet-100 dark:bg-violet-900/30">
                <Brain className="w-4 h-4 text-violet-600 dark:text-violet-400" />
              </div>
              <span className="font-semibold text-sm text-gray-900 dark:text-white">{t('training.title')}</span>
              {(trainingStats?.active_sessions ?? 0) > 0 && (
                <span className="flex items-center gap-1.5 text-[10px] px-2 py-0.5 rounded-full bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400">
                  <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />
                  {(trainingStats?.active_sessions ?? 0) === 1 ? t('training.active', { count: trainingStats?.active_sessions }) : t('training.actives', { count: trainingStats?.active_sessions })}
                </span>
              )}
            </div>
            <Link to="/training" className="text-xs text-blue-600 hover:text-blue-700 flex items-center gap-1">
              {tCommon('actions.manage')} <ArrowRight className="w-3 h-3" />
            </Link>
          </div>

          {/* Main Stats Row */}
          <div className="grid grid-cols-5 gap-3 mb-4">
            <div className="p-3 rounded-xl bg-gradient-to-br from-violet-50 to-purple-50 dark:from-violet-900/20 dark:to-purple-900/20 border border-violet-100 dark:border-violet-800/50 text-center">
              <p className="text-2xl font-bold text-violet-600 dark:text-violet-400">{trainingStats?.total_prompts ?? 0}</p>
              <p className="text-[10px] text-gray-600 dark:text-gray-400">{t('training.prompts')}</p>
            </div>
            <div className="p-3 rounded-xl bg-gradient-to-br from-fuchsia-50 to-pink-50 dark:from-fuchsia-900/20 dark:to-pink-900/20 border border-fuchsia-100 dark:border-fuchsia-800/50 text-center">
              <p className="text-2xl font-bold text-fuchsia-600 dark:text-fuchsia-400">{trainingStats?.validated_prompts ?? 0}</p>
              <p className="text-[10px] text-gray-600 dark:text-gray-400">{t('training.validated')}</p>
            </div>
            <div className="p-3 rounded-xl bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 border border-blue-100 dark:border-blue-800/50 text-center">
              <p className="text-2xl font-bold text-blue-600 dark:text-blue-400">{trainingStats?.total_sessions ?? 0}</p>
              <p className="text-[10px] text-gray-600 dark:text-gray-400">{t('training.sessions')}</p>
            </div>
            <div className="p-3 rounded-xl bg-gradient-to-br from-green-50 to-emerald-50 dark:from-green-900/20 dark:to-emerald-900/20 border border-green-100 dark:border-green-800/50 text-center">
              <p className="text-2xl font-bold text-green-600 dark:text-green-400">{trainingStats?.completed_sessions ?? 0}</p>
              <p className="text-[10px] text-gray-600 dark:text-gray-400">{t('training.completed')}</p>
            </div>
            <div className="p-3 rounded-xl bg-gradient-to-br from-cyan-50 to-teal-50 dark:from-cyan-900/20 dark:to-teal-900/20 border border-cyan-100 dark:border-cyan-800/50 text-center">
              <p className="text-2xl font-bold text-cyan-600 dark:text-cyan-400">{trainingWorkers.length}</p>
              <p className="text-[10px] text-gray-600 dark:text-gray-400">{t('training.workers')}</p>
            </div>
          </div>

          {/* Two Column Layout: Prompts by Category + Workers */}
          <div className="grid grid-cols-2 gap-4">
            {/* Prompts by Service - Stacked Bar (same style as TrainingOverview) */}
            <div className="border-t border-gray-100 dark:border-gray-700 pt-3">
              <div className="flex items-center gap-2 mb-3">
                <Sparkles className="w-3.5 h-3.5 text-violet-500" />
                <span className="text-xs font-medium text-gray-500 dark:text-gray-400">{t('training.byService')}</span>
              </div>
              {Object.keys(promptsByService).length > 0 ? (
                (() => {
                  // Service colors matching TrainingOverview exactly
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
                  const getColor = (name: string, index: number) => {
                    const lower = name.toLowerCase();
                    return SERVICE_COLORS[lower] || DEFAULT_COLORS[index % DEFAULT_COLORS.length];
                  };

                  const sortedServices = Object.entries(promptsByService)
                    .sort(([, a], [, b]) => b - a);
                  const totalCount = Object.values(promptsByService).reduce((a, b) => a + b, 0);

                  return (
                    <div className="space-y-3">
                      {/* Stacked Bar */}
                      <div className="h-5 rounded-full overflow-hidden flex bg-gray-100 dark:bg-gray-700">
                        {sortedServices.map(([serviceName, count], index) => {
                          const color = getColor(serviceName, index);
                          const percentage = totalCount > 0 ? (count / totalCount) * 100 : 0;

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
                          const color = getColor(serviceName, index);
                          const percentage = totalCount > 0 ? (count / totalCount) * 100 : 0;

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
                })()
              ) : (
                <div className="h-20 flex items-center justify-center">
                  <p className="text-xs text-gray-500 dark:text-gray-400">{t('training.noPrompts')}</p>
                </div>
              )}
            </div>

            {/* Workers Status */}
            <div className="border-t border-gray-100 dark:border-gray-700 pt-3">
              <div className="flex items-center gap-2 mb-3">
                <Server className="w-3.5 h-3.5 text-cyan-500" />
                <span className="text-xs font-medium text-gray-500 dark:text-gray-400">{t('training.gpuWorkers')}</span>
              </div>
              {trainingWorkers.length > 0 ? (
                <div className="space-y-2">
                  {trainingWorkers.map(worker => {
                    const isOnline = worker.status === 'online';
                    const isBusy = !!worker.current_job_id;
                    const gpuMemoryGb = worker.gpu_memory_total_mb ? (worker.gpu_memory_total_mb / 1024).toFixed(0) : '—';

                    return (
                      <div key={worker.id} className="flex items-center justify-between text-xs p-2 rounded-lg bg-gray-50 dark:bg-gray-900/50 border border-gray-100 dark:border-gray-800">
                        <div className="flex items-center gap-2">
                          <div className={`w-2 h-2 rounded-full ${
                            isBusy ? 'bg-yellow-500 animate-pulse' : isOnline ? 'bg-green-500' : 'bg-gray-400'
                          }`} />
                          <span className="text-gray-700 dark:text-gray-300 font-medium">{worker.name}</span>
                        </div>
                        <div className="flex items-center gap-2">
                          {worker.gpu_names && worker.gpu_names[0] && (
                            <span className="text-[10px] text-gray-500 dark:text-gray-400 truncate max-w-[100px]">
                              {worker.gpu_names[0].replace('NVIDIA ', '').replace('GeForce ', '')}
                            </span>
                          )}
                          {worker.gpu_available && (
                            <span className="text-[10px] px-1.5 py-0.5 rounded bg-cyan-100 dark:bg-cyan-900/30 text-cyan-700 dark:text-cyan-300 font-medium">
                              {gpuMemoryGb} GB
                            </span>
                          )}
                          <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${
                            isBusy
                              ? 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-300'
                              : isOnline
                                ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300'
                                : 'bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400'
                          }`}>
                            {isBusy ? t('training.training') : isOnline ? t('training.ready') : t('training.offline')}
                          </span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="h-20 flex items-center justify-center">
                  <p className="text-xs text-gray-500 dark:text-gray-400">{t('training.noWorkers')}</p>
                </div>
              )}
            </div>
          </div>

          {/* Sessions Success Rate Bar */}
          {(trainingStats?.total_sessions ?? 0) > 0 && (
            <div className="mt-4 pt-3 border-t border-gray-100 dark:border-gray-700">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-medium text-gray-500 dark:text-gray-400">{t('training.successRate')}</span>
                <span className="text-xs font-semibold text-gray-700 dark:text-gray-300">
                  {((trainingStats?.completed_sessions ?? 0) / (trainingStats?.total_sessions ?? 1) * 100).toFixed(0)}%
                </span>
              </div>
              <div className="h-2.5 rounded-full overflow-hidden flex bg-gray-100 dark:bg-gray-700">
                <div
                  className="h-full bg-green-500 rounded-l-full"
                  style={{ width: `${((trainingStats?.completed_sessions ?? 0) / (trainingStats?.total_sessions ?? 1) * 100)}%` }}
                  title={`${t('training.completedSessions')}: ${trainingStats?.completed_sessions ?? 0}`}
                />
                <div
                  className="h-full bg-red-500"
                  style={{ width: `${((trainingStats?.failed_sessions ?? 0) / (trainingStats?.total_sessions ?? 1) * 100)}%` }}
                  title={`${t('training.failedSessions')}: ${trainingStats?.failed_sessions ?? 0}`}
                />
                <div
                  className="h-full bg-yellow-500"
                  style={{ width: `${((trainingStats?.active_sessions ?? 0) / (trainingStats?.total_sessions ?? 1) * 100)}%` }}
                  title={`${t('training.activeSessions')}: ${trainingStats?.active_sessions ?? 0}`}
                />
              </div>
              <div className="flex items-center justify-between mt-1.5 text-[10px] text-gray-500 dark:text-gray-400">
                <div className="flex items-center gap-3">
                  <span className="flex items-center gap-1">
                    <span className="w-2 h-2 rounded-sm bg-green-500" /> {t('training.completedSessions')}: {trainingStats?.completed_sessions ?? 0}
                  </span>
                  <span className="flex items-center gap-1">
                    <span className="w-2 h-2 rounded-sm bg-red-500" /> {t('training.failedSessions')}: {trainingStats?.failed_sessions ?? 0}
                  </span>
                  <span className="flex items-center gap-1">
                    <span className="w-2 h-2 rounded-sm bg-yellow-500" /> {t('training.activeSessions')}: {trainingStats?.active_sessions ?? 0}
                  </span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Observability Block - Compact */}
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 p-4">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <div className="p-1.5 rounded-lg bg-cyan-100 dark:bg-cyan-900/30">
                <Activity className="w-4 h-4 text-cyan-600 dark:text-cyan-400" />
              </div>
              <span className="font-semibold text-sm text-gray-900 dark:text-white">{t('observability.title')}</span>
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400">{t('observability.period')}</span>
            </div>
            <Link to="/monitoring" className="text-xs text-blue-600 hover:text-blue-700 flex items-center gap-1">
              {tCommon('actions.manage')} <ArrowRight className="w-3 h-3" />
            </Link>
          </div>

          <div className="space-y-3">
            {/* Logs Card */}
            <div className="p-3 rounded-xl bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 border border-blue-100 dark:border-blue-800/50">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <div className="p-1 rounded-md bg-blue-100 dark:bg-blue-900/50">
                    <FileText className="w-3.5 h-3.5 text-blue-600 dark:text-blue-400" />
                  </div>
                  <span className="text-xs font-medium text-gray-700 dark:text-gray-300">{t('observability.logs')}</span>
                </div>
                <span className="text-lg font-bold text-gray-900 dark:text-white">
                  {(logStats?.total ?? 0).toLocaleString()}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-[10px] text-gray-500 dark:text-gray-400">{t('observability.errorRate')}</span>
                <span className={`text-xs font-semibold px-1.5 py-0.5 rounded ${
                  (logStats?.error_rate ?? 0) > 5
                    ? 'bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400'
                    : 'bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400'
                }`}>
                  {logStats?.error_rate?.toFixed(1) ?? 0}%
                </span>
              </div>
            </div>

            {/* Network Card */}
            <div className="p-3 rounded-xl bg-gradient-to-br from-emerald-50 to-teal-50 dark:from-emerald-900/20 dark:to-teal-900/20 border border-emerald-100 dark:border-emerald-800/50">
              <div className="flex items-center gap-2 mb-2">
                <div className="p-1 rounded-md bg-emerald-100 dark:bg-emerald-900/50">
                  <Wifi className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
                </div>
                <span className="text-xs font-medium text-gray-700 dark:text-gray-300">{t('observability.network')}</span>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1">
                    <span className="w-4 h-4 flex items-center justify-center rounded bg-blue-100 dark:bg-blue-900/50 text-blue-600 dark:text-blue-400 text-[10px] font-bold">↑</span>
                  </div>
                  <span className="text-xs font-semibold text-gray-900 dark:text-white">{formatBytes(metrics?.network_bytes_sent || 0)}</span>
                </div>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1">
                    <span className="w-4 h-4 flex items-center justify-center rounded bg-green-100 dark:bg-green-900/50 text-green-600 dark:text-green-400 text-[10px] font-bold">↓</span>
                  </div>
                  <span className="text-xs font-semibold text-gray-900 dark:text-white">{formatBytes(metrics?.network_bytes_recv || 0)}</span>
                </div>
              </div>
            </div>

            {/* Alerts Card */}
            <div className={`p-3 rounded-xl border ${
              (alertStats?.active || 0) > 0
                ? 'bg-gradient-to-br from-red-50 to-orange-50 dark:from-red-900/20 dark:to-orange-900/20 border-red-200 dark:border-red-800/50'
                : 'bg-gradient-to-br from-green-50 to-emerald-50 dark:from-green-900/20 dark:to-emerald-900/20 border-green-100 dark:border-green-800/50'
            }`}>
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <div className={`p-1 rounded-md ${
                    (alertStats?.active || 0) > 0
                      ? 'bg-red-100 dark:bg-red-900/50'
                      : 'bg-green-100 dark:bg-green-900/50'
                  }`}>
                    <AlertTriangle className={`w-3.5 h-3.5 ${
                      (alertStats?.active || 0) > 0
                        ? 'text-red-600 dark:text-red-400'
                        : 'text-green-600 dark:text-green-400'
                    }`} />
                  </div>
                  <span className="text-xs font-medium text-gray-700 dark:text-gray-300">{t('observability.alerts')}</span>
                </div>
                <span className={`text-lg font-bold ${
                  (alertStats?.active || 0) > 0
                    ? 'text-red-600 dark:text-red-400'
                    : 'text-green-600 dark:text-green-400'
                }`}>
                  {alertStats?.active || 0}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-[10px] text-gray-500 dark:text-gray-400">{t('observability.totalPeriod')}</span>
                <span className="text-xs font-medium text-gray-700 dark:text-gray-300">{alertStats?.total || 0}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
