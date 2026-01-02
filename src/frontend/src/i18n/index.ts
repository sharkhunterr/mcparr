import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';

// Import French translations
import commonFR from './locales/fr/common.json';
import dashboardFR from './locales/fr/dashboard.json';
import servicesFR from './locales/fr/services.json';
import usersFR from './locales/fr/users.json';
import groupsFR from './locales/fr/groups.json';
import trainingFR from './locales/fr/training.json';
import monitoringFR from './locales/fr/monitoring.json';
import configurationFR from './locales/fr/configuration.json';
import wizardFR from './locales/fr/wizard.json';
import mcpFR from './locales/fr/mcp.json';

// Import English translations
import commonEN from './locales/en/common.json';
import dashboardEN from './locales/en/dashboard.json';
import servicesEN from './locales/en/services.json';
import usersEN from './locales/en/users.json';
import groupsEN from './locales/en/groups.json';
import trainingEN from './locales/en/training.json';
import monitoringEN from './locales/en/monitoring.json';
import configurationEN from './locales/en/configuration.json';
import wizardEN from './locales/en/wizard.json';
import mcpEN from './locales/en/mcp.json';

// Import Italian translations
import commonIT from './locales/it/common.json';
import dashboardIT from './locales/it/dashboard.json';
import servicesIT from './locales/it/services.json';
import usersIT from './locales/it/users.json';
import groupsIT from './locales/it/groups.json';
import trainingIT from './locales/it/training.json';
import monitoringIT from './locales/it/monitoring.json';
import configurationIT from './locales/it/configuration.json';
import wizardIT from './locales/it/wizard.json';
import mcpIT from './locales/it/mcp.json';

// Import German translations
import commonDE from './locales/de/common.json';
import dashboardDE from './locales/de/dashboard.json';
import servicesDE from './locales/de/services.json';
import usersDE from './locales/de/users.json';
import groupsDE from './locales/de/groups.json';
import trainingDE from './locales/de/training.json';
import monitoringDE from './locales/de/monitoring.json';
import configurationDE from './locales/de/configuration.json';
import wizardDE from './locales/de/wizard.json';
import mcpDE from './locales/de/mcp.json';

// Import Spanish translations
import commonES from './locales/es/common.json';
import dashboardES from './locales/es/dashboard.json';
import servicesES from './locales/es/services.json';
import usersES from './locales/es/users.json';
import groupsES from './locales/es/groups.json';
import trainingES from './locales/es/training.json';
import monitoringES from './locales/es/monitoring.json';
import configurationES from './locales/es/configuration.json';
import wizardES from './locales/es/wizard.json';
import mcpES from './locales/es/mcp.json';

// Configure i18next
i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: {
      fr: {
        common: commonFR,
        dashboard: dashboardFR,
        services: servicesFR,
        users: usersFR,
        groups: groupsFR,
        training: trainingFR,
        monitoring: monitoringFR,
        configuration: configurationFR,
        wizard: wizardFR,
        mcp: mcpFR,
      },
      en: {
        common: commonEN,
        dashboard: dashboardEN,
        services: servicesEN,
        users: usersEN,
        groups: groupsEN,
        training: trainingEN,
        monitoring: monitoringEN,
        configuration: configurationEN,
        wizard: wizardEN,
        mcp: mcpEN,
      },
      it: {
        common: commonIT,
        dashboard: dashboardIT,
        services: servicesIT,
        users: usersIT,
        groups: groupsIT,
        training: trainingIT,
        monitoring: monitoringIT,
        configuration: configurationIT,
        wizard: wizardIT,
        mcp: mcpIT,
      },
      de: {
        common: commonDE,
        dashboard: dashboardDE,
        services: servicesDE,
        users: usersDE,
        groups: groupsDE,
        training: trainingDE,
        monitoring: monitoringDE,
        configuration: configurationDE,
        wizard: wizardDE,
        mcp: mcpDE,
      },
      es: {
        common: commonES,
        dashboard: dashboardES,
        services: servicesES,
        users: usersES,
        groups: groupsES,
        training: trainingES,
        monitoring: monitoringES,
        configuration: configurationES,
        wizard: wizardES,
        mcp: mcpES,
      },
    },
    fallbackLng: 'fr',
    defaultNS: 'common',
    ns: ['common', 'dashboard', 'services', 'users', 'groups', 'training', 'monitoring', 'configuration', 'wizard', 'mcp'],
    interpolation: {
      escapeValue: false, // React already escapes values
    },
    detection: {
      order: ['localStorage', 'navigator'],
      caches: ['localStorage'],
      lookupLocalStorage: 'i18nextLng',
    },
  });

export default i18n;
