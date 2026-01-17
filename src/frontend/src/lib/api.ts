/**
 * API client with error handling and correlation IDs
 */

// ApiResponse type is defined in types/api.ts but not used here directly

interface RequestOptions extends RequestInit {
  params?: Record<string, string | number | boolean>;
}

/**
 * Get the API base URL dynamically based on the current environment
 * This allows the frontend to work from any device on the network
 */
const getApiBaseUrl = (): string => {
  // Check for explicit environment variable first
  const envApiUrl = import.meta.env.VITE_API_URL;

  // If VITE_API_URL is set, use it
  if (envApiUrl) {
    return envApiUrl;
  }

  // In production (Docker), use empty string so requests go through nginx proxy
  // nginx will proxy /api/* to the backend on port 8000
  if (import.meta.env.PROD) {
    return '';
  }

  // In development, dynamically use the current hostname with backend port
  // This allows access from other devices on the local network
  const hostname = typeof window !== 'undefined' ? window.location.hostname : 'localhost';
  return `http://${hostname}:8000`;
};

class ApiClient {
  private baseUrl: string;
  private defaultHeaders: Record<string, string>;

  constructor(baseUrl?: string) {
    this.baseUrl = baseUrl || getApiBaseUrl();
    this.defaultHeaders = {
      'Content-Type': 'application/json',
    };
  }

