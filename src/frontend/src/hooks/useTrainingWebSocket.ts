import { useState, useEffect, useRef, useCallback } from 'react';
import { getApiBaseUrl } from '../lib/api';

// ============= Training Metrics Types =============

export interface ProgressMetrics {
  current_epoch: number;
  total_epochs: number;
  current_step: number;
  total_steps: number;
  progress_percent: number;
  samples_processed: number;
  tokens_processed: number;
}

export interface PerformanceMetrics {
  loss: number | null;
  loss_history: number[];
  perplexity: number | null;
  gradient_norm: number | null;
  learning_rate: number | null;
  accuracy: number | null;
  entropy: number | null;
}

export interface GPUMetrics {
  gpu_id?: number;
  gpu_name?: string;
  memory_used_mb: number | null;
  memory_total_mb: number | null;
  memory_percent: number | null;
  utilization_percent: number | null;
  temperature_celsius: number | null;
  power_watts?: number | null;
}

export interface TimeMetrics {
  elapsed_seconds: number;
  eta_seconds: number | null;
  samples_per_second: number;
  tokens_per_second: number;
  step_duration_ms: number;
}

export type LossTrend = 'decreasing' | 'stable' | 'increasing' | 'fluctuating';
export type TrainingHealth = 'excellent' | 'good' | 'warning' | 'critical';
export type OverfittingRisk = 'low' | 'medium' | 'high';

export interface QualityIndicators {
  loss_trend: LossTrend;
  loss_improvement_rate: number;
  training_health: TrainingHealth;
  health_message: string;
  overfitting_risk: OverfittingRisk;
}

export interface ConvergenceMetrics {
  best_loss: number | null;
  best_loss_epoch: number;
  best_loss_step: number;
  epochs_without_improvement: number;
  should_early_stop: boolean;
  early_stop_reason: string | null;
}

export interface TrainingMetrics {
  progress: ProgressMetrics;
  performance: PerformanceMetrics;
  gpu: GPUMetrics | null;
  time: TimeMetrics;
  quality: QualityIndicators;
  convergence: ConvergenceMetrics;
}

// ============= Message Types =============

export type UpdateType = 'progress' | 'metrics' | 'started' | 'completed' | 'failed' | 'cancelled';

export interface SessionUpdate {
  type: 'session_update';
  session_id: string;
  update_type: UpdateType;
  data: TrainingMetrics;
  timestamp: string;
}

export interface LogLine {
  timestamp: string;
  level: string;
  message: string;
  job_id?: string;
}

export interface LogLineMessage {
  type: 'log_line';
  session_id: string;
  data: LogLine;
  timestamp: string;
}

// Legacy types for backward compatibility
export interface OllamaHealth {
  status: 'healthy' | 'unhealthy' | 'unknown';
  version?: string;
  url?: string;
  error?: string;
}

export interface OllamaModel {
  name: string;
  model: string;
  modified_at?: string;
  size: number;
  size_gb: number;
  digest: string;
  family: string;
  parameter_size: string;
  quantization_level: string;
  details: Record<string, unknown>;
}

export interface OllamaMetrics {
  type: 'ollama_metrics';
  health: OllamaHealth;
  models: OllamaModel[];
  running_models: Record<string, unknown>[];
  model_count?: number;
  total_size_gb?: number;
  running_count?: number;
  error?: string;
  timestamp?: string;
}

export interface TrainingStats {
  active_sessions: number;
  queued_sessions: number;
  completed_today: number;
  total_prompts: number;
  validated_prompts: number;
}

export interface TrainingUpdate {
  type: 'training_update';
  stats: TrainingStats;
  recent_activity: Record<string, unknown>[];
  timestamp?: string;
}

export interface SessionProgress {
  current_step: number;
  total_steps: number;
  percent_complete: number;
  current_prompt: string | null;
  prompts_processed: number;
  prompts_total: number;
}

export interface SessionMetricsLegacy {
  loss: number | null;
  accuracy: number | null;
  learning_rate: number | null;
  elapsed_seconds: number;
  estimated_remaining_seconds: number | null;
}

export interface SessionProgressUpdate {
  type: 'session_progress';
  session_id: string;
  status: string;
  progress: SessionProgress;
  metrics: SessionMetricsLegacy;
  timestamp?: string;
}

type TrainingMessage =
  | OllamaMetrics
  | TrainingUpdate
  | SessionProgressUpdate
  | SessionUpdate
  | LogLineMessage
  | { type: string; [key: string]: unknown };

interface UseTrainingWebSocketOptions {
  autoConnect?: boolean;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
  onSessionUpdate?: (update: SessionUpdate) => void;
  onLogLine?: (log: LogLineMessage) => void;
}

