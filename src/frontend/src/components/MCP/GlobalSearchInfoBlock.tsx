import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Search, Zap, ArrowRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import { getApiBaseUrl } from '../../lib/api';

interface GlobalSearchSettings {
  enabled: boolean;
  hide_notifications: boolean;
}

interface GlobalSearchInfoBlockProps {
  /** Callback when clicking configure - if provided, uses this instead of Link */
  onConfigure?: () => void;
  /** Custom class for container */
  className?: string;
}

export default function GlobalSearchInfoBlock({ onConfigure, className = '' }: GlobalSearchInfoBlockProps) {
  const { t } = useTranslation('mcp');
  const [settings, setSettings] = useState<GlobalSearchSettings | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchSettings = async () => {
      try {
        const response = await fetch(`${getApiBaseUrl()}/api/global-search/settings`);
        if (response.ok) {
          const data = await response.json();
          setSettings(data);
        }
      } catch (err) {
        console.error('Failed to fetch global search settings:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchSettings();
  }, []);

  // Don't show if loading, or if settings say to hide, or if feature is disabled
  if (loading || !settings || settings.hide_notifications || !settings.enabled) {
    return null;
  }

  const content = (
    <div className={`p-3 bg-gradient-to-r from-teal-50 to-cyan-50 dark:from-teal-900/20 dark:to-cyan-900/20 border border-teal-200 dark:border-teal-800 rounded-lg ${className}`}>
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 sm:gap-3">
        <div className="flex items-center gap-2 sm:gap-3">
          <div className="p-1.5 sm:p-2 bg-teal-100 dark:bg-teal-900/30 rounded-lg flex-shrink-0">
            <Search className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-teal-600 dark:text-teal-400" />
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-1.5 sm:gap-2 flex-wrap">
              <span className="text-xs sm:text-sm font-medium text-gray-900 dark:text-white">
                {t('globalSearch.infoBlock.title')}
              </span>
              <span className="inline-flex items-center gap-0.5 sm:gap-1 px-1.5 py-0.5 rounded-full text-[10px] sm:text-xs font-medium bg-teal-100 text-teal-700 dark:bg-teal-900/30 dark:text-teal-300">
                <Zap className="w-2.5 h-2.5 sm:w-3 sm:h-3" />
                Smart
              </span>
            </div>
            <p className="text-[10px] sm:text-xs text-gray-500 dark:text-gray-400 truncate sm:whitespace-normal">
              {t('globalSearch.infoBlock.description')}
            </p>
          </div>
        </div>
        {onConfigure ? (
          <button
            onClick={onConfigure}
            className="self-end sm:self-auto px-2.5 sm:px-3 py-1 sm:py-1.5 text-[10px] sm:text-xs font-medium text-teal-700 dark:text-teal-300 bg-teal-100 dark:bg-teal-900/30 hover:bg-teal-200 dark:hover:bg-teal-900/50 rounded-lg transition-colors flex items-center gap-1 flex-shrink-0"
          >
            {t('globalSearch.infoBlock.configure')}
            <ArrowRight className="w-2.5 h-2.5 sm:w-3 sm:h-3" />
          </button>
        ) : (
          <Link
            to="/mcp?tab=config"
            className="self-end sm:self-auto px-2.5 sm:px-3 py-1 sm:py-1.5 text-[10px] sm:text-xs font-medium text-teal-700 dark:text-teal-300 bg-teal-100 dark:bg-teal-900/30 hover:bg-teal-200 dark:hover:bg-teal-900/50 rounded-lg transition-colors flex items-center gap-1 flex-shrink-0"
          >
            {t('globalSearch.infoBlock.configure')}
            <ArrowRight className="w-2.5 h-2.5 sm:w-3 sm:h-3" />
          </Link>
        )}
      </div>
    </div>
  );

  return content;
}
