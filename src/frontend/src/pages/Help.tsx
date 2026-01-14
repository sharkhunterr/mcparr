import { useState, useMemo } from 'react';
import {
  HelpCircle,
  Search,
  ChevronRight,
  ArrowLeft,
  Bot,
  Wrench,
  History,
  Link2,
  BookOpen,
  ExternalLink,
  Server,
  Layers,
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { helpCategories, type HelpTopic } from '../lib/helpContent';

// Icon mapping for dynamic rendering
const iconMap: Record<string, React.ElementType> = {
  Bot,
  Wrench,
  History,
  Link2,
  HelpCircle,
  BookOpen,
  Server,
  Layers,
};

// Color mapping for topics
const topicColors: Record<string, { bg: string; text: string; border: string; iconBg: string }> = {
  services: {
    bg: 'bg-orange-50 dark:bg-orange-900/20',
    text: 'text-orange-700 dark:text-orange-300',
    border: 'border-orange-200 dark:border-orange-800',
    iconBg: 'bg-orange-100 dark:bg-orange-900/40',
  },
  serviceGroups: {
    bg: 'bg-teal-50 dark:bg-teal-900/20',
    text: 'text-teal-700 dark:text-teal-300',
    border: 'border-teal-200 dark:border-teal-800',
    iconBg: 'bg-teal-100 dark:bg-teal-900/40',
  },
  tools: {
    bg: 'bg-blue-50 dark:bg-blue-900/20',
    text: 'text-blue-700 dark:text-blue-300',
    border: 'border-blue-200 dark:border-blue-800',
    iconBg: 'bg-blue-100 dark:bg-blue-900/40',
  },
  history: {
    bg: 'bg-amber-50 dark:bg-amber-900/20',
    text: 'text-amber-700 dark:text-amber-300',
    border: 'border-amber-200 dark:border-amber-800',
    iconBg: 'bg-amber-100 dark:bg-amber-900/40',
  },
  toolChains: {
    bg: 'bg-purple-50 dark:bg-purple-900/20',
    text: 'text-purple-700 dark:text-purple-300',
    border: 'border-purple-200 dark:border-purple-800',
    iconBg: 'bg-purple-100 dark:bg-purple-900/40',
  },
};

const defaultColors = {
  bg: 'bg-gray-50 dark:bg-gray-800',
  text: 'text-gray-700 dark:text-gray-300',
  border: 'border-gray-200 dark:border-gray-700',
  iconBg: 'bg-gray-100 dark:bg-gray-700',
};

const Help = () => {
  // Support multiple namespaces for translations (mcp and services)
  const { t } = useTranslation(['mcp', 'services']);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedTopic, setSelectedTopic] = useState<HelpTopic | null>(null);

  // Flatten all topics for grid display
  const allTopics = useMemo(() => {
    return helpCategories.flatMap((cat) => cat.topics);
  }, []);

  // Filter topics based on search
  const filteredTopics = useMemo(() => {
    if (!searchTerm.trim()) return allTopics;

    const lowerSearch = searchTerm.toLowerCase();
    return allTopics.filter((topic) => {
      const title = t(topic.titleKey).toLowerCase();
      const description = topic.descriptionKey ? t(topic.descriptionKey).toLowerCase() : '';
      const sectionsText = topic.sections
        .map((s) => `${t(s.titleKey)} ${t(s.contentKey)}`)
        .join(' ')
        .toLowerCase();
      return (
        title.includes(lowerSearch) ||
        description.includes(lowerSearch) ||
        sectionsText.includes(lowerSearch)
      );
    });
  }, [searchTerm, t, allTopics]);

  const getIcon = (iconName?: string) => {
    if (!iconName) return HelpCircle;
    return iconMap[iconName] || HelpCircle;
  };

  const getTopicColors = (topicId: string) => {
    return topicColors[topicId] || defaultColors;
  };

  // Render topic detail view
  if (selectedTopic) {
    const TopicIcon = getIcon(selectedTopic.icon);
    const colors = getTopicColors(selectedTopic.id);

    return (
      <div className="p-4 sm:p-6 space-y-4 sm:space-y-6">
        {/* Back button */}
        <button
          onClick={() => setSelectedTopic(null)}
          className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          {t('help.backToList')}
        </button>

        {/* Topic header - same style as site */}
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <TopicIcon className={`w-6 h-6 sm:w-8 sm:h-8 ${colors.text}`} />
            {t(selectedTopic.titleKey)}
          </h1>
          {selectedTopic.descriptionKey && (
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
              {t(selectedTopic.descriptionKey)}
            </p>
          )}
        </div>

        {/* Sections as cards */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {selectedTopic.sections.map((section, index) => (
            <div
              key={index}
              className="bg-white dark:bg-gray-800 rounded-lg shadow p-4 sm:p-5"
            >
              <h2 className="flex items-center gap-2 font-semibold text-gray-900 dark:text-white mb-3">
                <span className={`w-1.5 h-1.5 rounded-full ${colors.text.replace('text-', 'bg-')}`} />
                {t(section.titleKey)}
              </h2>
              <div className="text-sm text-gray-600 dark:text-gray-400 whitespace-pre-line leading-relaxed">
                {t(section.contentKey)}
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  // Render topics list
  return (
    <div className="p-4 sm:p-6 space-y-4 sm:space-y-6">
      {/* Header - same style as other pages */}
      <div>
        <h1 className="text-xl sm:text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
          <HelpCircle className="w-6 h-6 sm:w-8 sm:h-8 text-purple-600" />
          {t('help.pageTitle')}
        </h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          {t('help.pageSubtitle')}
        </p>
      </div>

      {/* Search bar */}
      <div className="relative max-w-md">
        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
        <input
          type="text"
          placeholder={t('help.searchPlaceholder')}
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="w-full pl-10 pr-4 py-2 text-sm border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
        />
      </div>

      {/* Topics grid */}
      {filteredTopics.length > 0 ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredTopics.map((topic) => {
            const TopicIcon = getIcon(topic.icon);
            const colors = getTopicColors(topic.id);

            return (
              <button
                key={topic.id}
                onClick={() => setSelectedTopic(topic)}
                className={`group text-left rounded-lg border ${colors.border} ${colors.bg} p-4 hover:shadow-md transition-all duration-200`}
              >
                <div className="flex items-start gap-3">
                  <div className={`p-2.5 rounded-lg ${colors.iconBg} flex-shrink-0`}>
                    <TopicIcon className={`w-5 h-5 ${colors.text}`} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <h3 className="font-semibold text-gray-900 dark:text-white mb-1 flex items-center gap-1">
                      {t(topic.titleKey)}
                      <ChevronRight className="w-4 h-4 text-gray-400 opacity-0 group-hover:opacity-100 transition-opacity" />
                    </h3>
                    {topic.descriptionKey && (
                      <p className="text-xs text-gray-500 dark:text-gray-400 line-clamp-2">
                        {t(topic.descriptionKey)}
                      </p>
                    )}
                    <div className="mt-2 flex items-center gap-1 text-xs text-gray-400 dark:text-gray-500">
                      <BookOpen className="w-3 h-3" />
                      <span>{topic.sections.length} sections</span>
                    </div>
                  </div>
                </div>
              </button>
            );
          })}
        </div>
      ) : (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-12 text-center">
          <Search className="w-12 h-12 mx-auto mb-3 text-gray-300 dark:text-gray-600" />
          <p className="text-gray-500 dark:text-gray-400">{t('help.noResults')}</p>
          <p className="text-sm text-gray-400 dark:text-gray-500 mt-1">
            {searchTerm && `"${searchTerm}"`}
          </p>
        </div>
      )}

      {/* Quick links footer */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4 mt-6">
        <div className="flex flex-wrap items-center gap-4 text-sm">
          <span className="text-gray-500 dark:text-gray-400">Liens rapides :</span>
          <a
            href="/mcp"
            className="flex items-center gap-1 text-purple-600 dark:text-purple-400 hover:underline"
          >
            <Bot className="w-4 h-4" />
            MCP Gateway
            <ExternalLink className="w-3 h-3" />
          </a>
          <a
            href="/mcp"
            onClick={() => {
              // This would need proper state management to work
            }}
            className="flex items-center gap-1 text-purple-600 dark:text-purple-400 hover:underline"
          >
            <Link2 className="w-4 h-4" />
            Chaînes d'outils
            <ExternalLink className="w-3 h-3" />
          </a>
        </div>
      </div>
    </div>
  );
};

export default Help;