interface UseTrainingWebSocketReturn {
  connected: boolean;
  connecting: boolean;
  error: string | null;
  ollamaMetrics: OllamaMetrics | null;
  trainingUpdate: TrainingUpdate | null;
  sessionProgress: SessionProgressUpdate | null;
  // New: real-time session updates
  sessionUpdates: Map<string, SessionUpdate>;
  sessionLogs: Map<string, LogLine[]>;
  connect: () => void;
  disconnect: () => void;
  subscribeToOllamaMetrics: (intervalSeconds?: number, ollamaUrl?: string) => void;
  unsubscribeFromOllamaMetrics: () => void;
  subscribeToTraining: (intervalSeconds?: number) => void;
  unsubscribeFromTraining: () => void;
  subscribeToSession: (sessionId: string, intervalSeconds?: number) => void;
  unsubscribeFromSession: (sessionId?: string) => void;
}

export function useTrainingWebSocket(
  options: UseTrainingWebSocketOptions = {}
): UseTrainingWebSocketReturn {
  const {
    autoConnect = false,
    reconnectInterval = 5000,
    maxReconnectAttempts = 5,
    onSessionUpdate,
    onLogLine,
  } = options;

  const [connected, setConnected] = useState(false);
  const [connecting, setConnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [ollamaMetrics, setOllamaMetrics] = useState<OllamaMetrics | null>(null);
  const [trainingUpdate, setTrainingUpdate] = useState<TrainingUpdate | null>(null);
  const [sessionProgress, setSessionProgress] = useState<SessionProgressUpdate | null>(null);
  const [sessionUpdates, setSessionUpdates] = useState<Map<string, SessionUpdate>>(new Map());
  const [sessionLogs, setSessionLogs] = useState<Map<string, LogLine[]>>(new Map());

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const subscribedSessionsRef = useRef<Set<string>>(new Set());
  const connectingRef = useRef(false);
  const mountedRef = useRef(true);
  // Store callbacks in refs to avoid dependency issues
  const onSessionUpdateRef = useRef(onSessionUpdate);
  const onLogLineRef = useRef(onLogLine);

  // Keep refs updated with latest callbacks
  useEffect(() => {
    onSessionUpdateRef.current = onSessionUpdate;
  }, [onSessionUpdate]);

  useEffect(() => {
    onLogLineRef.current = onLogLine;
  }, [onLogLine]);

  const getWsUrl = useCallback(() => {
    const baseUrl = getApiBaseUrl();
    // Convert http(s) to ws(s)
    const wsProtocol = baseUrl.startsWith('https') ? 'wss' : 'ws';
    const wsHost = baseUrl.replace(/^https?:\/\//, '');
    return `${wsProtocol}://${wsHost}/api/training/ws`;
  }, []);

  const handleMessage = useCallback((event: MessageEvent) => {
    try {
      const message: TrainingMessage = JSON.parse(event.data);

      switch (message.type) {
        case 'connected':
          console.log('[TrainingWS] Connected');
          break;

        case 'session_update':
          const sessionUpdate = message as SessionUpdate;
          setSessionUpdates(prev => {
            const updated = new Map(prev);
            updated.set(sessionUpdate.session_id, sessionUpdate);
            return updated;
          });
          // Use ref to avoid re-creating this callback
          onSessionUpdateRef.current?.(sessionUpdate);
          break;

        case 'log_line':
          const logMessage = message as LogLineMessage;
          setSessionLogs(prev => {
            const updated = new Map(prev);
            const logs = updated.get(logMessage.session_id) || [];
            // Keep last 500 logs per session
            const newLogs = [...logs, logMessage.data].slice(-500);
            updated.set(logMessage.session_id, newLogs);
            return updated;
          });
          // Use ref to avoid re-creating this callback
          onLogLineRef.current?.(logMessage);
          break;

        case 'ollama_metrics':
          setOllamaMetrics(message as OllamaMetrics);
          break;

        case 'training_update':
          setTrainingUpdate(message as TrainingUpdate);
          break;

        case 'session_progress':
          setSessionProgress(message as SessionProgressUpdate);
          break;

        case 'subscribed':
        case 'unsubscribed':
          console.log(`[TrainingWS] ${message.type}: ${(message as any).session_id}`);
          break;

        case 'ollama_metrics_subscribed':
        case 'ollama_metrics_unsubscribed':
        case 'training_subscribed':
        case 'training_unsubscribed':
        case 'session_subscribed':
        case 'session_unsubscribed':
          console.log(`[TrainingWS] ${message.type}`);
          break;

        case 'pong':
          // Heartbeat response
          break;

        case 'error':
          console.error('[TrainingWS] Error:', message);
          setError((message as { message?: string }).message || 'Unknown error');
          break;

        default:
          console.log('[TrainingWS] Unknown message:', message);
      }
    } catch (err) {
      console.error('[TrainingWS] Failed to parse message:', err);
    }
  }, []);

  const connect = useCallback(() => {
    // Check if already connected or connecting using refs to avoid dependency issues
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    if (wsRef.current?.readyState === WebSocket.CONNECTING) {
      return;
    }

    if (connectingRef.current) {
      return;
    }

    connectingRef.current = true;
    setConnecting(true);
    setError(null);

    const wsUrl = getWsUrl();
    console.log('[TrainingWS] Connecting to:', wsUrl);

    try {
      const ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        if (!mountedRef.current) return;
        console.log('[TrainingWS] Opened');
        connectingRef.current = false;
        setConnected(true);
        setConnecting(false);
        setError(null);
        reconnectAttemptsRef.current = 0;

        // Re-subscribe to all previously subscribed sessions
        subscribedSessionsRef.current.forEach((sessionId) => {
          ws.send(JSON.stringify({ type: 'subscribe', session_id: sessionId }));
        });
      };

      ws.onclose = (event) => {
        if (!mountedRef.current) return;
        console.log('[TrainingWS] Closed:', event.code, event.reason);
        connectingRef.current = false;
        setConnected(false);
        setConnecting(false);
        wsRef.current = null;

        // Auto-reconnect if not closed intentionally and component still mounted
        if (mountedRef.current && event.code !== 1000 && reconnectAttemptsRef.current < maxReconnectAttempts) {
          reconnectAttemptsRef.current += 1;
          console.log(
            `[TrainingWS] Reconnecting (attempt ${reconnectAttemptsRef.current}/${maxReconnectAttempts})...`
          );
          reconnectTimeoutRef.current = setTimeout(() => {
            if (mountedRef.current) {
              connect();
            }
          }, reconnectInterval);
        }
      };

      ws.onerror = (event) => {
        if (!mountedRef.current) return;
        console.error('[TrainingWS] Error:', event);
        setError('WebSocket connection error');
        connectingRef.current = false;
        setConnecting(false);
      };

      ws.onmessage = handleMessage;

      wsRef.current = ws;
    } catch (err) {
      console.error('[TrainingWS] Failed to create WebSocket:', err);
      setError(err instanceof Error ? err.message : 'Failed to connect');
      connectingRef.current = false;
      setConnecting(false);
    }
  }, [getWsUrl, handleMessage, maxReconnectAttempts, reconnectInterval]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    if (wsRef.current) {
      wsRef.current.close(1000, 'Client disconnect');
      wsRef.current = null;
    }

    connectingRef.current = false;
    setConnected(false);
    setConnecting(false);
    reconnectAttemptsRef.current = maxReconnectAttempts; // Prevent auto-reconnect
  }, [maxReconnectAttempts]);

  const sendMessage = useCallback((message: Record<string, unknown>) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    } else {
      console.warn('[TrainingWS] Not connected, cannot send message');
    }
  }, []);

  const subscribeToOllamaMetrics = useCallback(
    (intervalSeconds: number = 10, ollamaUrl?: string) => {
      sendMessage({
        type: 'subscribe_ollama_metrics',
        interval_seconds: intervalSeconds,
        ...(ollamaUrl && { ollama_url: ollamaUrl }),
      });
    },
    [sendMessage]
  );

  const unsubscribeFromOllamaMetrics = useCallback(() => {
    sendMessage({ type: 'unsubscribe_ollama_metrics' });
    setOllamaMetrics(null);
  }, [sendMessage]);

  const subscribeToTraining = useCallback(
    (intervalSeconds: number = 5) => {
      sendMessage({
        type: 'subscribe_training',
        interval_seconds: intervalSeconds,
      });
    },
    [sendMessage]
  );

  const unsubscribeFromTraining = useCallback(() => {
    sendMessage({ type: 'unsubscribe_training' });
    setTrainingUpdate(null);
  }, [sendMessage]);

  const subscribeToSession = useCallback(
    (sessionId: string, intervalSeconds: number = 2) => {
      subscribedSessionsRef.current.add(sessionId);
      sendMessage({
        type: 'subscribe',
        session_id: sessionId,
        interval_seconds: intervalSeconds,
      });
    },
    [sendMessage]
  );

  const unsubscribeFromSession = useCallback((sessionId?: string) => {
    if (sessionId) {
      subscribedSessionsRef.current.delete(sessionId);
      sendMessage({ type: 'unsubscribe', session_id: sessionId });
    } else {
      // Legacy: unsubscribe from current session
      sendMessage({ type: 'unsubscribe_session' });
    }
    setSessionProgress(null);
  }, [sendMessage]);

  // Auto-connect on mount if enabled
  useEffect(() => {
    mountedRef.current = true;

    if (autoConnect) {
      connect();
    }

    return () => {
      mountedRef.current = false;
      disconnect();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoConnect]);

  // Keepalive ping
  useEffect(() => {
    if (!connected) return;

    const pingInterval = setInterval(() => {
      sendMessage({ type: 'ping' });
    }, 30000);

    return () => clearInterval(pingInterval);
  }, [connected, sendMessage]);

  return {
    connected,
    connecting,
    error,
    ollamaMetrics,
    trainingUpdate,
    sessionProgress,
    sessionUpdates,
    sessionLogs,
    connect,
    disconnect,
    subscribeToOllamaMetrics,
    unsubscribeFromOllamaMetrics,
    subscribeToTraining,
    unsubscribeFromTraining,
    subscribeToSession,
    unsubscribeFromSession,
  };
}
