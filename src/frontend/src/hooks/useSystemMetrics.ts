import { useState, useEffect, useRef, useCallback } from 'react';
import type { SystemMetrics } from '../types/api';
import { getApiBaseUrl } from '../lib/api';

interface UseSystemMetricsOptions {
  interval?: number;
  autoConnect?: boolean;
}

interface UseSystemMetricsReturn {
  metrics: SystemMetrics | null;
  connected: boolean;
  loading: boolean;
  error: string | null;
  connect: () => void;
  disconnect: () => void;
}

export function useSystemMetrics(
  options: UseSystemMetricsOptions = {}
): UseSystemMetricsReturn {
  const { interval = 5000, autoConnect = true } = options;

  const [metrics, setMetrics] = useState<SystemMetrics | null>(null);
  const [connected, setConnected] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchMetrics = useCallback(async () => {
    try {
      const response = await fetch(`${getApiBaseUrl()}/api/v1/system/system-metrics`);

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      setMetrics(data);
      setConnected(true);
      setLoading(false);
      setError(null);
    } catch (err) {
      console.error('Failed to fetch system metrics:', err);
      setError(err instanceof Error ? err.message : 'Failed to fetch system metrics');
      setConnected(false);
      setLoading(false);
    }
  }, []);

  const connect = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
    }

    // Fetch immediately
    fetchMetrics();

    // Set up polling
    intervalRef.current = setInterval(fetchMetrics, interval);
  }, [fetchMetrics, interval]);

  const disconnect = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }

    setConnected(false);
  }, []);

  useEffect(() => {
    if (autoConnect) {
      connect();
    }

    return () => {
      disconnect();
    };
  }, [autoConnect, connect, disconnect]);

  return {
    metrics,
    connected,
    loading,
    error,
    connect,
    disconnect
  };
}
