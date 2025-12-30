/**
 * Centralized service colors configuration.
 * Use this everywhere in the app for consistent service styling.
 */

import {
  Film,
  Eye,
  Zap,
  Bot,
  Shield,
  Server,
  BookOpen,
  Gamepad2,
  Download,
  Search,
  Tv,
  Headphones,
  FileText,
  Film as Movie,
  type LucideIcon
} from 'lucide-react';

export interface ServiceColorConfig {
  // Tailwind classes
  dot: string;
  bg: string;
  border: string;
  text: string;
  badge: string;
  badgeDark: string;
  // Icon component
  icon: LucideIcon;
  // Raw hex color for custom styling
  hex: string;
}

// Service type to color mapping
const SERVICE_COLORS: Record<string, ServiceColorConfig> = {
  // Media servers
  plex: {
    dot: 'bg-amber-500',
    bg: 'bg-amber-50 dark:bg-amber-900/20',
    border: 'border-amber-200 dark:border-amber-800',
    text: 'text-amber-600 dark:text-amber-400',
    badge: 'bg-amber-100 text-amber-800',
    badgeDark: 'dark:bg-amber-900 dark:text-amber-200',
    icon: Film,
    hex: '#f59e0b'
  },

  // Monitoring
  tautulli: {
    dot: 'bg-orange-500',
    bg: 'bg-orange-50 dark:bg-orange-900/20',
    border: 'border-orange-200 dark:border-orange-800',
    text: 'text-orange-600 dark:text-orange-400',
    badge: 'bg-orange-100 text-orange-800',
    badgeDark: 'dark:bg-orange-900 dark:text-orange-200',
    icon: Eye,
    hex: '#f97316'
  },

  // Request management
  overseerr: {
    dot: 'bg-emerald-500',
    bg: 'bg-emerald-50 dark:bg-emerald-900/20',
    border: 'border-emerald-200 dark:border-emerald-800',
    text: 'text-emerald-600 dark:text-emerald-400',
    badge: 'bg-emerald-100 text-emerald-800',
    badgeDark: 'dark:bg-emerald-900 dark:text-emerald-200',
    icon: Zap,
    hex: '#10b981'
  },

  // AI services
  openwebui: {
    dot: 'bg-violet-500',
    bg: 'bg-violet-50 dark:bg-violet-900/20',
    border: 'border-violet-200 dark:border-violet-800',
    text: 'text-violet-600 dark:text-violet-400',
    badge: 'bg-violet-100 text-violet-800',
    badgeDark: 'dark:bg-violet-900 dark:text-violet-200',
    icon: Bot,
    hex: '#8b5cf6'
  },

  ollama: {
    dot: 'bg-cyan-500',
    bg: 'bg-cyan-50 dark:bg-cyan-900/20',
    border: 'border-cyan-200 dark:border-cyan-800',
    text: 'text-cyan-600 dark:text-cyan-400',
    badge: 'bg-cyan-100 text-cyan-800',
    badgeDark: 'dark:bg-cyan-900 dark:text-cyan-200',
    icon: Bot,
    hex: '#06b6d4'
  },

  // Auth
  authentik: {
    dot: 'bg-blue-500',
    bg: 'bg-blue-50 dark:bg-blue-900/20',
    border: 'border-blue-200 dark:border-blue-800',
    text: 'text-blue-600 dark:text-blue-400',
    badge: 'bg-blue-100 text-blue-800',
    badgeDark: 'dark:bg-blue-900 dark:text-blue-200',
    icon: Shield,
    hex: '#3b82f6'
  },

  // *arr stack
  radarr: {
    dot: 'bg-yellow-500',
    bg: 'bg-yellow-50 dark:bg-yellow-900/20',
    border: 'border-yellow-200 dark:border-yellow-800',
    text: 'text-yellow-600 dark:text-yellow-400',
    badge: 'bg-yellow-100 text-yellow-800',
    badgeDark: 'dark:bg-yellow-900 dark:text-yellow-200',
    icon: Movie,
    hex: '#eab308'
  },

  sonarr: {
    dot: 'bg-sky-500',
    bg: 'bg-sky-50 dark:bg-sky-900/20',
    border: 'border-sky-200 dark:border-sky-800',
    text: 'text-sky-600 dark:text-sky-400',
    badge: 'bg-sky-100 text-sky-800',
    badgeDark: 'dark:bg-sky-900 dark:text-sky-200',
    icon: Tv,
    hex: '#0ea5e9'
  },

  prowlarr: {
    dot: 'bg-rose-500',
    bg: 'bg-rose-50 dark:bg-rose-900/20',
    border: 'border-rose-200 dark:border-rose-800',
    text: 'text-rose-600 dark:text-rose-400',
    badge: 'bg-rose-100 text-rose-800',
    badgeDark: 'dark:bg-rose-900 dark:text-rose-200',
    icon: Search,
    hex: '#f43f5e'
  },

  jackett: {
    dot: 'bg-slate-500',
    bg: 'bg-slate-50 dark:bg-slate-900/20',
    border: 'border-slate-200 dark:border-slate-800',
    text: 'text-slate-600 dark:text-slate-400',
    badge: 'bg-slate-100 text-slate-800',
    badgeDark: 'dark:bg-slate-900 dark:text-slate-200',
    icon: Search,
    hex: '#64748b'
  },

  // Downloads
  deluge: {
    dot: 'bg-indigo-500',
    bg: 'bg-indigo-50 dark:bg-indigo-900/20',
    border: 'border-indigo-200 dark:border-indigo-800',
    text: 'text-indigo-600 dark:text-indigo-400',
    badge: 'bg-indigo-100 text-indigo-800',
    badgeDark: 'dark:bg-indigo-900 dark:text-indigo-200',
    icon: Download,
    hex: '#6366f1'
  },

  // Comics/Books
  komga: {
    dot: 'bg-teal-500',
    bg: 'bg-teal-50 dark:bg-teal-900/20',
    border: 'border-teal-200 dark:border-teal-800',
    text: 'text-teal-600 dark:text-teal-400',
    badge: 'bg-teal-100 text-teal-800',
    badgeDark: 'dark:bg-teal-900 dark:text-teal-200',
    icon: BookOpen,
    hex: '#14b8a6'
  },

  // Gaming
  romm: {
    dot: 'bg-fuchsia-500',
    bg: 'bg-fuchsia-50 dark:bg-fuchsia-900/20',
    border: 'border-fuchsia-200 dark:border-fuchsia-800',
    text: 'text-fuchsia-600 dark:text-fuchsia-400',
    badge: 'bg-fuchsia-100 text-fuchsia-800',
    badgeDark: 'dark:bg-fuchsia-900 dark:text-fuchsia-200',
    icon: Gamepad2,
    hex: '#d946ef'
  },

  // Audiobooks/Podcasts
  audiobookshelf: {
    dot: 'bg-purple-500',
    bg: 'bg-purple-50 dark:bg-purple-900/20',
    border: 'border-purple-200 dark:border-purple-800',
    text: 'text-purple-600 dark:text-purple-400',
    badge: 'bg-purple-100 text-purple-800',
    badgeDark: 'dark:bg-purple-900 dark:text-purple-200',
    icon: Headphones,
    hex: '#a855f7'
  },

  // Documentation/Wiki
  wikijs: {
    dot: 'bg-blue-500',
    bg: 'bg-blue-50 dark:bg-blue-900/20',
    border: 'border-blue-200 dark:border-blue-800',
    text: 'text-blue-600 dark:text-blue-400',
    badge: 'bg-blue-100 text-blue-800',
    badgeDark: 'dark:bg-blue-900 dark:text-blue-200',
    icon: FileText,
    hex: '#3b82f6'
  },

  // Support
  zammad: {
    dot: 'bg-lime-500',
    bg: 'bg-lime-50 dark:bg-lime-900/20',
    border: 'border-lime-200 dark:border-lime-800',
    text: 'text-lime-600 dark:text-lime-400',
    badge: 'bg-lime-100 text-lime-800',
    badgeDark: 'dark:bg-lime-900 dark:text-lime-200',
    icon: Shield,
    hex: '#84cc16'
  },

  // System
  system: {
    dot: 'bg-gray-500',
    bg: 'bg-gray-50 dark:bg-gray-900/20',
    border: 'border-gray-200 dark:border-gray-800',
    text: 'text-gray-600 dark:text-gray-400',
    badge: 'bg-gray-100 text-gray-800',
    badgeDark: 'dark:bg-gray-700 dark:text-gray-200',
    icon: Server,
    hex: '#6b7280'
  }
};

