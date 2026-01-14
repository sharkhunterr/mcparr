import { useState, useEffect } from 'react';
import type { FC } from 'react';
import {
  Link2,
  Plus,
  Trash2,
  RefreshCw,
  Search,
  XCircle,
  ChevronRight,
  ToggleLeft,
  ToggleRight,
  Layers
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { getApiBaseUrl } from '../../lib/api';
import { HelpTooltip } from '../common';
import type { ToolChain } from '../../types/api';

interface ToolChainListProps {
  onSelectChain: (chain: ToolChain) => void;
  onCreateChain: () => void;
  selectedChainId?: string;
}

const ToolChainList: FC<ToolChainListProps> = ({ onSelectChain, onCreateChain, selectedChainId }) => {
  const { t } = useTranslation('mcp');
  const [chains, setChains] = useState<ToolChain[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [showDisabled, setShowDisabled] = useState(false);

  const backendUrl = getApiBaseUrl();

  useEffect(() => {
    fetchChains();
  }, [showDisabled]);

  const fetchChains = async () => {
    try {
      setLoading(true);
      setError(null);
      const url = showDisabled
        ? `${backendUrl}/api/tool-chains/`
        : `${backendUrl}/api/tool-chains/?enabled=true`;
      const response = await fetch(url);
      if (!response.ok) throw new Error('Failed to fetch tool chains');
      const data = await response.json();
      setChains(data.chains);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch tool chains');
    } finally {
      setLoading(false);
    }
  };

  const handleToggleEnabled = async (chain: ToolChain, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      const response = await fetch(`${backendUrl}/api/tool-chains/${chain.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled: !chain.enabled })
      });
      if (!response.ok) throw new Error('Failed to update chain');
      fetchChains();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update chain');
    }
  };

  const handleDeleteChain = async (chain: ToolChain, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm(t('toolChains.list.deleteConfirm', { name: chain.name }))) {
      return;
    }
    try {
      const response = await fetch(`${backendUrl}/api/tool-chains/${chain.id}`, {
        method: 'DELETE'
      });
      if (!response.ok) throw new Error('Failed to delete chain');
      fetchChains();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete chain');
    }
  };

  const filteredChains = chains.filter(chain =>
    chain.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    (chain.description && chain.description.toLowerCase().includes(searchTerm.toLowerCase()))
  );

  if (loading) {
    return (
      <div className="p-4">
        <div className="animate-pulse space-y-3">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-20 bg-gray-200 dark:bg-gray-700 rounded-lg" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="p-3 sm:p-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center space-x-2">
            <Link2 className="w-5 h-5 text-purple-600" />
            <h2 className="text-base sm:text-lg font-semibold text-gray-900 dark:text-white">{t('toolChains.list.title')}</h2>
          </div>
          <div className="flex items-center space-x-1 sm:space-x-2">
            <HelpTooltip topicId="toolChains" iconSize="sm" />
            <button
              onClick={fetchChains}
              disabled={loading}
              className="p-2 text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
              title={t('toolChains.list.refresh')}
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            </button>
            <button
              onClick={onCreateChain}
              className="flex items-center space-x-1 px-2 sm:px-3 py-1.5 sm:py-2 bg-purple-600 text-white text-xs sm:text-sm rounded-lg hover:bg-purple-700 transition-colors"
            >
              <Plus className="w-4 h-4" />
              <span className="hidden sm:inline">{t('toolChains.list.new')}</span>
            </button>
          </div>
        </div>

        {/* Search */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
          <input
            type="text"
            placeholder={t('toolChains.list.search')}
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-9 pr-3 py-2 text-sm border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
          />
        </div>

        {/* Show disabled toggle */}
        <div className="flex items-center justify-between mt-3">
          <span className="text-xs text-gray-500 dark:text-gray-400">
            {t('toolChains.list.count', { count: filteredChains.length })}
          </span>
          <label className="flex items-center space-x-2 cursor-pointer">
            <input
              type="checkbox"
              checked={showDisabled}
              onChange={(e) => setShowDisabled(e.target.checked)}
              className="sr-only"
            />
            <span className="text-xs text-gray-500 dark:text-gray-400">{t('toolChains.list.showDisabled')}</span>
            {showDisabled ? (
              <ToggleRight className="w-5 h-5 text-purple-600" />
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

      {/* Chain List */}
      <div className="flex-1 overflow-y-auto p-3 sm:p-4 space-y-2">
        {filteredChains.map((chain) => (
          <div
            key={chain.id}
            onClick={() => onSelectChain(chain)}
            className={`p-3 rounded-lg border cursor-pointer transition-all ${
              selectedChainId === chain.id
                ? 'border-purple-500 bg-purple-50 dark:bg-purple-900/20'
                : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-800'
            } ${!chain.enabled ? 'opacity-60' : ''}`}
          >
            <div className="flex items-start justify-between">
              <div className="flex-1 min-w-0">
                <div className="flex items-center flex-wrap gap-1 sm:gap-2">
                  {/* Color indicator */}
                  <div
                    className="w-3 h-3 rounded-full flex-shrink-0"
                    style={{ backgroundColor: chain.color || '#8b5cf6' }}
                  />
                  <h3 className="font-medium text-sm sm:text-base text-gray-900 dark:text-white truncate">
                    {chain.name}
                  </h3>
                  {!chain.enabled && (
                    <span className="px-1.5 py-0.5 text-xs bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-400 rounded">
                      {t('toolChains.list.disabled')}
                    </span>
                  )}
                </div>
                {chain.description && (
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5 ml-5 line-clamp-1">
                    {chain.description}
                  </p>
                )}
                {/* Step count */}
                <div className="flex items-center gap-2 mt-2 ml-5 text-xs">
                  <span className="flex items-center text-gray-500 dark:text-gray-400">
                    <Layers className="w-3 h-3 mr-1" />
                    {t('toolChains.list.stepCount', { count: chain.step_count })}
                  </span>
                  {chain.priority > 0 && (
                    <span className="px-1.5 py-0.5 bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 rounded">
                      {t('toolChains.list.priority')}: {chain.priority}
                    </span>
                  )}
                </div>
              </div>
              <div className="flex items-center space-x-0.5 sm:space-x-1 flex-shrink-0 ml-1 sm:ml-2">
                <button
                  onClick={(e) => handleToggleEnabled(chain, e)}
                  className={`p-1 sm:p-1.5 rounded transition-colors ${
                    chain.enabled
                      ? 'text-purple-600 hover:bg-purple-50 dark:hover:bg-purple-900/20'
                      : 'text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700'
                  }`}
                  title={chain.enabled ? t('toolChains.list.disable') : t('toolChains.list.enable')}
                >
                  {chain.enabled ? (
                    <ToggleRight className="w-4 h-4" />
                  ) : (
                    <ToggleLeft className="w-4 h-4" />
                  )}
                </button>
                <button
                  onClick={(e) => handleDeleteChain(chain, e)}
                  className="p-1 sm:p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded transition-colors"
                  title={t('toolChains.list.delete')}
                >
                  <Trash2 className="w-4 h-4" />
                </button>
                <ChevronRight className="w-4 h-4 text-gray-400" />
              </div>
            </div>
          </div>
        ))}

        {filteredChains.length === 0 && (
          <div className="text-center py-8">
            <Link2 className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-3" />
            <p className="text-sm text-gray-500 dark:text-gray-400">
              {searchTerm ? t('toolChains.list.noChainsFound') : t('toolChains.list.noChains')}
            </p>
            {!searchTerm && (
              <button
                onClick={onCreateChain}
                className="mt-3 text-sm text-purple-600 hover:text-purple-700 dark:text-purple-400"
              >
                {t('toolChains.list.createFirst')}
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default ToolChainList;
