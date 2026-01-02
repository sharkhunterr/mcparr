import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';

// Import translations
import commonFR from './locales/fr/common.json';
import commonEN from './locales/en/common.json';

import dashboardFR from './locales/fr/dashboard.json';
import dashboardEN from './locales/en/dashboard.json';

import servicesFR from './locales/fr/services.json';
import servicesEN from './locales/en/services.json';

import usersFR from './locales/fr/users.json';
import usersEN from './locales/en/users.json';

import groupsFR from './locales/fr/groups.json';
import groupsEN from './locales/en/groups.json';

import trainingFR from './locales/fr/training.json';
import trainingEN from './locales/en/training.json';

import monitoringFR from './locales/fr/monitoring.json';
import monitoringEN from './locales/en/monitoring.json';

import configurationFR from './locales/fr/configuration.json';
import configurationEN from './locales/en/configuration.json';

import wizardFR from './locales/fr/wizard.json';
import wizardEN from './locales/en/wizard.json';

import mcpFR from './locales/fr/mcp.json';
import mcpEN from './locales/en/mcp.json';

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
