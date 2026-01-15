import { useState } from 'react';
import type { FC } from 'react';
import { Server, Layers } from 'lucide-react';
import { useTranslation } from 'react-i18next';

import ServiceList from './ServiceList';
import { ServiceGroupManagement } from '../ServiceGroups';

const ServicesDashboard: FC = () => {
  const { t } = useTranslation(['services', 'common']);
  const [activeTab, setActiveTab] = useState<'services' | 'groups'>('services');

  const tabs = [
    {
      id: 'services' as const,
      label: t('services:tabs.services.label'),
      labelFull: t('services:tabs.services.labelFull'),
      icon: Server
    },
    {
      id: 'groups' as const,
      label: t('services:tabs.groups.label'),
      labelFull: t('services:tabs.groups.labelFull'),
      icon: Layers
    }
  ];

  return (
    <div className="p-4 sm:p-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <Server className="w-6 h-6 sm:w-8 sm:h-8 text-orange-600" />
            {t('services:title')}
          </h1>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
            {t('services:description')}
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
                    ? 'bg-orange-600 text-white shadow-sm'
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
        {activeTab === 'services' && (
          <ServiceList />
        )}

        {activeTab === 'groups' && (
          <ServiceGroupManagement />
        )}
      </div>
    </div>
  );
};

export default ServicesDashboard;
