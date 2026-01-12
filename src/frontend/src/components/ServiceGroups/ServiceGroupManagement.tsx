import { useState, useCallback } from 'react';
import type { FC } from 'react';
import { Layers } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import ServiceGroupList from './ServiceGroupList';
import ServiceGroupDetail from './ServiceGroupDetail';
import ServiceGroupCreateModal from './ServiceGroupCreateModal';
import type { ServiceGroup } from '../../types/api';

const ServiceGroupManagement: FC = () => {
  const { t } = useTranslation('services');
  const [selectedGroup, setSelectedGroup] = useState<ServiceGroup | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);

  const handleRefresh = useCallback(() => {
    setRefreshKey(prev => prev + 1);
  }, []);

  const handleSelectGroup = useCallback((group: ServiceGroup) => {
    setSelectedGroup(group);
  }, []);

  const handleCloseDetail = useCallback(() => {
    setSelectedGroup(null);
  }, []);

  const handleCreateGroup = useCallback(() => {
    setShowCreateModal(true);
  }, []);

  const handleGroupCreated = useCallback(() => {
    setShowCreateModal(false);
    handleRefresh();
  }, [handleRefresh]);

  const handleGroupUpdated = useCallback(() => {
    handleRefresh();
  }, [handleRefresh]);

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 overflow-hidden">
      {/* Desktop Layout: Side by Side */}
      <div className="hidden md:flex h-[600px]">
        {/* Left sidebar - Group List */}
        <div className="w-80 border-r border-gray-200 dark:border-gray-700 flex-shrink-0">
          <ServiceGroupList
            key={refreshKey}
            onSelectGroup={handleSelectGroup}
            onCreateGroup={handleCreateGroup}
            selectedGroupId={selectedGroup?.id}
          />
        </div>

        {/* Right content - Group Detail */}
        <div className="flex-1 min-w-0">
          {selectedGroup ? (
            <ServiceGroupDetail
              key={selectedGroup.id}
              group={selectedGroup}
              onClose={handleCloseDetail}
              onUpdated={handleGroupUpdated}
            />
          ) : (
            <div className="h-full flex flex-col items-center justify-center text-gray-400 dark:text-gray-500">
              <Layers className="w-16 h-16 mb-4 opacity-50" />
              <p className="text-lg font-medium">{t('serviceGroups.management.title')}</p>
              <p className="text-sm mt-2 max-w-md text-center">
                {t('serviceGroups.management.description')}
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Mobile Layout: Full width list, detail as modal */}
      <div className="md:hidden">
        {/* Group List - Full Width */}
        <div className="min-h-[400px]">
          <ServiceGroupList
            key={refreshKey}
            onSelectGroup={handleSelectGroup}
            onCreateGroup={handleCreateGroup}
            selectedGroupId={selectedGroup?.id}
          />
        </div>

        {/* Mobile Detail Modal - Slide up from bottom */}
        {selectedGroup && (
          <div className="fixed inset-0 z-50 md:hidden">
            {/* Backdrop */}
            <div
              className="absolute inset-0 bg-black/50"
              onClick={handleCloseDetail}
            />

            {/* Modal Content - Full screen with rounded top */}
            <div className="absolute inset-x-0 bottom-0 top-12 bg-white dark:bg-gray-800 rounded-t-2xl shadow-xl flex flex-col animate-in slide-in-from-bottom duration-300">
              {/* Drag handle */}
              <div className="flex justify-center pt-3 pb-1">
                <div className="w-10 h-1 bg-gray-300 dark:bg-gray-600 rounded-full" />
              </div>

              {/* Content */}
              <div className="flex-1 overflow-hidden">
                <ServiceGroupDetail
                  key={selectedGroup.id}
                  group={selectedGroup}
                  onClose={handleCloseDetail}
                  onUpdated={handleGroupUpdated}
                />
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Create Modal */}
      {showCreateModal && (
        <ServiceGroupCreateModal
          onClose={() => setShowCreateModal(false)}
          onCreated={handleGroupCreated}
        />
      )}
    </div>
  );
};

export default ServiceGroupManagement;
