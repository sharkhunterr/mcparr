import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';

export type LogLevel = 'debug' | 'info' | 'warning' | 'error' | 'critical';
export type Language = 'fr' | 'en';

interface AppSettings {
  // General
  language: Language;
  autoRefresh: boolean;
  refreshInterval: number; // seconds

  // Logging
  logLevel: LogLevel;
  logToConsole: boolean;
  logToBackend: boolean;

  // Notifications
  notificationsEnabled: boolean;
  soundEnabled: boolean;
  alertOnError: boolean;

  // Dashboard
  dashboardCompactMode: boolean;
  showSystemMetrics: boolean;
  showMcpStats: boolean;
}

const defaultSettings: AppSettings = {
  language: 'fr',
  autoRefresh: true,
  refreshInterval: 10,
  logLevel: 'info',
  logToConsole: true,
  logToBackend: true,
  notificationsEnabled: true,
  soundEnabled: false,
  alertOnError: true,
  dashboardCompactMode: false,
  showSystemMetrics: true,
  showMcpStats: true,
};

interface SettingsContextType {
  settings: AppSettings;
  updateSettings: (updates: Partial<AppSettings>) => void;
  resetSettings: () => void;
}

const SettingsContext = createContext<SettingsContextType | undefined>(undefined);

const SETTINGS_KEY = 'mcparr-settings';

export function SettingsProvider({ children }: { children: ReactNode }) {
  const [settings, setSettings] = useState<AppSettings>(() => {
    if (typeof window === 'undefined') return defaultSettings;
    try {
      const stored = localStorage.getItem(SETTINGS_KEY);
      if (stored) {
        return { ...defaultSettings, ...JSON.parse(stored) };
      }
    } catch {
      // Invalid JSON, use defaults
    }
    return defaultSettings;
  });

  useEffect(() => {
    localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings));
  }, [settings]);

  const updateSettings = (updates: Partial<AppSettings>) => {
    setSettings((prev) => ({ ...prev, ...updates }));
  };

  const resetSettings = () => {
    setSettings(defaultSettings);
    localStorage.removeItem(SETTINGS_KEY);
  };

  return (
    <SettingsContext.Provider value={{ settings, updateSettings, resetSettings }}>
      {children}
    </SettingsContext.Provider>
  );
}

export function useSettings() {
  const context = useContext(SettingsContext);
  if (context === undefined) {
    throw new Error('useSettings must be used within a SettingsProvider');
  }
  return context;
}
