// Type definitions for i18next
import 'react-i18next';

// Import all namespaces
import common from './locales/fr/common.json';
import dashboard from './locales/fr/dashboard.json';
import services from './locales/fr/services.json';
import users from './locales/fr/users.json';
import groups from './locales/fr/groups.json';
import training from './locales/fr/training.json';
import monitoring from './locales/fr/monitoring.json';
import configuration from './locales/fr/configuration.json';
import wizard from './locales/fr/wizard.json';
import mcp from './locales/fr/mcp.json';

declare module 'react-i18next' {
  interface CustomTypeOptions {
    defaultNS: 'common';
    resources: {
      common: typeof common;
      dashboard: typeof dashboard;
      services: typeof services;
      users: typeof users;
      groups: typeof groups;
      training: typeof training;
      monitoring: typeof monitoring;
      configuration: typeof configuration;
      wizard: typeof wizard;
      mcp: typeof mcp;
    };
  }
}
