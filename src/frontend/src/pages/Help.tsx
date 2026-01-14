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
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { helpCategories, type HelpTopic, type HelpCategory } from '../lib/helpContent';

// Icon mapping for dynamic rendering
const iconMap: Record<string, React.ElementType> = {
  Bot,
  Wrench,
  History,
  Link2,
  HelpCircle,
};

const Help = () => {
  const { t } = useTranslation('mcp');
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedTopic, setSelectedTopic] = useState<HelpTopic | null>(null);
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(
    new Set(helpCategories.map((c) => c.id))
  );

  // Filter topics based on search
  const filteredCategories = useMemo(() => {
    if (!searchTerm.trim()) return helpCategories;

    const lowerSearch = searchTerm.toLowerCase();
    return helpCategories
      .map((category) => ({
        ...category,
        topics: category.topics.filter((topic) => {
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
        }),
      }))
      .filter((category) => category.topics.length > 0);
  }, [searchTerm, t]);

  const toggleCategory = (categoryId: string) => {
    setExpandedCategories((prev) => {
      const next = new Set(prev);
      if (next.has(categoryId)) {
        next.delete(categoryId);
      } else {
        next.add(categoryId);
      }
      return next;
    });
  };

  const getIcon = (iconName?: string) => {
    if (!iconName) return HelpCircle;
    return iconMap[iconName] || HelpCircle;
  };

  // Render topic detail view
  if (selectedTopic) {
    const TopicIcon = getIcon(selectedTopic.icon);
    return (
      <div className="p-4 sm:p-6 max-w-4xl mx-auto">
        {/* Back button */}
        <button
          onClick={() => setSelectedTopic(null)}
          className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white mb-4 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          {t('help.backToList')}
        </button>

        {/* Topic header */}
        <div className="flex items-center gap-3 mb-6">
          <div className="p-3 rounded-xl bg-purple-100 dark:bg-purple-900/30">
            <TopicIcon className="w-6 h-6 text-purple-600 dark:text-purple-400" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            {t(selectedTopic.titleKey)}
          </h1>
        </div>

        {/* Sections */}
        <div className="space-y-6">
          {selectedTopic.sections.map((section, index) => (
            <div
              key={index}
              className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4 sm:p-5"
            >
              <h2 className="flex items-center gap-2 text-lg font-semibold text-gray-900 dark:text-white mb-3">
                <span className="w-2 h-2 rounded-full bg-purple-500" />
                {t(section.titleKey)}
              </h2>
              <div className="text-gray-600 dark:text-gray-400 whitespace-pre-line leading-relaxed">
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
    <div className="p-4 sm:p-6 max-w-4xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center gap-3 mb-2">
          <div className="p-2 rounded-lg bg-purple-100 dark:bg-purple-900/30">
            <HelpCircle className="w-6 h-6 text-purple-600 dark:text-purple-400" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
              {t('help.pageTitle')}
            </h1>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              {t('help.pageSubtitle')}
            </p>
          </div>
        </div>
      </div>

      {/* Search */}
      <div className="relative mb-6">
        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
        <input
          type="text"
          placeholder={t('help.searchPlaceholder')}
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="w-full pl-10 pr-4 py-3 text-sm border border-gray-300 dark:border-gray-600 dark:bg-gray-800 dark:text-white rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
        />
      </div>

      {/* Categories and topics */}
      {filteredCategories.length > 0 ? (
        <div className="space-y-4">
          {filteredCategories.map((category) => {
            const CategoryIcon = getIcon(category.icon);
            const isExpanded = expandedCategories.has(category.id);

            return (
              <div
                key={category.id}
                className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden"
              >
                {/* Category header */}
                <button
                  onClick={() => toggleCategory(category.id)}
                  className="w-full flex items-center justify-between p-4 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <CategoryIcon className="w-5 h-5 text-purple-600 dark:text-purple-400" />
                    <span className="font-medium text-gray-900 dark:text-white">
                      {t(category.titleKey)}
                    </span>
                    <span className="text-xs text-gray-500 dark:text-gray-400 bg-gray-100 dark:bg-gray-700 px-2 py-0.5 rounded-full">
                      {category.topics.length}
                    </span>
                  </div>
                  <ChevronRight
                    className={`w-5 h-5 text-gray-400 transition-transform ${
                      isExpanded ? 'rotate-90' : ''
                    }`}
                  />
                </button>

                {/* Topics list */}
                {isExpanded && (
                  <div className="border-t border-gray-200 dark:border-gray-700">
                    {category.topics.map((topic) => {
                      const TopicIcon = getIcon(topic.icon);
                      return (
                        <button
                          key={topic.id}
                          onClick={() => setSelectedTopic(topic)}
                          className="w-full flex items-start gap-3 p-4 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors border-b border-gray-100 dark:border-gray-700/50 last:border-b-0"
                        >
                          <div className="p-2 rounded-lg bg-gray-100 dark:bg-gray-700 flex-shrink-0">
                            <TopicIcon className="w-4 h-4 text-gray-600 dark:text-gray-400" />
                          </div>
                          <div className="flex-1 text-left min-w-0">
                            <h3 className="font-medium text-gray-900 dark:text-white mb-1">
                              {t(topic.titleKey)}
                            </h3>
                            {topic.descriptionKey && (
                              <p className="text-sm text-gray-500 dark:text-gray-400 line-clamp-2">
                                {t(topic.descriptionKey)}
                              </p>
                            )}
                          </div>
                          <ChevronRight className="w-4 h-4 text-gray-400 flex-shrink-0 mt-2" />
                        </button>
                      );
                    })}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      ) : (
        <div className="text-center py-12 text-gray-500 dark:text-gray-400">
          <HelpCircle className="w-12 h-12 mx-auto mb-3 opacity-50" />
          <p>{t('help.noResults')}</p>
        </div>
      )}
    </div>
  );
};

export default Help;
