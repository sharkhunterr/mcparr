import { useState, useEffect } from 'react';
import type { FC } from 'react';
import {
  Users,
  Edit,
  Trash2,
  XCircle,
  Search,
  RefreshCw,
  Plus,
  Pause,
  User,
  Link
} from 'lucide-react';
import { getApiBaseUrl } from '../../lib/api';
import { getServiceColor } from '../../lib/serviceColors';

interface UserMapping {
  id: string;
  central_user_id: string;
  service_config_id: string;
  service_user_id?: string;
  service_username?: string;
  service_email?: string;
  role: string;
  status: string;
  sync_enabled: boolean;
  last_sync_at?: string;
  last_sync_success?: boolean;
  last_sync_error?: string;
  sync_attempts: number;
  service_metadata?: Record<string, any>;
  created_at: string;
  updated_at: string;
  service_config?: {
    id: string;
    name: string;
    service_type: string;
    base_url: string;
  };
}

interface UserMappingListResponse {
  mappings: UserMapping[];
  total: number;
  skip: number;
  limit: number;
}

interface GroupedUserMapping {
  central_user_id: string;
  central_username: string;
  central_email?: string;
  mappings: UserMapping[];
  total_services: number;
  active_services: number;
  last_activity: string;
}

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
  [key: string]: any;
}

interface ServiceData {
  service_name: string;
  service_type: string;
  base_url: string;
  users: ServiceUser[];
  user_count: number;
  error?: string;
}

interface EnumerationData {
  services: Record<string, ServiceData>;
  total_services: number;
  successful_enumerations: number;
  errors: string[];
}

interface UserMappingListProps {
  onEditMapping?: (mapping: UserMapping) => void;
  onCreateMapping?: () => void;
}

