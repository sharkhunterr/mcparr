import React, { useState, useRef, useEffect, useCallback } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import {
  Home,
  Server,
  Users,
  Settings,
  Activity,
  Menu,
  X,
  Zap,
  Bot,
  Brain,
  Sun,
  Moon,
  ChevronDown,
  Bell,
  CheckCircle,
  ExternalLink,
  AlertTriangle,
} from 'lucide-react';
import { useTheme } from '../contexts/ThemeContext';
import { api } from '../lib/api';

// Language configuration with flags
const languages = [
  { code: 'fr', name: 'Français', flag: '🇫🇷' },
  { code: 'en', name: 'English', flag: '🇬🇧' },
  { code: 'de', name: 'Deutsch', flag: '🇩🇪' },
  { code: 'es', name: 'Español', flag: '🇪🇸' },
  { code: 'it', name: 'Italiano', flag: '🇮🇹' },
];

interface NavigationItem {
  labelKey: string;
  href: string;
  icon: React.FC<any>;
  badge?: number;
}

const navigation: NavigationItem[] = [
  { labelKey: 'nav.dashboard', href: '/', icon: Home },
  { labelKey: 'nav.services', href: '/services', icon: Server },
  { labelKey: 'nav.users', href: '/users', icon: Users },
  { labelKey: 'nav.mcp', href: '/mcp', icon: Bot },
  { labelKey: 'nav.training', href: '/training', icon: Brain },
  { labelKey: 'nav.monitoring', href: '/monitoring', icon: Activity },
  { labelKey: 'nav.configuration', href: '/configuration', icon: Settings },
];

interface LayoutProps {
  children: React.ReactNode;
}

interface AlertStats {
  active_count: number;
  total_triggered: number;
  by_severity: Record<string, number>;
}

interface ActiveAlert {
  id: string;
  alert_name: string;
  severity: string;
  triggered_at: string;
  message: string;
  acknowledged: boolean;
}

const severityColors: Record<string, string> = {
  low: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
  medium: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300',
  high: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300',
  critical: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300',
};

