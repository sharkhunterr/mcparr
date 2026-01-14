import { useState, useMemo } from 'react';
import {
  HelpCircle,
  Search,
  ChevronRight,
  Bot,
  Wrench,
  History,
  Link2,
  BookOpen,
  Server,
  Layers,
  RefreshCw,
  X,
  User,
  Users,
  Shield,
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
  User,
  Users,
  Shield,
  Search,
};

// Color mapping for topics
const topicColors: Record<string, { bg: string; text: string; border: string; iconBg: string }> = {
  // Users category - green
  userDetector: {
    bg: 'bg-green-50 dark:bg-green-900/20',
    text: 'text-green-700 dark:text-green-300',
    border: 'border-green-200 dark:border-green-800',
    iconBg: 'bg-green-100 dark:bg-green-900/40',
  },
  userManualMapping: {
    bg: 'bg-green-50 dark:bg-green-900/20',
    text: 'text-green-700 dark:text-green-300',
    border: 'border-green-200 dark:border-green-800',
    iconBg: 'bg-green-100 dark:bg-green-900/40',
  },
  userMappingList: {
    bg: 'bg-green-50 dark:bg-green-900/20',
    text: 'text-green-700 dark:text-green-300',
    border: 'border-green-200 dark:border-green-800',
    iconBg: 'bg-green-100 dark:bg-green-900/40',
  },
  groups: {
    bg: 'bg-green-50 dark:bg-green-900/20',
    text: 'text-green-700 dark:text-green-300',
    border: 'border-green-200 dark:border-green-800',
    iconBg: 'bg-green-100 dark:bg-green-900/40',
  },
  // Services category - orange
  services: {
    bg: 'bg-orange-50 dark:bg-orange-900/20',
    text: 'text-orange-700 dark:text-orange-300',
    border: 'border-orange-200 dark:border-orange-800',
    iconBg: 'bg-orange-100 dark:bg-orange-900/40',
  },
  serviceGroups: {
    bg: 'bg-orange-50 dark:bg-orange-900/20',
    text: 'text-orange-700 dark:text-orange-300',
    border: 'border-orange-200 dark:border-orange-800',
    iconBg: 'bg-orange-100 dark:bg-orange-900/40',
  },
  // MCP category - green (MCP color)
  tools: {
    bg: 'bg-emerald-50 dark:bg-emerald-900/20',
    text: 'text-emerald-700 dark:text-emerald-300',
    border: 'border-emerald-200 dark:border-emerald-800',
    iconBg: 'bg-emerald-100 dark:bg-emerald-900/40',
  },
  history: {
    bg: 'bg-emerald-50 dark:bg-emerald-900/20',
    text: 'text-emerald-700 dark:text-emerald-300',
    border: 'border-emerald-200 dark:border-emerald-800',
    iconBg: 'bg-emerald-100 dark:bg-emerald-900/40',
  },
  toolChains: {
    bg: 'bg-emerald-50 dark:bg-emerald-900/20',
    text: 'text-emerald-700 dark:text-emerald-300',
    border: 'border-emerald-200 dark:border-emerald-800',
    iconBg: 'bg-emerald-100 dark:bg-emerald-900/40',
  },
};

const defaultColors = {
  bg: 'bg-gray-50 dark:bg-gray-800',
  text: 'text-gray-700 dark:text-gray-300',
  border: 'border-gray-200 dark:border-gray-700',
  iconBg: 'bg-gray-100 dark:bg-gray-700',
};

