/**
 * Session Logs Modal - Displays training logs for a session
 */

import { useState, useEffect, useRef } from 'react';
import { apiClient } from '../../lib/api';
import { FileText, Download, RefreshCw, X, Radio } from 'lucide-react';

interface SessionLogsModalProps {
  sessionId: string | null;
  sessionName?: string;
  sessionStatus?: string;
  isOpen: boolean;
  onClose: () => void;
}

export default function SessionLogsModal({
  sessionId,
  sessionName,
  sessionStatus,
  isOpen,
  onClose,
}: SessionLogsModalProps) {
  // Only allow live refresh for running/preparing sessions (status is lowercase from API)
  const isSessionRunning = sessionStatus === 'running' || sessionStatus === 'preparing';
  const [logs, setLogs] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false); // Silent refresh indicator
  const [error, setError] = useState<string | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const logsEndRef = useRef<HTMLDivElement>(null);
  const logsContainerRef = useRef<HTMLDivElement>(null);
  const refreshIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const previousLogsLength = useRef<number>(0);

  const fetchLogs = async (silent = false) => {
    if (!sessionId) return;

    // Only show full loading on initial load, not on silent refreshes
    if (!silent) {
      setLoading(true);
    } else {
      setRefreshing(true);
    }
    setError(null);

    try {
      const data = await apiClient.get<{ logs: string | null }>(`/api/training/sessions/${sessionId}/logs`);
      // Only update if logs actually changed (compare length to avoid unnecessary re-renders)
      const newLogsLength = data.logs?.length || 0;
      if (newLogsLength !== previousLogsLength.current) {
        previousLogsLength.current = newLogsLength;
        setLogs(data.logs);
      }
    } catch (err: unknown) {
      const error = err as { message?: string };
      // Only show error on initial load, ignore errors during silent refresh
      if (!silent) {
        setError(error.message || 'Erreur lors du chargement des logs');
      }
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    if (isOpen && sessionId) {
      fetchLogs();
    }
    // Reset autoRefresh when modal opens - only enable for running sessions
    if (isOpen) {
      setAutoRefresh(isSessionRunning);
    }
  }, [isOpen, sessionId, isSessionRunning]);

  // Auto-refresh logs every 3 seconds when enabled (only for running sessions)
  useEffect(() => {
    if (isOpen && sessionId && autoRefresh && isSessionRunning) {
      refreshIntervalRef.current = setInterval(() => {
        fetchLogs(true); // Silent refresh
      }, 3000);
    }

    return () => {
      if (refreshIntervalRef.current) {
        clearInterval(refreshIntervalRef.current);
        refreshIntervalRef.current = null;
      }
    };
  }, [isOpen, sessionId, autoRefresh, isSessionRunning]);

  // Auto-scroll to bottom when logs are loaded or updated
  useEffect(() => {
    if (logs && !loading && logsContainerRef.current) {
      // Use setTimeout to ensure DOM is updated before scrolling
      setTimeout(() => {
        if (logsContainerRef.current) {
          logsContainerRef.current.scrollTop = logsContainerRef.current.scrollHeight;
        }
      }, 50);
    }
  }, [logs, loading]);

  const scrollToBottom = () => {
    if (logsContainerRef.current) {
      logsContainerRef.current.scrollTop = logsContainerRef.current.scrollHeight;
    }
  };

  const downloadLogs = () => {
    if (!logs) return;

    const blob = new Blob([logs], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `training-logs-${sessionId}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/50 transition-opacity"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="flex min-h-full items-center justify-center p-4">
        <div className="relative bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-hidden">
          {/* Header */}
          <div className="flex items-center justify-between px-6 py-4 border-b dark:border-gray-700">
            <div className="flex items-center gap-3">
              <FileText className="w-5 h-5 text-gray-500" />
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                Logs de la session
              </h2>
              {sessionName && (
                <span className="text-sm text-gray-500 dark:text-gray-400">
                  - {sessionName}
                </span>
              )}
            </div>
            <div className="flex items-center gap-2">
              {/* Live toggle - only show for running sessions */}
              {isSessionRunning && (
                <button
                  onClick={() => setAutoRefresh(!autoRefresh)}
                  className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                    autoRefresh
                      ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400'
                      : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400'
                  }`}
                  title={autoRefresh ? 'Désactiver le rafraîchissement automatique' : 'Activer le rafraîchissement automatique'}
                >
                  <Radio className={`w-3.5 h-3.5 ${autoRefresh ? 'animate-pulse' : ''}`} />
                  Live
                </button>
              )}
              <button
                onClick={() => fetchLogs(false)}
                disabled={loading || refreshing}
                className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 disabled:opacity-50"
                title="Rafraîchir"
              >
                <RefreshCw className={`w-5 h-5 ${loading || refreshing ? 'animate-spin' : ''}`} />
              </button>
              {logs && (
                <button
                  onClick={downloadLogs}
                  className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                  title="Télécharger"
                >
                  <Download className="w-5 h-5" />
                </button>
              )}
              <button
                onClick={onClose}
                className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
          </div>

          {/* Content */}
          <div ref={logsContainerRef} className="px-6 py-4 overflow-y-auto max-h-[calc(90vh-140px)]">
            {loading && (
              <div className="flex items-center justify-center py-12">
                <div className="animate-spin rounded-full h-8 w-8 border-2 border-blue-500 border-t-transparent"></div>
              </div>
            )}

            {error && (
              <div className="bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 p-4 rounded-lg">
                {error}
              </div>
            )}

            {!loading && !error && logs === null && (
              <div className="text-center py-12 text-gray-500 dark:text-gray-400">
                <FileText className="w-12 h-12 mx-auto mb-4 opacity-50" />
                <p>Aucun log disponible pour cette session</p>
                <p className="text-sm mt-2">
                  Les logs sont enregistrés à la fin de l'entraînement
                </p>
              </div>
            )}

            {!loading && !error && logs && (
              <div className="bg-gray-900 dark:bg-black rounded-lg p-4 font-mono text-sm overflow-x-auto">
                <pre className="text-gray-100 whitespace-pre-wrap break-words">
                  {logs}
                </pre>
                <div ref={logsEndRef} />
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="flex justify-between items-center px-6 py-4 border-t dark:border-gray-700">
            <div className="text-sm text-gray-500 dark:text-gray-400">
              {logs && `${logs.split('\n').length} lignes`}
            </div>
            <div className="flex gap-2">
              {logs && (
                <button
                  onClick={scrollToBottom}
                  className="px-4 py-2 text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200 transition-colors"
                >
                  Aller à la fin
                </button>
              )}
              <button
                onClick={onClose}
                className="px-4 py-2 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
              >
                Fermer
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
