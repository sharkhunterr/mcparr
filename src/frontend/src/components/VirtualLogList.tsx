import React, { useRef, useCallback, useState, useEffect } from 'react';

interface LogEntry {
  id: string;
  level: string;
  message: string;
  source: string;
  component: string | null;
  logged_at: string;
  duration_ms: number | null;
}

interface VirtualLogListProps {
  logs: LogEntry[];
  onLogClick?: (log: LogEntry) => void;
  rowHeight?: number;
  overscan?: number;
  className?: string;
}

const levelColors: Record<string, string> = {
  debug: 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300',
  info: 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300',
  warning: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300',
  error: 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300',
  critical: 'bg-purple-100 text-purple-700 dark:bg-purple-900 dark:text-purple-300',
};

export const VirtualLogList: React.FC<VirtualLogListProps> = ({
  logs,
  onLogClick,
  rowHeight = 48,
  overscan = 5,
  className = '',
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [scrollTop, setScrollTop] = useState(0);
  const [containerHeight, setContainerHeight] = useState(0);

  // Calculate visible range
  const totalHeight = logs.length * rowHeight;
  const startIndex = Math.max(0, Math.floor(scrollTop / rowHeight) - overscan);
  const endIndex = Math.min(
    logs.length - 1,
    Math.ceil((scrollTop + containerHeight) / rowHeight) + overscan
  );
  const visibleLogs = logs.slice(startIndex, endIndex + 1);

  const handleScroll = useCallback((e: React.UIEvent<HTMLDivElement>) => {
    setScrollTop(e.currentTarget.scrollTop);
  }, []);

  useEffect(() => {
    const container = containerRef.current;
    if (container) {
      const resizeObserver = new ResizeObserver((entries) => {
        for (const entry of entries) {
          setContainerHeight(entry.contentRect.height);
        }
      });
      resizeObserver.observe(container);
      setContainerHeight(container.clientHeight);
      return () => resizeObserver.disconnect();
    }
  }, []);

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
    });
  };

  if (logs.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-gray-500 dark:text-gray-400">
        No logs to display
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className={`overflow-auto ${className}`}
      onScroll={handleScroll}
    >
      <div style={{ height: totalHeight, position: 'relative' }}>
        {visibleLogs.map((log, index) => {
          const actualIndex = startIndex + index;
          return (
            <div
              key={log.id}
              style={{
                position: 'absolute',
                top: actualIndex * rowHeight,
                height: rowHeight,
                left: 0,
                right: 0,
              }}
              className={`flex items-center px-4 border-b border-gray-200 dark:border-gray-700 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors ${
                actualIndex % 2 === 0 ? 'bg-white dark:bg-gray-800' : 'bg-gray-50 dark:bg-gray-850'
              }`}
              onClick={() => onLogClick?.(log)}
            >
              {/* Time */}
              <div className="w-24 flex-shrink-0 text-sm text-gray-500 dark:text-gray-400 font-mono">
                {formatTimestamp(log.logged_at)}
              </div>

              {/* Level */}
              <div className="w-20 flex-shrink-0">
                <span
                  className={`inline-flex px-2 py-0.5 text-xs font-medium rounded ${
                    levelColors[log.level] || levelColors.info
                  }`}
                >
                  {log.level.toUpperCase()}
                </span>
              </div>

              {/* Source */}
              <div className="w-32 flex-shrink-0 text-sm text-gray-900 dark:text-white truncate">
                {log.source}
                {log.component && (
                  <span className="text-gray-400 dark:text-gray-500">
                    /{log.component}
                  </span>
                )}
              </div>

              {/* Message */}
              <div className="flex-1 text-sm text-gray-700 dark:text-gray-300 truncate px-2">
                {log.message}
              </div>

              {/* Duration */}
              <div className="w-20 flex-shrink-0 text-sm text-gray-500 dark:text-gray-400 text-right">
                {log.duration_ms ? `${log.duration_ms}ms` : ''}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default VirtualLogList;
