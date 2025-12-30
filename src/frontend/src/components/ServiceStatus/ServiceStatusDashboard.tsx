import { useState, useEffect } from 'react';
import type { FC } from 'react';
import {
  Activity,
  CheckCircle,
  XCircle,
  AlertCircle,
  Clock,
  RefreshCw,
  TrendingUp,
  Server,
  Wifi,
  WifiOff
} from 'lucide-react';
import { getApiBaseUrl } from '../../lib/api';

interface ServiceHealth {
  service_id: string;
  service_name: string;
  service_type: string;
  status: 'active' | 'inactive' | 'error' | 'testing';
  last_test_at?: string;
  last_test_success?: boolean;
  last_error?: string;
  response_time_ms?: number;
  enabled: boolean;
  uptime_percentage?: number;
  base_url: string;
  port?: number;
}

interface ServiceMetrics {
  total_services: number;
  active_services: number;
  error_services: number;
  average_response_time: number;
  uptime_percentage: number;
  services_by_type: Record<string, number>;
}

const ServiceStatusDashboard: FC = () => {
  const [services, setServices] = useState<ServiceHealth[]>([]);
  const [metrics, setMetrics] = useState<ServiceMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [refreshInterval, setRefreshInterval] = useState(30); // seconds

  useEffect(() => {
    fetchServiceStatus();

    if (autoRefresh) {
      const interval = setInterval(fetchServiceStatus, refreshInterval * 1000);
      return () => clearInterval(interval);
    }
  }, [autoRefresh, refreshInterval]);

  const fetchServiceStatus = async () => {
    try {
      setRefreshing(true);
      setError(null);

      // Fetch services data
      const servicesResponse = await fetch(`${getApiBaseUrl()}/api/services/`);
      if (!servicesResponse.ok) {
        throw new Error('Failed to fetch services');
      }
      const servicesData = await servicesResponse.json();

      // Calculate metrics
      const totalServices = servicesData.length;
      const activeServices = servicesData.filter((s: any) => s.status === 'active').length;
      const errorServices = servicesData.filter((s: any) => s.status === 'error').length;

      const responseTimes = servicesData
        .filter((s: any) => s.last_test_success && s.response_time_ms)
        .map((s: any) => s.response_time_ms);

      const avgResponseTime = responseTimes.length > 0
        ? Math.round(responseTimes.reduce((a: number, b: number) => a + b, 0) / responseTimes.length)
        : 0;

      const servicesByType = servicesData.reduce((acc: Record<string, number>, service: any) => {
        acc[service.service_type] = (acc[service.service_type] || 0) + 1;
        return acc;
      }, {});

      const uptimePercentage = totalServices > 0
        ? Math.round((activeServices / totalServices) * 100)
        : 100;

      setServices(servicesData);
      setMetrics({
        total_services: totalServices,
        active_services: activeServices,
        error_services: errorServices,
        average_response_time: avgResponseTime,
        uptime_percentage: uptimePercentage,
        services_by_type: servicesByType
      });

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch service status');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const getStatusIcon = (service: ServiceHealth) => {
    if (service.status === 'testing') {
      return <Activity className="w-4 h-4 text-blue-500 animate-pulse" />;
    }
    if (!service.enabled) {
      return <Clock className="w-4 h-4 text-gray-400" />;
    }
    if (service.status === 'active' && service.last_test_success) {
      return <CheckCircle className="w-4 h-4 text-green-500" />;
    }
    if (service.status === 'error' || service.last_test_success === false) {
      return <XCircle className="w-4 h-4 text-red-500" />;
    }
    return <AlertCircle className="w-4 h-4 text-yellow-500" />;
  };

  const getServiceTypeIcon = (type: string) => {
    const iconClass = "w-2 h-2 rounded-full";
    switch (type?.toLowerCase()) {
      case 'plex':
        return <div className={`${iconClass} bg-purple-500`}></div>;
      case 'authentik':
        return <div className={`${iconClass} bg-blue-500`}></div>;
      case 'overseerr':
        return <div className={`${iconClass} bg-green-500`}></div>;
      case 'tautulli':
        return <div className={`${iconClass} bg-orange-500`}></div>;
      case 'zammad':
        return <div className={`${iconClass} bg-red-500`}></div>;
      default:
        return <div className={`${iconClass} bg-gray-500`}></div>;
    }
  };

  const formatResponseTime = (timeMs?: number) => {
    if (!timeMs) return 'N/A';
    if (timeMs < 1000) return `${timeMs}ms`;
    return `${(timeMs / 1000).toFixed(1)}s`;
  };

  const formatLastTest = (timestamp?: string) => {
    if (!timestamp) return 'Never tested';

    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / (1000 * 60));

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffMins < 1440) return `${Math.floor(diffMins / 60)}h ago`;
    return date.toLocaleDateString();
  };

  if (loading) {
    return (
      <div className="p-6">
        <div className="animate-pulse">
          <div className="h-8 bg-gray-200 rounded w-1/4 mb-6"></div>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="bg-gray-200 h-24 rounded-lg"></div>
            ))}
          </div>
          <div className="bg-gray-200 h-64 rounded-lg"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center">
            <Activity className="w-8 h-8 mr-3 text-blue-600" />
            Service Status Monitor
          </h1>
          <p className="text-gray-600 mt-1">
            Real-time monitoring of all homelab services
          </p>
        </div>
        <div className="flex items-center space-x-4">
          <label className="flex items-center space-x-2">
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
              className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <span className="text-sm text-gray-700">Auto-refresh</span>
          </label>

          <select
            value={refreshInterval}
            onChange={(e) => setRefreshInterval(parseInt(e.target.value))}
            className="text-sm border border-gray-300 rounded px-2 py-1"
          >
            <option value={10}>10s</option>
            <option value={30}>30s</option>
            <option value={60}>1m</option>
            <option value={300}>5m</option>
          </select>

          <button
            onClick={fetchServiceStatus}
            disabled={refreshing}
            className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
          <div className="flex items-center">
            <XCircle className="w-5 h-5 text-red-500 mr-2" />
            <span className="text-red-700">{error}</span>
          </div>
        </div>
      )}

      {/* Metrics Cards */}
      {metrics && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Total Services</p>
                <p className="text-2xl font-bold text-gray-900">{metrics.total_services}</p>
              </div>
              <Server className="w-8 h-8 text-blue-500" />
            </div>
          </div>

          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Active Services</p>
                <p className="text-2xl font-bold text-green-600">{metrics.active_services}</p>
              </div>
              <Wifi className="w-8 h-8 text-green-500" />
            </div>
          </div>

          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Error Services</p>
                <p className="text-2xl font-bold text-red-600">{metrics.error_services}</p>
              </div>
              <WifiOff className="w-8 h-8 text-red-500" />
            </div>
          </div>

          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Uptime</p>
                <p className="text-2xl font-bold text-blue-600">{metrics.uptime_percentage}%</p>
              </div>
              <TrendingUp className="w-8 h-8 text-blue-500" />
            </div>
          </div>
        </div>
      )}

      {/* Service Status Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {services.map((service) => (
          <div
            key={service.service_id}
            className="bg-white rounded-lg shadow-sm border border-gray-200 p-4"
          >
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center space-x-3">
                {getServiceTypeIcon(service.service_type)}
                <div>
                  <h3 className="font-semibold text-gray-900">{service.service_name}</h3>
                  <p className="text-sm text-gray-600 capitalize">{service.service_type}</p>
                </div>
              </div>
              <div className="flex items-center space-x-2">
                {getStatusIcon(service)}
                <span className={`text-sm px-2 py-1 rounded ${
                  service.status === 'active' && service.last_test_success
                    ? 'bg-green-100 text-green-800'
                    : service.status === 'error' || service.last_test_success === false
                    ? 'bg-red-100 text-red-800'
                    : !service.enabled
                    ? 'bg-gray-100 text-gray-800'
                    : 'bg-yellow-100 text-yellow-800'
                }`}>
                  {!service.enabled
                    ? 'Disabled'
                    : service.status === 'active' && service.last_test_success
                    ? 'Online'
                    : service.status === 'error' || service.last_test_success === false
                    ? 'Offline'
                    : 'Unknown'
                  }
                </span>
              </div>
            </div>

            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-600">URL:</span>
                <span className="font-mono text-gray-900">
                  {service.base_url}{service.port ? `:${service.port}` : ''}
                </span>
              </div>

              <div className="flex justify-between">
                <span className="text-gray-600">Response Time:</span>
                <span className="font-medium">
                  {formatResponseTime(service.response_time_ms)}
                </span>
              </div>

              <div className="flex justify-between">
                <span className="text-gray-600">Last Test:</span>
                <span className="font-medium">
                  {formatLastTest(service.last_test_at)}
                </span>
              </div>

              {service.last_error && (
                <div className="mt-2 p-2 bg-red-50 rounded text-red-600 text-sm">
                  {service.last_error}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {services.length === 0 && !loading && (
        <div className="text-center py-12 bg-gray-50 rounded-lg">
          <Server className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No Services Found</h3>
          <p className="text-gray-600">Configure services first to see their status here.</p>
        </div>
      )}
    </div>
  );
};

export default ServiceStatusDashboard;