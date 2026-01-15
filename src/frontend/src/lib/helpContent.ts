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
 * Keys reference i18n translation keys in mcp.json (for MCP topics),
 * services.json (for services topics), and users.json (for users topics)
 */
export const helpCategories: HelpCategory[] = [
  {
    id: 'users',
    titleKey: 'users:help.category',
    icon: 'User',
    topics: [
      {
        id: 'userDetector',
        titleKey: 'users:detector.help.title',
        descriptionKey: 'users:detector.help.overviewContent',
        icon: 'Search',
        sections: [
          { titleKey: 'users:detector.help.overview', contentKey: 'users:detector.help.overviewContent' },
          { titleKey: 'users:detector.help.scan', contentKey: 'users:detector.help.scanContent' },
          { titleKey: 'users:detector.help.results', contentKey: 'users:detector.help.resultsContent' },
          { titleKey: 'users:detector.help.create', contentKey: 'users:detector.help.createContent' },
        ],
      },
      {
        id: 'userManualMapping',
        titleKey: 'users:creator.help.title',
        descriptionKey: 'users:creator.help.overviewContent',
        icon: 'User',
        sections: [
          { titleKey: 'users:creator.help.overview', contentKey: 'users:creator.help.overviewContent' },
          { titleKey: 'users:creator.help.enumerate', contentKey: 'users:creator.help.enumerateContent' },
          { titleKey: 'users:creator.help.select', contentKey: 'users:creator.help.selectContent' },
          { titleKey: 'users:creator.help.create', contentKey: 'users:creator.help.createContent' },
        ],
      },
      {
        id: 'userMappingList',
        titleKey: 'users:list.help.title',
        descriptionKey: 'users:list.help.overviewContent',
        icon: 'Users',
        sections: [
          { titleKey: 'users:list.help.overview', contentKey: 'users:list.help.overviewContent' },
          { titleKey: 'users:list.help.cards', contentKey: 'users:list.help.cardsContent' },
          { titleKey: 'users:list.help.edit', contentKey: 'users:list.help.editContent' },
          { titleKey: 'users:list.help.sync', contentKey: 'users:list.help.syncContent' },
        ],
      },
      {
        id: 'groups',
        titleKey: 'groups:help.title',
        descriptionKey: 'groups:help.overviewContent',
        icon: 'Shield',
        sections: [
          { titleKey: 'groups:help.overview', contentKey: 'groups:help.overviewContent' },
          { titleKey: 'groups:help.create', contentKey: 'groups:help.createContent' },
          { titleKey: 'groups:help.members', contentKey: 'groups:help.membersContent' },
          { titleKey: 'groups:help.permissions', contentKey: 'groups:help.permissionsContent' },
        ],
      },
    ],
  },
  {
    id: 'services',
    titleKey: 'services:help.category',
    icon: 'Server',
    topics: [
      {
        id: 'services',
        titleKey: 'services:help.title',
        descriptionKey: 'services:help.overviewContent',
        icon: 'Server',
        sections: [
          { titleKey: 'services:help.overview', contentKey: 'services:help.overviewContent' },
          { titleKey: 'services:help.configure', contentKey: 'services:help.configureContent' },
          { titleKey: 'services:help.test', contentKey: 'services:help.testContent' },
          { titleKey: 'services:help.status', contentKey: 'services:help.statusContent' },
        ],
      },
      {
        id: 'serviceGroups',
        titleKey: 'services:serviceGroups.help.title',
        descriptionKey: 'services:serviceGroups.help.overviewContent',
        icon: 'Layers',
        sections: [
          { titleKey: 'services:serviceGroups.help.overview', contentKey: 'services:serviceGroups.help.overviewContent' },
          { titleKey: 'services:serviceGroups.help.create', contentKey: 'services:serviceGroups.help.createContent' },
          { titleKey: 'services:serviceGroups.help.assign', contentKey: 'services:serviceGroups.help.assignContent' },
          { titleKey: 'services:serviceGroups.help.mcp', contentKey: 'services:serviceGroups.help.mcpContent' },
        ],
      },
    ],
  },
  {
    id: 'mcp',
    titleKey: 'help.categories.mcp',
    icon: 'Bot',
    topics: [
      {
        id: 'stats',
        titleKey: 'stats.help.title',
        descriptionKey: 'stats.help.overviewContent',
        icon: 'BarChart3',
        sections: [
          { titleKey: 'stats.help.overview', contentKey: 'stats.help.overviewContent' },
          { titleKey: 'stats.help.cards', contentKey: 'stats.help.cardsContent' },
          { titleKey: 'stats.help.charts', contentKey: 'stats.help.chartsContent' },
          { titleKey: 'stats.help.timeRange', contentKey: 'stats.help.timeRangeContent' },
        ],
      },
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
      {
        id: 'config',
        titleKey: 'config.help.title',
        descriptionKey: 'config.help.overviewContent',
        icon: 'Settings',
        sections: [
          { titleKey: 'config.help.overview', contentKey: 'config.help.overviewContent' },
          { titleKey: 'config.help.autoConfig', contentKey: 'config.help.autoConfigContent' },
          { titleKey: 'config.help.endpoints', contentKey: 'config.help.endpointsContent' },
          { titleKey: 'config.help.systemPrompt', contentKey: 'config.help.systemPromptContent' },
          { titleKey: 'config.help.otherConfigs', contentKey: 'config.help.otherConfigsContent' },
        ],
      },
    ],
  },
  {
    id: 'training',
    titleKey: 'training:help.category',
    icon: 'Brain',
    topics: [
      {
        id: 'trainingStats',
        titleKey: 'training:overview.help.title',
        descriptionKey: 'training:overview.help.overviewContent',
        icon: 'BarChart3',
        sections: [
          { titleKey: 'training:overview.help.overview', contentKey: 'training:overview.help.overviewContent' },
          { titleKey: 'training:overview.help.cards', contentKey: 'training:overview.help.cardsContent' },
          { titleKey: 'training:overview.help.activeSessions', contentKey: 'training:overview.help.activeSessionsContent' },
          { titleKey: 'training:overview.help.workers', contentKey: 'training:overview.help.workersContent' },
        ],
      },
      {
        id: 'trainingSessions',
        titleKey: 'training:sessions.help.title',
        descriptionKey: 'training:sessions.help.overviewContent',
        icon: 'History',
        sections: [
          { titleKey: 'training:sessions.help.overview', contentKey: 'training:sessions.help.overviewContent' },
          { titleKey: 'training:sessions.help.lifecycle', contentKey: 'training:sessions.help.lifecycleContent' },
          { titleKey: 'training:sessions.help.actions', contentKey: 'training:sessions.help.actionsContent' },
          { titleKey: 'training:sessions.help.creation', contentKey: 'training:sessions.help.creationContent' },
        ],
      },
      {
        id: 'trainingWorkers',
        titleKey: 'training:workers.help.title',
        descriptionKey: 'training:workers.help.overviewContent',
        icon: 'Cpu',
        sections: [
          { titleKey: 'training:workers.help.overview', contentKey: 'training:workers.help.overviewContent' },
          { titleKey: 'training:workers.help.configuration', contentKey: 'training:workers.help.configurationContent' },
          { titleKey: 'training:workers.help.status', contentKey: 'training:workers.help.statusContent' },
          { titleKey: 'training:workers.help.metrics', contentKey: 'training:workers.help.metricsContent' },
        ],
      },
      {
        id: 'trainingModels',
        titleKey: 'training:models.help.title',
        descriptionKey: 'training:models.help.overviewContent',
        icon: 'Brain',
        sections: [
          { titleKey: 'training:models.help.overview', contentKey: 'training:models.help.overviewContent' },
          { titleKey: 'training:models.help.management', contentKey: 'training:models.help.managementContent' },
          { titleKey: 'training:models.help.status', contentKey: 'training:models.help.statusContent' },
          { titleKey: 'training:models.help.info', contentKey: 'training:models.help.infoContent' },
        ],
      },
      {
        id: 'trainingPrompts',
        titleKey: 'training:prompts.help.title',
        descriptionKey: 'training:prompts.help.overviewContent',
        icon: 'FileText',
        sections: [
          { titleKey: 'training:prompts.help.overview', contentKey: 'training:prompts.help.overviewContent' },
          { titleKey: 'training:prompts.help.structure', contentKey: 'training:prompts.help.structureContent' },
          { titleKey: 'training:prompts.help.management', contentKey: 'training:prompts.help.managementContent' },
          { titleKey: 'training:prompts.help.filtering', contentKey: 'training:prompts.help.filteringContent' },
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