export default function Layout({ children }: LayoutProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [langMenuOpen, setLangMenuOpen] = useState(false);
  const [alertMenuOpen, setAlertMenuOpen] = useState(false);
  const [alertStats, setAlertStats] = useState<AlertStats | null>(null);
  const [activeAlerts, setActiveAlerts] = useState<ActiveAlert[]>([]);
  const [loadingAlerts, setLoadingAlerts] = useState(false);
  const langMenuRef = useRef<HTMLDivElement>(null);
  const alertMenuRef = useRef<HTMLDivElement>(null);
  const { theme, resolvedTheme, setTheme } = useTheme();
  const { t: tCommon, i18n } = useTranslation('common');
  const { t: tMonitoring } = useTranslation('monitoring');
  const navigate = useNavigate();

  const currentLanguage = languages.find(l => l.code === i18n.language) || languages[0];

  // Fetch active alerts count and list
  const fetchAlertData = useCallback(async () => {
    try {
      const [stats, alerts] = await Promise.all([
        api.alerts.stats(24),
        api.alerts.history.active(),
      ]);
      setAlertStats(stats);
      setActiveAlerts(alerts);
    } catch (error) {
      console.error('Failed to fetch alert data:', error);
    }
  }, []);

  // Fetch alerts on mount and periodically (every 10 seconds for real-time updates)
  useEffect(() => {
    fetchAlertData();
    const interval = setInterval(fetchAlertData, 10000); // Every 10 seconds

    // Also refresh when user returns to the tab
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        fetchAlertData();
      }
    };
    document.addEventListener('visibilitychange', handleVisibilityChange);

    return () => {
      clearInterval(interval);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [fetchAlertData]);

  const toggleTheme = () => {
    if (theme === 'system') {
      setTheme(resolvedTheme === 'dark' ? 'light' : 'dark');
    } else {
      setTheme(theme === 'dark' ? 'light' : 'dark');
    }
  };

  const changeLanguage = (langCode: string) => {
    i18n.changeLanguage(langCode);
    setLangMenuOpen(false);
  };

  // Close menus when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (langMenuRef.current && !langMenuRef.current.contains(event.target as Node)) {
        setLangMenuOpen(false);
      }
      if (alertMenuRef.current && !alertMenuRef.current.contains(event.target as Node)) {
        setAlertMenuOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Handle resolve alert (same action in dropdown and AlertManager)
  const handleResolveAlert = async (alertId: string, event: React.MouseEvent) => {
    event.stopPropagation();
    setLoadingAlerts(true);
    try {
      await api.alerts.history.resolve(alertId);
      await fetchAlertData();
    } catch (error) {
      console.error('Failed to resolve alert:', error);
    } finally {
      setLoadingAlerts(false);
    }
  };

  // Handle resolve all alerts
  const handleResolveAll = async (event: React.MouseEvent) => {
    event.stopPropagation();
    setLoadingAlerts(true);
    try {
      // Resolve all active alerts one by one
      for (const alert of activeAlerts) {
        await api.alerts.history.resolve(alert.id);
      }
      await fetchAlertData();
    } catch (error) {
      console.error('Failed to resolve all alerts:', error);
    } finally {
      setLoadingAlerts(false);
    }
  };

  // Format relative time
  const formatRelativeTime = (timestamp: string) => {
    const now = new Date();
    const date = new Date(timestamp);
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffMins < 1) return tCommon('time.justNow');
    if (diffMins < 60) return tCommon('time.minutesAgo', { count: diffMins });
    if (diffHours < 24) return tCommon('time.hoursAgo', { count: diffHours });
    return tCommon('time.daysAgo', { count: diffDays });
  };

  // Calculate alert badge color based on severity
  const getAlertBadgeColor = () => {
    if (!alertStats || alertStats.active_count === 0) return null;
    const { by_severity } = alertStats;
    if (by_severity?.critical > 0) return 'bg-red-500';
    if (by_severity?.high > 0) return 'bg-orange-500';
    if (by_severity?.medium > 0) return 'bg-yellow-500';
    return 'bg-blue-500';
  };

  const alertBadgeColor = getAlertBadgeColor();

  return (
    <div className="h-screen flex bg-gray-50 dark:bg-gray-900">
      {/* Mobile sidebar backdrop */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 md:hidden"
          onClick={() => setSidebarOpen(false)}
        >
          <div className="fixed inset-0 bg-gray-600 bg-opacity-75" />
        </div>
      )}

      {/* Sidebar */}
      <div
        className={`fixed inset-y-0 left-0 z-50 w-64 bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 transform ${
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        } transition-transform duration-200 ease-in-out md:translate-x-0 md:static md:flex md:flex-col`}
      >
        {/* Sidebar header - height matches main header */}
        <div className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 px-6 h-[57px] flex items-center flex-shrink-0">
          <div className="flex items-center justify-between w-full">
            <div className="flex items-center space-x-2">
              <Zap className="h-7 w-7 text-primary-600" />
              <h1 className="text-xl font-bold text-gray-900 dark:text-white">
                MCParr
              </h1>
            </div>
            <button
              type="button"
              className="md:hidden p-1 rounded-md text-gray-400 hover:text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700"
              onClick={() => setSidebarOpen(false)}
            >
              <X className="h-6 w-6" />
            </button>
          </div>
        </div>

        {/* Sidebar content */}
        <div className="flex-1 flex flex-col overflow-y-auto">
          {/* Navigation */}
          <nav className="flex-1 px-3 pt-4 pb-4">
            <div className="space-y-1">
              {navigation.map((item) => (
                <NavLink
                  key={item.labelKey}
                  to={item.href}
                  className={({ isActive }) =>
                    `nav-link ${isActive ? 'nav-link-active' : 'nav-link-inactive'}`
                  }
                  onClick={() => setSidebarOpen(false)}
                >
                  <item.icon className="mr-3 h-5 w-5 flex-shrink-0" />
                  {tCommon(item.labelKey)}
                  {item.badge && (
                    <span className="ml-auto bg-primary-100 text-primary-600 py-0.5 px-2.5 text-xs rounded-full">
                      {item.badge}
                    </span>
                  )}
                </NavLink>
              ))}
            </div>
          </nav>
        </div>
      </div>

      {/* Main content area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top navigation - height matches sidebar header */}
        <header className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 px-4 md:px-6 h-[57px] flex items-center flex-shrink-0">
          <div className="flex items-center justify-end w-full">
            {/* Mobile menu button */}
            <button
              type="button"
              className="md:hidden p-1 rounded-md text-gray-400 hover:text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700 mr-auto"
              onClick={() => setSidebarOpen(true)}
            >
              <Menu className="h-6 w-6" />
            </button>

            <div className="flex items-center space-x-3">
              {/* Alert indicator with dropdown */}
              <div className="relative" ref={alertMenuRef}>
                <button
                  onClick={() => setAlertMenuOpen(!alertMenuOpen)}
                  className={`relative p-2 rounded-lg transition-colors ${
                    alertBadgeColor
                      ? 'text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700'
                      : 'text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700'
                  }`}
                  title={alertStats?.active_count ? `${alertStats.active_count} ${tCommon('alerts.activeAlerts')}` : tCommon('alerts.noActiveAlerts')}
                >
                  <Bell className={`h-5 w-5 ${alertBadgeColor ? 'animate-pulse' : ''}`} />
                  {alertStats && alertStats.active_count > 0 && (
                    <span className={`absolute -top-0.5 -right-0.5 flex items-center justify-center min-w-[18px] h-[18px] px-1 text-[10px] font-bold text-white rounded-full ${alertBadgeColor}`}>
                      {alertStats.active_count > 99 ? '99+' : alertStats.active_count}
                    </span>
                  )}
                </button>

                {/* Alert dropdown menu */}
                {alertMenuOpen && (
                  <div className="absolute right-0 mt-2 w-80 sm:w-96 bg-white dark:bg-gray-800 rounded-lg shadow-xl border border-gray-200 dark:border-gray-700 z-50 overflow-hidden">
                    {/* Header */}
                    <div className="px-4 py-3 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 flex items-center justify-between">
                      <h3 className="font-medium text-gray-900 dark:text-white flex items-center gap-2">
                        <AlertTriangle className="w-4 h-4 text-orange-500" />
                        {tCommon('alerts.title')}
                        {alertStats && alertStats.active_count > 0 && (
                          <span className="text-xs bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300 px-2 py-0.5 rounded-full">
                            {alertStats.active_count}
                          </span>
                        )}
                      </h3>
                      {activeAlerts.length > 0 && (
                        <button
                          onClick={handleResolveAll}
                          disabled={loadingAlerts}
                          className="text-xs text-green-600 dark:text-green-400 hover:underline disabled:opacity-50"
                        >
                          {tMonitoring('alerts.resolveAll')}
                        </button>
                      )}
                    </div>

                    {/* Alert list */}
                    <div className="max-h-80 overflow-y-auto">
                      {activeAlerts.length === 0 ? (
                        <div className="p-6 text-center text-gray-500 dark:text-gray-400">
                          <CheckCircle className="w-10 h-10 mx-auto mb-2 text-green-500" />
                          <p className="text-sm">{tMonitoring('alerts.noActive')}</p>
                        </div>
                      ) : (
                        <ul className="divide-y divide-gray-100 dark:divide-gray-700">
                          {activeAlerts.slice(0, 5).map(alert => (
                            <li key={alert.id} className="p-3 hover:bg-gray-50 dark:hover:bg-gray-700/50">
                              <div className="flex items-start gap-3">
                                <span className={`inline-flex px-2 py-0.5 text-xs font-medium rounded shrink-0 ${severityColors[alert.severity]}`}>
                                  {tMonitoring(`alerts.severity.${alert.severity}`)}
                                </span>
                                <div className="flex-1 min-w-0">
                                  <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
                                    {alert.alert_name}
                                  </p>
                                  <p className="text-xs text-gray-500 dark:text-gray-400 truncate">
                                    {alert.message}
                                  </p>
                                  <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">
                                    {formatRelativeTime(alert.triggered_at)}
                                  </p>
                                </div>
                                <button
                                  onClick={(e) => handleResolveAlert(alert.id, e)}
                                  disabled={loadingAlerts}
                                  className="p-1.5 text-green-600 hover:bg-green-50 dark:hover:bg-green-900/20 rounded transition-colors disabled:opacity-50"
                                  title={tMonitoring('alerts.resolve')}
                                >
                                  <CheckCircle className="w-4 h-4" />
                                </button>
                              </div>
                            </li>
                          ))}
                        </ul>
                      )}
                    </div>

                    {/* Footer with link to full alerts page */}
                    <div className="px-4 py-3 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900">
                      <button
                        onClick={() => {
                          setAlertMenuOpen(false);
                          navigate('/monitoring?tab=alerts');
                        }}
                        className="w-full flex items-center justify-center gap-2 text-sm text-blue-600 dark:text-blue-400 hover:underline"
                      >
                        {tCommon('alerts.viewAll')}
                        <ExternalLink className="w-3 h-3" />
                      </button>
                    </div>
                  </div>
                )}
              </div>

              {/* Theme toggle */}
              <button
                onClick={toggleTheme}
                className="p-2 rounded-lg text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                title={`Theme: ${theme}`}
              >
                {resolvedTheme === 'dark' ? (
                  <Sun className="h-5 w-5" />
                ) : (
                  <Moon className="h-5 w-5" />
                )}
              </button>

              {/* Language selector */}
              <div className="relative" ref={langMenuRef}>
                <button
                  onClick={() => setLangMenuOpen(!langMenuOpen)}
                  className="flex items-center space-x-1 px-2 py-1.5 rounded-lg text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                  title={currentLanguage.name}
                >
                  <span className="text-lg" style={{ fontFamily: 'Apple Color Emoji, Segoe UI Emoji, Noto Color Emoji, sans-serif' }}>{currentLanguage.flag}</span>
                  <ChevronDown className={`h-4 w-4 transition-transform ${langMenuOpen ? 'rotate-180' : ''}`} />
                </button>

                {/* Dropdown menu */}
                {langMenuOpen && (
                  <div className="absolute right-0 mt-2 w-40 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 py-1 z-50">
                    {languages.map((lang) => (
                      <button
                        key={lang.code}
                        onClick={() => changeLanguage(lang.code)}
                        className={`w-full flex items-center space-x-2 px-3 py-2 text-sm hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors ${
                          lang.code === i18n.language
                            ? 'bg-primary-50 dark:bg-primary-900/20 text-primary-600 dark:text-primary-400'
                            : 'text-gray-700 dark:text-gray-300'
                        }`}
                      >
                        <span className="text-lg" style={{ fontFamily: 'Apple Color Emoji, Segoe UI Emoji, Noto Color Emoji, sans-serif' }}>{lang.flag}</span>
                        <span>{lang.name}</span>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 p-4 md:p-6 overflow-y-auto bg-gray-50 dark:bg-gray-900">
          {children}
        </main>
      </div>
    </div>
  );
}