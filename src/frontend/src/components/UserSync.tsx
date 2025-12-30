import { useState, useEffect } from 'react';
import type { FC } from 'react';
import {
  RefreshCw,
  CheckCircle,
  XCircle,
  Clock,
  Play,
  Settings,
  Eye,
  EyeOff,
  Activity,
  User
} from 'lucide-react';
import { getApiBaseUrl } from '../lib/api';

interface SyncProgress {
  totalMappings: number;
  successfulSyncs: number;
  failedSyncs: number;
  skippedSyncs: number;
  currentMapping?: string;
  startedAt?: string;
  completedAt?: string;
}

interface SyncResult {
  success: boolean;
  centralUserId: string;
  totalMappings: number;
  successfulSyncs: number;
  failedSyncs: number;
  syncDetails: Array<{
    serviceId: string;
    serviceName: string;
    success: boolean;
    error?: string;
  }>;
}

interface UserSyncProps {
  centralUserId?: string;
  serviceFilter?: string;
  onSyncComplete?: (result: any) => void;
}

const UserSync: FC<UserSyncProps> = ({
  centralUserId,
  serviceFilter,
  onSyncComplete
}) => {
  const [syncing, setSyncing] = useState(false);
  const [syncProgress, setSyncProgress] = useState<SyncProgress | null>(null);
  const [syncResult, setSyncResult] = useState<SyncResult | null>(null);
  const [showDetails, setShowDetails] = useState(false);
  const [autoSync, setAutoSync] = useState(false);
  const [syncInterval, setSyncInterval] = useState(3600); // Default 1 hour
  const [lastSyncTime, setLastSyncTime] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Load last sync time from localStorage or API
    const savedSyncTime = localStorage.getItem(`lastSync_${centralUserId || 'all'}`);
    if (savedSyncTime) {
      setLastSyncTime(savedSyncTime);
    }
  }, [centralUserId]);

  const startSync = async (forceSync: boolean = false) => {
    setSyncing(true);
    setSyncResult(null);
    setSyncProgress({
      totalMappings: 0,
      successfulSyncs: 0,
      failedSyncs: 0,
      skippedSyncs: 0,
      startedAt: new Date().toISOString()
    });
    setError(null);

    try {
      const endpoint = centralUserId
        ? `/api/users/${centralUserId}/sync`
        : '/api/users/sync-all';

      const requestBody: any = {
        force_sync: forceSync
      };

      if (serviceFilter) {
        requestBody.service_type = serviceFilter;
      }

      console.log('🔄 Starting user synchronization...');

      const response = await fetch(`${getApiBaseUrl()}${endpoint}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Sync request failed');
      }

      const result = await response.json();
      console.log('✅ Sync completed:', result);

      setSyncResult(result);
      setSyncProgress(prev => prev ? {
        ...prev,
        completedAt: new Date().toISOString(),
        totalMappings: result.totalMappings || 0,
        successfulSyncs: result.successfulSyncs || 0,
        failedSyncs: result.failedSyncs || 0,
        skippedSyncs: result.skippedSyncs || 0
      } : null);

      // Save sync time
      const syncTime = new Date().toISOString();
      setLastSyncTime(syncTime);
      localStorage.setItem(`lastSync_${centralUserId || 'all'}`, syncTime);

      // Call completion callback
      onSyncComplete?.(result);

    } catch (err) {
      console.error('❌ Sync failed:', err);
      const errorMessage = err instanceof Error ? err.message : 'Unknown error occurred';
      setError(errorMessage);
      setSyncProgress(prev => prev ? {
        ...prev,
        completedAt: new Date().toISOString()
      } : null);
    } finally {
      setSyncing(false);
    }
  };

  const formatLastSync = (timestamp: string | null) => {
    if (!timestamp) return 'Never';

    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffMins = Math.floor(diffMs / (1000 * 60));

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    return date.toLocaleDateString();
  };

  const getSyncIcon = () => {
    if (syncing) {
      return <RefreshCw className="w-5 h-5 text-blue-500 animate-spin" />;
    }
    if (syncResult?.success) {
      return <CheckCircle className="w-5 h-5 text-green-500" />;
    }
    if (error) {
      return <XCircle className="w-5 h-5 text-red-500" />;
    }
    return <RefreshCw className="w-5 h-5 text-gray-500" />;
  };

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200">
      <div className="p-4 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            {getSyncIcon()}
            <div>
              <h3 className="text-lg font-semibold text-gray-900">
                User Synchronization
              </h3>
              <p className="text-sm text-gray-600">
                {centralUserId
                  ? `Sync user: ${centralUserId}`
                  : 'Sync all users across services'
                }
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={() => setShowDetails(!showDetails)}
              className="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded transition-colors"
            >
              {showDetails ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            </button>
            <button
              onClick={() => startSync(false)}
              disabled={syncing}
              className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <Play className="w-4 h-4" />
              <span>{syncing ? 'Syncing...' : 'Start Sync'}</span>
            </button>
          </div>
        </div>
      </div>

      <div className="p-4">
        {/* Sync Status */}
        {syncProgress && (
          <div className="mb-4 p-3 bg-blue-50 rounded-lg border border-blue-200">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-blue-900">
                {syncing ? 'Synchronizing...' : 'Sync Completed'}
              </span>
              {syncing && <Activity className="w-4 h-4 text-blue-500 animate-pulse" />}
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div>
                <span className="text-gray-600">Total:</span>
                <span className="ml-2 font-medium">{syncProgress.totalMappings}</span>
              </div>
              <div>
                <span className="text-gray-600">Success:</span>
                <span className="ml-2 font-medium text-green-600">{syncProgress.successfulSyncs}</span>
              </div>
              <div>
                <span className="text-gray-600">Failed:</span>
                <span className="ml-2 font-medium text-red-600">{syncProgress.failedSyncs}</span>
              </div>
              <div>
                <span className="text-gray-600">Skipped:</span>
                <span className="ml-2 font-medium text-yellow-600">{syncProgress.skippedSyncs}</span>
              </div>
            </div>

            {syncProgress.currentMapping && (
              <div className="mt-2 text-sm text-gray-600">
                Currently syncing: <span className="font-medium">{syncProgress.currentMapping}</span>
              </div>
            )}
          </div>
        )}

        {/* Error Display */}
        {error && (
          <div className="mb-4 p-3 bg-red-50 rounded-lg border border-red-200">
            <div className="flex items-center">
              <XCircle className="w-5 h-5 text-red-500 mr-2" />
              <span className="text-sm text-red-700">{error}</span>
            </div>
          </div>
        )}

        {/* Quick Info */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
          <div className="flex items-center space-x-2">
            <Clock className="w-4 h-4 text-gray-500" />
            <div>
              <span className="text-sm text-gray-600">Last Sync:</span>
              <span className="ml-2 text-sm font-medium">{formatLastSync(lastSyncTime)}</span>
            </div>
          </div>

          {serviceFilter && (
            <div className="flex items-center space-x-2">
              <Settings className="w-4 h-4 text-gray-500" />
              <div>
                <span className="text-sm text-gray-600">Service:</span>
                <span className="ml-2 text-sm font-medium capitalize">{serviceFilter}</span>
              </div>
            </div>
          )}

          {centralUserId && (
            <div className="flex items-center space-x-2">
              <User className="w-4 h-4 text-gray-500" />
              <div>
                <span className="text-sm text-gray-600">User:</span>
                <span className="ml-2 text-sm font-medium">{centralUserId}</span>
              </div>
            </div>
          )}
        </div>

        {/* Sync Controls */}
        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={() => startSync(true)}
            disabled={syncing}
            className="px-3 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 transition-colors"
          >
            Force Sync
          </button>

          <label className="flex items-center space-x-2 text-sm">
            <input
              type="checkbox"
              checked={autoSync}
              onChange={(e) => setAutoSync(e.target.checked)}
              className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <span>Auto-sync</span>
          </label>

          <select
            value={syncInterval}
            onChange={(e) => setSyncInterval(parseInt(e.target.value))}
            className="text-sm border border-gray-300 rounded px-2 py-1"
          >
            <option value={300}>5 minutes</option>
            <option value={900}>15 minutes</option>
            <option value={3600}>1 hour</option>
            <option value={21600}>6 hours</option>
            <option value={86400}>24 hours</option>
          </select>
        </div>

        {/* Detailed Results */}
        {showDetails && syncResult && (
          <div className="mt-4 space-y-3">
            <h4 className="text-sm font-medium text-gray-900">Sync Details</h4>
            {syncResult.syncDetails.map((detail, index) => (
              <div
                key={index}
                className={`p-3 rounded-lg border ${
                  detail.success
                    ? 'border-green-200 bg-green-50'
                    : 'border-red-200 bg-red-50'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    {detail.success ? (
                      <CheckCircle className="w-4 h-4 text-green-500" />
                    ) : (
                      <XCircle className="w-4 h-4 text-red-500" />
                    )}
                    <span className="text-sm font-medium">{detail.serviceName}</span>
                  </div>
                  <span className={`text-xs px-2 py-1 rounded ${
                    detail.success
                      ? 'bg-green-100 text-green-800'
                      : 'bg-red-100 text-red-800'
                  }`}>
                    {detail.success ? 'Success' : 'Failed'}
                  </span>
                </div>
                {detail.error && (
                  <p className="mt-1 text-sm text-red-600">{detail.error}</p>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default UserSync;