import { useState, useEffect } from 'react';
import type { FC } from 'react';
import {
  User,
  Mail,
  Users,
  RefreshCw,
  Shield,
  Clock,
  Database,
  AlertCircle,
  CheckCircle
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { getApiBaseUrl } from '../../lib/api';
import { getServiceColor } from '../../lib/serviceColors';

interface CentralizedUserData {
  central_user_id: string;
  emails: string[];
  usernames: string[];
  display_names: string[];
  primary_email: string;
  primary_username: string;
  primary_display_name: string;
  service_data: Record<string, {
    service_name: string;
    service_type: string;
    user_data: any;
    updated_at: string;
  }>;
  active_services: string[];
  service_count: number;
  roles: Record<string, string>;
  is_admin_anywhere: boolean;
  last_updated: string;
}

interface UserGroup {
  id: string;
  name: string;
  description?: string;
  color?: string;
  icon?: string;
  priority: number;
}

interface CentralizedUserDashboardProps {
  centralUserId?: string;
  onUserSelect?: (userId: string) => void;
}

const CentralizedUserDashboard: FC<CentralizedUserDashboardProps> = ({
  centralUserId,
  onUserSelect
}) => {
  const { t } = useTranslation('users');
  const [userData, setUserData] = useState<CentralizedUserData | null>(null);
  const [allUsers, setAllUsers] = useState<CentralizedUserData[]>([]);
  const [userGroups, setUserGroups] = useState<UserGroup[]>([]);
  const [loading, setLoading] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedUser, setSelectedUser] = useState<string | null>(centralUserId || null);

  const fetchUserGroups = async (userId: string) => {
    try {
      const response = await fetch(`${getApiBaseUrl()}/api/groups/user/${encodeURIComponent(userId)}`);
      if (response.ok) {
        const data = await response.json();
        setUserGroups(data.groups || []);
      }
    } catch (err) {
      console.error('Error fetching user groups:', err);
    }
  };

  const fetchCentralizedUser = async (userId: string, refresh = false) => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch(
        `${getApiBaseUrl()}/api/users/centralized/${userId}${refresh ? '?refresh=true' : ''}`
      );

      if (!response.ok) {
        if (response.status === 404) {
          throw new Error('User not found or has no active mappings');
        }
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to fetch user data');
      }

      const data = await response.json();
      setUserData(data);

      // Also fetch user groups
      await fetchUserGroups(userId);

    } catch (err) {
      console.error('Error fetching centralized user data:', err);
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch user data';
      setError(errorMessage);
      setUserData(null);
    } finally {
      setLoading(false);
    }
  };

  const fetchAllUsers = async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch(`${getApiBaseUrl()}/api/users/centralized`);

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to fetch users');
      }

      const data = await response.json();
      setAllUsers(data.users || []);

    } catch (err) {
      console.error('Error fetching all users:', err);
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch users';
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const syncUserMetadata = async (userId: string) => {
    try {
      setSyncing(true);
      setError(null);

      const response = await fetch(
        `${getApiBaseUrl()}/api/users/centralized/${userId}/sync`,
        { method: 'POST' }
      );

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to sync user data');
      }

      const result = await response.json();
      console.log('Sync result:', result);

      // Refresh user data after sync
      if (selectedUser) {
        await fetchCentralizedUser(selectedUser, false);
      }

    } catch (err) {
      console.error('Error syncing user data:', err);
      const errorMessage = err instanceof Error ? err.message : 'Failed to sync user data';
      setError(errorMessage);
    } finally {
      setSyncing(false);
    }
  };

  useEffect(() => {
    if (centralUserId) {
      setSelectedUser(centralUserId);
      fetchCentralizedUser(centralUserId);
    } else {
      fetchAllUsers();
    }
  }, [centralUserId]);

  const handleUserSelect = (userId: string) => {
    setSelectedUser(userId);
    fetchCentralizedUser(userId);
    onUserSelect?.(userId);
  };


  const formatDateTime = (dateStr: string) => {
    return new Date(dateStr).toLocaleString();
  };

  if (loading && !userData && allUsers.length === 0) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-4 sm:p-6">
        <div className="flex items-center justify-center">
          <RefreshCw className="w-5 h-5 sm:w-6 sm:h-6 text-blue-500 animate-spin mr-2 sm:mr-3" />
          <span className="text-sm sm:text-lg text-gray-600 dark:text-gray-400">{t('centralized.loading')}</span>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4 sm:space-y-6">
      {/* Header */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-3 sm:p-4">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div className="flex items-center space-x-3 min-w-0">
            <Database className="w-5 h-5 sm:w-6 sm:h-6 text-blue-600 flex-shrink-0" />
            <div className="min-w-0">
              <h3 className="text-base sm:text-lg font-semibold text-gray-900 dark:text-white">
                {t('centralized.title')}
              </h3>
              <p className="text-xs sm:text-sm text-gray-600 dark:text-gray-400">
                {t('centralized.subtitle')}
              </p>
            </div>
          </div>

          {selectedUser && (
            <div className="flex items-center gap-2">
              {/* Refresh button - icon only on all screens */}
              <button
                onClick={() => fetchCentralizedUser(selectedUser, true)}
                disabled={loading}
                className="p-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-600 disabled:opacity-50 flex items-center transition-colors flex-shrink-0"
              >
                <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
              </button>

              {/* Sync button - text visible on all screens */}
              <button
                onClick={() => syncUserMetadata(selectedUser)}
                disabled={syncing}
                className="flex items-center gap-2 px-3 py-2 bg-green-600 text-white text-sm font-medium rounded-lg hover:bg-green-700 disabled:opacity-50 transition-colors"
              >
                <Database className={`w-4 h-4 ${syncing ? 'animate-pulse' : ''}`} />
                <span>{syncing ? t('centralized.syncing') : t('centralized.sync')}</span>
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
          <div className="flex items-center">
            <AlertCircle className="w-5 h-5 text-red-500 mr-2" />
            <span className="text-sm text-red-700 dark:text-red-400">{error}</span>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 sm:gap-6">
        {/* User Selection Panel */}
        {!centralUserId && (
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-3 sm:p-4">
            <h4 className="font-semibold text-gray-900 dark:text-white mb-3 sm:mb-4 text-sm sm:text-base">{t('centralized.selectUser')}</h4>
            <div className="space-y-2 max-h-64 sm:max-h-96 overflow-y-auto">
              {allUsers.map((user) => (
                <div
                  key={user.central_user_id}
                  onClick={() => handleUserSelect(user.central_user_id)}
                  className={`p-2 sm:p-3 rounded-lg cursor-pointer transition-colors ${
                    selectedUser === user.central_user_id
                      ? 'bg-blue-50 dark:bg-blue-900/30 border-blue-200 dark:border-blue-700'
                      : 'hover:bg-gray-50 dark:hover:bg-gray-700 border-transparent'
                  } border`}
                >
                  <div className="flex items-center justify-between">
                    <div className="min-w-0">
                      <p className="font-medium text-sm sm:text-base text-gray-900 dark:text-white truncate">
                        {user.primary_display_name || user.primary_username || user.central_user_id}
                      </p>
                      <p className="text-xs sm:text-sm text-gray-600 dark:text-gray-400 truncate">{user.primary_email}</p>
                      <div className="flex items-center space-x-2 mt-1">
                        <span className="text-xs text-gray-500 dark:text-gray-500">{t('centralized.stats.services', { count: user.service_count })}</span>
                        {user.is_admin_anywhere && (
                          <Shield className="w-3 h-3 text-red-500" />
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* User Details Panel */}
        {userData && (
          <div className={`space-y-6 ${centralUserId ? 'lg:col-span-3' : 'lg:col-span-2'}`}>
            {/* User Overview */}
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
              <div className="flex items-center justify-between mb-6">
                <div className="flex items-center space-x-4">
                  <div className="w-16 h-16 bg-blue-100 dark:bg-blue-900/30 rounded-full flex items-center justify-center">
                    <User className="w-8 h-8 text-blue-600" />
                  </div>
                  <div>
                    <h2 className="text-xl font-bold text-gray-900 dark:text-white">
                      {userData.primary_display_name || userData.primary_username || userData.central_user_id}
                    </h2>
                    <p className="text-gray-600 dark:text-gray-400">{userData.primary_email}</p>
                    <div className="flex items-center space-x-2 mt-1">
                      <span className="text-sm text-gray-500 dark:text-gray-400">ID: {userData.central_user_id}</span>
                      {userData.is_admin_anywhere && (
                        <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-400">
                          <Shield className="w-3 h-3 mr-1" />
                          {t('centralized.admin')}
                        </span>
                      )}
                    </div>
                    {/* Group Labels */}
                    {userGroups.length > 0 && (
                      <div className="flex flex-wrap items-center gap-1.5 mt-2">
                        {userGroups.map((group) => (
                          <span
                            key={group.id}
                            className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium"
                            style={{
                              backgroundColor: `${group.color || '#6366f1'}20`,
                              color: group.color || '#6366f1',
                              border: `1px solid ${group.color || '#6366f1'}40`
                            }}
                          >
                            <Shield className="w-3 h-3 mr-1" />
                            {group.name}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>

                <div className="text-right">
                  <p className="text-sm text-gray-500 dark:text-gray-400">{t('centralized.lastUpdated')}</p>
                  <p className="text-sm font-medium text-gray-900 dark:text-white">
                    {formatDateTime(userData.last_updated)}
                  </p>
                </div>
              </div>

              {/* Summary Stats */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="text-center p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                  <Users className="w-6 h-6 text-blue-600 mx-auto mb-1" />
                  <p className="text-sm text-gray-600 dark:text-gray-400">{t('centralized.stats.services')}</p>
                  <p className="text-xl font-bold text-blue-600">{userData.service_count}</p>
                </div>

                <div className="text-center p-3 bg-green-50 dark:bg-green-900/20 rounded-lg">
                  <Mail className="w-6 h-6 text-green-600 mx-auto mb-1" />
                  <p className="text-sm text-gray-600 dark:text-gray-400">{t('centralized.stats.emails')}</p>
                  <p className="text-xl font-bold text-green-600">{userData.emails.length}</p>
                </div>

                <div className="text-center p-3 bg-purple-50 dark:bg-purple-900/20 rounded-lg">
                  <User className="w-6 h-6 text-purple-600 mx-auto mb-1" />
                  <p className="text-sm text-gray-600 dark:text-gray-400">{t('centralized.stats.usernames')}</p>
                  <p className="text-xl font-bold text-purple-600">{userData.usernames.length}</p>
                </div>

                <div className="text-center p-3 bg-orange-50 dark:bg-orange-900/20 rounded-lg">
                  <Shield className="w-6 h-6 text-orange-600 mx-auto mb-1" />
                  <p className="text-sm text-gray-600 dark:text-gray-400">{t('centralized.stats.adminAccess')}</p>
                  <p className="text-xl font-bold text-orange-600">
                    {Object.values(userData.roles).filter(r => r === 'admin').length}
                  </p>
                </div>
              </div>
            </div>

            {/* All Emails & Usernames */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-4">
                <h4 className="font-semibold text-gray-900 dark:text-white mb-3 flex items-center">
                  <Mail className="w-4 h-4 mr-2 text-green-600" />
                  {t('centralized.allEmails', { count: userData.emails.length })}
                </h4>
                <div className="space-y-2">
                  {userData.emails.map((email, index) => (
                    <div key={index} className="flex items-center justify-between p-2 bg-gray-50 dark:bg-gray-800/50 rounded">
                      <span className="text-sm text-gray-900 dark:text-white">{email}</span>
                      {email === userData.primary_email && (
                        <span className="text-xs bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 px-2 py-1 rounded">{t('centralized.primary')}</span>
                      )}
                    </div>
                  ))}
                </div>
              </div>

              <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-4">
                <h4 className="font-semibold text-gray-900 dark:text-white mb-3 flex items-center">
                  <User className="w-4 h-4 mr-2 text-purple-600" />
                  {t('centralized.allUsernames', { count: userData.usernames.length })}
                </h4>
                <div className="space-y-2">
                  {userData.usernames.map((username, index) => (
                    <div key={index} className="flex items-center justify-between p-2 bg-gray-50 dark:bg-gray-800/50 rounded">
                      <span className="text-sm text-gray-900 dark:text-white">{username}</span>
                      {username === userData.primary_username && (
                        <span className="text-xs bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-400 px-2 py-1 rounded">{t('centralized.primary')}</span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Service Details */}
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-4">
              <h4 className="font-semibold text-gray-900 dark:text-white mb-4 flex items-center">
                <Database className="w-4 h-4 mr-2 text-blue-600" />
                {t('centralized.serviceDetails', { count: userData.service_count })}
              </h4>
              <div className="space-y-4">
                {Object.entries(userData.service_data).map(([serviceId, serviceInfo]) => (
                  <div key={serviceId} className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center space-x-3">
                        <div className={`w-3 h-3 rounded-full ${getServiceColor(serviceInfo.service_type).dot}`}></div>
                        <div>
                          <h5 className="font-medium text-gray-900 dark:text-white">{serviceInfo.service_name}</h5>
                          <p className="text-sm text-gray-600 dark:text-gray-400 capitalize">{serviceInfo.service_type}</p>
                        </div>
                      </div>
                      <div className="flex items-center space-x-2">
                        <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                          userData.roles[serviceId] === 'admin'
                            ? 'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-400'
                            : 'bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-300'
                        }`}>
                          {userData.roles[serviceId] === 'admin' && <Shield className="w-3 h-3 mr-1" />}
                          {userData.roles[serviceId]}
                        </span>
                        <span className="text-xs text-gray-500 dark:text-gray-400">
                          {formatDateTime(serviceInfo.updated_at)}
                        </span>
                      </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-sm">
                      <div>
                        <span className="text-gray-600 dark:text-gray-400">{t('centralized.userId')}:</span>
                        <p className="font-medium text-gray-900 dark:text-white">{serviceInfo.user_data.user_id || 'N/A'}</p>
                      </div>
                      <div>
                        <span className="text-gray-600 dark:text-gray-400">{t('centralized.username')}:</span>
                        <p className="font-medium text-gray-900 dark:text-white">{serviceInfo.user_data.username || 'N/A'}</p>
                      </div>
                      <div>
                        <span className="text-gray-600 dark:text-gray-400">{t('centralized.email')}:</span>
                        <p className="font-medium text-gray-900 dark:text-white">{serviceInfo.user_data.email || 'N/A'}</p>
                      </div>
                    </div>

                    {serviceInfo.user_data.fresh_data && (
                      <div className="mt-3 p-3 bg-green-50 dark:bg-green-900/20 rounded">
                        <div className="flex items-center space-x-2">
                          <CheckCircle className="w-4 h-4 text-green-600" />
                          <span className="text-sm text-green-700 dark:text-green-400">{t('centralized.freshData')}</span>
                          <Clock className="w-3 h-3 text-green-600" />
                          <span className="text-xs text-green-600 dark:text-green-400">
                            {formatDateTime(serviceInfo.user_data.last_fetched)}
                          </span>
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default CentralizedUserDashboard;