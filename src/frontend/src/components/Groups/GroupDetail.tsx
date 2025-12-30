import { useState, useEffect, useMemo } from 'react';
import type { FC } from 'react';
import {
  Shield,
  Users,
  Wrench,
  Save,
  X,
  Plus,
  Trash2,
  RefreshCw,
  ChevronDown,
  ChevronRight,
  Search,
  Zap
} from 'lucide-react';
import { api } from '../../lib/api';
import type { Group, GroupDetail as GroupDetailType, AvailableToolsResponse } from '../../types/api';
import { getServiceColor } from '../../lib/serviceColors';

interface GroupDetailProps {
  group: Group;
  onClose: () => void;
  onUpdated: () => void;
}

interface CentralUser {
  central_user_id: string;
  central_username: string;
  service_count: number;
}

const GroupDetail: FC<GroupDetailProps> = ({ group, onClose, onUpdated }) => {
  const [groupDetail, setGroupDetail] = useState<GroupDetailType | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'info' | 'members' | 'permissions'>('info');

  // Edit state
  const [editName, setEditName] = useState(group.name);
  const [editDescription, setEditDescription] = useState(group.description || '');
  const [editColor, setEditColor] = useState(group.color || '#6366f1');
  const [editPriority, setEditPriority] = useState(group.priority);

  // Members state
  const [centralUsers, setCentralUsers] = useState<CentralUser[]>([]);
  const [loadingUsers, setLoadingUsers] = useState(false);
  const [showAddMember, setShowAddMember] = useState(false);
  const [memberSearchTerm, setMemberSearchTerm] = useState('');

  // Permissions state
  const [availableTools, setAvailableTools] = useState<AvailableToolsResponse | null>(null);
  const [loadingTools, setLoadingTools] = useState(false);
  const [expandedServices, setExpandedServices] = useState<Set<string>>(new Set());
  const [toolSearchQuery, setToolSearchQuery] = useState('');
  const [savingTool, setSavingTool] = useState<string | null>(null);

  useEffect(() => {
    fetchGroupDetail();
  }, [group.id]);

  useEffect(() => {
    if (activeTab === 'members' && centralUsers.length === 0) {
      fetchCentralUsers();
    }
    if (activeTab === 'permissions' && !availableTools) {
      fetchAvailableTools();
    }
  }, [activeTab]);

  const fetchGroupDetail = async () => {
    try {
      setLoading(true);
      setError(null);
      const detail = await api.groups.get(group.id);
      setGroupDetail(detail);
      setEditName(detail.name);
      setEditDescription(detail.description || '');
      setEditColor(detail.color || '#6366f1');
      setEditPriority(detail.priority);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch group details');
    } finally {
      setLoading(false);
    }
  };

  const fetchCentralUsers = async () => {
    try {
      setLoadingUsers(true);
      const response = await fetch(`${api.getBaseUrl()}/api/users/central-users`);
      if (response.ok) {
        const data = await response.json();
        setCentralUsers(data.users || []);
      }
    } catch (err) {
      console.error('Failed to fetch central users:', err);
    } finally {
      setLoadingUsers(false);
    }
  };

  const fetchAvailableTools = async () => {
    try {
      setLoadingTools(true);
      const tools = await api.groups.availableTools();
      setAvailableTools(tools);
    } catch (err) {
      console.error('Failed to fetch available tools:', err);
    } finally {
      setLoadingTools(false);
    }
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      setError(null);
      await api.groups.update(group.id, {
        name: editName,
        description: editDescription || undefined,
        color: editColor,
        priority: editPriority
      });
      onUpdated();
      fetchGroupDetail();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save group');
    } finally {
      setSaving(false);
    }
  };

  const handleAddMember = async (centralUserId: string) => {
    try {
      await api.groups.members.add(group.id, { central_user_id: centralUserId, enabled: true });
      fetchGroupDetail();
      setShowAddMember(false);
      setMemberSearchTerm('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add member');
    }
  };

  const handleRemoveMember = async (membershipId: string) => {
    if (!confirm('Remove this member from the group?')) return;
    try {
      await api.groups.members.remove(group.id, membershipId);
      fetchGroupDetail();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to remove member');
    }
  };

  const handleToggleTool = async (toolName: string, serviceType: string, isCurrentlyEnabled: boolean) => {
    setSavingTool(toolName);
    try {
      if (isCurrentlyEnabled) {
        // Find and remove the permission
        const permission = groupDetail?.tool_permissions.find(p => p.tool_name === toolName);
        if (permission) {
          await api.groups.permissions.delete(group.id, permission.id);
        }
      } else {
        await api.groups.permissions.add(group.id, {
          tool_name: toolName,
          service_type: serviceType,
          enabled: true
        });
      }
      await fetchGroupDetail();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to toggle tool');
    } finally {
      setSavingTool(null);
    }
  };

  const handleAddAllToolsForService = async (serviceType: string) => {
    if (!availableTools) return;
    const tools = availableTools.tools_by_service[serviceType];
    if (!tools || tools.length === 0) return;

    try {
      // Add each tool individually (not as wildcard) so they show as labels
      const toolNames = tools.map(t => t.name);
      await api.groups.permissions.bulk(group.id, {
        tool_names: toolNames,
        service_type: serviceType,
        enabled: true
      });
      fetchGroupDetail();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add permissions');
    }
  };

  const handleRemoveAllToolsForService = async (serviceType: string) => {
    if (!groupDetail || !availableTools) return;
    const tools = availableTools.tools_by_service[serviceType];
    if (!tools || tools.length === 0) return;

    try {
      // Remove each permission for this service
      const toolNames = tools.map(t => t.name);
      for (const toolName of toolNames) {
        const permission = groupDetail.tool_permissions.find(p => p.tool_name === toolName);
        if (permission) {
          await api.groups.permissions.delete(group.id, permission.id);
        }
      }
      fetchGroupDetail();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to remove permissions');
    }
  };

  const handleAddAllTools = async () => {
    if (!availableTools) return;

    try {
      // Add ALL tools from ALL services individually
      for (const [serviceType, tools] of Object.entries(availableTools.tools_by_service)) {
        if (tools.length > 0) {
          const toolNames = tools.map(t => t.name);
          await api.groups.permissions.bulk(group.id, {
            tool_names: toolNames,
            service_type: serviceType,
            enabled: true
          });
        }
      }
      fetchGroupDetail();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add permissions');
    }
  };

  const toggleServiceExpand = (service: string) => {
    const newExpanded = new Set(expandedServices);
    if (newExpanded.has(service)) {
      newExpanded.delete(service);
    } else {
      newExpanded.add(service);
    }
    setExpandedServices(newExpanded);
  };

  const isToolPermitted = (toolName: string, serviceType?: string): boolean => {
    if (!groupDetail) return false;
    return groupDetail.tool_permissions.some(p =>
      p.enabled && (
        p.tool_name === toolName ||
        (p.tool_name === '*' && (!p.service_type || p.service_type === serviceType))
      )
    );
  };

  const getMemberIds = (): Set<string> => {
    if (!groupDetail) return new Set();
    return new Set(groupDetail.memberships.map(m => m.central_user_id));
  };

  const filteredUsersToAdd = centralUsers.filter(user => {
    const memberIds = getMemberIds();
    if (memberIds.has(user.central_user_id)) return false;
    if (!memberSearchTerm) return true;
    return user.central_username.toLowerCase().includes(memberSearchTerm.toLowerCase()) ||
           user.central_user_id.toLowerCase().includes(memberSearchTerm.toLowerCase());
  });

  // Filter tools by search query
  const filteredToolsByService = useMemo(() => {
    if (!availableTools) return {};
    if (!toolSearchQuery.trim()) return availableTools.tools_by_service;

    const query = toolSearchQuery.toLowerCase();
    const filtered: Record<string, typeof availableTools.tools_by_service[string]> = {};

    Object.entries(availableTools.tools_by_service).forEach(([service, tools]) => {
      const matchingTools = tools.filter(
        tool => tool.name.toLowerCase().includes(query) ||
                tool.description?.toLowerCase().includes(query) ||
                service.toLowerCase().includes(query)
      );
      if (matchingTools.length > 0) {
        filtered[service] = matchingTools;
      }
    });

    return filtered;
  }, [availableTools, toolSearchQuery]);

  // Count enabled tools per service
  const enabledCountByService = useMemo(() => {
    if (!groupDetail || !availableTools) return {};
    const counts: Record<string, { enabled: number; total: number }> = {};

    Object.entries(availableTools.tools_by_service).forEach(([service, tools]) => {
      const enabled = tools.filter(t => isToolPermitted(t.name, service)).length;
      counts[service] = { enabled, total: tools.length };
    });

    return counts;
  }, [groupDetail, availableTools]);

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <RefreshCw className="w-6 h-6 text-indigo-600 animate-spin" />
      </div>
    );
  }

  if (!groupDetail) {
    return (
      <div className="h-full flex items-center justify-center text-gray-500">
        Groupe non trouvé
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div
            className="w-4 h-4 rounded-full"
            style={{ backgroundColor: groupDetail.color || '#6366f1' }}
          />
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
            {groupDetail.name}
          </h2>
          {groupDetail.is_system && (
            <span className="px-2 py-0.5 text-xs bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-400 rounded">
              Système
            </span>
          )}
        </div>
        <button
          onClick={onClose}
          className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-gray-200 dark:border-gray-700">
        {[
          { id: 'info', label: 'Informations', icon: Shield },
          { id: 'members', label: `Membres (${groupDetail.member_count})`, icon: Users },
          { id: 'permissions', label: `Outils (${groupDetail.tool_count})`, icon: Wrench }
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as typeof activeTab)}
            className={`flex items-center space-x-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
              activeTab === tab.id
                ? 'border-indigo-500 text-indigo-600 dark:text-indigo-400'
                : 'border-transparent text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'
            }`}
          >
            <tab.icon className="w-4 h-4" />
            <span>{tab.label}</span>
          </button>
        ))}
      </div>

      {/* Error */}
      {error && (
        <div className="mx-4 mt-4 p-3 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-800">
          <span className="text-sm text-red-700 dark:text-red-400">{error}</span>
        </div>
      )}

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4">
        {/* Info Tab */}
        {activeTab === 'info' && (
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Nom
              </label>
              <input
                type="text"
                value={editName}
                onChange={(e) => setEditName(e.target.value)}
                disabled={groupDetail.is_system}
                className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded-lg focus:ring-2 focus:ring-indigo-500 disabled:bg-gray-100 dark:disabled:bg-gray-800"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Description
              </label>
              <textarea
                value={editDescription}
                onChange={(e) => setEditDescription(e.target.value)}
                rows={3}
                className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded-lg focus:ring-2 focus:ring-indigo-500"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Couleur
                </label>
                <div className="flex items-center space-x-2">
                  <input
                    type="color"
                    value={editColor}
                    onChange={(e) => setEditColor(e.target.value)}
                    className="w-10 h-10 rounded cursor-pointer border border-gray-300 dark:border-gray-600"
                  />
                  <input
                    type="text"
                    value={editColor}
                    onChange={(e) => setEditColor(e.target.value)}
                    className="flex-1 px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded-lg"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Priorité
                </label>
                <input
                  type="number"
                  value={editPriority}
                  onChange={(e) => setEditPriority(parseInt(e.target.value) || 0)}
                  className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded-lg focus:ring-2 focus:ring-indigo-500"
                />
                <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                  Priorité plus élevée = résolution en premier
                </p>
              </div>
            </div>

            <div className="pt-4 flex justify-end">
              <button
                onClick={handleSave}
                disabled={saving || !editName.trim()}
                className="flex items-center space-x-2 px-4 py-2 bg-indigo-600 text-white text-sm rounded-lg hover:bg-indigo-700 disabled:opacity-50 transition-colors"
              >
                {saving ? (
                  <RefreshCw className="w-4 h-4 animate-spin" />
                ) : (
                  <Save className="w-4 h-4" />
                )}
                <span>Sauvegarder</span>
              </button>
            </div>
          </div>
        )}

        {/* Members Tab */}
        {activeTab === 'members' && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300">
                Membres du groupe
              </h3>
              <button
                onClick={() => setShowAddMember(!showAddMember)}
                className="flex items-center space-x-1 px-3 py-1.5 text-sm text-indigo-600 hover:bg-indigo-50 dark:hover:bg-indigo-900/20 rounded-lg transition-colors"
              >
                <Plus className="w-4 h-4" />
                <span>Ajouter</span>
              </button>
            </div>

            {/* Add Member Panel */}
            {showAddMember && (
              <div className="p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-gray-200 dark:border-gray-700">
                <div className="relative mb-3">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
                  <input
                    type="text"
                    placeholder="Rechercher un utilisateur..."
                    value={memberSearchTerm}
                    onChange={(e) => setMemberSearchTerm(e.target.value)}
                    className="w-full pl-9 pr-3 py-2 text-sm border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded-lg"
                  />
                </div>

                {loadingUsers ? (
                  <div className="flex items-center justify-center py-4">
                    <RefreshCw className="w-5 h-5 text-indigo-500 animate-spin" />
                  </div>
                ) : (
                  <div className="max-h-48 overflow-y-auto space-y-1">
                    {filteredUsersToAdd.map(user => (
                      <div
                        key={user.central_user_id}
                        onClick={() => handleAddMember(user.central_user_id)}
                        className="flex items-center justify-between p-2 hover:bg-white dark:hover:bg-gray-700 rounded cursor-pointer"
                      >
                        <div>
                          <p className="text-sm font-medium text-gray-900 dark:text-white">
                            {user.central_username}
                          </p>
                          <p className="text-xs text-gray-500 dark:text-gray-400">
                            {user.service_count} service{user.service_count > 1 ? 's' : ''}
                          </p>
                        </div>
                        <Plus className="w-4 h-4 text-indigo-600" />
                      </div>
                    ))}
                    {filteredUsersToAdd.length === 0 && (
                      <p className="text-sm text-gray-500 dark:text-gray-400 text-center py-4">
                        Aucun utilisateur disponible
                      </p>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* Members List */}
            <div className="space-y-2">
              {groupDetail.memberships.map(member => (
                <div
                  key={member.id}
                  className="flex items-center justify-between p-3 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg"
                >
                  <div className="flex items-center space-x-3">
                    <div className="w-8 h-8 bg-indigo-100 dark:bg-indigo-900/30 rounded-full flex items-center justify-center">
                      <Users className="w-4 h-4 text-indigo-600" />
                    </div>
                    <div>
                      <p className="text-sm font-medium text-gray-900 dark:text-white">
                        {member.central_username || member.central_user_id}
                      </p>
                      <p className="text-xs text-gray-500 dark:text-gray-400">
                        Ajouté le {new Date(member.granted_at).toLocaleDateString()}
                      </p>
                    </div>
                  </div>
                  <button
                    onClick={() => handleRemoveMember(member.central_user_id)}
                    className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded transition-colors"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              ))}

              {groupDetail.memberships.length === 0 && (
                <div className="text-center py-8 text-gray-500 dark:text-gray-400">
                  <Users className="w-10 h-10 mx-auto mb-2 opacity-50" />
                  <p className="text-sm">Aucun membre</p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Permissions Tab - Refonte Mobile-First */}
        {activeTab === 'permissions' && (
          <div className="space-y-3">
            {/* Search + Quick Actions - Compact */}
            <div className="sticky top-0 bg-white dark:bg-gray-800 pb-2 -mt-1 pt-1 z-10">
              {/* Search bar + action in one row */}
              <div className="flex items-center gap-2">
                <div className="relative flex-1">
                  <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400" />
                  <input
                    type="text"
                    placeholder="Rechercher..."
                    value={toolSearchQuery}
                    onChange={(e) => setToolSearchQuery(e.target.value)}
                    className="w-full pl-8 pr-7 py-1.5 text-xs border border-gray-300 dark:border-gray-600 bg-transparent dark:text-white rounded-md focus:ring-1 focus:ring-indigo-500"
                  />
                  {toolSearchQuery && (
                    <button
                      onClick={() => setToolSearchQuery('')}
                      className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>
                <button
                  onClick={handleAddAllTools}
                  className="flex items-center gap-1 px-2 py-1.5 text-xs font-medium bg-indigo-600 text-white rounded-md hover:bg-indigo-700 transition-colors whitespace-nowrap"
                >
                  <Zap className="w-3 h-3" />
                  Tout
                </button>
                <span className="text-xs text-gray-500 dark:text-gray-400 whitespace-nowrap">
                  {groupDetail.tool_count}/{availableTools?.total_tools || 0}
                </span>
              </div>
            </div>

            {/* Tools by service */}
            {loadingTools ? (
              <div className="flex items-center justify-center py-8">
                <RefreshCw className="w-6 h-6 text-indigo-500 animate-spin" />
              </div>
            ) : Object.keys(filteredToolsByService).length > 0 ? (
              <div className="space-y-2">
                {Object.entries(filteredToolsByService).map(([serviceType, tools]) => {
                  const colors = getServiceColor(serviceType);
                  const Icon = colors.icon;
                  const isExpanded = expandedServices.has(serviceType);
                  const counts = enabledCountByService[serviceType] || { enabled: 0, total: 0 };

                  return (
                    <div
                      key={serviceType}
                      className={`rounded-lg overflow-hidden border ${colors.border}`}
                    >
                      {/* Service header */}
                      <button
                        onClick={() => toggleServiceExpand(serviceType)}
                        className={`w-full flex items-center justify-between px-3 py-2.5 ${colors.bg} hover:opacity-90 transition-opacity`}
                      >
                        <div className="flex items-center gap-2">
                          <div className={`p-1.5 rounded-lg ${colors.badge} ${colors.badgeDark}`}>
                            <Icon className="w-4 h-4" />
                          </div>
                          <div className="text-left">
                            <span className={`font-medium text-sm capitalize ${colors.text}`}>
                              {serviceType}
                            </span>
                            <span className="text-xs text-gray-500 dark:text-gray-400 ml-2">
                              {counts.enabled}/{counts.total}
                            </span>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          {/* Quick toggle all for this service */}
                          {counts.enabled === counts.total && counts.total > 0 ? (
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                handleRemoveAllToolsForService(serviceType);
                              }}
                              className="px-2 py-0.5 text-xs font-medium text-red-600 dark:text-red-400 hover:bg-red-100 dark:hover:bg-red-900/30 rounded transition-colors"
                            >
                              Aucun
                            </button>
                          ) : (
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                handleAddAllToolsForService(serviceType);
                              }}
                              className="px-2 py-0.5 text-xs font-medium text-indigo-600 dark:text-indigo-400 hover:bg-indigo-100 dark:hover:bg-indigo-900/30 rounded transition-colors"
                            >
                              Tous
                            </button>
                          )}
                          {isExpanded ? (
                            <ChevronDown className="w-4 h-4 text-gray-500" />
                          ) : (
                            <ChevronRight className="w-4 h-4 text-gray-500" />
                          )}
                        </div>
                      </button>

                      {/* Tools list */}
                      {isExpanded && (
                        <div className="bg-white dark:bg-gray-800 divide-y divide-gray-100 dark:divide-gray-700">
                          {tools.map(tool => {
                            const isEnabled = isToolPermitted(tool.name, serviceType);
                            const isSaving = savingTool === tool.name;

                            return (
                              <div
                                key={tool.name}
                                className={`flex items-center gap-3 px-3 py-2.5 transition-colors ${
                                  isEnabled ? 'bg-indigo-50/50 dark:bg-indigo-900/10' : ''
                                }`}
                              >
                                {/* Toggle button */}
                                <button
                                  onClick={() => handleToggleTool(tool.name, serviceType, isEnabled)}
                                  disabled={isSaving}
                                  className={`flex-shrink-0 w-9 h-5 rounded-full transition-colors relative ${
                                    isEnabled
                                      ? 'bg-indigo-600'
                                      : 'bg-gray-300 dark:bg-gray-600'
                                  } ${isSaving ? 'opacity-50' : ''}`}
                                >
                                  <span
                                    className={`absolute top-0.5 w-4 h-4 bg-white rounded-full shadow-sm transition-all duration-200 ${
                                      isEnabled ? 'left-[18px]' : 'left-0.5'
                                    }`}
                                  />
                                  {isSaving && (
                                    <RefreshCw className="absolute inset-0 m-auto w-3 h-3 text-white animate-spin" />
                                  )}
                                </button>

                                {/* Tool info */}
                                <div className="flex-1 min-w-0">
                                  <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
                                    {tool.name.replace(`${serviceType}_`, '')}
                                  </p>
                                  {tool.description && (
                                    <p className="text-xs text-gray-500 dark:text-gray-400 truncate">
                                      {tool.description}
                                    </p>
                                  )}
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="text-center py-8 text-gray-500 dark:text-gray-400">
                <Wrench className="w-10 h-10 mx-auto mb-2 opacity-50" />
                <p className="text-sm">
                  {toolSearchQuery ? 'Aucun outil ne correspond à la recherche' : 'Aucun outil disponible'}
                </p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default GroupDetail;
