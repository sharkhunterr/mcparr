import React, { useState } from 'react';
import { getApiBaseUrl } from '../lib/api';

interface LogExportProps {
  filters?: {
    level?: string;
    source?: string;
    service_id?: string;
    search?: string;
    start_time?: string;
    end_time?: string;
  };
  onClose?: () => void;
}

type ExportFormat = 'json' | 'csv' | 'text';

const formatDescriptions: Record<ExportFormat, string> = {
  json: 'Complete data with all fields, ideal for programmatic processing',
  csv: 'Spreadsheet-compatible format for analysis in Excel or similar tools',
  text: 'Human-readable log file format, similar to traditional server logs',
};

export const LogExport: React.FC<LogExportProps> = ({ filters = {}, onClose }) => {
  const [format, setFormat] = useState<ExportFormat>('json');
  const [limit, setLimit] = useState(10000);
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleExport = async () => {
    setExporting(true);
    setError(null);

    try {
      const apiUrl = getApiBaseUrl();
      const params = new URLSearchParams({
        format,
        limit: limit.toString(),
      });

      // Add filters to params
      if (filters.level) params.append('level', filters.level);
      if (filters.source) params.append('source', filters.source);
      if (filters.service_id) params.append('service_id', filters.service_id);
      if (filters.search) params.append('search', filters.search);
      if (filters.start_time) params.append('start_time', filters.start_time);
      if (filters.end_time) params.append('end_time', filters.end_time);

      const response = await fetch(`${apiUrl}/api/logs/export?${params.toString()}`);

      if (!response.ok) {
        throw new Error(`Export failed: ${response.statusText}`);
      }

      // Get filename from Content-Disposition header or generate one
      const contentDisposition = response.headers.get('Content-Disposition');
      let filename = `mcparr_logs.${format === 'text' ? 'log' : format}`;
      if (contentDisposition) {
        const match = contentDisposition.match(/filename="?([^"]+)"?/);
        if (match) filename = match[1];
      }

      // Download the file
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      if (onClose) onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Export failed');
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
          Export Logs
        </h3>
        <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
          Export logs with current filters applied. Choose a format and maximum number of logs to export.
        </p>
      </div>

      {/* Format Selection */}
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Export Format
        </label>
        <div className="space-y-2">
          {(['json', 'csv', 'text'] as ExportFormat[]).map((fmt) => (
            <label
              key={fmt}
              className={`flex items-start p-3 rounded-lg border cursor-pointer transition-colors ${
                format === fmt
                  ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                  : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
              }`}
            >
              <input
                type="radio"
                name="format"
                value={fmt}
                checked={format === fmt}
                onChange={() => setFormat(fmt)}
                className="mt-1 text-blue-600 focus:ring-blue-500"
              />
              <div className="ml-3">
                <span className="block text-sm font-medium text-gray-900 dark:text-white uppercase">
                  {fmt}
                </span>
                <span className="block text-xs text-gray-500 dark:text-gray-400">
                  {formatDescriptions[fmt]}
                </span>
              </div>
            </label>
          ))}
        </div>
      </div>

      {/* Limit Selection */}
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Maximum Logs to Export
        </label>
        <select
          value={limit}
          onChange={(e) => setLimit(parseInt(e.target.value, 10))}
          className="w-full rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white shadow-sm focus:border-blue-500 focus:ring-blue-500"
        >
          <option value={1000}>1,000 logs</option>
          <option value={5000}>5,000 logs</option>
          <option value={10000}>10,000 logs</option>
          <option value={25000}>25,000 logs</option>
          <option value={50000}>50,000 logs</option>
          <option value={100000}>100,000 logs</option>
        </select>
        <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
          Larger exports may take longer to process and download
        </p>
      </div>

      {/* Active Filters Info */}
      {Object.keys(filters).some(k => filters[k as keyof typeof filters]) && (
        <div className="p-3 bg-gray-50 dark:bg-gray-900 rounded-lg">
          <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Active Filters:
          </p>
          <div className="flex flex-wrap gap-2">
            {filters.level && (
              <span className="px-2 py-1 text-xs bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300 rounded">
                Level: {filters.level}
              </span>
            )}
            {filters.source && (
              <span className="px-2 py-1 text-xs bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300 rounded">
                Source: {filters.source}
              </span>
            )}
            {filters.search && (
              <span className="px-2 py-1 text-xs bg-purple-100 text-purple-700 dark:bg-purple-900 dark:text-purple-300 rounded">
                Search: {filters.search}
              </span>
            )}
          </div>
        </div>
      )}

      {/* Error Message */}
      {error && (
        <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
          <p className="text-sm text-red-700 dark:text-red-300">{error}</p>
        </div>
      )}

      {/* Actions */}
      <div className="flex justify-end gap-3">
        {onClose && (
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-gray-700 dark:text-gray-300 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
          >
            Cancel
          </button>
        )}
        <button
          type="button"
          onClick={handleExport}
          disabled={exporting}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
        >
          {exporting ? (
            <>
              <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                  fill="none"
                />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                />
              </svg>
              Exporting...
            </>
          ) : (
            <>
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
                />
              </svg>
              Export Logs
            </>
          )}
        </button>
      </div>
    </div>
  );
};

export default LogExport;
