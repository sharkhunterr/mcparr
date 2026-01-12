/**
 * TypeScript interfaces matching backend models
 */

// Service Types
export const ServiceType = {
  PLEX: 'plex',
  TAUTULLI: 'tautulli',
  OVERSEERR: 'overseerr',
  ZAMMAD: 'zammad',
  AUTHENTIK: 'authentik',
  OPENWEBUI: 'openwebui',
  OLLAMA: 'ollama',
  RADARR: 'radarr',
  SONARR: 'sonarr',
  PROWLARR: 'prowlarr',
  JACKETT: 'jackett',
  DELUGE: 'deluge',
  KOMGA: 'komga',
  ROMM: 'romm',
  MONITORING: 'monitoring',
  CUSTOM: 'custom',
} as const;
export type ServiceType = typeof ServiceType[keyof typeof ServiceType];

// Status Types
export const TestStatus = {
  SUCCESS: 'success',
  FAILED: 'failed',
  PENDING: 'pending',
} as const;
export type TestStatus = typeof TestStatus[keyof typeof TestStatus];

export const TrainingStatus = {
  PENDING: 'pending',
  RUNNING: 'running',
  COMPLETED: 'completed',
  FAILED: 'failed',
  CANCELLED: 'cancelled',
} as const;
export type TrainingStatus = typeof TrainingStatus[keyof typeof TrainingStatus];

export const RequestStatus = {
  SUCCESS: 'success',
  ERROR: 'error',
  TIMEOUT: 'timeout',
} as const;
export type RequestStatus = typeof RequestStatus[keyof typeof RequestStatus];

export const UserRole = {
  ADMIN: 'admin',
  USER: 'user',
} as const;
export type UserRole = typeof UserRole[keyof typeof UserRole];

export const LogLevel = {
  DEBUG: 'debug',
  INFO: 'info',
  WARNING: 'warning',
  ERROR: 'error',
  CRITICAL: 'critical',
} as const;
export type LogLevel = typeof LogLevel[keyof typeof LogLevel];

// API Response Types
export interface ApiResponse<T = any> {
  data?: T;
  error?: string;
  message?: string;
  correlation_id?: string;
}

export interface PaginatedResponse<T = any> {
  entries: T[];
  total: number;
  offset: number;
  limit: number;
  has_more: boolean;
}

// Dashboard Types
export interface DashboardOverview {
  services: {
    total: number;
    active: number;
    failing: number;
  };
  users: {
    total: number;
    active_sessions: number;
  };
  training: {
    active_sessions: number;
    completed_today: number;
  };
  logs: {
    recent_errors: number;
    total_today: number;
  };
  mcp: {
    requests_today: number;
    average_response_time: number;
  };
  system: SystemStatus;
}

export interface SystemStatus {
  cpu_percent: number;
  memory_used_mb: number;
  memory_total_mb: number;
  disk_used_gb: number;
  disk_total_gb: number;
  uptime_seconds: number;
  docker_containers: {
    running: number;
    stopped: number;
  };
}

// System Metrics for real-time monitoring
export interface SystemMetrics {
  cpu_usage: number;
  cpu_load_avg: number;
  memory_usage: number;
  memory_used: number;
  memory_total: number;
  disk_usage: number;
  disk_used: number;
  disk_total: number;
  network_bytes_sent: number;
  network_bytes_recv: number;
  services_running: number;
  services_total: number;
  uptime: number;
}

export interface HealthStatus {
  status: 'healthy' | 'degraded' | 'unhealthy';
  checks: Array<{
    name: string;
    status: string;
    message: string;
    response_time_ms?: number;
  }>;
}

// Service Configuration Types
export interface ServiceConfig {
  id: string;
  name: string;
  service_type: ServiceType;
  base_url: string;
  connection_timeout: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  last_test_at?: string;
  test_status: TestStatus;
  test_error?: string;
}

export interface ServiceConfigCreate {
  name: string;
  service_type: ServiceType;
  base_url: string;
  api_key?: string;
  username?: string;
  password?: string;
  custom_headers?: Record<string, string>;
  connection_timeout?: number;
}

