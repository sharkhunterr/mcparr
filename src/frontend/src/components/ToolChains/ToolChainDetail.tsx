import { useState, useEffect } from 'react';
import type { FC } from 'react';
import {
  X,
  Save,
  Loader2,
  Info,
  Layers,
  Plus,
  Trash2,
  GripVertical,
  ArrowRight,
  ChevronDown,
  ChevronUp,
  MessageSquare,
  Target,
  ToggleLeft,
  ToggleRight,
  Pencil
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { getApiBaseUrl } from '../../lib/api';
import type { ToolChain, ToolChainStepDetail, StepTarget, AvailableTool, ConditionOperatorInfo } from '../../types/api';

interface ToolChainDetailProps {
  chain: ToolChain;
  onClose: () => void;
  onUpdated: () => void;
}

type TabType = 'info' | 'steps';

// Predefined colors for chains
const CHAIN_COLORS = [
  '#8b5cf6', '#3b82f6', '#10b981', '#f59e0b',
  '#ef4444', '#ec4899', '#06b6d4', '#84cc16',
];

const ToolChainDetail: FC<ToolChainDetailProps> = ({ chain, onClose, onUpdated }) => {
  const { t } = useTranslation('mcp');
  const [activeTab, setActiveTab] = useState<TabType>('steps');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Info tab state
  const [name, setName] = useState(chain.name);
  const [description, setDescription] = useState(chain.description || '');
  const [color, setColor] = useState(chain.color || '#8b5cf6');
  const [priority, setPriority] = useState(chain.priority);

  // Steps tab state
  const [steps, setSteps] = useState<ToolChainStepDetail[]>([]);
  const [stepsLoading, setStepsLoading] = useState(false);
  const [availableTools, setAvailableTools] = useState<AvailableTool[]>([]);
  const [operators, setOperators] = useState<ConditionOperatorInfo[]>([]);
  const [expandedSteps, setExpandedSteps] = useState<Set<string>>(new Set());

  // Add step form state
  const [showAddStep, setShowAddStep] = useState(false);
  const [newStepSourceService, setNewStepSourceService] = useState('');
  const [newStepSourceTool, setNewStepSourceTool] = useState('');
  const [newStepOperator, setNewStepOperator] = useState('success');
  const [newStepConditionField, setNewStepConditionField] = useState('');
  const [newStepConditionValue, setNewStepConditionValue] = useState('');
  const [newStepAiComment, setNewStepAiComment] = useState('');

  // Edit step form state
  const [editingStep, setEditingStep] = useState<ToolChainStepDetail | null>(null);
  const [editStepSourceService, setEditStepSourceService] = useState('');
  const [editStepSourceTool, setEditStepSourceTool] = useState('');
  const [editStepOperator, setEditStepOperator] = useState('success');
  const [editStepConditionField, setEditStepConditionField] = useState('');
  const [editStepConditionValue, setEditStepConditionValue] = useState('');
  const [editStepAiComment, setEditStepAiComment] = useState('');

  // Add target form state
  const [addingTargetToStep, setAddingTargetToStep] = useState<string | null>(null);
  const [newTargetService, setNewTargetService] = useState('');
  const [newTargetTool, setNewTargetTool] = useState('');
  const [newTargetMode, setNewTargetMode] = useState('sequential');
  const [newTargetComment, setNewTargetComment] = useState('');

  const backendUrl = getApiBaseUrl();

  useEffect(() => {
    if (activeTab === 'steps') {
      fetchSteps();
      fetchAvailableTools();
      fetchOperators();
    }
  }, [activeTab]);

  const fetchSteps = async () => {
    try {
      setStepsLoading(true);
      const response = await fetch(`${backendUrl}/api/tool-chains/${chain.id}/steps`);
      if (!response.ok) throw new Error('Failed to fetch steps');
      const data = await response.json();
      setSteps(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch steps');
    } finally {
      setStepsLoading(false);
    }
  };

  const fetchAvailableTools = async () => {
    try {
      const response = await fetch(`${backendUrl}/api/tool-chains/available-tools`);
      if (!response.ok) throw new Error('Failed to fetch tools');
      const data = await response.json();
      setAvailableTools(data.tools);
    } catch (err) {
      console.error('Failed to fetch tools:', err);
    }
  };

  const fetchOperators = async () => {
    try {
      const response = await fetch(`${backendUrl}/api/tool-chains/operators`);
      if (!response.ok) throw new Error('Failed to fetch operators');
      const data = await response.json();
      setOperators(data.operators);
    } catch (err) {
      console.error('Failed to fetch operators:', err);
    }
  };

  // Group tools by service
  const serviceGroups = availableTools.reduce((acc, tool) => {
    if (!acc[tool.service_type]) {
      acc[tool.service_type] = {
        service_name: tool.service_name,
        tools: []
      };
    }
    acc[tool.service_type].tools.push(tool);
    return acc;
  }, {} as Record<string, { service_name: string; tools: AvailableTool[] }>);

  const selectedNewStepOperator = operators.find(op => op.value === newStepOperator);
  const selectedEditStepOperator = operators.find(op => op.value === editStepOperator);

  const startEditingStep = (step: ToolChainStepDetail) => {
    setEditingStep(step);
    setEditStepSourceService(step.source_service);
    setEditStepSourceTool(step.source_tool);
    setEditStepOperator(step.condition_operator);
    setEditStepConditionField(step.condition_field || '');
    setEditStepConditionValue(step.condition_value || '');
    setEditStepAiComment(step.ai_comment || '');
  };

  const cancelEditingStep = () => {
    setEditingStep(null);
    setEditStepSourceService('');
    setEditStepSourceTool('');
    setEditStepOperator('success');
    setEditStepConditionField('');
    setEditStepConditionValue('');
    setEditStepAiComment('');
  };

  const handleUpdateStep = async () => {
    if (!editingStep || !editStepSourceService || !editStepSourceTool) return;

    try {
      setError(null);
      const response = await fetch(`${backendUrl}/api/tool-chains/${chain.id}/steps/${editingStep.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          source_service: editStepSourceService,
          source_tool: editStepSourceTool,
          condition_operator: editStepOperator,
          condition_field: editStepConditionField || null,
          condition_value: editStepConditionValue || null,
          ai_comment: editStepAiComment || null
        })
      });
      if (!response.ok) throw new Error('Failed to update step');

      cancelEditingStep();
      fetchSteps();
      onUpdated();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update step');
    }
  };

  const handleSaveInfo = async () => {
    try {
      setSaving(true);
      setError(null);
      const response = await fetch(`${backendUrl}/api/tool-chains/${chain.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name,
          description: description || null,
          color,
          priority
        })
      });
      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Failed to update chain');
      }
      onUpdated();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update chain');
    } finally {
      setSaving(false);
    }
  };

  const handleAddStep = async () => {
    if (!newStepSourceService || !newStepSourceTool) return;

    try {
      setError(null);
      const response = await fetch(`${backendUrl}/api/tool-chains/${chain.id}/steps`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          source_service: newStepSourceService,
          source_tool: newStepSourceTool,
          condition_operator: newStepOperator,
          condition_field: newStepConditionField || null,
          condition_value: newStepConditionValue || null,
          ai_comment: newStepAiComment || null,
          order: steps.length
        })
      });
      if (!response.ok) throw new Error('Failed to add step');

      // Reset form and refresh
      setNewStepSourceService('');
      setNewStepSourceTool('');
      setNewStepOperator('success');
      setNewStepConditionField('');
      setNewStepConditionValue('');
      setNewStepAiComment('');
      setShowAddStep(false);
      fetchSteps();
      onUpdated();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add step');
    }
  };

  const handleDeleteStep = async (stepId: string) => {
    if (!confirm(t('toolChains.detail.deleteStepConfirm'))) return;

    try {
      setError(null);
      const response = await fetch(`${backendUrl}/api/tool-chains/${chain.id}/steps/${stepId}`, {
        method: 'DELETE'
      });
      if (!response.ok) throw new Error('Failed to delete step');
      fetchSteps();
      onUpdated();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete step');
    }
  };

  const handleToggleStepEnabled = async (step: ToolChainStepDetail) => {
    try {
      setError(null);
      const response = await fetch(`${backendUrl}/api/tool-chains/${chain.id}/steps/${step.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled: !step.enabled })
      });
      if (!response.ok) throw new Error('Failed to update step');
      fetchSteps();
      onUpdated();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update step');
    }
  };

  const handleAddTarget = async (stepId: string) => {
    if (!newTargetService || !newTargetTool) return;

    try {
      setError(null);
      const step = steps.find(s => s.id === stepId);
      const response = await fetch(`${backendUrl}/api/tool-chains/${chain.id}/steps/${stepId}/targets`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          target_service: newTargetService,
          target_tool: newTargetTool,
          execution_mode: newTargetMode,
          target_ai_comment: newTargetComment || null,
          order: step?.targets?.length || 0
        })
      });
      if (!response.ok) throw new Error('Failed to add target');

      // Reset form and refresh
      setNewTargetService('');
      setNewTargetTool('');
      setNewTargetMode('sequential');
      setNewTargetComment('');
      setAddingTargetToStep(null);
      fetchSteps();
      onUpdated();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add target');
    }
  };

  const handleDeleteTarget = async (stepId: string, targetId: string) => {
    if (!confirm(t('toolChains.detail.deleteTargetConfirm'))) return;

    try {
      setError(null);
      const response = await fetch(`${backendUrl}/api/tool-chains/${chain.id}/steps/${stepId}/targets/${targetId}`, {
        method: 'DELETE'
      });
      if (!response.ok) throw new Error('Failed to delete target');
      fetchSteps();
      onUpdated();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete target');
    }
  };

  const handleToggleTargetEnabled = async (stepId: string, target: StepTarget) => {
    try {
      setError(null);
      const response = await fetch(`${backendUrl}/api/tool-chains/${chain.id}/steps/${stepId}/targets/${target.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled: !target.enabled })
      });
      if (!response.ok) throw new Error('Failed to update target');
      fetchSteps();
      onUpdated();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update target');
    }
  };

  const toggleStepExpanded = (stepId: string) => {
    setExpandedSteps(prev => {
      const newSet = new Set(prev);
      if (newSet.has(stepId)) {
        newSet.delete(stepId);
      } else {
        newSet.add(stepId);
      }
      return newSet;
    });
  };

  const getOperatorLabel = (value: string) => {
    const op = operators.find(o => o.value === value);
    return op?.label || value;
  };

  const tabs: { id: TabType; label: string; icon: React.ReactNode }[] = [
    { id: 'steps', label: t('toolChains.detail.tabs.steps'), icon: <Layers className="w-4 h-4" /> },
    { id: 'info', label: t('toolChains.detail.tabs.info'), icon: <Info className="w-4 h-4" /> },
  ];

  return (
    <div className="h-full flex flex-col">
      {/* Header - hidden on mobile as we have back button in parent */}
      <div className="hidden md:flex px-4 py-3 border-b border-gray-200 dark:border-gray-700 items-center justify-between">
        <div className="flex items-center space-x-3">
          <div
            className="w-8 h-8 rounded-full flex items-center justify-center"
            style={{ backgroundColor: color + '30' }}
          >
            <div className="w-4 h-4 rounded-full" style={{ backgroundColor: color }} />
          </div>
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white truncate">{chain.name}</h2>
        </div>
        <button
          onClick={onClose}
          className="p-1.5 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Mobile header with chain name */}
      <div className="md:hidden px-3 py-2 border-b border-gray-200 dark:border-gray-700 flex items-center space-x-2">
        <div className="w-4 h-4 rounded-full" style={{ backgroundColor: color }} />
        <h2 className="text-base font-semibold text-gray-900 dark:text-white truncate">{chain.name}</h2>
      </div>

      {/* Tabs */}
      <div className="px-3 sm:px-4 py-2 border-b border-gray-200 dark:border-gray-700">
        <div className="flex space-x-1">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center space-x-1.5 sm:space-x-2 px-2.5 sm:px-3 py-1.5 sm:py-2 text-xs sm:text-sm font-medium rounded-lg transition-colors ${
                activeTab === tab.id
                  ? 'bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300'
                  : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700'
              }`}
            >
              {tab.icon}
              <span>{tab.label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="mx-3 sm:mx-4 mt-3 sm:mt-4 p-3 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-800">
          <span className="text-sm text-red-700 dark:text-red-400">{error}</span>
        </div>
      )}

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-3 sm:p-4">
        {activeTab === 'info' && (
          <div className="space-y-4">
            {/* Name */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                {t('toolChains.detail.name')}
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              />
            </div>

            {/* Description */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                {t('toolChains.detail.description')}
              </label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={2}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent resize-none"
              />
            </div>

            {/* Color Selection */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                {t('toolChains.detail.color')}
              </label>
              <div className="flex flex-wrap gap-2">
                {CHAIN_COLORS.map((c) => (
                  <button
                    key={c}
                    type="button"
                    onClick={() => setColor(c)}
                    className={`w-8 h-8 rounded-full transition-all ${
                      color === c
                        ? 'ring-2 ring-offset-2 ring-gray-400 dark:ring-offset-gray-800'
                        : 'hover:scale-110'
                    }`}
                    style={{ backgroundColor: c }}
                  />
                ))}
                <input
                  type="color"
                  value={color}
                  onChange={(e) => setColor(e.target.value)}
                  className="w-8 h-8 rounded-full cursor-pointer appearance-none border-0 p-0"
                  style={{ backgroundColor: color }}
                  title={t('toolChains.detail.customColor')}
                />
              </div>
            </div>

            {/* Priority */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                {t('toolChains.detail.priority')}
              </label>
              <input
                type="number"
                value={priority}
                onChange={(e) => setPriority(parseInt(e.target.value) || 0)}
                className="w-24 px-3 py-2 border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              />
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                {t('toolChains.detail.priorityHelp')}
              </p>
            </div>

            {/* Save button */}
            <div className="pt-4">
              <button
                onClick={handleSaveInfo}
                disabled={saving || !name.trim()}
                className="flex items-center space-x-2 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 transition-colors"
              >
                {saving ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Save className="w-4 h-4" />
                )}
                <span>{t('toolChains.detail.save')}</span>
              </button>
            </div>
          </div>
        )}

        {activeTab === 'steps' && (
          <div className="space-y-4">
            <p className="text-sm text-gray-600 dark:text-gray-400">
              {t('toolChains.detail.stepsHelp')}
            </p>

            {stepsLoading ? (
              <div className="flex justify-center py-8">
                <Loader2 className="w-6 h-6 text-purple-600 animate-spin" />
              </div>
            ) : (
              <>
                {/* Steps List */}
                <div className="space-y-3">
                  {steps.map((step, index) => (
                    <div
                      key={step.id}
                      className={`border rounded-lg overflow-hidden ${
                        step.enabled
                          ? 'border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800'
                          : 'border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 opacity-60'
                      }`}
                    >
                      {/* Edit Step Form */}
                      {editingStep?.id === step.id ? (
                        <div className="p-3 sm:p-4 bg-purple-50 dark:bg-purple-900/20 space-y-3">
                          <div className="flex items-center justify-between">
                            <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300">
                              {t('toolChains.detail.editStep')}
                            </h4>
                            <span className="text-xs text-gray-400 font-mono">#{index + 1}</span>
                          </div>

                          {/* Source Tool */}
                          <div className="p-3 bg-white dark:bg-gray-800 rounded border border-gray-200 dark:border-gray-700 space-y-2">
                            <label className="block text-xs font-medium text-gray-600 dark:text-gray-400">
                              {t('toolChains.detail.sourceTool')} ({t('toolChains.detail.trigger')})
                            </label>
                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                              <select
                                value={editStepSourceService}
                                onChange={(e) => {
                                  setEditStepSourceService(e.target.value);
                                  setEditStepSourceTool('');
                                }}
                                className="px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded-lg"
                              >
                                <option value="">{t('toolChains.detail.selectService')}</option>
                                {Object.entries(serviceGroups).map(([serviceType, group]) => (
                                  <option key={serviceType} value={serviceType}>
                                    {group.service_name}
                                  </option>
                                ))}
                              </select>
                              <select
                                value={editStepSourceTool}
                                onChange={(e) => setEditStepSourceTool(e.target.value)}
                                disabled={!editStepSourceService}
                                className="px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded-lg"
                              >
                                <option value="">{t('toolChains.detail.selectTool')}</option>
                                {editStepSourceService && serviceGroups[editStepSourceService]?.tools.map((tool) => (
                                  <option key={tool.tool_name} value={tool.tool_name}>
                                    {tool.tool_display_name}
                                  </option>
                                ))}
                              </select>
                            </div>
                          </div>

                          {/* Condition */}
                          <div className="p-3 bg-white dark:bg-gray-800 rounded border border-gray-200 dark:border-gray-700 space-y-2">
                            <label className="block text-xs font-medium text-gray-600 dark:text-gray-400">
                              {t('toolChains.detail.condition')}
                            </label>
                            <select
                              value={editStepOperator}
                              onChange={(e) => setEditStepOperator(e.target.value)}
                              className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded-lg"
                            >
                              {operators.map((op) => (
                                <option key={op.value} value={op.value}>
                                  {op.label} - {op.description}
                                </option>
                              ))}
                            </select>
                            {selectedEditStepOperator?.requires_field && (
                              <input
                                type="text"
                                value={editStepConditionField}
                                onChange={(e) => setEditStepConditionField(e.target.value)}
                                placeholder={t('toolChains.detail.conditionFieldPlaceholder')}
                                className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded-lg"
                              />
                            )}
                            {selectedEditStepOperator?.requires_value && (
                              <input
                                type="text"
                                value={editStepConditionValue}
                                onChange={(e) => setEditStepConditionValue(e.target.value)}
                                placeholder={t('toolChains.detail.conditionValuePlaceholder')}
                                className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded-lg"
                              />
                            )}
                          </div>

                          {/* AI Comment */}
                          <div>
                            <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">
                              {t('toolChains.detail.aiComment')}
                            </label>
                            <input
                              type="text"
                              value={editStepAiComment}
                              onChange={(e) => setEditStepAiComment(e.target.value)}
                              placeholder={t('toolChains.detail.stepCommentPlaceholder')}
                              className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded-lg"
                            />
                          </div>

                          <div className="flex justify-end space-x-2 pt-1">
                            <button
                              onClick={cancelEditingStep}
                              className="px-3 py-1.5 text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
                            >
                              {t('toolChains.detail.cancel')}
                            </button>
                            <button
                              onClick={handleUpdateStep}
                              disabled={!editStepSourceService || !editStepSourceTool}
                              className="px-3 py-1.5 text-sm bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50"
                            >
                              {t('toolChains.detail.save')}
                            </button>
                          </div>
                        </div>
                      ) : (
                        <>
                          {/* Step Header */}
                          <div
                            className="p-3 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700/50"
                            onClick={() => toggleStepExpanded(step.id)}
                          >
                            <div className="flex items-start justify-between">
                              <div className="flex items-start space-x-3">
                                <div className="flex items-center space-x-2 text-gray-400">
                                  <GripVertical className="w-4 h-4" />
                                  <span className="text-sm font-mono">{index + 1}</span>
                                </div>
                                <div className="flex-1">
                                  {/* Source Tool */}
                                  <div className="flex items-center flex-wrap gap-2">
                                    <span className="text-xs text-gray-500 dark:text-gray-400">
                                      {t('toolChains.detail.when')}
                                    </span>
                                    <span className="px-2 py-0.5 text-xs bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded">
                                      {step.source_service_name || step.source_service}
                                    </span>
                                    <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                                      {step.source_tool_display_name || step.source_tool}
                                    </span>
                                  </div>
                                  {/* Condition */}
                                  <div className="flex items-center flex-wrap gap-1 mt-1 text-xs text-gray-500 dark:text-gray-400">
                                    <span>{t('toolChains.detail.condition')}:</span>
                                    <span className="font-medium">{getOperatorLabel(step.condition_operator)}</span>
                                    {step.condition_field && (
                                      <>
                                        <span>({step.condition_field})</span>
                                      </>
                                    )}
                                    {step.condition_value && (
                                      <span>= "{step.condition_value}"</span>
                                    )}
                                  </div>
                                  {/* Targets count */}
                                  <div className="flex items-center gap-2 mt-1">
                                    <span className="flex items-center text-xs text-gray-500 dark:text-gray-400">
                                      <Target className="w-3 h-3 mr-1" />
                                      {step.targets?.length || 0} {t('toolChains.detail.targets')}
                                    </span>
                                  </div>
                                  {/* AI Comment */}
                                  {step.ai_comment && (
                                    <p className="flex items-start mt-1 text-xs text-gray-500 dark:text-gray-400">
                                      <MessageSquare className="w-3 h-3 mr-1 mt-0.5 flex-shrink-0" />
                                      {step.ai_comment}
                                    </p>
                                  )}
                                </div>
                              </div>
                              <div className="flex items-center space-x-1">
                                <button
                                  onClick={(e) => { e.stopPropagation(); startEditingStep(step); }}
                                  className="p-1 text-gray-400 hover:text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded transition-colors"
                                  title={t('toolChains.detail.editStep')}
                                >
                                  <Pencil className="w-4 h-4" />
                                </button>
                                <button
                                  onClick={(e) => { e.stopPropagation(); handleToggleStepEnabled(step); }}
                                  className={`p-1 rounded transition-colors ${
                                    step.enabled
                                      ? 'text-purple-600 hover:bg-purple-50 dark:hover:bg-purple-900/20'
                                      : 'text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700'
                                  }`}
                                >
                                  {step.enabled ? (
                                    <ToggleRight className="w-4 h-4" />
                                  ) : (
                                    <ToggleLeft className="w-4 h-4" />
                                  )}
                                </button>
                                <button
                                  onClick={(e) => { e.stopPropagation(); handleDeleteStep(step.id); }}
                                  className="p-1 text-gray-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded transition-colors"
                                >
                                  <Trash2 className="w-4 h-4" />
                                </button>
                                {expandedSteps.has(step.id) ? (
                                  <ChevronUp className="w-4 h-4 text-gray-400" />
                                ) : (
                                  <ChevronDown className="w-4 h-4 text-gray-400" />
                                )}
                              </div>
                            </div>
                          </div>

                      {/* Expanded: Targets */}
                      {expandedSteps.has(step.id) && (
                        <div className="border-t border-gray-200 dark:border-gray-700 p-3 bg-gray-50 dark:bg-gray-900/50">
                          <h4 className="text-xs font-medium text-gray-600 dark:text-gray-400 mb-2 flex items-center">
                            <Target className="w-3 h-3 mr-1" />
                            {t('toolChains.detail.targetTools')}
                          </h4>

                          {/* Targets list */}
                          <div className="space-y-2">
                            {step.targets?.map((target, targetIdx) => (
                              <div
                                key={target.id}
                                className={`p-2 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded ${
                                  !target.enabled ? 'opacity-60' : ''
                                }`}
                              >
                                <div className="flex items-center justify-between">
                                  <div className="flex items-center space-x-2">
                                    <span className="text-xs text-gray-400 font-mono">{targetIdx + 1}.</span>
                                    <span className="px-1.5 py-0.5 text-xs bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 rounded">
                                      {target.target_service_name || target.target_service}
                                    </span>
                                    <span className="text-sm text-gray-700 dark:text-gray-300">
                                      {target.target_tool_display_name || target.target_tool}
                                    </span>
                                    {target.execution_mode === 'parallel' && (
                                      <span className="px-1 py-0.5 text-xs bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300 rounded">
                                        {t('toolChains.detail.parallel')}
                                      </span>
                                    )}
                                  </div>
                                  <div className="flex items-center space-x-1">
                                    <button
                                      onClick={() => handleToggleTargetEnabled(step.id, target)}
                                      className={`p-0.5 rounded ${
                                        target.enabled
                                          ? 'text-purple-600 hover:bg-purple-50 dark:hover:bg-purple-900/20'
                                          : 'text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700'
                                      }`}
                                    >
                                      {target.enabled ? (
                                        <ToggleRight className="w-3 h-3" />
                                      ) : (
                                        <ToggleLeft className="w-3 h-3" />
                                      )}
                                    </button>
                                    <button
                                      onClick={() => handleDeleteTarget(step.id, target.id)}
                                      className="p-0.5 text-gray-400 hover:text-red-600 rounded"
                                    >
                                      <Trash2 className="w-3 h-3" />
                                    </button>
                                  </div>
                                </div>
                                {target.target_ai_comment && (
                                  <p className="mt-1 text-xs text-gray-500 dark:text-gray-400 ml-5">
                                    {target.target_ai_comment}
                                  </p>
                                )}
                              </div>
                            ))}
                          </div>

                          {/* Add target form */}
                          {addingTargetToStep === step.id ? (
                            <div className="mt-3 p-3 border border-green-200 dark:border-green-800 bg-green-50 dark:bg-green-900/20 rounded-lg space-y-2">
                              <div className="grid grid-cols-2 gap-2">
                                <select
                                  value={newTargetService}
                                  onChange={(e) => {
                                    setNewTargetService(e.target.value);
                                    setNewTargetTool('');
                                  }}
                                  className="px-2 py-1.5 text-sm border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded"
                                >
                                  <option value="">{t('toolChains.detail.selectService')}</option>
                                  {Object.entries(serviceGroups).map(([svc, group]) => (
                                    <option key={svc} value={svc}>{group.service_name}</option>
                                  ))}
                                </select>
                                <select
                                  value={newTargetTool}
                                  onChange={(e) => setNewTargetTool(e.target.value)}
                                  disabled={!newTargetService}
                                  className="px-2 py-1.5 text-sm border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded"
                                >
                                  <option value="">{t('toolChains.detail.selectTool')}</option>
                                  {newTargetService && serviceGroups[newTargetService]?.tools.map((tool) => (
                                    <option key={tool.tool_name} value={tool.tool_name}>
                                      {tool.tool_display_name}
                                    </option>
                                  ))}
                                </select>
                              </div>
                              <select
                                value={newTargetMode}
                                onChange={(e) => setNewTargetMode(e.target.value)}
                                className="w-full px-2 py-1.5 text-sm border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded"
                              >
                                <option value="sequential">{t('toolChains.detail.sequential')}</option>
                                <option value="parallel">{t('toolChains.detail.parallel')}</option>
                              </select>
                              <input
                                type="text"
                                value={newTargetComment}
                                onChange={(e) => setNewTargetComment(e.target.value)}
                                placeholder={t('toolChains.detail.targetCommentPlaceholder')}
                                className="w-full px-2 py-1.5 text-sm border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded"
                              />
                              <div className="flex justify-end space-x-2">
                                <button
                                  onClick={() => setAddingTargetToStep(null)}
                                  className="px-2 py-1 text-xs text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
                                >
                                  {t('toolChains.detail.cancel')}
                                </button>
                                <button
                                  onClick={() => handleAddTarget(step.id)}
                                  disabled={!newTargetService || !newTargetTool}
                                  className="px-2 py-1 text-xs bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50"
                                >
                                  {t('toolChains.detail.add')}
                                </button>
                              </div>
                            </div>
                          ) : (
                            <button
                              onClick={() => {
                                setAddingTargetToStep(step.id);
                                setNewTargetService('');
                                setNewTargetTool('');
                                setNewTargetMode('sequential');
                                setNewTargetComment('');
                              }}
                              className="mt-2 w-full p-2 border border-dashed border-gray-300 dark:border-gray-600 rounded text-xs text-gray-500 hover:border-green-400 hover:text-green-600 flex items-center justify-center space-x-1"
                            >
                              <Plus className="w-3 h-3" />
                              <span>{t('toolChains.detail.addTarget')}</span>
                            </button>
                          )}
                        </div>
                      )}
                        </>
                      )}
                    </div>
                  ))}
                </div>

                {steps.length === 0 && !showAddStep && (
                  <div className="text-center py-6 text-gray-500 dark:text-gray-400">
                    <Layers className="w-10 h-10 mx-auto mb-2 opacity-50" />
                    <p className="text-sm">{t('toolChains.detail.noSteps')}</p>
                  </div>
                )}

                {/* Add Step Form */}
                {showAddStep ? (
                  <div className="p-3 sm:p-4 border border-purple-200 dark:border-purple-800 bg-purple-50 dark:bg-purple-900/20 rounded-lg space-y-3">
                    <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300">
                      {t('toolChains.detail.addStep')}
                    </h4>

                    {/* Source Tool */}
                    <div className="p-3 bg-white dark:bg-gray-800 rounded border border-gray-200 dark:border-gray-700 space-y-2">
                      <label className="block text-xs font-medium text-gray-600 dark:text-gray-400">
                        {t('toolChains.detail.sourceTool')} ({t('toolChains.detail.trigger')})
                      </label>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                        <select
                          value={newStepSourceService}
                          onChange={(e) => {
                            setNewStepSourceService(e.target.value);
                            setNewStepSourceTool('');
                          }}
                          className="px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded-lg"
                        >
                          <option value="">{t('toolChains.detail.selectService')}</option>
                          {Object.entries(serviceGroups).map(([serviceType, group]) => (
                            <option key={serviceType} value={serviceType}>
                              {group.service_name}
                            </option>
                          ))}
                        </select>
                        <select
                          value={newStepSourceTool}
                          onChange={(e) => setNewStepSourceTool(e.target.value)}
                          disabled={!newStepSourceService}
                          className="px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded-lg"
                        >
                          <option value="">{t('toolChains.detail.selectTool')}</option>
                          {newStepSourceService && serviceGroups[newStepSourceService]?.tools.map((tool) => (
                            <option key={tool.tool_name} value={tool.tool_name}>
                              {tool.tool_display_name}
                            </option>
                          ))}
                        </select>
                      </div>
                    </div>

                    {/* Condition */}
                    <div className="p-3 bg-white dark:bg-gray-800 rounded border border-gray-200 dark:border-gray-700 space-y-2">
                      <label className="block text-xs font-medium text-gray-600 dark:text-gray-400">
                        {t('toolChains.detail.condition')}
                      </label>
                      <select
                        value={newStepOperator}
                        onChange={(e) => setNewStepOperator(e.target.value)}
                        className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded-lg"
                      >
                        {operators.map((op) => (
                          <option key={op.value} value={op.value}>
                            {op.label} - {op.description}
                          </option>
                        ))}
                      </select>
                      {selectedNewStepOperator?.requires_field && (
                        <input
                          type="text"
                          value={newStepConditionField}
                          onChange={(e) => setNewStepConditionField(e.target.value)}
                          placeholder={t('toolChains.detail.conditionFieldPlaceholder')}
                          className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded-lg"
                        />
                      )}
                      {selectedNewStepOperator?.requires_value && (
                        <input
                          type="text"
                          value={newStepConditionValue}
                          onChange={(e) => setNewStepConditionValue(e.target.value)}
                          placeholder={t('toolChains.detail.conditionValuePlaceholder')}
                          className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded-lg"
                        />
                      )}
                    </div>

                    {/* AI Comment */}
                    <div>
                      <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">
                        {t('toolChains.detail.aiComment')}
                      </label>
                      <input
                        type="text"
                        value={newStepAiComment}
                        onChange={(e) => setNewStepAiComment(e.target.value)}
                        placeholder={t('toolChains.detail.stepCommentPlaceholder')}
                        className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded-lg"
                      />
                    </div>

                    <div className="flex justify-end space-x-2 pt-1">
                      <button
                        onClick={() => setShowAddStep(false)}
                        className="px-3 py-1.5 text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
                      >
                        {t('toolChains.detail.cancel')}
                      </button>
                      <button
                        onClick={handleAddStep}
                        disabled={!newStepSourceService || !newStepSourceTool}
                        className="px-3 py-1.5 text-sm bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50"
                      >
                        {t('toolChains.detail.add')}
                      </button>
                    </div>
                  </div>
                ) : (
                  <button
                    onClick={() => setShowAddStep(true)}
                    className="w-full p-3 border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-lg text-gray-500 dark:text-gray-400 hover:border-purple-400 hover:text-purple-600 transition-colors flex items-center justify-center space-x-2"
                  >
                    <Plus className="w-4 h-4" />
                    <span>{t('toolChains.detail.addStep')}</span>
                  </button>
                )}
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default ToolChainDetail;