const UserMappingList: FC<UserMappingListProps> = ({
  onEditMapping,
  onCreateMapping
}) => {
  const [mappings, setMappings] = useState<UserMapping[]>([]);
  const [groupedMappings, setGroupedMappings] = useState<GroupedUserMapping[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [serviceFilter, setServiceFilter] = useState<string>('all');
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [limit] = useState(1000); // Maximum limit to get all mappings
  const [editingUser, setEditingUser] = useState<GroupedUserMapping | null>(null);
  const [showEditModal, setShowEditModal] = useState(false);
  const [editUsername, setEditUsername] = useState('');
  const [enumerationData, setEnumerationData] = useState<EnumerationData | null>(null);
  const [loadingEnumeration, setLoadingEnumeration] = useState(false);
  const [showAddServicePanel, setShowAddServicePanel] = useState(false);
  const [selectedServiceId, setSelectedServiceId] = useState<string>('');
  const [selectedServiceUser, setSelectedServiceUser] = useState<ServiceUser | null>(null);
  const [addingMapping, setAddingMapping] = useState(false);

  useEffect(() => {
    fetchMappings();
  }, [page, statusFilter, serviceFilter, searchTerm]);

  const fetchMappings = async () => {
    try {
      setLoading(true);
      setError(null);

      const params = new URLSearchParams({
        skip: (page * limit).toString(),
        limit: limit.toString(),
      });

      if (statusFilter !== 'all') {
        params.append('status', statusFilter);
      }

      if (serviceFilter !== 'all') {
        params.append('service_id', serviceFilter);
      }

      if (searchTerm) {
        params.append('central_user_id', searchTerm);
      }

      const response = await fetch(`${getApiBaseUrl()}/api/users/?${params.toString()}`);
      if (!response.ok) {
        throw new Error('Failed to fetch user mappings');
      }

      const data: UserMappingListResponse = await response.json();
      setMappings(data.mappings);
      setTotal(data.total);

      // Group mappings by central user
      groupMappingsByUser(data.mappings);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch mappings');
    } finally {
      setLoading(false);
    }
  };

  const deleteMapping = async (mappingId: string) => {
    if (!confirm('Are you sure you want to delete this user mapping?')) {
      return;
    }

    try {
      const response = await fetch(`${getApiBaseUrl()}/api/users/${mappingId}`, {
        method: 'DELETE'
      });

      if (!response.ok) {
        throw new Error('Failed to delete mapping');
      }

      // Refresh the list
      fetchMappings();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete mapping');
    }
  };

  const toggleSyncEnabled = async (mapping: UserMapping) => {
    try {
      const response = await fetch(`${getApiBaseUrl()}/api/users/${mapping.id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          sync_enabled: !mapping.sync_enabled
        })
      });

      if (!response.ok) {
        throw new Error('Failed to update mapping');
      }

      // Refresh the list
      fetchMappings();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update mapping');
    }
  };

  const formatLastSync = (timestamp?: string) => {
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

  const groupMappingsByUser = (mappings: UserMapping[]) => {
    const grouped = mappings.reduce((acc, mapping) => {
      const centralUserId = mapping.central_user_id;

      if (!acc[centralUserId]) {
        // Find the username from any mapping with central data
        const centralUsername = mappings.find(m =>
          m.central_user_id === centralUserId &&
          m.service_username &&
          m.service_username.trim() !== ''
        )?.service_username || `user${centralUserId}`;

        acc[centralUserId] = {
          central_user_id: centralUserId,
          central_username: centralUsername,
          central_email: mapping.service_email || undefined,
          mappings: [],
          total_services: 0,
          active_services: 0,
          last_activity: mapping.last_sync_at || mapping.created_at
        };
      }

      acc[centralUserId].mappings.push(mapping);
      acc[centralUserId].total_services += 1;

      if (mapping.status === 'active') {
        acc[centralUserId].active_services += 1;
      }

      // Update last activity to most recent
      const lastActivity = mapping.last_sync_at || mapping.updated_at;
      if (lastActivity > acc[centralUserId].last_activity) {
        acc[centralUserId].last_activity = lastActivity;
      }

      return acc;
    }, {} as Record<string, GroupedUserMapping>);

    setGroupedMappings(Object.values(grouped).sort((a, b) =>
      new Date(b.last_activity).getTime() - new Date(a.last_activity).getTime()
    ));
  };

  const getServiceTypeColorClass = (serviceType: string, isActive: boolean = true) => {
    const colors = getServiceColor(serviceType);
    if (isActive) {
      return `${colors.badge} ${colors.badgeDark} border ${colors.border}`;
    }
    return `bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400 border border-gray-200 dark:border-gray-600`;
  };

  const getServiceDisplayName = (serviceType: string) => {
    // Capitalize first letter
    return serviceType.charAt(0).toUpperCase() + serviceType.slice(1);
  };

  const deleteUserGroup = async (centralUserId: string) => {
    if (!confirm('Are you sure you want to delete all mappings for this user? This action cannot be undone.')) {
      return;
    }

    try {
      const userMappings = mappings.filter(m => m.central_user_id === centralUserId);

      // Delete all mappings for this user
      await Promise.all(userMappings.map(mapping =>
        fetch(`${getApiBaseUrl()}/api/users/${mapping.id}`, {
          method: 'DELETE'
        })
      ));

      // Refresh the list
      fetchMappings();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete user mappings');
    }
  };

  const openEditUserModal = async (userGroup: GroupedUserMapping) => {
    setShowEditModal(true);
    setEditUsername(userGroup.central_username);
    setShowAddServicePanel(false);
    setSelectedServiceId('');
    setSelectedServiceUser(null);

    // Fetch ALL mappings for this user (not just paginated ones)
    try {
      const response = await fetch(`${getApiBaseUrl()}/api/users/central-user/${encodeURIComponent(userGroup.central_user_id)}`);
      if (response.ok) {
        const allMappings: UserMapping[] = await response.json();
        setEditingUser({
          ...userGroup,
          mappings: allMappings,
          total_services: allMappings.length,
          active_services: allMappings.filter(m => m.status === 'active').length
        });
      } else {
        // Fallback to paginated data
        setEditingUser(userGroup);
      }
    } catch (err) {
      console.error('Failed to fetch all user mappings:', err);
      setEditingUser(userGroup);
    }

    // Fetch enumeration data if not already loaded
    if (!enumerationData) {
      await fetchEnumerationData();
    }
  };

  const closeEditModal = () => {
    setEditingUser(null);
    setEditUsername('');
    setShowEditModal(false);
    setShowAddServicePanel(false);
    setSelectedServiceId('');
    setSelectedServiceUser(null);
  };

  const fetchEnumerationData = async () => {
    try {
      setLoadingEnumeration(true);
      const response = await fetch(`${getApiBaseUrl()}/api/users/enumerate-users`);
      if (response.ok) {
        const data = await response.json();
        setEnumerationData(data);
      }
    } catch (err) {
      console.error('Failed to fetch enumeration data:', err);
    } finally {
      setLoadingEnumeration(false);
    }
  };

  const getDisplayName = (user: ServiceUser): string => {
    return user.username || user.login || user.name || user.friendly_name || user.email || 'Unknown User';
  };

  const getUserId = (user: ServiceUser): string => {
    return String(user.id || user.user_id || user.username || user.login || 'unknown');
  };

  // Get services that are not yet mapped for this user
  const getUnmappedServices = (): [string, ServiceData][] => {
    if (!enumerationData || !editingUser) return [];

    const mappedServiceIds = new Set(
      editingUser.mappings.map(m => m.service_config_id)
    );

    return Object.entries(enumerationData.services).filter(
      ([serviceId]) => !mappedServiceIds.has(serviceId)
    );
  };

  const addServiceMapping = async () => {
    if (!editingUser || !selectedServiceId || !selectedServiceUser || !enumerationData) return;

    try {
      setAddingMapping(true);

      const mappingRequest = {
        central_user_id: editingUser.central_user_id,
        central_username: editUsername || editingUser.central_username,
        central_email: editingUser.central_email || null,
        service_config_id: selectedServiceId,
        service_user_id: getUserId(selectedServiceUser),
        service_username: getDisplayName(selectedServiceUser),
        service_email: selectedServiceUser.email || null,
        role: selectedServiceUser.is_admin || selectedServiceUser.is_superuser ? 'admin' : 'user',
        status: 'active',
        sync_enabled: true,
        service_metadata: {}
      };

      const response = await fetch(`${getApiBaseUrl()}/api/users/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(mappingRequest)
      });

      if (response.ok) {
        // Refresh mappings and update modal
        await fetchMappings();
        setShowAddServicePanel(false);
        setSelectedServiceId('');
        setSelectedServiceUser(null);

        // Update editingUser with new mapping
        const newMapping = await response.json();
        setEditingUser(prev => prev ? {
          ...prev,
          mappings: [...prev.mappings, newMapping],
          total_services: prev.total_services + 1,
          active_services: prev.active_services + 1
        } : null);
      } else {
        const errorData = await response.json();
        setError(errorData.detail || 'Failed to add service mapping');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add service mapping');
    } finally {
      setAddingMapping(false);
    }
  };

  const removeMappingFromEditModal = async (mappingId: string) => {
    if (!confirm('Are you sure you want to remove this service mapping?')) return;

    try {
      const response = await fetch(`${getApiBaseUrl()}/api/users/${mappingId}`, {
        method: 'DELETE'
      });

      if (response.ok) {
        // Update editingUser
        setEditingUser(prev => prev ? {
          ...prev,
          mappings: prev.mappings.filter(m => m.id !== mappingId),
          total_services: prev.total_services - 1,
          active_services: prev.active_services - 1
        } : null);

        // Refresh main list
        fetchMappings();
      } else {
        setError('Failed to remove service mapping');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to remove mapping');
    }
  };

  const saveUserEdit = async () => {
    if (!editingUser || !editUsername.trim()) return;

    try {
      // Update all mappings for this user with the new username
      const updatePromises = editingUser.mappings.map(mapping =>
        fetch(`${getApiBaseUrl()}/api/users/${mapping.id}`, {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            service_username: editUsername.trim()
          })
        })
      );

      await Promise.all(updatePromises);

      // Refresh the list
      fetchMappings();
      closeEditModal();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update user mappings');
    }
  };

  if (loading) {
    return (
      <div className="p-6">
        <div className="animate-pulse">
          <div className="h-8 bg-gray-200 rounded w-1/4 mb-6"></div>
          <div className="space-y-4">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="bg-gray-200 h-16 rounded-lg"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
      <div className="p-3 sm:p-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div className="flex items-center space-x-3 min-w-0">
            <Users className="w-5 h-5 sm:w-6 sm:h-6 text-blue-600 flex-shrink-0" />
            <div className="min-w-0">
              <h3 className="text-base sm:text-lg font-semibold text-gray-900 dark:text-white">
                Mappings
              </h3>
              <p className="text-xs sm:text-sm text-gray-600 dark:text-gray-400">
                {total} mapping{total > 1 ? 's' : ''}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={fetchMappings}
              disabled={loading}
              className="flex items-center space-x-2 px-2 sm:px-3 py-1.5 sm:py-2 text-xs sm:text-sm border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 transition-colors"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
              <span className="hidden sm:inline">Actualiser</span>
            </button>
            {onCreateMapping && (
              <button
                onClick={onCreateMapping}
                className="flex items-center space-x-2 px-3 sm:px-4 py-1.5 sm:py-2 bg-blue-600 text-white text-xs sm:text-sm rounded-lg hover:bg-blue-700 transition-colors"
              >
                <Plus className="w-4 h-4" />
                <span className="hidden sm:inline">Ajouter</span>
              </button>
            )}
          </div>
        </div>
      </div>

      <div className="p-3 sm:p-4">
        {/* Filters */}
        <div className="flex flex-col sm:flex-row gap-2 sm:gap-3 mb-4">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
            <input
              type="text"
              placeholder="Rechercher..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-3 py-2 text-sm border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="all">Tous statuts</option>
            <option value="active">Actif</option>
            <option value="pending">En attente</option>
            <option value="failed">Échoué</option>
            <option value="syncing">Synchro</option>
          </select>

          <select
            value={serviceFilter}
            onChange={(e) => setServiceFilter(e.target.value)}
            className="px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="all">Tous services</option>
          </select>
        </div>

        {/* Error Display */}
        {error && (
          <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-800">
            <div className="flex items-center">
              <XCircle className="w-5 h-5 text-red-500 mr-2 flex-shrink-0" />
              <span className="text-sm text-red-700 dark:text-red-400">{error}</span>
            </div>
          </div>
        )}

        {/* Grouped Mappings List */}
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-3 sm:gap-4">
          {groupedMappings.map((userGroup) => (
            <div
              key={userGroup.central_user_id}
              className="p-3 sm:p-4 border border-gray-200 dark:border-gray-700 rounded-lg hover:border-gray-300 dark:hover:border-gray-600 transition-colors h-fit"
            >
              {/* User Header */}
              <div className="flex items-start justify-between mb-2 sm:mb-3">
                <div className="flex items-center space-x-2 sm:space-x-3 min-w-0 flex-1">
                  <div className="w-7 h-7 sm:w-8 sm:h-8 bg-blue-100 dark:bg-blue-900/30 rounded-full flex items-center justify-center shrink-0">
                    <Users className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-blue-600" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <h3 className="font-medium text-sm sm:text-base text-gray-900 dark:text-white truncate">{userGroup.central_username}</h3>
                    <p className="text-xs text-gray-600 dark:text-gray-400">
                      {userGroup.active_services}/{userGroup.total_services} actif
                    </p>
                  </div>
                </div>

                <div className="flex items-center space-x-1 shrink-0">
                  <button
                    onClick={() => openEditUserModal(userGroup)}
                    className="p-1.5 text-gray-600 hover:text-blue-600 hover:bg-blue-50 rounded transition-colors"
                    title="Edit user information"
                  >
                    <Edit className="w-3.5 h-3.5" />
                  </button>
                  <button
                    onClick={() => deleteUserGroup(userGroup.central_user_id)}
                    className="p-1.5 text-gray-600 hover:text-red-600 hover:bg-red-50 rounded transition-colors"
                    title="Delete all mappings for this user"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>

              {/* Last Activity */}
              <div className="text-xs text-gray-500 dark:text-gray-400 mb-3">
                Dernière activité: {formatLastSync(userGroup.last_activity)}
              </div>

              {/* Service Badges */}
              <div className="flex flex-wrap gap-2 mb-3">
                {userGroup.mappings.map((mapping) => {
                  const isActive = mapping.status === 'active' && mapping.sync_enabled && mapping.last_sync_success !== false;
                  return (
                    <div
                      key={mapping.id}
                      className={`inline-flex items-center px-2 py-1 rounded text-xs font-medium transition-colors relative group ${
                        getServiceTypeColorClass(mapping.service_config?.service_type || '', isActive)
                      }`}
                    >
                      {/* Status indicator */}
                      <div className={`w-1.5 h-1.5 rounded-full mr-1.5 ${
                        mapping.status === 'active' && mapping.last_sync_success !== false
                          ? 'bg-green-500'
                          : mapping.status === 'syncing'
                          ? 'bg-blue-500'
                          : 'bg-red-500'
                      }`}></div>

                      <span>
                        {getServiceDisplayName(mapping.service_config?.service_type || '')}
                      </span>

                      {!mapping.sync_enabled && (
                        <Pause className="w-3 h-3 ml-1 opacity-60" />
                      )}

                      {/* Simplified Tooltip */}
                      <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-2 py-1 bg-gray-900 text-white text-xs rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap z-20">
                        <div>{mapping.service_username} • {mapping.status}</div>
                        <div className="absolute top-full left-1/2 transform -translate-x-1/2 w-0 h-0 border-l-2 border-r-2 border-t-2 border-transparent border-t-gray-900"></div>
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Service Details (expandable) */}
              <details className="mt-3">
                <summary className="cursor-pointer text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white">
                  Voir les détails
                </summary>
                <div className="mt-2 space-y-2 pl-4 border-l-2 border-gray-200 dark:border-gray-600">
                  {userGroup.mappings.map((mapping) => (
                    <div key={mapping.id} className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-sm">
                      <div className="flex items-center space-x-2 min-w-0">
                        <span className="font-medium text-gray-700 dark:text-gray-300 truncate">
                          {mapping.service_config?.name || 'Unknown'}
                        </span>
                        <span className="text-gray-500 dark:text-gray-400">→</span>
                        <span className="text-gray-600 dark:text-gray-400 truncate">
                          {mapping.service_username || 'No user'}
                        </span>
                      </div>

                      <div className="flex items-center space-x-2 flex-shrink-0">
                        <button
                          onClick={() => toggleSyncEnabled(mapping)}
                          className={`px-2 py-1 text-xs font-medium rounded ${
                            mapping.sync_enabled
                              ? 'bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-400'
                              : 'bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-400'
                          }`}
                        >
                          {mapping.sync_enabled ? 'Sync On' : 'Sync Off'}
                        </button>

                        {onEditMapping && (
                          <button
                            onClick={() => onEditMapping(mapping)}
                            className="p-1 text-gray-600 dark:text-gray-400 hover:text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/30 rounded transition-colors"
                          >
                            <Edit className="w-3 h-3" />
                          </button>
                        )}

                        <button
                          onClick={() => deleteMapping(mapping.id)}
                          className="p-1 text-gray-600 dark:text-gray-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/30 rounded transition-colors"
                        >
                          <Trash2 className="w-3 h-3" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </details>
            </div>
          ))}
        </div>

        {/* Empty State */}
        {groupedMappings.length === 0 && !loading && (
          <div className="text-center py-8 sm:py-12 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
            <Users className="w-10 h-10 sm:w-12 sm:h-12 text-gray-400 mx-auto mb-3 sm:mb-4" />
            <h3 className="text-base sm:text-lg font-medium text-gray-900 dark:text-white mb-2">Aucun mapping</h3>
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-4 px-4">
              {searchTerm || statusFilter !== 'all' || serviceFilter !== 'all'
                ? 'Aucun mapping ne correspond aux filtres.'
                : 'Commencez par détecter ou créer des mappings.'
              }
            </p>
            {onCreateMapping && (
              <button
                onClick={onCreateMapping}
                className="inline-flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 transition-colors"
              >
                <Plus className="w-4 h-4" />
                <span>Créer un mapping</span>
              </button>
            )}
          </div>
        )}

        {/* Pagination */}
        {total > limit && (
          <div className="flex flex-col sm:flex-row items-center justify-between gap-3 mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
            <div className="text-xs sm:text-sm text-gray-600 dark:text-gray-400">
              {groupedMappings.length} utilisateurs / {total} mappings
            </div>

            <div className="flex items-center space-x-2">
              <button
                onClick={() => setPage(page - 1)}
                disabled={page === 0}
                className="px-3 py-1.5 sm:py-2 text-xs sm:text-sm border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 transition-colors"
              >
                Précédent
              </button>
              <button
                onClick={() => setPage(page + 1)}
                disabled={(page + 1) * limit >= total}
                className="px-3 py-1.5 sm:py-2 text-xs sm:text-sm border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 transition-colors"
              >
                Suivant
              </button>
            </div>
          </div>
        )}

        {/* Edit User Modal */}
        {showEditModal && editingUser && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <div className="bg-white dark:bg-gray-800 rounded-lg p-4 sm:p-6 max-w-2xl w-full max-h-[90vh] overflow-y-auto">
              <h3 className="text-base sm:text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center">
                <Edit className="w-5 h-5 mr-2 text-blue-600" />
                Éditer: {editingUser.central_username}
              </h3>

              <div className="space-y-4 mb-6">
                {/* Central Username */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Nom d'utilisateur
                  </label>
                  <input
                    type="text"
                    value={editUsername}
                    onChange={(e) => setEditUsername(e.target.value)}
                    className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    placeholder="Entrer un nom..."
                  />
                </div>

                {/* Connected Services with Remove Button */}
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                      Services connectés ({editingUser.mappings.length})
                    </label>
                    {getUnmappedServices().length > 0 && (
                      <button
                        onClick={() => setShowAddServicePanel(!showAddServicePanel)}
                        className="flex items-center space-x-1 px-2 py-1 text-sm text-blue-600 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/30 rounded transition-colors"
                      >
                        <Plus className="w-4 h-4" />
                        <span>Ajouter</span>
                      </button>
                    )}
                  </div>

                  <div className="space-y-2">
                    {editingUser.mappings.map((mapping) => (
                      <div key={mapping.id} className="flex items-center justify-between p-2 sm:p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-gray-200 dark:border-gray-700">
                        <div className="flex items-center space-x-2 sm:space-x-3 min-w-0">
                          <div className={`w-3 h-3 rounded-full flex-shrink-0 ${getServiceColor(mapping.service_config?.service_type || '').dot}`}></div>
                          <div className="min-w-0">
                            <span className="text-sm font-medium text-gray-900 dark:text-white truncate block">
                              {mapping.service_config?.name || 'Unknown Service'}
                            </span>
                            <p className="text-xs text-gray-600 dark:text-gray-400 truncate">
                              {mapping.service_username}
                              {mapping.service_email && ` (${mapping.service_email})`}
                            </p>
                          </div>
                        </div>
                        <button
                          onClick={() => removeMappingFromEditModal(mapping.id)}
                          className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/30 rounded transition-colors flex-shrink-0"
                          title="Supprimer ce mapping"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    ))}

                    {editingUser.mappings.length === 0 && (
                      <div className="text-center py-4 text-gray-500 dark:text-gray-400 text-sm">
                        Aucun mapping. Ajoutez-en un ci-dessous.
                      </div>
                    )}
                  </div>
                </div>

                {/* Add Service Panel */}
                {showAddServicePanel && (
                  <div className="p-3 sm:p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
                    <h4 className="font-medium text-gray-900 dark:text-white mb-3 flex items-center text-sm">
                      <Link className="w-4 h-4 mr-2 text-blue-600" />
                      Ajouter un service
                    </h4>

                    {loadingEnumeration ? (
                      <div className="flex items-center justify-center py-4">
                        <RefreshCw className="w-5 h-5 text-blue-500 animate-spin mr-2" />
                        <span className="text-sm text-gray-600 dark:text-gray-400">Chargement...</span>
                      </div>
                    ) : (
                      <div className="space-y-3">
                        {/* Service Selection */}
                        <div>
                          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                            Service
                          </label>
                          <select
                            value={selectedServiceId}
                            onChange={(e) => {
                              setSelectedServiceId(e.target.value);
                              setSelectedServiceUser(null);
                            }}
                            className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                          >
                            <option value="">Choisir un service...</option>
                            {getUnmappedServices().map(([serviceId, serviceData]) => (
                              <option key={serviceId} value={serviceId}>
                                {serviceData.service_name} ({serviceData.user_count})
                              </option>
                            ))}
                          </select>
                        </div>

                        {/* User Selection */}
                        {selectedServiceId && enumerationData?.services[selectedServiceId] && (
                          <div>
                            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                              Utilisateur
                            </label>
                            <div className="max-h-40 overflow-y-auto border border-gray-200 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800">
                              {enumerationData.services[selectedServiceId].users.map((user, index) => (
                                <div
                                  key={index}
                                  onClick={() => setSelectedServiceUser(user)}
                                  className={`p-2 cursor-pointer border-b dark:border-gray-700 last:border-b-0 transition-colors ${
                                    selectedServiceUser === user
                                      ? 'bg-blue-100 dark:bg-blue-900/30 border-blue-200'
                                      : 'hover:bg-gray-50 dark:hover:bg-gray-700'
                                  }`}
                                >
                                  <div className="flex items-center space-x-2">
                                    <User className="w-4 h-4 text-gray-400" />
                                    <div className="min-w-0">
                                      <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
                                        {getDisplayName(user)}
                                      </p>
                                      {user.email && (
                                        <p className="text-xs text-gray-500 dark:text-gray-400 truncate">{user.email}</p>
                                      )}
                                    </div>
                                  </div>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Add Button */}
                        <div className="flex justify-end space-x-2">
                          <button
                            onClick={() => {
                              setShowAddServicePanel(false);
                              setSelectedServiceId('');
                              setSelectedServiceUser(null);
                            }}
                            className="px-3 py-1.5 text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors"
                          >
                            Annuler
                          </button>
                          <button
                            onClick={addServiceMapping}
                            disabled={!selectedServiceId || !selectedServiceUser || addingMapping}
                            className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 transition-colors flex items-center"
                          >
                            {addingMapping ? (
                              <>
                                <RefreshCw className="w-4 h-4 mr-1 animate-spin" />
                                Ajout...
                              </>
                            ) : (
                              <>
                                <Plus className="w-4 h-4 mr-1" />
                                Ajouter
                              </>
                            )}
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* User Info */}
                <div className="text-xs text-gray-500 dark:text-gray-400 pt-2 border-t border-gray-200 dark:border-gray-700">
                  <p><strong>ID:</strong> {editingUser.central_user_id}</p>
                  <p><strong>Services:</strong> {editingUser.total_services} ({editingUser.active_services} actifs)</p>
                </div>
              </div>

              <div className="flex justify-end space-x-2 sm:space-x-3 pt-4 border-t border-gray-200 dark:border-gray-700">
                <button
                  onClick={closeEditModal}
                  className="px-3 sm:px-4 py-2 text-sm text-gray-700 dark:text-gray-300 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
                >
                  Fermer
                </button>
                <button
                  onClick={saveUserEdit}
                  disabled={!editUsername.trim()}
                  className="px-3 sm:px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
                >
                  Sauvegarder
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default UserMappingList;