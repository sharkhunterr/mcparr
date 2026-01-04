import { useState, useEffect } from 'react';
import type { FC } from 'react';
import {
  Search,
  XCircle,
  Activity,
  Filter
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { getApiBaseUrl } from '../../lib/api';
import { getServiceColor } from '../../lib/serviceColors';

interface UserSuggestion {
  central_user_id: string;
  service_config_id: string;
  service_user_id?: string;
  service_username?: string;
  service_email?: string;
  confidence_score: number;
  matching_attributes: string[];
  role: string;
  metadata: Record<string, any>;
}

interface DetectionResults {
  total_services: number;
  services_scanned: number;
  total_suggestions: number;
  suggestions: UserSuggestion[];
  high_confidence_suggestions: UserSuggestion[];
  medium_confidence_suggestions: UserSuggestion[];
  low_confidence_suggestions: UserSuggestion[];
  errors: string[];
  service_combinations?: Array<{
    service_1: string;
    service_2: string;
    suggestions_found: number;
  }>;
  started_at: string;
  completed_at?: string;
}

interface UserMappingDetectorProps {
  onDetectionComplete?: (results: DetectionResults) => void;
}

const UserMappingDetector: FC<UserMappingDetectorProps> = ({
  onDetectionComplete
}) => {
  const { t } = useTranslation('users');
  const [detecting, setDetecting] = useState(false);
  const [results, setResults] = useState<DetectionResults | null>(null);
  const [availableServices, setAvailableServices] = useState<any[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [selectedSuggestions, setSelectedSuggestions] = useState<Set<number>>(new Set());
  const [confidenceFilter, setConfidenceFilter] = useState<'all' | 'high' | 'medium' | 'low'>('all');

  useEffect(() => {
    fetchAvailableServices();
  }, []);

  const fetchAvailableServices = async () => {
    try {
      const response = await fetch(`${getApiBaseUrl()}/api/services/`);
      const services = await response.json();

      // Get all enabled services for display
      const enabledServices = services.filter(
        (service: any) => service.enabled
      );
      setAvailableServices(enabledServices);
    } catch (err) {
      console.error('Failed to fetch services:', err);
      setError('Failed to load available services');
    }
  };

  const startDetection = async () => {
    if (availableServices.length < 2) {
      setError(t('detector.needTwoServices'));
      return;
    }

    setDetecting(true);
    setResults(null);
    setError(null);
    setSelectedSuggestions(new Set());

    try {
      console.log('🔍 Starting automatic user mapping detection across all services...');

      const response = await fetch(`${getApiBaseUrl()}/api/users/auto-detect-mappings`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || t('errors.detectFailed'));
      }

      const detectionResults = await response.json();
      console.log('✅ Detection completed:', detectionResults);

      setResults(detectionResults);
      onDetectionComplete?.(detectionResults);

    } catch (err) {
      console.error('❌ Detection failed:', err);
      const errorMessage = err instanceof Error ? err.message : 'Unknown error occurred';
      setError(errorMessage);
    } finally {
      setDetecting(false);
    }
  };

  // Toggle all suggestions for a user group
  const toggleUserGroupSelection = (userGroup: any) => {
    const newSelection = new Set(selectedSuggestions);
    const groupIndices = userGroup.suggestions.map((suggestion: any) =>
      results!.suggestions.indexOf(suggestion)
    );

    const allSelected = groupIndices.every((idx: number) => newSelection.has(idx));

    if (allSelected) {
      // Deselect all
      groupIndices.forEach((idx: number) => newSelection.delete(idx));
    } else {
      // Select all
      groupIndices.forEach((idx: number) => newSelection.add(idx));
    }

    setSelectedSuggestions(newSelection);
  };

  const selectAllByConfidence = (confidence: 'high' | 'medium' | 'low') => {
    if (!results) return;

    const suggestionsToSelect = results[`${confidence}_confidence_suggestions`] || [];
    const newSelection = new Set(selectedSuggestions);

    suggestionsToSelect.forEach((suggestion) => {
      const globalIndex = results.suggestions.indexOf(suggestion);
      if (globalIndex !== -1) {
        newSelection.add(globalIndex);
      }
    });

    setSelectedSuggestions(newSelection);
  };

  const createMappingsFromSelected = async () => {
    if (!results || selectedSuggestions.size === 0) {
      setError(t('detector.selectOne'));
      return;
    }

    try {
      const selectedSuggestionsArray = Array.from(selectedSuggestions).map(
        index => results.suggestions[index]
      );

      const response = await fetch(`${getApiBaseUrl()}/api/users/create-from-suggestions`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          suggestions: selectedSuggestionsArray,
          auto_approve_high_confidence: false
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || t('errors.createFailed'));
      }

      const createResults = await response.json();
      console.log('✅ Mappings created:', createResults);

      // Reset selection and show success
      setSelectedSuggestions(new Set());
      setError(null);

      // Optionally refresh detection results
      alert(t('detector.createSuccess', { count: createResults.created_mappings }));

    } catch (err) {
      console.error('❌ Failed to create mappings:', err);
      const errorMessage = err instanceof Error ? err.message : 'Failed to create mappings';
      setError(errorMessage);
    }
  };

  const getConfidenceColor = (score: number) => {
    if (score >= 0.9) return 'text-green-600 bg-green-100';
    if (score >= 0.7) return 'text-yellow-600 bg-yellow-100';
    return 'text-red-600 bg-red-100';
  };

  const getConfidenceBadge = (score: number) => {
    if (score >= 0.9) return t('detector.confidence.high');
    if (score >= 0.7) return t('detector.confidence.medium');
    return t('detector.confidence.low');
  };

  const getFilteredSuggestions = () => {
    if (!results) return [];

    switch (confidenceFilter) {
      case 'high':
        return results.high_confidence_suggestions;
      case 'medium':
        return results.medium_confidence_suggestions;
      case 'low':
        return results.low_confidence_suggestions;
      default:
        return results.suggestions;
    }
  };

  // Group suggestions by central user ID to show all services for each user
  const getGroupedSuggestions = () => {
    const suggestions = getFilteredSuggestions();
    const grouped: Record<string, typeof suggestions> = {};

    suggestions.forEach((suggestion) => {
      const key = suggestion.central_user_id;
      if (!grouped[key]) {
        grouped[key] = [];
      }
      grouped[key].push(suggestion);
    });

    return Object.entries(grouped).map(([centralUserId, userSuggestions]) => ({
      centralUserId,
      suggestions: userSuggestions,
      // Calculate average confidence for this user
      avgConfidence: userSuggestions.reduce((sum, s) => sum + s.confidence_score, 0) / userSuggestions.length,
      // Use the best suggestion for display purposes
      mainSuggestion: userSuggestions.reduce((best, current) =>
        current.confidence_score > best.confidence_score ? current : best
      )
    }));
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
      <div className="p-3 sm:p-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div className="flex items-center space-x-3 min-w-0">
            <Search className="w-5 h-5 sm:w-6 sm:h-6 text-blue-600 flex-shrink-0" />
            <div className="min-w-0">
              <h3 className="text-base sm:text-lg font-semibold text-gray-900 dark:text-white">
                {t('detector.title')}
              </h3>
              <p className="text-xs sm:text-sm text-gray-600 dark:text-gray-400">
                {t('detector.description')}
              </p>
            </div>
          </div>

          <button
            onClick={startDetection}
            disabled={detecting || availableServices.length < 2}
            className="w-full sm:w-auto flex items-center justify-center space-x-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-sm"
            title={availableServices.length < 2 ? t('detector.needTwoServices') : t('detector.detect')}
          >
            {detecting ? (
              <Activity className="w-4 h-4 animate-pulse" />
            ) : (
              <Search className="w-4 h-4" />
            )}
            <span>{detecting ? t('detector.scanning') : t('detector.detect')}</span>
          </button>
        </div>
      </div>

      <div className="p-3 sm:p-4">
        {/* Available Services Display - Compact */}
        <div className="mb-3">
          <div className="flex items-center flex-wrap gap-2">
            <span className="text-xs font-medium text-gray-500 dark:text-gray-400">{t('detector.servicesLabel', { count: availableServices.length })}:</span>
            {availableServices.length > 0 ? (
              availableServices.map((service) => (
                <span
                  key={service.id}
                  className="inline-flex items-center gap-1.5 px-2 py-0.5 text-xs font-medium rounded-full border border-gray-200 dark:border-gray-600 bg-gray-50 dark:bg-gray-700/50 text-gray-700 dark:text-gray-300"
                >
                  <span className={`w-2 h-2 rounded-full flex-shrink-0 ${getServiceColor(service.service_type).dot}`}></span>
                  {service.name}
                </span>
              ))
            ) : (
              <span className="text-xs text-gray-500 dark:text-gray-400 italic">{t('detector.noServices')}</span>
            )}
          </div>
        </div>

        {/* Error Display */}
        {error && (
          <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-800">
            <div className="flex items-center">
              <XCircle className="w-5 h-5 text-red-500 mr-2" />
              <span className="text-sm text-red-700 dark:text-red-400">{error}</span>
            </div>
          </div>
        )}

        {/* Detection Progress */}
        {detecting && (
          <div className="mb-4 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
            <div className="flex items-center">
              <Activity className="w-5 h-5 text-blue-500 mr-2 animate-spin" />
              <span className="text-sm text-blue-700 dark:text-blue-400">
                {t('detector.scanInProgress')}
              </span>
            </div>
          </div>
        )}

        {/* Detection Results */}
        {results && (
          <div className="space-y-3">
            {/* Confidence Filters */}
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
              <div className="flex items-center space-x-2">
                <Filter className="w-4 h-4 text-gray-500 dark:text-gray-400" />
                <select
                  value={confidenceFilter}
                  onChange={(e) => setConfidenceFilter(e.target.value as any)}
                  className="px-2 py-1.5 text-xs sm:text-sm border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded"
                >
                  <option value="all">{t('detector.allFilter', { count: results.total_suggestions })}</option>
                  <option value="high">{t('detector.highFilter', { count: results.high_confidence_suggestions.length })}</option>
                  <option value="medium">{t('detector.mediumFilter', { count: results.medium_confidence_suggestions.length })}</option>
                  <option value="low">{t('detector.lowFilter', { count: results.low_confidence_suggestions.length })}</option>
                </select>
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={() => selectAllByConfidence('high')}
                  className="px-2 sm:px-3 py-1.5 text-xs bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 rounded hover:bg-green-200 dark:hover:bg-green-900/50 transition-colors"
                >
                  {t('detector.selectHighConf')}
                </button>
                <button
                  onClick={createMappingsFromSelected}
                  disabled={selectedSuggestions.size === 0}
                  className="px-3 py-1.5 text-xs sm:text-sm bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50 transition-colors"
                >
                  {t('detector.create', { count: selectedSuggestions.size })}
                </button>
              </div>
            </div>

            {/* Users List - Grouped by Central User */}
            {getGroupedSuggestions().length > 0 ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-3 max-h-80 sm:max-h-96 overflow-y-auto">
                {getGroupedSuggestions().map((userGroup) => {
                const groupIndices = userGroup.suggestions.map(suggestion =>
                  results!.suggestions.indexOf(suggestion)
                );
                const allSelected = groupIndices.every(idx => selectedSuggestions.has(idx));
                const someSelected = groupIndices.some(idx => selectedSuggestions.has(idx));

                const mainSuggestion = userGroup.mainSuggestion;
                const sourceUser = mainSuggestion.metadata?.source_user;
                const targetUser = mainSuggestion.metadata?.target_user;
                const displayEmail = targetUser?.email || mainSuggestion.service_email;

                // Use the best display name available
                const mainName = targetUser?.username || targetUser?.friendly_name ||
                               sourceUser?.name || mainSuggestion.service_username ||
                               userGroup.centralUserId;

                return (
                  <div
                    key={userGroup.centralUserId}
                    className={`p-3 border rounded-lg cursor-pointer transition-all duration-200 ${
                      allSelected
                        ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20 shadow-sm'
                        : someSelected
                        ? 'border-yellow-400 bg-yellow-50 dark:bg-yellow-900/20 shadow-sm'
                        : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600 hover:shadow-sm bg-white dark:bg-gray-800'
                    }`}
                    onClick={() => toggleUserGroupSelection(userGroup)}
                  >
                    <div className="space-y-2">
                      {/* Header with checkbox and confidence */}
                      <div className="flex items-start justify-between">
                        <input
                          type="checkbox"
                          checked={allSelected}
                          ref={(el) => {
                            if (el) el.indeterminate = someSelected && !allSelected;
                          }}
                          onChange={() => toggleUserGroupSelection(userGroup)}
                          className="mt-1 rounded border-gray-300 dark:border-gray-600 text-blue-600 focus:ring-blue-500"
                        />
                        <div className="flex items-center space-x-2">
                          <span className={`px-2 py-1 text-xs font-medium rounded ${getConfidenceColor(userGroup.avgConfidence)}`}>
                            {getConfidenceBadge(userGroup.avgConfidence)} {Math.round(userGroup.avgConfidence * 100)}%
                          </span>
                          <span className="px-2 py-1 text-xs font-medium bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded">
                            {t('detector.services', { count: userGroup.suggestions.length })}
                          </span>
                        </div>
                      </div>

                      {/* Main name and email */}
                      <div className="flex items-center justify-between">
                        <h3 className="font-semibold text-gray-900 dark:text-white text-base">{mainName}</h3>
                        {displayEmail && (
                          <span className="text-xs text-gray-500 dark:text-gray-400 ml-2">{displayEmail}</span>
                        )}
                      </div>

                      {/* Service details - show all services with user info */}
                      <div className="space-y-2">
                        {userGroup.suggestions.map((suggestion, idx) => {
                          const serviceType = suggestion.metadata?.target_service?.toLowerCase() || 'unknown';
                          const colors = getServiceColor(serviceType);

                          // Get user details from metadata
                          const targetUser = suggestion.metadata?.target_user || {};
                          const userId = targetUser.id || targetUser.user_id || suggestion.service_user_id || '-';
                          const username = targetUser.username || targetUser.friendly_name || targetUser.name || suggestion.service_username || '-';
                          const email = targetUser.email || suggestion.service_email || '-';

                          return (
                            <div key={idx} className={`p-2 border rounded ${colors.border} ${colors.bg}`}>
                              <div className="flex items-center space-x-2 mb-1">
                                <div className={`w-2.5 h-2.5 ${colors.dot} rounded-full`}></div>
                                <span className={`text-xs font-semibold capitalize ${colors.text}`}>{serviceType}</span>
                              </div>
                              <div className="grid grid-cols-3 gap-1 text-xs">
                                <div>
                                  <span className="text-gray-500">ID:</span>
                                  <span className="ml-1 text-gray-800 font-mono">{String(userId).substring(0, 12)}{String(userId).length > 12 ? '...' : ''}</span>
                                </div>
                                <div>
                                  <span className="text-gray-500">User:</span>
                                  <span className="ml-1 text-gray-800">{username}</span>
                                </div>
                                <div>
                                  <span className="text-gray-500">Email:</span>
                                  <span className="ml-1 text-gray-800">{email !== '-' ? email : <span className="text-gray-400">-</span>}</span>
                                </div>
                              </div>
                            </div>
                          );
                        })}
                      </div>

                      {/* Matching criteria badges - show all unique attributes */}
                      <div className="flex flex-wrap gap-1">
                        {Array.from(new Set(userGroup.suggestions.flatMap(s => s.matching_attributes))).map((attr, idx) => (
                          <span
                            key={idx}
                            className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-green-100 text-green-700"
                          >
                            {attr === 'id_exact' && t('matching.sameId')}
                            {attr === 'username_exact' && t('matching.sameUsername')}
                            {attr === 'email_exact' && t('matching.sameEmail')}
                            {attr === 'friendly_name_exact' && t('matching.sameDisplayName')}
                            {attr === 'username_friendly_match' && t('matching.usernameFriendlyMatch')}
                            {attr === 'username_fuzzy' && t('matching.usernameFuzzy')}
                            {attr === 'email_fuzzy' && t('matching.emailFuzzy')}
                            {attr === 'name_fuzzy' && t('matching.nameFuzzy')}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                );
                })}
              </div>
            ) : (
              <div className="text-center py-6 sm:py-8 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-gray-200 dark:border-gray-700">
                <Search className="w-10 h-10 sm:w-12 sm:h-12 text-gray-400 mx-auto mb-3 sm:mb-4" />
                <h3 className="text-base sm:text-lg font-medium text-gray-900 dark:text-white mb-2">{t('detector.noMappings')}</h3>
                <p className="text-sm text-gray-600 dark:text-gray-400 mb-3 sm:mb-4 px-4">
                  {t('detector.noMappingsDesc')}
                </p>
                <p className="text-sm text-blue-600 dark:text-blue-400">
                  {t('detector.useManual')}
                </p>
              </div>
            )}

            {/* Errors */}
            {results.errors.length > 0 && (
              <div className="space-y-2">
                <h4 className="text-sm font-medium text-gray-900 dark:text-white">{t('detector.detectionErrors')}</h4>
                {results.errors.map((error, index) => (
                  <div key={index} className="p-2 bg-red-50 dark:bg-red-900/20 rounded text-red-700 dark:text-red-400 text-sm">
                    {error}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default UserMappingDetector;