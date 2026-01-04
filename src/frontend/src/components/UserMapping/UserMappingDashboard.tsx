import { useState } from 'react';
import type { FC } from 'react';
import {
  Users,
  Search,
  Link,
  Shield
} from 'lucide-react';
import { useTranslation } from 'react-i18next';

import UserMappingDetector from './UserMappingDetector';
import UserMappingList from './UserMappingList';
import UserMappingCreator from './UserMappingCreator';
import { GroupManagement } from '../Groups';

interface UserMappingDashboardProps {
  onEditMapping?: (mapping: any) => void;
}

const UserMappingDashboard: FC<UserMappingDashboardProps> = ({
  onEditMapping
}) => {
  const { t } = useTranslation('users');
  const [activeTab, setActiveTab] = useState<'detector' | 'manual' | 'list' | 'groups'>('detector');
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  const handleDetectionComplete = () => {
    // Refresh the mappings list when detection completes
    setRefreshTrigger(prev => prev + 1);
    // Stay on detector tab to show results
    // Only switch to list if there are actual suggestions
  };

  const handleMappingChange = () => {
    // Refresh components when mappings are modified
    setRefreshTrigger(prev => prev + 1);
  };

  const tabs = [
    {
      id: 'detector' as const,
      label: t('tabs.detector.label'),
      labelFull: t('tabs.detector.labelFull'),
      icon: Search
    },
    {
      id: 'manual' as const,
      label: t('tabs.manual.label'),
      labelFull: t('tabs.manual.labelFull'),
      icon: Link
    },
    {
      id: 'list' as const,
      label: t('tabs.list.label'),
      labelFull: t('tabs.list.labelFull'),
      icon: Users
    },
    {
      id: 'groups' as const,
      label: t('tabs.groups.label'),
      labelFull: t('tabs.groups.labelFull'),
      icon: Shield
    }
  ];

  return (
    <div className="p-4 sm:p-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <Users className="w-6 h-6 sm:w-8 sm:h-8 text-green-600" />
            {t('title')}
          </h1>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
            {t('description')}
          </p>
        </div>

      </div>

      {/* Tab Navigation - Compact horizontal pills */}
      <div className="mb-4 sm:mb-6 overflow-x-auto -mx-4 px-4 sm:mx-0 sm:px-0">
        <nav className="flex gap-1.5 sm:gap-2 min-w-max sm:min-w-0 sm:flex-wrap">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;

            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                title={tab.labelFull}
                className={`flex items-center gap-1.5 py-1.5 px-2.5 sm:py-2 sm:px-3 rounded-full font-medium text-xs sm:text-sm transition-all whitespace-nowrap ${
                  isActive
                    ? 'bg-green-600 text-white shadow-sm'
                    : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
                }`}
              >
                <Icon className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </nav>
      </div>

      {/* Tab Content */}
      <div className="space-y-6">
        {activeTab === 'manual' && (
          <UserMappingCreator onMappingCreated={handleMappingChange} />
        )}

        {activeTab === 'detector' && (
          <UserMappingDetector onDetectionComplete={handleDetectionComplete} />
        )}

        {activeTab === 'list' && (
          <UserMappingList
            key={refreshTrigger}
            onEditMapping={onEditMapping}
          />
        )}

        {activeTab === 'groups' && (
          <GroupManagement />
        )}
      </div>
    </div>
  );
};

export default UserMappingDashboard;