// Default colors for unknown services
const DEFAULT_COLORS: ServiceColorConfig = {
  dot: 'bg-gray-500',
  bg: 'bg-gray-50 dark:bg-gray-900/20',
  border: 'border-gray-200 dark:border-gray-800',
  text: 'text-gray-600 dark:text-gray-400',
  badge: 'bg-gray-100 text-gray-800',
  badgeDark: 'dark:bg-gray-700 dark:text-gray-200',
  icon: Server,
  hex: '#6b7280'
};

/**
 * Get color configuration for a service type
 */
export function getServiceColor(serviceType: string): ServiceColorConfig {
  const normalized = serviceType.toLowerCase().trim();
  return SERVICE_COLORS[normalized] || DEFAULT_COLORS;
}

/**
 * Get service type from a tool name (e.g., "plex_search_media" -> "plex")
 */
export function getServiceFromToolName(toolName: string): string | null {
  const prefix = toolName.split('_')[0]?.toLowerCase();
  if (prefix && SERVICE_COLORS[prefix]) {
    return prefix;
  }
  return null;
}

/**
 * Get all registered service types
 */
export function getAllServiceTypes(): string[] {
  return Object.keys(SERVICE_COLORS);
}

/**
 * Check if a service type has custom colors defined
 */
export function hasServiceColor(serviceType: string): boolean {
  return serviceType.toLowerCase() in SERVICE_COLORS;
}

export { SERVICE_COLORS, DEFAULT_COLORS };
