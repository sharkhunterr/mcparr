import { useState, useEffect } from 'react';
import type { FC } from 'react';
import {
  Search,
  CheckCircle,
  XCircle,
  RefreshCw,
  User
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { getApiBaseUrl } from '../../lib/api';
import { getServiceColor } from '../../lib/serviceColors';
import HelpTooltip from '../common/HelpTooltip';

interface ServiceUser {
  id?: string;
  user_id?: string;
  username?: string;
  login?: string;
  email?: string;
  name?: string;
  friendly_name?: string;
  is_active?: boolean;
  is_admin?: boolean;
  is_superuser?: boolean;
  is_staff?: boolean;
  [key: string]: any;
}

interface ServiceData {
  service_name: string;
  service_type: string;
  base_url: string;
  users: ServiceUser[];
  user_count: number;
  note?: string;
  error?: string;
}

interface EnumerationData {
  services: Record<string, ServiceData>;
  total_services: number;
  successful_enumerations: number;
  errors: string[];
  enumerated_at: string;
}

interface SelectedUser {
  service_id: string;
  service_name: string;
  service_type: string;
  user_id: string;
  username: string;
  email?: string;
  role: string;
  user_data: ServiceUser;
}


interface UserMappingCreatorProps {
  onMappingCreated?: () => void;
}

const UserMappingCreator: FC<UserMappingCreatorProps> = ({
  onMappingCreated
}) => {
  const { t } = useTranslation('users');
  const [loading, setLoading] = useState(false);
  const [enumerationData, setEnumerationData] = useState<EnumerationData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedServiceFilter, setSelectedServiceFilter] = useState<string>('all');
  const [selectedUsers, setSelectedUsers] = useState<SelectedUser[]>([]);
  const [creating, setCreating] = useState(false);
  const [success, setSuccess] = useState<string | null>(null);
  const [showUsernameModal, setShowUsernameModal] = useState(false);
  const [selectedUsernameOption, setSelectedUsernameOption] = useState<string>('');
  const [customUsernameInput, setCustomUsernameInput] = useState('');

  const enumerateUsers = async () => {
    try {
      setLoading(true);
      setError(null);

      console.log('🔍 Enumerating users from all services...');

      const response = await fetch(`${getApiBaseUrl()}/api/users/enumerate-users`);

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || t('errors.enumerateFailed'));
      }

      const data = await response.json();
      console.log('✅ User enumeration completed:', data);

      setEnumerationData(data);

    } catch (err) {
      console.error('❌ User enumeration failed:', err);
      const errorMessage = err instanceof Error ? err.message : 'Failed to enumerate users';
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    enumerateUsers();
  }, []);

  const getDisplayName = (user: ServiceUser): string => {
    return user.username || user.login || user.name || user.friendly_name || user.email || 'Unknown User';
  };

  const getUserId = (user: ServiceUser): string => {
    return user.id || user.user_id || user.username || user.login || 'unknown';
  };

  const toggleUserSelection = (serviceId: string, user: ServiceUser) => {
    if (!enumerationData) return;

    const serviceData = enumerationData.services[serviceId];
    const selectedUser: SelectedUser = {
      service_id: serviceId,
      service_name: serviceData.service_name,
      service_type: serviceData.service_type,
      user_id: getUserId(user),
      username: getDisplayName(user),
      email: user.email,
      role: user.is_admin || user.is_superuser ? 'admin' : 'user',
      user_data: user
    };

    setSelectedUsers(prev => {
      const isAlreadySelected = prev.some(
        u => u.service_id === serviceId && u.user_id === selectedUser.user_id
      );

      if (isAlreadySelected) {
        // Remove if already selected
        return prev.filter(
          u => !(u.service_id === serviceId && u.user_id === selectedUser.user_id)
        );
      } else {
        // Add to selection
        return [...prev, selectedUser];
      }
    });
  };

  const isUserSelected = (serviceId: string, user: ServiceUser): boolean => {
    const userId = getUserId(user);
    return selectedUsers.some(u => u.service_id === serviceId && u.user_id === userId);
  };

  const createMappingFromSelection = async () => {
    if (selectedUsers.length === 0) {
      setError(t('creator.selectOneUser'));
      return;
    }

    try {
      setCreating(true);
      setError(null);
      setSuccess(null);

      // Get primary email and username from selection
      const allEmails = selectedUsers
        .map(u => u.email)
        .filter(email => email && email.trim() !== '');
      const primaryEmail = allEmails.length > 0 ? allEmails[0] : null;

      const allUsernames = selectedUsers
        .map(u => u.username)
        .filter(username => username && username.trim() !== '' && username !== 'Unknown User');

      // Use the selected username from modal
      let primaryUsername: string;
      if (selectedUsernameOption === 'custom') {
        primaryUsername = customUsernameInput.trim();
      } else if (selectedUsernameOption && selectedUsernameOption !== 'auto') {
        primaryUsername = selectedUsernameOption;
      } else {
        primaryUsername = allUsernames.length > 0 ? allUsernames[0] : '';
      }

      // Generate central_user_id like auto-detection: email > username > fallback
      let centralUserId: string;
      if (primaryEmail) {
        centralUserId = primaryEmail.toLowerCase().trim();
      } else if (primaryUsername) {
        centralUserId = primaryUsername.toLowerCase().trim();
      } else {
        // Fallback: use first user's username or generate unique ID
        const fallbackName = allUsernames[0] || `user_${Date.now()}`;
        centralUserId = fallbackName.toLowerCase().trim();
      }

      // Ensure primaryUsername has a value
      if (!primaryUsername) {
        primaryUsername = centralUserId;
      }

      // Create all mappings directly
      const results = [];
      for (const user of selectedUsers) {
        const mappingRequest = {
          central_user_id: centralUserId,
          central_username: primaryUsername,
          central_email: primaryEmail,
          service_config_id: user.service_id,
          service_user_id: String(user.user_id),
          service_username: String(user.username || user.user_id),
          service_email: user.email || null,
          role: user.role,
          status: 'active',
          sync_enabled: true,
          service_metadata: {}
        };

        try {
          const response = await fetch(`${getApiBaseUrl()}/api/users/`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify(mappingRequest),
          });

          if (response.ok) {
            results.push({ success: true, user: user });
          } else {
            const errorData = await response.json();
            console.error('❌ Mapping creation failed:', {
              errorData,
              detail: errorData.detail,
              request: mappingRequest
            });
            const errorMessage = Array.isArray(errorData.detail)
              ? errorData.detail.map((e: { loc?: string[]; msg: string }) => `${e.loc?.join('.')}: ${e.msg}`).join(', ')
              : errorData.detail || 'Unknown error';
            results.push({ success: false, user: user, error: errorMessage });
          }
        } catch (err) {
          results.push({ success: false, user: user, error: (err as Error).message });
        }
      }

      const successCount = results.filter(r => r.success).length;
      const failCount = results.filter(r => !r.success).length;

      if (successCount > 0) {
        setSuccess(t('creator.createSuccess', { count: successCount, username: primaryUsername }));
        // Clear selection
        setSelectedUsers([]);
        resetUsernameModal();

        // Trigger parent refresh if available
        if (onMappingCreated) {
          onMappingCreated();
        }
      }

      if (failCount > 0) {
        setError(t('creator.createFailed', { count: failCount }));
      }

    } catch (err) {
      setError(`Failed to create mappings: ${(err as Error).message}`);
    } finally {
      setCreating(false);
    }
  };

  const clearSelection = () => {
    setSelectedUsers([]);
    resetUsernameModal();
  };

  const resetUsernameModal = () => {
    setShowUsernameModal(false);
    setSelectedUsernameOption('');
    setCustomUsernameInput('');
  };

  // Get suggested username from selected users
  const getSuggestedUsernames = () => {
    const usernames = selectedUsers
      .map(u => u.username)
      .filter(username => username && username.trim() !== '' && username !== 'Unknown User');
    return [...new Set(usernames)]; // Remove duplicates
  };

  const handleCreateMappingClick = () => {
    if (selectedUsers.length === 0) {
      setError(t('creator.selectOneUser'));
      return;
    }

    const suggestedUsernames = getSuggestedUsernames();
    if (suggestedUsernames.length > 1) {
      // Show modal to let user choose
      setShowUsernameModal(true);
    } else {
      // Proceed directly with creation
      createMappingFromSelection();
    }
  };

  const proceedWithMappingCreation = () => {
    setShowUsernameModal(false);
    createMappingFromSelection();
  };

  // Removed removeMappingEntry and createMappings - no longer needed without pending mappings

  /*const createMappings = async () => {
    if (pendingMappings.length === 0) {
      setError('No mappings to create');
      return;
    }

    try {
      setCreating(true);
      setError(null);

      const mappingRequests = [];

      for (const userMapping of pendingMappings) {
        // Get the primary email and username from all mappings for this central user
        const allEmails = userMapping.mappings
          .map(m => m.email)
          .filter(email => email && email.trim() !== '');
        const primaryEmail = allEmails.length > 0 ? allEmails[0] : null;

        const allUsernames = userMapping.mappings
          .map(m => m.username)
          .filter(username => username && username.trim() !== '' && username !== 'Unknown User');
        const primaryUsername = allUsernames.length > 0 ? allUsernames[0] : `user${userMapping.central_user_id}`;

        for (const mapping of userMapping.mappings) {
          mappingRequests.push({
            central_user_id: userMapping.central_user_id,
            central_username: primaryUsername,
            central_email: primaryEmail,
            service_config_id: mapping.service_id,
            service_user_id: mapping.user_id,
            service_username: mapping.username,
            service_email: mapping.email,
            role: mapping.role,
            status: 'active',
            sync_enabled: true
          });
        }
      }

      console.log('🔄 Creating mappings:', mappingRequests);

      const results = [];
      for (const mappingRequest of mappingRequests) {
        try {
          const response = await fetch(`${getApiBaseUrl()}/api/users/`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify(mappingRequest),
          });

          if (response.ok) {
            results.push({ success: true, mapping: mappingRequest });
          } else {
            const errorData = await response.json();
            console.error('❌ Mapping creation failed:', {
              status: response.status,
              errorData,
              requestData: mappingRequest
            });
            results.push({
              success: false,
              mapping: mappingRequest,
              error: errorData.detail || `HTTP ${response.status}: ${JSON.stringify(errorData)}`
            });
          }
        } catch (err) {
          results.push({
            success: false,
            mapping: mappingRequest,
            error: err instanceof Error ? err.message : 'Unknown error'
          });
        }
      }

      const successful = results.filter(r => r.success).length;
      const failed = results.filter(r => !r.success).length;

      console.log('✅ Mappings created:', { successful, failed, results });

      if (successful > 0) {
        setPendingMappings([]);
        onMappingCreated?.();
        alert(`Successfully created ${successful} user mappings!${failed > 0 ? ` (${failed} failed)` : ''}`);
      } else {
        const failedResults = results.filter(r => !r.success);
        const errorDetails = failedResults.map(r => r.error).join('; ');
        setError(`Failed to create mappings: ${errorDetails}`);
        console.error('❌ Failed mapping results:', failedResults);
      }

    } catch (err) {
      console.error('❌ Failed to create mappings:', err);
      const errorMessage = err instanceof Error ? err.message : 'Failed to create mappings';
      setError(errorMessage);
    } finally {
      setCreating(false);
    }
  };*/


  const filteredServices = enumerationData ? Object.entries(enumerationData.services).filter(([serviceId, serviceData]) => {
    const matchesSearch = !searchTerm ||
      serviceData.service_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      serviceData.users.some(user =>
        getDisplayName(user).toLowerCase().includes(searchTerm.toLowerCase()) ||
        (user.email && user.email.toLowerCase().includes(searchTerm.toLowerCase()))
      );

    const matchesService = selectedServiceFilter === 'all' || serviceId === selectedServiceFilter;

    return matchesSearch && matchesService && serviceData.users.length > 0;
  }) : [];

  if (loading) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-4 sm:p-6">
        <div className="flex items-center justify-center">
          <RefreshCw className="w-5 h-5 sm:w-6 sm:h-6 text-blue-500 animate-spin mr-2 sm:mr-3" />
          <span className="text-sm sm:text-lg text-gray-600 dark:text-gray-400">{t('creator.loading')}</span>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4 sm:space-y-6">
      {/* Actions bar with search and filters */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-3 sm:p-4">
        <div className="flex flex-row gap-2 sm:gap-3 items-center">
          {/* Refresh button - icon only on all screens */}
          <button
            onClick={enumerateUsers}
            disabled={loading}
            className="p-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-600 disabled:opacity-50 flex items-center transition-colors flex-shrink-0"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>

          {/* Search input */}
          <div className="relative flex-1 min-w-0">
            <Search className="w-4 h-4 absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              placeholder={t('creator.search')}
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-3 py-2 text-sm border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          {/* Service filter */}
          {enumerationData && (
            <select
              value={selectedServiceFilter}
              onChange={(e) => setSelectedServiceFilter(e.target.value)}
              className="hidden sm:block px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent flex-shrink-0"
            >
              <option value="all">{t('creator.allServices')}</option>
              {Object.entries(enumerationData.services).map(([serviceId, serviceData]) => (
                <option key={serviceId} value={serviceId}>
                  {serviceData.service_name} ({serviceData.user_count})
                </option>
              ))}
            </select>
          )}

          {/* Help button */}
          <HelpTooltip topicId="userManualMapping" />
        </div>

        {/* Mobile service filter - second row */}
        {enumerationData && (
          <div className="sm:hidden mt-2">
            <select
              value={selectedServiceFilter}
              onChange={(e) => setSelectedServiceFilter(e.target.value)}
              className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="all">{t('creator.allServices')}</option>
              {Object.entries(enumerationData.services).map(([serviceId, serviceData]) => (
                <option key={serviceId} value={serviceId}>
                  {serviceData.service_name} ({serviceData.user_count})
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      {/* Error Display */}
      {error && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-3 sm:p-4">
          <div className="flex items-center">
            <XCircle className="w-5 h-5 text-red-500 mr-2 flex-shrink-0" />
            <span className="text-sm text-red-700 dark:text-red-400">{error}</span>
          </div>
        </div>
      )}

      {/* Success Display */}
      {success && (
        <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-3 sm:p-4">
          <div className="flex items-center">
            <CheckCircle className="w-5 h-5 text-green-500 mr-2 flex-shrink-0" />
            <span className="text-sm text-green-700 dark:text-green-400">{success}</span>
          </div>
        </div>
      )}

      {/* Selected Users Panel */}
      {selectedUsers.length > 0 && (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-blue-200 dark:border-blue-800 p-3 sm:p-4">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-3 sm:mb-4">
            <h4 className="font-semibold text-gray-900 dark:text-white flex items-center text-sm sm:text-base">
              <User className="w-4 h-4 mr-2 text-blue-600" />
              {t('creator.selected', { count: selectedUsers.length })}
            </h4>
            <div className="flex items-center gap-2">
              <button
                onClick={clearSelection}
                className="px-2 sm:px-3 py-1.5 text-xs sm:text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors"
              >
                {t('creator.clear')}
              </button>
              <button
                onClick={handleCreateMappingClick}
                disabled={creating}
                className="px-3 sm:px-4 py-1.5 sm:py-2 bg-green-600 text-white text-xs sm:text-sm rounded-lg hover:bg-green-700 disabled:opacity-50 transition-colors"
              >
                {creating ? t('creator.creating') : t('creator.create')}
              </button>
            </div>
          </div>

          {/* Preview usernames and emails */}
          <div className="mb-3 sm:mb-4 p-2 sm:p-3 bg-gray-50 dark:bg-gray-900 rounded-lg">
            <p className="text-xs sm:text-sm text-gray-600 dark:text-gray-400 mb-2">{t('creator.previewBased')}</p>
            <div className="flex flex-wrap gap-1.5 sm:gap-2">
              {selectedUsers.filter(u => u.email).length > 0 && (
                <span className="px-2 py-0.5 sm:py-1 bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-400 rounded text-xs sm:text-sm truncate max-w-full">
                  {selectedUsers.find(u => u.email)?.email}
                </span>
              )}
              {getSuggestedUsernames().slice(0, 3).map((username, index) => (
                <span key={index} className="px-2 py-0.5 sm:py-1 bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-400 rounded text-xs sm:text-sm">
                  {username}
                </span>
              ))}
              {getSuggestedUsernames().length === 0 && !selectedUsers.some(u => u.email) && (
                <span className="text-xs sm:text-sm text-gray-500 dark:text-gray-500">{t('creator.noEmailUsername')}</span>
              )}
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2 sm:gap-3 max-h-40 overflow-y-auto">
            {selectedUsers.map((user, index) => (
              <div key={index} className="flex items-center justify-between p-2 sm:p-3 bg-gray-50 dark:bg-gray-900 rounded-lg">
                <div className="flex items-center space-x-2 min-w-0">
                  <div className={`w-2 h-2 rounded-full flex-shrink-0 ${getServiceColor(user.service_type).dot}`}></div>
                  <div className="min-w-0">
                    <p className="text-xs sm:text-sm font-medium text-gray-900 dark:text-white truncate">{user.username}</p>
                    <p className="text-xs text-gray-600 dark:text-gray-400 truncate">{user.service_name}</p>
                  </div>
                </div>
                <button
                  onClick={() => toggleUserSelection(user.service_id, user.user_data)}
                  className="p-1 text-gray-600 dark:text-gray-400 hover:text-red-700 dark:hover:text-red-400 hover:bg-red-100 dark:hover:bg-red-900/30 rounded transition-colors flex-shrink-0"
                >
                  <XCircle className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Services and Users */}
      {enumerationData && (
        <div className="space-y-4">
            <h4 className="font-semibold text-gray-900 dark:text-white text-sm sm:text-base">{t('creator.usersByService')}</h4>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-3 sm:gap-4">
            {filteredServices.map(([serviceId, serviceData]) => (
              <div key={serviceId} className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
                <div className="p-3 sm:p-4 border-b border-gray-200 dark:border-gray-700">
                  <div className="flex items-center space-x-3">
                    <div className={`w-3 h-3 rounded-full flex-shrink-0 ${getServiceColor(serviceData.service_type).dot}`}></div>
                    <div className="min-w-0">
                      <h3 className="font-medium text-gray-900 dark:text-white text-sm sm:text-base truncate">{serviceData.service_name}</h3>
                      <p className="text-xs sm:text-sm text-gray-600 dark:text-gray-400">{t('creator.users', { count: serviceData.user_count })}</p>
                    </div>
                  </div>
                </div>

                <div className="divide-y divide-gray-100 dark:divide-gray-700 max-h-60 sm:max-h-80 overflow-y-auto">
                  {serviceData.users
                    .filter(user =>
                      !searchTerm ||
                      getDisplayName(user).toLowerCase().includes(searchTerm.toLowerCase()) ||
                      (user.email && user.email.toLowerCase().includes(searchTerm.toLowerCase()))
                    )
                    .map((user, index) => {
                      // Extract user details
                      const userId = user.id || user.user_id || '-';
                      const username = user.username || user.login || '-';
                      const displayName = user.friendly_name || user.name || username;
                      const email = user.email || '-';
                      const lastActivity = user.last_seen || user.last_active || user.updated_at || user.last_login || null;

                      // Format last activity
                      const formatLastActivity = (timestamp: string | null) => {
                        if (!timestamp) return null;
                        try {
                          const date = new Date(timestamp);
                          const now = new Date();
                          const diffMs = now.getTime() - date.getTime();
                          const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
                          const diffHours = Math.floor(diffMs / (1000 * 60 * 60));

                          if (diffHours < 1) return 'Just now';
                          if (diffHours < 24) return `${diffHours}h ago`;
                          if (diffDays < 7) return `${diffDays}d ago`;
                          return date.toLocaleDateString();
                        } catch {
                          return null;
                        }
                      };

                      return (
                        <div
                          key={index}
                          className={`p-2 sm:p-3 cursor-pointer transition-colors border-2 ${
                            isUserSelected(serviceId, user)
                              ? 'bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-700 hover:bg-blue-100 dark:hover:bg-blue-900/30'
                              : 'bg-white dark:bg-gray-800 border-transparent hover:bg-gray-50 dark:hover:bg-gray-700'
                          }`}
                          onClick={() => toggleUserSelection(serviceId, user)}
                        >
                          <div className="flex items-start space-x-2 sm:space-x-3">
                            <User className="w-4 h-4 text-gray-500 dark:text-gray-400 mt-1 shrink-0" />
                            <div className="flex-1 min-w-0">
                              {/* Main display name */}
                              <p className="font-medium text-gray-900 dark:text-white truncate text-sm">{displayName}</p>

                              {/* User details grid */}
                              <div className="mt-1 grid grid-cols-2 gap-x-2 gap-y-0.5 text-xs">
                                {/* ID */}
                                <div className="flex items-center text-gray-500 dark:text-gray-400">
                                  <span className="text-gray-400 dark:text-gray-500 mr-1">ID:</span>
                                  <span className="font-mono truncate">{String(userId).substring(0, 8)}{String(userId).length > 8 ? '..' : ''}</span>
                                </div>

                                {/* Username */}
                                {username !== displayName && username !== '-' && (
                                  <div className="flex items-center text-gray-500 dark:text-gray-400">
                                    <span className="text-gray-400 dark:text-gray-500 mr-1">User:</span>
                                    <span className="truncate">{username}</span>
                                  </div>
                                )}

                                {/* Email */}
                                {email !== '-' && (
                                  <div className="flex items-center text-gray-500 dark:text-gray-400 col-span-2">
                                    <span className="text-gray-400 dark:text-gray-500 mr-1">Email:</span>
                                    <span className="truncate">{email}</span>
                                  </div>
                                )}

                                {/* Last activity */}
                                {formatLastActivity(lastActivity) && (
                                  <div className="flex items-center text-gray-500 dark:text-gray-400">
                                    <span className="text-gray-400 dark:text-gray-500 mr-1">Last:</span>
                                    <span>{formatLastActivity(lastActivity)}</span>
                                  </div>
                                )}
                              </div>

                              {/* Role badges */}
                              <div className="flex items-center flex-wrap gap-1 mt-1.5">
                                {(user.is_admin || user.is_superuser) && (
                                  <span className="px-1.5 py-0.5 bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400 rounded text-xs">Admin</span>
                                )}
                                {user.is_staff && (
                                  <span className="px-1.5 py-0.5 bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-400 rounded text-xs">Staff</span>
                                )}
                                {user.is_active === false && (
                                  <span className="px-1.5 py-0.5 bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 rounded text-xs">Inactif</span>
                                )}
                              </div>
                            </div>
                          </div>
                        </div>
                      );
                    })}
                </div>
              </div>
            ))}
            </div>
        </div>
      )}

      {/* Enumeration Errors */}
      {enumerationData?.errors && enumerationData.errors.length > 0 && (
        <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-3 sm:p-4">
          <h4 className="font-medium text-yellow-800 dark:text-yellow-400 mb-2 text-sm">{t('creator.warnings')}</h4>
          <div className="space-y-1">
            {enumerationData.errors.map((error, index) => (
              <p key={index} className="text-xs sm:text-sm text-yellow-700 dark:text-yellow-400">{error}</p>
            ))}
          </div>
        </div>
      )}

      {/* Username Selection Modal */}
      {showUsernameModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white dark:bg-gray-800 rounded-lg p-4 sm:p-6 max-w-md w-full">
            <h3 className="text-base sm:text-lg font-semibold text-gray-900 dark:text-white mb-3 sm:mb-4">
              {t('creator.chooseUsername')}
            </h3>
            <p className="text-xs sm:text-sm text-gray-600 dark:text-gray-400 mb-3 sm:mb-4">
              {t('creator.multipleUsernamesFound')}
            </p>

            <div className="space-y-2 sm:space-y-3 mb-4 sm:mb-6 max-h-64 overflow-y-auto">
              {/* Auto-select first username */}
              <label className="flex items-center space-x-3 p-2 sm:p-3 border border-gray-200 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 cursor-pointer">
                <input
                  type="radio"
                  name="username"
                  value="auto"
                  checked={selectedUsernameOption === 'auto'}
                  onChange={(e) => setSelectedUsernameOption(e.target.value)}
                  className="text-blue-600 focus:ring-blue-500"
                />
                <div className="min-w-0">
                  <div className="font-medium text-gray-900 dark:text-white text-sm">{t('creator.auto')}</div>
                  <div className="text-xs sm:text-sm text-gray-600 dark:text-gray-400 truncate">
                    {getSuggestedUsernames()[0] || t('creator.autoGenerated')}
                  </div>
                </div>
              </label>

              {/* Individual service usernames */}
              {getSuggestedUsernames().map((username, index) => {
                const serviceNames = selectedUsers
                  .filter(u => u.username === username)
                  .map(u => u.service_name)
                  .join(', ');

                return (
                  <label key={index} className="flex items-center space-x-3 p-2 sm:p-3 border border-gray-200 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 cursor-pointer">
                    <input
                      type="radio"
                      name="username"
                      value={username}
                      checked={selectedUsernameOption === username}
                      onChange={(e) => setSelectedUsernameOption(e.target.value)}
                      className="text-blue-600 focus:ring-blue-500"
                    />
                    <div className="min-w-0">
                      <div className="font-medium text-gray-900 dark:text-white text-sm truncate">{username}</div>
                      <div className="text-xs sm:text-sm text-gray-600 dark:text-gray-400 truncate">{t('creator.from', { services: serviceNames })}</div>
                    </div>
                  </label>
                );
              })}

              {/* Custom username */}
              <label className="flex items-center space-x-3 p-2 sm:p-3 border border-gray-200 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 cursor-pointer">
                <input
                  type="radio"
                  name="username"
                  value="custom"
                  checked={selectedUsernameOption === 'custom'}
                  onChange={(e) => setSelectedUsernameOption(e.target.value)}
                  className="text-blue-600 focus:ring-blue-500"
                />
                <div className="flex-1 min-w-0">
                  <div className="font-medium text-gray-900 dark:text-white text-sm">{t('creator.custom')}</div>
                  {selectedUsernameOption === 'custom' && (
                    <input
                      type="text"
                      placeholder={t('creator.enterName')}
                      value={customUsernameInput}
                      onChange={(e) => setCustomUsernameInput(e.target.value)}
                      className="mt-2 w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      autoFocus
                    />
                  )}
                </div>
              </label>
            </div>

            <div className="flex justify-end space-x-2 sm:space-x-3">
              <button
                onClick={resetUsernameModal}
                className="px-3 sm:px-4 py-2 text-sm text-gray-700 dark:text-gray-300 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
              >
                {t('creator.cancel')}
              </button>
              <button
                onClick={proceedWithMappingCreation}
                disabled={!selectedUsernameOption || (selectedUsernameOption === 'custom' && !customUsernameInput.trim())}
                className="px-3 sm:px-4 py-2 text-sm bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 transition-colors"
              >
                {t('creator.create')}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default UserMappingCreator;