export interface ServiceTestResult {
  success: boolean;
  message: string;
  response_time_ms: number;
  details?: Record<string, any>;
  tested_at: string;
}

// User Types
export interface UserMapping {
  id: string;
  email: string;
  display_name: string;
  role: UserRole;
  open_webui_username?: string;
  authentik_user_id?: string;
  authentik_username?: string;
  plex_user_id?: string;
  plex_username?: string;
  overseerr_user_id?: string;
  overseerr_username?: string;
  zammad_user_id?: string;
  zammad_email?: string;
  tautulli_user_id?: string;
  is_active: boolean;
  auto_detected: boolean;
  confidence_score: number;
  created_at: string;
  updated_at: string;
  last_sync_at?: string;
}

// Log Types
export interface LogEntry {
  id: string;
  timestamp: string;
  level: LogLevel;
  service_id?: string;
  service_name?: string;
  user_mapping_id?: string;
  user_email?: string;
  correlation_id: string;
  component: string;
  action: string;
  message: string;
  details?: Record<string, any>;
  request_path?: string;
  request_method?: string;
  response_status?: number;
  duration_ms?: number;
  error_type?: string;
  ip_address?: string;
}

// WebSocket Message Types
export interface WebSocketMessage {
  type: string;
  timestamp: string;
  correlation_id?: string;
}

export interface LogEntryMessage extends WebSocketMessage {
  type: 'log_entry';
  log: LogEntry;
}

export interface MetricsUpdateMessage extends WebSocketMessage {
  type: 'metrics_update';
  system?: SystemStatus;
  services?: Array<{
    service_id: string;
    name: string;
    status: 'online' | 'offline' | 'degraded';
    response_time_ms: number;
    last_check: string;
  }>;
}

// Configuration Types
export interface ConfigurationSetting {
  id: string;
  category: string;
  key: string;
  value: string;
  value_type: string;
  default_value: string;
  description: string;
  is_sensitive: boolean;
  requires_restart: boolean;
  updated_at: string;
  updated_by?: string;
}

// Group Types
export interface Group {
  id: string;
  name: string;
  description?: string;
  color?: string;
  icon?: string;
  priority: number;
  is_system: boolean;
  enabled: boolean;
  created_at: string;
  updated_at: string;
  member_count: number;
  tool_count: number;
}

export interface GroupDetail extends Group {
  memberships: GroupMembership[];
  tool_permissions: GroupToolPermission[];
}

export interface GroupMembership {
  id: string;
  group_id: string;
  central_user_id: string;
  enabled: boolean;
  granted_at: string;
  granted_by?: string;
  created_at: string;
  updated_at: string;
  central_username?: string;
}

export interface GroupToolPermission {
  id: string;
  group_id: string;
  tool_name: string;
  service_type?: string;
  enabled: boolean;
  description?: string;
  created_at: string;
  updated_at: string;
}

export interface GroupListResponse {
  groups: Group[];
  total: number;
  skip: number;
  limit: number;
}

export interface UserGroupsResponse {
  central_user_id: string;
  groups: Group[];
  total_groups: number;
}

export interface AvailableToolsResponse {
  tools_by_service: Record<string, Array<{
    name: string;
    description: string;
    category?: string;
  }>>;
  total_tools: number;
}

// Service Groups
export interface ServiceGroup {
  id: string;
  name: string;
  description?: string;
  color?: string;
  icon?: string;
  priority: number;
  is_system: boolean;
  enabled: boolean;
  created_at: string;
  updated_at: string;
  member_count: number;
  service_types: string[];
}

export interface ServiceGroupMembership {
  id: string;
  group_id: string;
  service_type: string;
  enabled: boolean;
  created_at: string;
  updated_at: string;
  service_name?: string;
  service_configured: boolean;
}

export interface ServiceGroupDetail extends ServiceGroup {
  memberships: ServiceGroupMembership[];
}

export interface ServiceGroupListResponse {
  groups: ServiceGroup[];
  total: number;
  skip: number;
  limit: number;
}

export interface AvailableService {
  service_type: string;
  display_name: string;
  configured: boolean;
  tool_count: number;
}

export interface AvailableServicesResponse {
  services: AvailableService[];
  total: number;
}