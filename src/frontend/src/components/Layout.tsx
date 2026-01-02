import React, { useState } from 'react';
import { NavLink } from 'react-router-dom';
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
} from 'lucide-react';
import { useTheme } from '../contexts/ThemeContext';

interface NavigationItem {
  labelKey: string;
  href: string;
  icon: React.FC<any>;
  badge?: number;
}

const getNavigation = (t: (key: string) => string): NavigationItem[] => [
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

export default function Layout({ children }: LayoutProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const { theme, resolvedTheme, setTheme } = useTheme();
  const { t: tCommon } = useTranslation('common');
  const navigation = getNavigation(tCommon);

  const toggleTheme = () => {
    if (theme === 'system') {
      setTheme(resolvedTheme === 'dark' ? 'light' : 'dark');
    } else {
      setTheme(theme === 'dark' ? 'light' : 'dark');
    }
  };

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
          <div className="flex items-center justify-between w-full">
            <div className="flex items-center">
              <button
                type="button"
                className="md:hidden p-1 rounded-md text-gray-400 hover:text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700 mr-3"
                onClick={() => setSidebarOpen(true)}
              >
                <Menu className="h-6 w-6" />
              </button>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                Dashboard
              </h2>
            </div>

            <div className="flex items-center space-x-3">
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

              {/* User menu placeholder */}
              <div className="flex items-center">
                <div className="h-8 w-8 bg-gray-200 dark:bg-gray-700 rounded-full flex items-center justify-center">
                  <span className="text-xs font-medium text-gray-600 dark:text-gray-300">A</span>
                </div>
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