  private generateCorrelationId(): string {
    return `frontend-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  }

  private buildUrl(path: string, params?: Record<string, any>): string {
    // Handle empty baseUrl (production mode with nginx proxy)
    let urlString: string;
    if (this.baseUrl) {
      const url = new URL(path, this.baseUrl);
      if (params) {
        Object.entries(params).forEach(([key, value]) => {
          if (value !== undefined && value !== null) {
            url.searchParams.append(key, value.toString());
          }
        });
      }
      urlString = url.toString();
    } else {
      // No baseUrl - use relative path (for nginx proxy)
      urlString = path;
      if (params) {
        const searchParams = new URLSearchParams();
        Object.entries(params).forEach(([key, value]) => {
          if (value !== undefined && value !== null) {
            searchParams.append(key, value.toString());
          }
        });
        const queryString = searchParams.toString();
        if (queryString) {
          urlString += (path.includes('?') ? '&' : '?') + queryString;
        }
      }
    }

    return urlString;
  }

  private async makeRequest<T = any>(
    method: string,
    path: string,
    options: RequestOptions = {}
  ): Promise<T> {
    const { params, ...fetchOptions } = options;

    const url = this.buildUrl(path, params);
    const correlationId = this.generateCorrelationId();

    const headers = {
      ...this.defaultHeaders,
      'X-Correlation-ID': correlationId,
      ...fetchOptions.headers,
    };

    try {
      const response = await fetch(url, {
        method,
        headers,
        ...fetchOptions,
      });

      // Handle 204 No Content responses (common for DELETE operations)
      if (response.status === 204) {
        return undefined as T;
      }

      const contentType = response.headers.get('Content-Type');
      let data;

      if (contentType?.includes('application/json')) {
        data = await response.json();
      } else {
        const text = await response.text();
        // Try to parse as JSON if it looks like JSON, otherwise return the text
        if (text && (text.startsWith('{') || text.startsWith('['))) {
          try {
            data = JSON.parse(text);
          } catch {
            data = text;
          }
        } else {
          data = text || undefined;
        }
      }

      if (!response.ok) {
        const error = new Error(
          data?.error || data?.message || `HTTP ${response.status}: ${response.statusText}`
        );
        (error as any).status = response.status;
        (error as any).correlationId = response.headers.get('X-Correlation-ID') || correlationId;
        throw error;
      }

      return data;
    } catch (error) {
      console.error(`API Error [${method} ${path}]:`, error);

      if (error instanceof TypeError && error.message.includes('fetch')) {
        throw new Error('Network error: Unable to connect to API server');
      }

      throw error;
    }
  }

  // HTTP Methods
  async get<T = any>(path: string, options: RequestOptions = {}): Promise<T> {
    return this.makeRequest<T>('GET', path, options);
  }

  async post<T = any>(path: string, data?: any, options: RequestOptions = {}): Promise<T> {
    return this.makeRequest<T>('POST', path, {
      ...options,
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  async put<T = any>(path: string, data?: any, options: RequestOptions = {}): Promise<T> {
    return this.makeRequest<T>('PUT', path, {
      ...options,
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  async patch<T = any>(path: string, data?: any, options: RequestOptions = {}): Promise<T> {
    return this.makeRequest<T>('PATCH', path, {
      ...options,
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  async delete<T = any>(path: string, options: RequestOptions = {}): Promise<T> {
    return this.makeRequest<T>('DELETE', path, options);
  }

  // Convenience methods for common patterns
  async getWithPagination<T = any>(
    path: string,
    offset: number = 0,
    limit: number = 100,
    options: RequestOptions = {}
  ): Promise<T> {
    return this.get<T>(path, {
      ...options,
      params: {
        ...options.params,
        offset,
        limit,
      },
    });
  }

  // File upload helper
  async uploadFile<T = any>(
    path: string,
    file: File,
    fieldName: string = 'file',
    additionalData?: Record<string, string>
  ): Promise<T> {
    const correlationId = this.generateCorrelationId();
    const formData = new FormData();

    formData.append(fieldName, file);

    if (additionalData) {
      Object.entries(additionalData).forEach(([key, value]) => {
        formData.append(key, value);
      });
    }

    const response = await fetch(this.buildUrl(path), {
      method: 'POST',
      headers: {
        'X-Correlation-ID': correlationId,
      },
      body: formData,
    });

    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      const error = new Error(data.error || `Upload failed: ${response.statusText}`);
      (error as any).status = response.status;
      (error as any).correlationId = response.headers.get('X-Correlation-ID') || correlationId;
      throw error;
    }

    return response.json();
  }
}

// Create default API client instance
export const apiClient = new ApiClient();

// Export class for custom instances
export { ApiClient };

// Export the base URL getter for components that need it
export { getApiBaseUrl };

// API endpoint helpers
export const api = {
  // Base URL helper
  getBaseUrl: getApiBaseUrl,

  // Health
  health: () => apiClient.get('/health'),
  healthDetailed: () => apiClient.get('/health/detailed'),

  // Version
  version: () => apiClient.get('/version'),

  // Dashboard
  dashboard: {
    overview: () => apiClient.get('/api/v1/dashboard/overview'),
  },

  // System
  system: {
    health: () => apiClient.get('/api/v1/system/health'),
    metrics: (duration: string = '5m') =>
      apiClient.get('/api/v1/system/metrics', { params: { duration } }),
    currentMetrics: () => apiClient.get('/api/v1/system/system-metrics'),
  },

  // Services
  services: {
    list: (status?: string) =>
      apiClient.get('/api/services/', { params: status ? { status } : {} }),
    get: (id: string) => apiClient.get(`/api/services/${id}`),
    create: (data: any) => apiClient.post('/api/services/', data),
    update: (id: string, data: any) => apiClient.put(`/api/services/${id}`, data),
    delete: (id: string) => apiClient.delete(`/api/services/${id}`),
    test: (id: string) => apiClient.post(`/api/services/${id}/test`),
  },

  // Users
  users: {
    list: (search?: string, service?: string) =>
      apiClient.get('/api/v1/users', {
        params: {
          ...(search && { search }),
          ...(service && { service })
        }
      }),
    get: (id: string) => apiClient.get(`/api/v1/users/${id}`),
    create: (data: any) => apiClient.post('/api/v1/users', data),
    update: (id: string, data: any) => apiClient.put(`/api/v1/users/${id}`, data),
    syncAuthentik: () => apiClient.post('/api/v1/users/sync-authentik'),
  },

  // Logs
  logs: {
    list: (filters?: Record<string, any>) =>
      apiClient.get('/api/logs/', { params: filters }),
    stats: (hours: number = 24) =>
      apiClient.get('/api/logs/stats', { params: { hours } }),
    sources: () => apiClient.get('/api/logs/sources'),
    components: (source?: string) =>
      apiClient.get('/api/logs/components', { params: source ? { source } : {} }),
    trace: (correlationId: string) =>
      apiClient.get(`/api/logs/trace/${correlationId}`),
    get: (id: string) => apiClient.get(`/api/logs/${id}`),
    create: (data: any) => apiClient.post('/api/logs/', data),
    cleanup: () => apiClient.post('/api/logs/cleanup'),
    levels: () => apiClient.get('/api/logs/levels/available'),
  },

  // Alerts
  alerts: {
    configs: {
      list: (filters?: Record<string, any>) =>
        apiClient.get('/api/alerts/configs', { params: filters }),
      get: (id: string) => apiClient.get(`/api/alerts/configs/${id}`),
      create: (data: any) => apiClient.post('/api/alerts/configs', data),
      update: (id: string, data: any) =>
        apiClient.patch(`/api/alerts/configs/${id}`, data),
      delete: (id: string) => apiClient.delete(`/api/alerts/configs/${id}`),
      toggle: (id: string, enabled: boolean) =>
        apiClient.post(`/api/alerts/configs/${id}/toggle`, null, {
          params: { enabled },
        }),
    },
    history: {
      list: (filters?: Record<string, any>) =>
        apiClient.get('/api/alerts/history', { params: filters }),
      active: () => apiClient.get('/api/alerts/active'),
      resolve: (id: string, message?: string) =>
        apiClient.post(`/api/alerts/history/${id}/resolve`, null, {
          params: message ? { message } : {},
        }),
    },
    stats: (hours: number = 24) =>
      apiClient.get('/api/alerts/stats', { params: { hours } }),
    severities: () => apiClient.get('/api/alerts/severities'),
    metricTypes: () => apiClient.get('/api/alerts/metric-types'),
    operators: () => apiClient.get('/api/alerts/operators'),
  },

  // Configuration
  config: {
    list: (category?: string) =>
      apiClient.get('/api/v1/config', { params: category ? { category } : {} }),
    update: (settings: Record<string, string>) =>
      apiClient.put('/api/v1/config', settings),
    backup: () => apiClient.get('/api/v1/config/backup'),
    restore: (backup: any) => apiClient.post('/api/v1/config/backup', backup),
  },

  // MCP
  mcp: {
    status: () => apiClient.get('/api/mcp/status'),
    requests: {
      list: (filters?: Record<string, any>) =>
        apiClient.get('/api/mcp/requests', { params: filters }),
      get: (id: string) => apiClient.get(`/api/mcp/requests/${id}`),
    },
    stats: (hours: number = 24) =>
      apiClient.get('/api/mcp/stats', { params: { hours } }),
    statsWithComparison: (hours: number = 24) =>
      apiClient.get('/api/mcp/stats/comparison', { params: { hours } }),
    toolUsage: (hours: number = 24) =>
      apiClient.get('/api/mcp/tools/usage', { params: { hours } }),
    hourlyUsage: (hours: number = 24) =>
      apiClient.get('/api/mcp/hourly-usage', { params: { hours } }),
    userStats: (hours: number = 24) =>
      apiClient.get('/api/mcp/user-stats', { params: { hours } }),
    userServiceStats: (hours: number = 24) =>
      apiClient.get('/api/mcp/user-service-stats', { params: { hours } }),
    hourlyUsageByUser: (hours: number = 24) =>
      apiClient.get('/api/mcp/hourly-usage-by-user', { params: { hours } }),
    tools: () => apiClient.get('/api/mcp/tools'),
    executeTool: (toolName: string, params: Record<string, any> = {}) =>
      apiClient.post('/api/mcp/tools/test', { tool_name: toolName, arguments: params }),
    cleanup: (retentionDays: number = 30) =>
      apiClient.delete('/api/mcp/cleanup', { params: { retention_days: retentionDays } }),
  },

  // Groups
  groups: {
    list: (enabled?: boolean) =>
      apiClient.get('/api/groups/', { params: enabled !== undefined ? { enabled } : {} }),
    get: (id: string) => apiClient.get(`/api/groups/${id}`),
    create: (data: any) => apiClient.post('/api/groups/', data),
    update: (id: string, data: any) => apiClient.put(`/api/groups/${id}`, data),
    delete: (id: string) => apiClient.delete(`/api/groups/${id}`),
    // Members
    members: {
      list: (groupId: string) => apiClient.get(`/api/groups/${groupId}/members`),
      add: (groupId: string, data: { central_user_id: string; enabled?: boolean; granted_by?: string }) =>
        apiClient.post(`/api/groups/${groupId}/members`, data),
      remove: (groupId: string, membershipId: string) =>
        apiClient.delete(`/api/groups/${groupId}/members/${membershipId}`),
      bulk: (groupId: string, data: { central_user_ids: string[]; action: 'add' | 'remove' }) =>
        apiClient.post(`/api/groups/${groupId}/members/bulk`, data),
    },
    // Permissions
    permissions: {
      list: (groupId: string, serviceType?: string) =>
        apiClient.get(`/api/groups/${groupId}/permissions`, {
          params: serviceType ? { service_type: serviceType } : {}
        }),
      add: (groupId: string, data: { tool_name: string; service_type?: string; enabled?: boolean; description?: string }) =>
        apiClient.post(`/api/groups/${groupId}/permissions`, data),
      update: (groupId: string, permissionId: string, data: any) =>
        apiClient.put(`/api/groups/${groupId}/permissions/${permissionId}`, data),
      delete: (groupId: string, permissionId: string) =>
        apiClient.delete(`/api/groups/${groupId}/permissions/${permissionId}`),
      bulk: (groupId: string, data: { tool_names: string[]; service_type?: string; enabled: boolean }) =>
        apiClient.post(`/api/groups/${groupId}/permissions/bulk`, data),
    },
    // User groups
    userGroups: (userId: string) => apiClient.get(`/api/groups/user/${userId}`),
    // Check permission
    checkPermission: (data: { central_user_id: string; tool_name: string; service_type?: string }) =>
      apiClient.post('/api/groups/check-permission', data),
    // Available tools
    availableTools: () => apiClient.get('/api/groups/available-tools'),
    // Tools with groups (for displaying group labels on tools)
    toolsWithGroups: () => apiClient.get('/api/groups/tools-with-groups'),
  },

  // Training
  training: {
    // Ollama
    ollama: {
      status: (serviceId?: string) =>
        apiClient.get('/api/training/ollama/status', { params: serviceId ? { service_id: serviceId } : {} }),
      metrics: (serviceId?: string) =>
        apiClient.get('/api/training/ollama/metrics', { params: serviceId ? { service_id: serviceId } : {} }),
      models: (serviceId?: string) =>
        apiClient.get('/api/training/ollama/models', { params: serviceId ? { service_id: serviceId } : {} }),
      modelInfo: (modelName: string, serviceId?: string) =>
        apiClient.get(`/api/training/ollama/models/${encodeURIComponent(modelName)}`, { params: serviceId ? { service_id: serviceId } : {} }),
      deleteModel: (modelName: string, serviceId?: string) =>
        apiClient.delete(`/api/training/ollama/models/${encodeURIComponent(modelName)}`, { params: serviceId ? { service_id: serviceId } : {} }),
      loadModel: (modelName: string, serviceId?: string) =>
        apiClient.post(`/api/training/ollama/models/${encodeURIComponent(modelName)}/load`, null, { params: serviceId ? { service_id: serviceId } : {} }),
      unloadModel: (modelName: string, serviceId?: string) =>
        apiClient.post(`/api/training/ollama/models/${encodeURIComponent(modelName)}/unload`, null, { params: serviceId ? { service_id: serviceId } : {} }),
    },
    // Sessions
    sessions: {
      list: (filters?: { status?: string; skip?: number; limit?: number }) =>
        apiClient.get('/api/training/sessions', { params: filters }),
      get: (id: string) => apiClient.get(`/api/training/sessions/${id}`),
      create: (data: any) => apiClient.post('/api/training/sessions', data),
      update: (id: string, data: any) => apiClient.patch(`/api/training/sessions/${id}`, data),
      delete: (id: string) => apiClient.delete(`/api/training/sessions/${id}`),
      duplicate: (id: string) => apiClient.post(`/api/training/sessions/${id}/duplicate`),
      start: (id: string, backend: 'ollama_modelfile' | 'unsloth' = 'ollama_modelfile') =>
        apiClient.post(`/api/training/sessions/${id}/start`, null, { params: { backend } }),
      cancel: (id: string) => apiClient.post(`/api/training/sessions/${id}/cancel`),
      getLogs: (id: string) => apiClient.get(`/api/training/sessions/${id}/logs`),
      getSummary: (id: string) => apiClient.get(`/api/training/sessions/${id}/summary`),
      // Session prompts management
      getPrompts: (id: string) => apiClient.get(`/api/training/sessions/${id}/prompts`),
      setPrompts: (id: string, promptIds: string[]) =>
        apiClient.put(`/api/training/sessions/${id}/prompts`, { prompt_ids: promptIds }),
      addPrompts: (id: string, promptIds: string[]) =>
        apiClient.post(`/api/training/sessions/${id}/prompts/add`, { prompt_ids: promptIds }),
      removePrompts: (id: string, promptIds: string[]) =>
        apiClient.post(`/api/training/sessions/${id}/prompts/remove`, { prompt_ids: promptIds }),
    },
    // Prompts
    prompts: {
      list: (filters?: {
        category?: string;
        difficulty?: string;
        validated?: boolean;
        enabled?: boolean;
        session_id?: string;
        search?: string;
        skip?: number;
        limit?: number;
      }) => apiClient.get('/api/training/prompts', { params: filters }),
      get: (id: string) => apiClient.get(`/api/training/prompts/${id}`),
      create: (data: any) => apiClient.post('/api/training/prompts', data),
      update: (id: string, data: any) => apiClient.patch(`/api/training/prompts/${id}`, data),
      delete: (id: string) => apiClient.delete(`/api/training/prompts/${id}`),
      validate: (id: string, score?: number, validatedBy?: string) =>
        apiClient.post(`/api/training/prompts/${id}/validate`, null, {
          params: {
            ...(score !== undefined && { score }),
            ...(validatedBy && { validated_by: validatedBy }),
          },
        }),
      import: (prompts: any[]) => apiClient.post('/api/training/prompts/import', prompts),
      export: (filters?: { category?: string; session_id?: string; format?: string }) =>
        apiClient.get('/api/training/prompts/export', { params: filters }),
      seed: (reset: boolean = false) => apiClient.post('/api/training/prompts/seed', undefined, { params: { reset } }),
      deleteAll: () => apiClient.delete('/api/training/prompts/all'),
    },
    // Stats
    stats: () => apiClient.get('/api/training/stats'),
    // Worker (GPU training worker)
    worker: {
      status: () => apiClient.get('/api/training/worker/status'),
      models: () => apiClient.get('/api/training/worker/models'),
    },
  },

  // Training Workers
  workers: {
    list: (enabledOnly?: boolean) =>
      apiClient.get('/api/workers', { params: enabledOnly ? { enabled_only: true } : {} }),
    get: (id: string) => apiClient.get(`/api/workers/${id}`),
    create: (data: {
      name: string;
      description?: string;
      url: string;
      api_key?: string;
      ollama_service_id?: string;
    }) => apiClient.post('/api/workers', data),
    update: (id: string, data: {
      name?: string;
      description?: string;
      url?: string;
      api_key?: string;
      enabled?: boolean;
      ollama_service_id?: string;
    }) => apiClient.patch(`/api/workers/${id}`, data),
    delete: (id: string) => apiClient.delete(`/api/workers/${id}`),
    test: (id: string) => apiClient.post(`/api/workers/${id}/test`),
    refresh: (id: string) => apiClient.post(`/api/workers/${id}/refresh`),
    refreshAll: () => apiClient.post('/api/workers/refresh-all'),
    getMetrics: (id: string) => apiClient.get(`/api/workers/${id}/metrics`),
    getMetricsHistory: (id: string, limit?: number, minutes?: number) =>
      apiClient.get(`/api/workers/${id}/metrics/history`, { params: { ...(limit && { limit }), ...(minutes && { minutes }) } }),
    getModels: (id: string) => apiClient.get(`/api/workers/${id}/models`),
    // Training control
    startTraining: (workerId: string, data: {
      session_id: string;
      base_model?: string;
      output_model_name: string;
      overwrite_existing?: boolean;
      num_epochs?: number;
      batch_size?: number;
      learning_rate?: number;
      max_seq_length?: number;
      warmup_steps?: number;
      lora_r?: number;
      lora_alpha?: number;
      quantization_method?: string;
    }) => apiClient.post(`/api/workers/${workerId}/training/start`, data),
    getTrainingStatus: (id: string) => apiClient.get(`/api/workers/${id}/training/status`),
    cancelTraining: (id: string) => apiClient.post(`/api/workers/${id}/training/cancel`),
  },

  // Service Groups
  serviceGroups: {
    list: (enabled?: boolean) =>
      apiClient.get('/api/service-groups/', { params: enabled !== undefined ? { enabled } : {} }),
    get: (id: string) => apiClient.get(`/api/service-groups/${id}`),
    create: (data: { name: string; description?: string; color?: string; priority?: number }) =>
      apiClient.post('/api/service-groups/', data),
    update: (id: string, data: { name?: string; description?: string; color?: string; priority?: number; enabled?: boolean }) =>
      apiClient.put(`/api/service-groups/${id}`, data),
    delete: (id: string) => apiClient.delete(`/api/service-groups/${id}`),
    // Members (services)
    members: {
      list: (groupId: string) => apiClient.get(`/api/service-groups/${groupId}/members`),
      add: (groupId: string, data: { service_type: string; enabled?: boolean }) =>
        apiClient.post(`/api/service-groups/${groupId}/members`, data),
      remove: (groupId: string, membershipId: string) =>
        apiClient.delete(`/api/service-groups/${groupId}/members/${membershipId}`),
      bulk: (groupId: string, data: { service_types: string[]; action: 'add' | 'remove' }) =>
        apiClient.post(`/api/service-groups/${groupId}/members/bulk`, data),
    },
    // Available services
    availableServices: () => apiClient.get('/api/service-groups/available-services'),
  },

  // Backup/Restore
  backup: {
    preview: (options?: {
      services?: boolean;
      service_groups?: boolean;
      user_mappings?: boolean;
      groups?: boolean;
      site_config?: boolean;
      training_prompts?: boolean;
      training_workers?: boolean;
      tool_chains?: boolean;
      global_search?: boolean;
      alerts?: boolean;
    }) => apiClient.get('/api/backup/preview', { params: options }),
    export: (options?: {
      services?: boolean;
      service_groups?: boolean;
      user_mappings?: boolean;
      groups?: boolean;
      site_config?: boolean;
      training_prompts?: boolean;
      training_workers?: boolean;
      tool_chains?: boolean;
      global_search?: boolean;
      alerts?: boolean;
    }) => apiClient.post('/api/backup/export', options || {}),
    import: (data: {
      version: string;
      data: Record<string, any>;
      options?: {
        services?: boolean;
        service_groups?: boolean;
        user_mappings?: boolean;
        groups?: boolean;
        site_config?: boolean;
        training_prompts?: boolean;
        training_workers?: boolean;
        tool_chains?: boolean;
        global_search?: boolean;
        alerts?: boolean;
        merge_mode?: boolean;
      };
    }) => apiClient.post('/api/backup/import', data),
    resetAll: () => apiClient.post('/api/backup/reset-all'),
  },

  // Expose baseURL for legacy code
  baseURL: apiClient['baseUrl'],
};