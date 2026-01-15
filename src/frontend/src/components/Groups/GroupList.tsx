import { useState, useEffect } from 'react';
import type { FC } from 'react';
import {
  Shield,
  Plus,
  Trash2,
  Users,
  Wrench,
  RefreshCw,
  Search,
  XCircle,
  ChevronRight,
  ToggleLeft,
  ToggleRight
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { api } from '../../lib/api';
import type { Group } from '../../types/api';
import HelpTooltip from '../common/HelpTooltip';

interface GroupListProps {
  onSelectGroup: (group: Group) => void;
  onCreateGroup: () => void;
  selectedGroupId?: string;
}

const GroupList: FC<GroupListProps> = ({ onSelectGroup, onCreateGroup, selectedGroupId }) => {
  const { t } = useTranslation('groups');
  const [groups, setGroups] = useState<Group[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [showDisabled, setShowDisabled] = useState(false);

  useEffect(() => {
    fetchGroups();
  }, [showDisabled]);

  const fetchGroups = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await api.groups.list(showDisabled ? undefined : true);
      setGroups(response.groups);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch groups');
    } finally {
      setLoading(false);
    }
  };

  const handleToggleEnabled = async (group: Group, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await api.groups.update(group.id, { enabled: !group.enabled });
      fetchGroups();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update group');
    }
  };

  const handleDeleteGroup = async (group: Group, e: React.MouseEvent) => {
    e.stopPropagation();
    if (group.is_system) {
      setError(t('list.cannotDeleteSystem'));
      return;
    }
    if (!confirm(t('list.deleteConfirm', { name: group.name }))) {
      return;
    }
    try {
      await api.groups.delete(group.id);
      fetchGroups();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete group');
    }
  };

  const filteredGroups = groups.filter(group =>
    group.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    (group.description && group.description.toLowerCase().includes(searchTerm.toLowerCase()))
  );

  if (loading) {
    return (
      <div className="p-4">
        <div className="animate-pulse space-y-3">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-16 bg-gray-200 dark:bg-gray-700 rounded-lg" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center space-x-2">
            <Shield className="w-5 h-5 text-green-600" />
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">{t('list.title')}</h2>
          </div>
          <div className="flex items-center space-x-2">
            <button
              onClick={fetchGroups}
              disabled={loading}
              className="p-2 text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
              title={t('list.refresh')}
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            </button>
            <button
              onClick={onCreateGroup}
              className="flex items-center gap-2 px-3 py-2 bg-green-600 text-white text-sm font-medium rounded-lg hover:bg-green-700 transition-colors"
            >
              <Plus className="w-4 h-4" />
              <span>{t('list.new')}</span>
            </button>
            <HelpTooltip topicId="groups" iconSize="sm" />
          </div>
        </div>

        {/* Search */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
          <input
            type="text"
            placeholder={t('list.search')}
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-9 pr-3 py-2 text-sm border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
          />
        </div>

        {/* Show disabled toggle */}
        <div className="flex items-center justify-between mt-3">
          <span className="text-xs text-gray-500 dark:text-gray-400">
            {t('list.count', { count: filteredGroups.length })}
          </span>
          <label className="flex items-center space-x-2 cursor-pointer">
            <input
              type="checkbox"
              checked={showDisabled}
              onChange={(e) => setShowDisabled(e.target.checked)}
              className="sr-only"
            />
            <span className="text-xs text-gray-500 dark:text-gray-400">{t('list.showDisabled')}</span>
            {showDisabled ? (
              <ToggleRight className="w-5 h-5 text-green-600" />
            ) : (
              <ToggleLeft className="w-5 h-5 text-gray-400" />
            )}
          </label>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="mx-4 mt-4 p-3 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-800">
          <div className="flex items-center">
            <XCircle className="w-4 h-4 text-red-500 mr-2" />
            <span className="text-sm text-red-700 dark:text-red-400">{error}</span>
          </div>
        </div>
      )}

      {/* Group List */}
      <div className="flex-1 overflow-y-auto p-4 space-y-2">
        {filteredGroups.map((group) => (
          <div
            key={group.id}
            onClick={() => onSelectGroup(group)}
            className={`p-3 rounded-lg border cursor-pointer transition-all ${
              selectedGroupId === group.id
                ? 'border-green-500 bg-green-50 dark:bg-green-900/20'
                : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-800'
            } ${!group.enabled ? 'opacity-60' : ''}`}
          >
            <div className="flex items-start justify-between">
              <div className="flex items-start space-x-3 min-w-0">
                {/* Color indicator */}
                <div
                  className="w-3 h-3 rounded-full mt-1.5 flex-shrink-0"
                  style={{ backgroundColor: group.color || '#6366f1' }}
                />
                <div className="min-w-0">
                  <div className="flex items-center space-x-2">
                    <h3 className="font-medium text-gray-900 dark:text-white truncate">
                      {group.name}
                    </h3>
                    {group.is_system && (
                      <span className="px-1.5 py-0.5 text-xs bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-400 rounded">
                        {t('list.system')}
                      </span>
                    )}
                    {!group.enabled && (
                      <span className="px-1.5 py-0.5 text-xs bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-400 rounded">
                        {t('list.disabled')}
                      </span>
                    )}
                  </div>
                  {group.description && (
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5 truncate">
                      {group.description}
                    </p>
                  )}
                  <div className="flex items-center space-x-3 mt-2 text-xs text-gray-500 dark:text-gray-400">
                    <span className="flex items-center">
                      <Users className="w-3 h-3 mr-1" />
                      {group.member_count}
                    </span>
                    <span className="flex items-center">
                      <Wrench className="w-3 h-3 mr-1" />
                      {group.tool_count}
                    </span>
                    <span>{t('list.priority')}: {group.priority}</span>
                  </div>
                </div>
              </div>
              <div className="flex items-center space-x-1 flex-shrink-0">
                <button
                  onClick={(e) => handleToggleEnabled(group, e)}
                  className={`p-1.5 rounded transition-colors ${
                    group.enabled
                      ? 'text-green-600 hover:bg-green-50 dark:hover:bg-green-900/20'
                      : 'text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700'
                  }`}
                  title={group.enabled ? t('list.disable') : t('list.enable')}
                >
                  {group.enabled ? (
                    <ToggleRight className="w-4 h-4" />
                  ) : (
                    <ToggleLeft className="w-4 h-4" />
                  )}
                </button>
                {!group.is_system && (
                  <button
                    onClick={(e) => handleDeleteGroup(group, e)}
                    className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded transition-colors"
                    title={t('list.delete')}
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                )}
                <ChevronRight className="w-4 h-4 text-gray-400" />
              </div>
            </div>
          </div>
        ))}

        {filteredGroups.length === 0 && (
          <div className="text-center py-8">
            <Shield className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-3" />
            <p className="text-sm text-gray-500 dark:text-gray-400">
              {searchTerm ? t('list.noGroupsFound') : t('list.noGroups')}
            </p>
            {!searchTerm && (
              <button
                onClick={onCreateGroup}
                className="mt-3 text-sm text-green-600 hover:text-green-700 dark:text-green-400"
              >
                {t('list.createFirst')}
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default GroupList;
