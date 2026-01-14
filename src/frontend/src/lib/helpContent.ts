/**
 * Centralized help content configuration.
 * This file defines all help sections used throughout the application.
 * Each help topic can be displayed in HelpTooltip components or on the Help page.
 */

export interface HelpSection {
  titleKey: string;
  contentKey: string;
}

export interface HelpTopic {
  id: string;
  titleKey: string;
  descriptionKey?: string;
  icon?: string;
  sections: HelpSection[];
}

export interface HelpCategory {
  id: string;
  titleKey: string;
  icon: string;
  topics: HelpTopic[];
}

/**
 * All help topics organized by category.
 * Keys reference i18n translation keys in mcp.json
 */
export const helpCategories: HelpCategory[] = [
  {
    id: 'mcp',
    titleKey: 'help.categories.mcp',
    icon: 'Bot',
    topics: [
      {
        id: 'tools',
        titleKey: 'tools.help.title',
        descriptionKey: 'tools.help.overviewContent',
        icon: 'Wrench',
        sections: [
          { titleKey: 'tools.help.overview', contentKey: 'tools.help.overviewContent' },
          { titleKey: 'tools.help.browse', contentKey: 'tools.help.browseContent' },
          { titleKey: 'tools.help.test', contentKey: 'tools.help.testContent' },
          { titleKey: 'tools.help.groups', contentKey: 'tools.help.groupsContent' },
          { titleKey: 'tools.help.mutations', contentKey: 'tools.help.mutationsContent' },
        ],
      },
      {
        id: 'history',
        titleKey: 'history.help.title',
        descriptionKey: 'history.help.overviewContent',
        icon: 'History',
        sections: [
          { titleKey: 'history.help.overview', contentKey: 'history.help.overviewContent' },
          { titleKey: 'history.help.filters', contentKey: 'history.help.filtersContent' },
          { titleKey: 'history.help.details', contentKey: 'history.help.detailsContent' },
          { titleKey: 'history.help.chains', contentKey: 'history.help.chainsContent' },
        ],
      },
      {
        id: 'toolChains',
        titleKey: 'toolChains.detail.help.title',
        descriptionKey: 'toolChains.detail.help.overviewContent',
        icon: 'Link2',
        sections: [
          { titleKey: 'toolChains.detail.help.overview', contentKey: 'toolChains.detail.help.overviewContent' },
          { titleKey: 'toolChains.detail.help.steps', contentKey: 'toolChains.detail.help.stepsContent' },
          { titleKey: 'toolChains.detail.help.conditions', contentKey: 'toolChains.detail.help.conditionsContent' },
          { titleKey: 'toolChains.detail.help.actions', contentKey: 'toolChains.detail.help.actionsContent' },
          { titleKey: 'toolChains.detail.help.mappings', contentKey: 'toolChains.detail.help.mappingsContent' },
          { titleKey: 'toolChains.detail.help.context', contentKey: 'toolChains.detail.help.contextContent' },
        ],
      },
    ],
  },
];

/**
 * Get a specific help topic by its ID.
 */
export function getHelpTopic(topicId: string): HelpTopic | undefined {
  for (const category of helpCategories) {
    const topic = category.topics.find((t) => t.id === topicId);
    if (topic) return topic;
  }
  return undefined;
}

/**
 * Get sections for a specific help topic (for use in HelpTooltip).
 */
export function getHelpSections(topicId: string): HelpSection[] {
  const topic = getHelpTopic(topicId);
  return topic?.sections || [];
}