const Help = () => {
  // Support multiple namespaces for translations (mcp, services, users, and groups)
  const { t } = useTranslation(['mcp', 'services', 'users', 'groups']);
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

  // Render topic detail content
  const renderTopicDetail = () => {
    if (!selectedTopic) {
      return (
        <div className="h-full flex flex-col items-center justify-center text-gray-400 dark:text-gray-500">
          <HelpCircle className="w-16 h-16 mb-4 opacity-50" />
          <p className="text-lg font-medium">{t('help.selectTopic')}</p>
          <p className="text-sm mt-2 max-w-md text-center">
            {t('help.selectTopicDescription')}
          </p>
        </div>
      );
    }

    const TopicIcon = getIcon(selectedTopic.icon);
    const colors = getTopicColors(selectedTopic.id);

    return (
      <div className="h-full flex flex-col overflow-hidden">
        {/* Topic header */}
        <div className="p-4 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-3">
            <div className={`p-2.5 rounded-lg ${colors.iconBg} flex-shrink-0`}>
              <TopicIcon className={`w-6 h-6 ${colors.text}`} />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                {t(selectedTopic.titleKey)}
              </h2>
              {selectedTopic.descriptionKey && (
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  {t(selectedTopic.descriptionKey)}
                </p>
              )}
            </div>
          </div>
        </div>

        {/* Sections */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {selectedTopic.sections.map((section, index) => (
            <div
              key={index}
              className="bg-gray-50 dark:bg-gray-900/50 rounded-lg p-4"
            >
              <h3 className="flex items-center gap-2 font-medium text-gray-900 dark:text-white mb-2">
                <span className={`w-1.5 h-1.5 rounded-full ${colors.text.replace('text-', 'bg-')}`} />
                {t(section.titleKey)}
              </h3>
              <div className="text-sm text-gray-600 dark:text-gray-400 whitespace-pre-line leading-relaxed">
                {t(section.contentKey)}
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  };

  // Render topics list
  const renderTopicsList = () => {
    return (
      <div className="h-full flex flex-col">
        {/* Header */}
        <div className="p-4 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center space-x-2">
              <BookOpen className="w-5 h-5 text-purple-600" />
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">{t('help.knowledgeBase')}</h2>
            </div>
            <div className="flex items-center space-x-2">
              <button
                onClick={() => setSearchTerm('')}
                className="p-2 text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                title={t('help.refresh')}
              >
                <RefreshCw className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Search */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
            <input
              type="text"
              placeholder={t('help.searchPlaceholder')}
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-9 pr-3 py-2 text-sm border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
            />
          </div>

          {/* Count */}
          <div className="flex items-center justify-between mt-3">
            <span className="text-xs text-gray-500 dark:text-gray-400">
              {filteredTopics.length} {t('help.topics')}
            </span>
          </div>
        </div>

        {/* Topic List */}
        <div className="flex-1 overflow-y-auto p-4 space-y-2">
          {filteredTopics.map((topic) => {
            const TopicIcon = getIcon(topic.icon);
            const colors = getTopicColors(topic.id);
            const isSelected = selectedTopic?.id === topic.id;

            return (
              <div
                key={topic.id}
                onClick={() => setSelectedTopic(topic)}
                className={`p-3 rounded-lg border cursor-pointer transition-all ${
                  isSelected
                    ? 'border-purple-500 bg-purple-50 dark:bg-purple-900/20'
                    : `${colors.border} hover:border-gray-300 dark:hover:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-800`
                }`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-start space-x-3 min-w-0">
                    {/* Color indicator */}
                    <div className={`p-2 rounded-lg ${colors.iconBg} flex-shrink-0`}>
                      <TopicIcon className={`w-4 h-4 ${colors.text}`} />
                    </div>
                    <div className="min-w-0">
                      <h3 className="font-medium text-gray-900 dark:text-white truncate">
                        {t(topic.titleKey)}
                      </h3>
                      {topic.descriptionKey && (
                        <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5 line-clamp-2">
                          {t(topic.descriptionKey)}
                        </p>
                      )}
                      <div className="flex items-center space-x-3 mt-2 text-xs text-gray-500 dark:text-gray-400">
                        <span className="flex items-center">
                          <BookOpen className="w-3 h-3 mr-1" />
                          {topic.sections.length} sections
                        </span>
                      </div>
                    </div>
                  </div>
                  <ChevronRight className="w-4 h-4 text-gray-400 flex-shrink-0" />
                </div>
              </div>
            );
          })}

          {filteredTopics.length === 0 && (
            <div className="text-center py-8">
              <Search className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-3" />
              <p className="text-sm text-gray-500 dark:text-gray-400">
                {t('help.noResults')}
              </p>
              {searchTerm && (
                <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">
                  "{searchTerm}"
                </p>
              )}
            </div>
          )}
        </div>
      </div>
    );
  };

  return (
    <div className="p-4 sm:p-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <HelpCircle className="w-6 h-6 sm:w-8 sm:h-8 text-purple-600" />
            {t('help.pageTitle')}
          </h1>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
            {t('help.pageSubtitle')}
          </p>
        </div>
      </div>

      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 overflow-hidden">
        {/* Desktop Layout: Side by Side - calc accounts for header, padding, and page title */}
        <div className="hidden md:flex h-[calc(100vh-220px)] min-h-[400px]">
          {/* Left sidebar - Topic List */}
          <div className="w-1/2 lg:w-2/5 border-r border-gray-200 dark:border-gray-700 flex-shrink-0">
            {renderTopicsList()}
          </div>

          {/* Right content - Topic Detail */}
          <div className="w-1/2 lg:w-3/5 min-w-0">
            {renderTopicDetail()}
          </div>
        </div>

        {/* Mobile Layout: Full width list, detail as modal */}
        <div className="md:hidden">
          {/* Topic List - Full Width - calc accounts for header and padding */}
          <div className="h-[calc(100vh-200px)] min-h-[300px]">
            {renderTopicsList()}
          </div>

          {/* Mobile Detail Modal - Slide up from bottom */}
          {selectedTopic && (
            <div className="fixed inset-0 z-50 md:hidden">
              {/* Backdrop */}
              <div
                className="absolute inset-0 bg-black/50"
                onClick={() => setSelectedTopic(null)}
              />

              {/* Modal Content - Full screen with rounded top */}
              <div className="absolute inset-x-0 bottom-0 top-12 bg-white dark:bg-gray-800 rounded-t-2xl shadow-xl flex flex-col animate-in slide-in-from-bottom duration-300">
                {/* Header with drag handle and close button */}
                <div className="flex items-center justify-between px-4 pt-3 pb-1">
                  <div className="w-8" /> {/* Spacer for centering */}
                  <div className="w-10 h-1 bg-gray-300 dark:bg-gray-600 rounded-full" />
                  <button
                    onClick={() => setSelectedTopic(null)}
                    className="w-8 h-8 flex items-center justify-center text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-full transition-colors"
                  >
                    <X className="w-5 h-5" />
                  </button>
                </div>

                {/* Content */}
                <div className="flex-1 overflow-hidden">
                  {renderTopicDetail()}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Help;
