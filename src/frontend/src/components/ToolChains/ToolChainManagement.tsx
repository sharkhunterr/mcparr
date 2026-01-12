import { useState, useCallback } from 'react';
import type { FC } from 'react';
import { ArrowLeft } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import type { ToolChain } from '../../types/api';
import ToolChainList from './ToolChainList';
import ToolChainDetail from './ToolChainDetail';
import ToolChainCreateModal from './ToolChainCreateModal';

interface ToolChainManagementProps {
  className?: string;
}

const ToolChainManagement: FC<ToolChainManagementProps> = ({ className = '' }) => {
  const { t } = useTranslation('mcp');
  const [selectedChain, setSelectedChain] = useState<ToolChain | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);

  const handleSelectChain = useCallback((chain: ToolChain) => {
    setSelectedChain(chain);
  }, []);

  const handleCreateChain = useCallback(() => {
    setShowCreateModal(true);
  }, []);

  const handleCreated = useCallback(() => {
    setShowCreateModal(false);
    setRefreshKey(prev => prev + 1);
  }, []);

  const handleUpdated = useCallback(() => {
    setRefreshKey(prev => prev + 1);
  }, []);

  const handleCloseDetail = useCallback(() => {
    setSelectedChain(null);
  }, []);

  return (
    <div className={`flex flex-col md:flex-row h-full ${className}`}>
      {/* Chain List - Hidden on mobile when detail is shown */}
      <div className={`
        ${selectedChain ? 'hidden md:flex' : 'flex'}
        flex-col
        w-full md:w-1/2 lg:w-2/5
        md:border-r border-gray-200 dark:border-gray-700
        overflow-hidden
        h-full
      `}>
        <ToolChainList
          key={refreshKey}
          onSelectChain={handleSelectChain}
          onCreateChain={handleCreateChain}
          selectedChainId={selectedChain?.id}
        />
      </div>

      {/* Chain Detail - Full width on mobile, half on desktop */}
      <div className={`
        ${selectedChain ? 'flex' : 'hidden md:flex'}
        flex-col
        w-full md:w-1/2 lg:w-3/5
        overflow-hidden
        h-full
      `}>
        {selectedChain ? (
          <div className="h-full flex flex-col">
            {/* Mobile back button */}
            <div className="md:hidden px-4 py-3 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900">
              <button
                onClick={handleCloseDetail}
                className="flex items-center space-x-2 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors"
              >
                <ArrowLeft className="w-4 h-4" />
                <span>{t('toolChains.detail.backToList')}</span>
              </button>
            </div>
            <div className="flex-1 overflow-hidden">
              <ToolChainDetail
                key={selectedChain.id}
                chain={selectedChain}
                onClose={handleCloseDetail}
                onUpdated={handleUpdated}
              />
            </div>
          </div>
        ) : (
          <div className="h-full flex items-center justify-center text-gray-400 dark:text-gray-600 p-4">
            <p className="text-center">{t('toolChains.detail.selectChain')}</p>
          </div>
        )}
      </div>

      {/* Create Modal */}
      {showCreateModal && (
        <ToolChainCreateModal
          onClose={() => setShowCreateModal(false)}
          onCreated={handleCreated}
        />
      )}
    </div>
  );
};

export default ToolChainManagement;
