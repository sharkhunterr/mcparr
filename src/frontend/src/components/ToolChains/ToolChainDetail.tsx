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
  ChevronDown,
  ChevronUp,
  MessageSquare,
  ToggleLeft,
  ToggleRight,
  Pencil,
  GitBranch,
  CheckCircle,
  XCircle,
  Flag
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { getApiBaseUrl } from '../../lib/api';
import type {
  ToolChain,
  ToolChainStepDetail,
  Action,
  ConditionGroup,
  AvailableTool,
  ConditionOperatorInfo,
  ActionType,
  StepPositionType,
  ConditionGroupOperator
} from '../../types/api';

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
  const [newStepPositionType, setNewStepPositionType] = useState<StepPositionType>('middle');
  const [newStepAiComment, setNewStepAiComment] = useState('');

  // Add condition group form state
  const [addingConditionToStep, setAddingConditionToStep] = useState<string | null>(null);
  const [newConditionOperator, setNewConditionOperator] = useState('success');
  const [newConditionField, setNewConditionField] = useState('');
  const [newConditionValue, setNewConditionValue] = useState('');
  const [newGroupOperator, setNewGroupOperator] = useState<ConditionGroupOperator>('and');

  // Add action form state
  const [addingActionToStep, setAddingActionToStep] = useState<{ stepId: string; branch: 'then' | 'else' } | null>(null);
  const [newActionType, setNewActionType] = useState<ActionType>('tool_call');
  const [newActionService, setNewActionService] = useState('');
  const [newActionTool, setNewActionTool] = useState('');
  const [newActionMessage, setNewActionMessage] = useState('');
  const [newActionComment, setNewActionComment] = useState('');

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

  const selectedConditionOperator = operators.find(op => op.value === newConditionOperator);

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
          position_type: newStepPositionType,
          ai_comment: newStepAiComment || null,
          order: steps.length
        })
      });
      if (!response.ok) throw new Error('Failed to add step');

      setNewStepSourceService('');
      setNewStepSourceTool('');
      setNewStepPositionType('middle');
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

  const handleAddConditionGroup = async (stepId: string) => {
    try {
      setError(null);
      const response = await fetch(`${backendUrl}/api/tool-chains/${chain.id}/steps/${stepId}/condition-groups`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          operator: newGroupOperator,
          conditions: [{
            operator: newConditionOperator,
            field: newConditionField || null,
            value: newConditionValue || null,
            order: 0
          }]
        })
      });
      if (!response.ok) throw new Error('Failed to add condition');

      setAddingConditionToStep(null);
      setNewConditionOperator('success');
      setNewConditionField('');
      setNewConditionValue('');
      setNewGroupOperator('and');
      fetchSteps();
      onUpdated();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add condition');
    }
  };

  const handleDeleteConditionGroup = async (stepId: string, groupId: string) => {
    try {
      setError(null);
      const response = await fetch(`${backendUrl}/api/tool-chains/${chain.id}/steps/${stepId}/condition-groups/${groupId}`, {
        method: 'DELETE'
      });
      if (!response.ok) throw new Error('Failed to delete condition group');
      fetchSteps();
      onUpdated();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete condition group');
    }
  };

  const handleAddAction = async (stepId: string, branch: 'then' | 'else') => {
    try {
      setError(null);
      const body: any = {
        branch,
        action_type: newActionType,
        order: 0,
        ai_comment: newActionComment || null,
        enabled: true
      };

      if (newActionType === 'tool_call') {
        body.target_service = newActionService;
        body.target_tool = newActionTool;
      } else {
        body.message_template = newActionMessage;
      }

      const response = await fetch(`${backendUrl}/api/tool-chains/${chain.id}/steps/${stepId}/actions/${branch}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      });
      if (!response.ok) throw new Error('Failed to add action');

      setAddingActionToStep(null);
      setNewActionType('tool_call');
      setNewActionService('');
      setNewActionTool('');
      setNewActionMessage('');
      setNewActionComment('');
      fetchSteps();
      onUpdated();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add action');
    }
  };

  const handleDeleteAction = async (stepId: string, branch: 'then' | 'else', actionId: string) => {
    try {
      setError(null);
      const response = await fetch(`${backendUrl}/api/tool-chains/${chain.id}/steps/${stepId}/actions/${branch}/${actionId}`, {
        method: 'DELETE'
      });
      if (!response.ok) throw new Error('Failed to delete action');
      fetchSteps();
      onUpdated();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete action');
    }
  };

  const handleToggleActionEnabled = async (stepId: string, action: Action) => {
    try {
      setError(null);
      const response = await fetch(`${backendUrl}/api/tool-chains/${chain.id}/steps/${stepId}/actions/${action.branch}/${action.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled: !action.enabled })
      });
      if (!response.ok) throw new Error('Failed to update action');
      fetchSteps();
      onUpdated();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update action');
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

  const renderConditions = (groups: ConditionGroup[], stepId: string) => {
    if (!groups || groups.length === 0) {
      return (
        <div className="text-xs text-gray-500 dark:text-gray-400 italic">
          {t('toolChains.detail.noConditions')} ({t('toolChains.detail.alwaysTrue')})
        </div>
      );
    }

    return (
      <div className="space-y-2">
        {groups.map((group, idx) => (
          <div key={group.id} className="flex items-start gap-2">
            {idx > 0 && (
              <span className="px-1.5 py-0.5 text-xs bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-400 rounded">
                AND
              </span>
            )}
            <div className="flex-1 p-2 bg-gray-50 dark:bg-gray-800/50 rounded border border-gray-200 dark:border-gray-700">
              <div className="flex items-center justify-between mb-1">
                <span className="px-1.5 py-0.5 text-xs bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded uppercase">
                  {group.operator}
                </span>
                <button
                  onClick={() => handleDeleteConditionGroup(stepId, group.id)}
                  className="p-0.5 text-gray-400 hover:text-red-600 rounded"
                >
                  <Trash2 className="w-3 h-3" />
                </button>
              </div>
              <div className="space-y-1">
                {group.conditions.map((cond, cIdx) => (
                  <div key={cond.id} className="flex items-center gap-1 text-xs text-gray-600 dark:text-gray-400">
                    {cIdx > 0 && <span className="text-gray-400">{group.operator.toUpperCase()}</span>}
                    <span className="font-medium">{getOperatorLabel(cond.operator)}</span>
                    {cond.field && <span className="text-gray-500">({cond.field})</span>}
                    {cond.value && <span className="text-purple-600 dark:text-purple-400">= "{cond.value}"</span>}
                  </div>
                ))}
              </div>
            </div>
          </div>
        ))}
      </div>
    );
  };

  const renderActions = (actions: Action[], stepId: string, branch: 'then' | 'else') => {
    const branchColor = branch === 'then' ? 'green' : 'orange';

    return (
      <div className={`p-2 rounded border border-${branchColor}-200 dark:border-${branchColor}-800/50 bg-${branchColor}-50/50 dark:bg-${branchColor}-900/10`}>
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-1.5">
            {branch === 'then' ? (
              <CheckCircle className={`w-3.5 h-3.5 text-green-600`} />
            ) : (
              <XCircle className={`w-3.5 h-3.5 text-orange-600`} />
            )}
            <span className={`text-xs font-medium ${branch === 'then' ? 'text-green-700 dark:text-green-400' : 'text-orange-700 dark:text-orange-400'}`}>
              {branch === 'then' ? t('toolChains.detail.thenBranch') : t('toolChains.detail.elseBranch')}
            </span>
          </div>
        </div>

        <div className="space-y-1.5">
          {actions.map((action) => (
            <div
              key={action.id}
              className={`flex items-center justify-between p-1.5 bg-white dark:bg-gray-800 rounded border border-gray-200 dark:border-gray-700 ${
                !action.enabled ? 'opacity-50' : ''
              }`}
            >
              <div className="flex items-center gap-2">
                {action.action_type === 'message' ? (
                  <>
                    <MessageSquare className="w-3 h-3 text-purple-500" />
                    <span className="text-xs text-gray-600 dark:text-gray-400 truncate max-w-[200px]">
                      {action.message_template || t('toolChains.detail.emptyMessage')}
                    </span>
                  </>
                ) : (
                  <>
                    <span className="px-1 py-0.5 text-xs bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 rounded">
                      {action.target_service_name || action.target_service}
                    </span>
                    <span className="text-xs text-gray-700 dark:text-gray-300">
                      {action.target_tool_display_name || action.target_tool}
                    </span>
                  </>
                )}
              </div>
              <div className="flex items-center gap-1">
                <button
                  onClick={() => handleToggleActionEnabled(stepId, action)}
                  className={`p-0.5 rounded ${
                    action.enabled
                      ? 'text-purple-600 hover:bg-purple-50 dark:hover:bg-purple-900/20'
                      : 'text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700'
                  }`}
                >
                  {action.enabled ? (
                    <ToggleRight className="w-3 h-3" />
                  ) : (
                    <ToggleLeft className="w-3 h-3" />
                  )}
                </button>
                <button
                  onClick={() => handleDeleteAction(stepId, branch, action.id)}
                  className="p-0.5 text-gray-400 hover:text-red-600 rounded"
                >
                  <Trash2 className="w-3 h-3" />
                </button>
              </div>
            </div>
          ))}

          {actions.length === 0 && (
            <div className="text-xs text-gray-400 italic py-1">
              {t('toolChains.detail.noActions')}
            </div>
          )}

          {/* Add action form */}
          {addingActionToStep?.stepId === stepId && addingActionToStep?.branch === branch ? (
            <div className="mt-2 p-2 bg-white dark:bg-gray-800 rounded border border-gray-300 dark:border-gray-600 space-y-2">
              <select
                value={newActionType}
                onChange={(e) => setNewActionType(e.target.value as ActionType)}
                className="w-full px-2 py-1 text-xs border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded"
              >
                <option value="tool_call">{t('toolChains.detail.actionTypeToolCall')}</option>
                <option value="message">{t('toolChains.detail.actionTypeMessage')}</option>
              </select>

              {newActionType === 'tool_call' ? (
                <div className="grid grid-cols-2 gap-1">
                  <select
                    value={newActionService}
                    onChange={(e) => {
                      setNewActionService(e.target.value);
                      setNewActionTool('');
                    }}
                    className="px-2 py-1 text-xs border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded"
                  >
                    <option value="">{t('toolChains.detail.selectService')}</option>
                    {Object.entries(serviceGroups).map(([svc, group]) => (
                      <option key={svc} value={svc}>{group.service_name}</option>
                    ))}
                  </select>
                  <select
                    value={newActionTool}
                    onChange={(e) => setNewActionTool(e.target.value)}
                    disabled={!newActionService}
                    className="px-2 py-1 text-xs border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded"
                  >
                    <option value="">{t('toolChains.detail.selectTool')}</option>
                    {newActionService && serviceGroups[newActionService]?.tools.map((tool) => (
                      <option key={tool.tool_name} value={tool.tool_name}>
                        {tool.tool_display_name}
                      </option>
                    ))}
                  </select>
                </div>
              ) : (
                <textarea
                  value={newActionMessage}
                  onChange={(e) => setNewActionMessage(e.target.value)}
                  placeholder={t('toolChains.detail.messageTemplatePlaceholder')}
                  rows={2}
                  className="w-full px-2 py-1 text-xs border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded resize-none"
                />
              )}

              <input
                type="text"
                value={newActionComment}
                onChange={(e) => setNewActionComment(e.target.value)}
                placeholder={t('toolChains.detail.actionCommentPlaceholder')}
                className="w-full px-2 py-1 text-xs border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded"
              />

              <div className="flex justify-end gap-1">
                <button
                  onClick={() => setAddingActionToStep(null)}
                  className="px-2 py-0.5 text-xs text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
                >
                  {t('toolChains.detail.cancel')}
                </button>
                <button
                  onClick={() => handleAddAction(stepId, branch)}
                  disabled={(newActionType === 'tool_call' && (!newActionService || !newActionTool)) || (newActionType === 'message' && !newActionMessage)}
                  className={`px-2 py-0.5 text-xs text-white rounded disabled:opacity-50 ${
                    branch === 'then' ? 'bg-green-600 hover:bg-green-700' : 'bg-orange-600 hover:bg-orange-700'
                  }`}
                >
                  {t('toolChains.detail.add')}
                </button>
              </div>
            </div>
          ) : (
            <button
              onClick={() => {
                setAddingActionToStep({ stepId, branch });
                setNewActionType('tool_call');
                setNewActionService('');
                setNewActionTool('');
                setNewActionMessage('');
                setNewActionComment('');
              }}
              className={`w-full mt-1 p-1 border border-dashed rounded text-xs flex items-center justify-center gap-1 ${
                branch === 'then'
                  ? 'border-green-300 dark:border-green-700 text-green-600 dark:text-green-400 hover:bg-green-50 dark:hover:bg-green-900/20'
                  : 'border-orange-300 dark:border-orange-700 text-orange-600 dark:text-orange-400 hover:bg-orange-50 dark:hover:bg-orange-900/20'
              }`}
            >
              <Plus className="w-3 h-3" />
              <span>{t('toolChains.detail.addAction')}</span>
            </button>
          )}
        </div>
      </div>
    );
  };

  const tabs: { id: TabType; label: string; icon: React.ReactNode }[] = [
    { id: 'steps', label: t('toolChains.detail.tabs.steps'), icon: <Layers className="w-4 h-4" /> },
    { id: 'info', label: t('toolChains.detail.tabs.info'), icon: <Info className="w-4 h-4" /> },
  ];

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
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

      {/* Mobile header */}
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
              </div>
            </div>

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
              {t('toolChains.detail.stepsHelpIfThenElse')}
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
                                {step.position_type === 'end' && (
                                  <span className="px-1.5 py-0.5 text-xs bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 rounded flex items-center gap-0.5">
                                    <Flag className="w-2.5 h-2.5" />
                                    {t('toolChains.detail.endStep')}
                                  </span>
                                )}
                              </div>
                              {/* Stats */}
                              <div className="flex items-center gap-3 mt-1 text-xs text-gray-500 dark:text-gray-400">
                                <span className="flex items-center gap-1">
                                  <GitBranch className="w-3 h-3" />
                                  {step.condition_count} {t('toolChains.detail.conditions')}
                                </span>
                                <span className="flex items-center gap-1">
                                  <CheckCircle className="w-3 h-3 text-green-500" />
                                  {step.then_action_count} {t('toolChains.detail.then')}
                                </span>
                                <span className="flex items-center gap-1">
                                  <XCircle className="w-3 h-3 text-orange-500" />
                                  {step.else_action_count} {t('toolChains.detail.else')}
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

                      {/* Expanded: Conditions + IF/THEN/ELSE */}
                      {expandedSteps.has(step.id) && (
                        <div className="border-t border-gray-200 dark:border-gray-700 p-3 bg-gray-50 dark:bg-gray-900/50 space-y-4">
                          {/* Conditions (IF) */}
                          <div>
                            <h4 className="text-xs font-medium text-gray-600 dark:text-gray-400 mb-2 flex items-center">
                              <GitBranch className="w-3 h-3 mr-1" />
                              {t('toolChains.detail.ifConditions')}
                            </h4>
                            {renderConditions(step.condition_groups, step.id)}

                            {/* Add condition form */}
                            {addingConditionToStep === step.id ? (
                              <div className="mt-2 p-2 bg-white dark:bg-gray-800 rounded border border-blue-200 dark:border-blue-800 space-y-2">
                                <div className="flex gap-2">
                                  <select
                                    value={newGroupOperator}
                                    onChange={(e) => setNewGroupOperator(e.target.value as ConditionGroupOperator)}
                                    className="px-2 py-1 text-xs border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded"
                                  >
                                    <option value="and">AND</option>
                                    <option value="or">OR</option>
                                  </select>
                                  <select
                                    value={newConditionOperator}
                                    onChange={(e) => setNewConditionOperator(e.target.value)}
                                    className="flex-1 px-2 py-1 text-xs border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded"
                                  >
                                    {operators.map((op) => (
                                      <option key={op.value} value={op.value}>
                                        {op.label}
                                      </option>
                                    ))}
                                  </select>
                                </div>
                                {selectedConditionOperator?.requires_field && (
                                  <input
                                    type="text"
                                    value={newConditionField}
                                    onChange={(e) => setNewConditionField(e.target.value)}
                                    placeholder={t('toolChains.detail.conditionFieldPlaceholder')}
                                    className="w-full px-2 py-1 text-xs border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded"
                                  />
                                )}
                                {selectedConditionOperator?.requires_value && (
                                  <input
                                    type="text"
                                    value={newConditionValue}
                                    onChange={(e) => setNewConditionValue(e.target.value)}
                                    placeholder={t('toolChains.detail.conditionValuePlaceholder')}
                                    className="w-full px-2 py-1 text-xs border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded"
                                  />
                                )}
                                <div className="flex justify-end gap-1">
                                  <button
                                    onClick={() => setAddingConditionToStep(null)}
                                    className="px-2 py-0.5 text-xs text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
                                  >
                                    {t('toolChains.detail.cancel')}
                                  </button>
                                  <button
                                    onClick={() => handleAddConditionGroup(step.id)}
                                    className="px-2 py-0.5 text-xs bg-blue-600 text-white rounded hover:bg-blue-700"
                                  >
                                    {t('toolChains.detail.add')}
                                  </button>
                                </div>
                              </div>
                            ) : (
                              <button
                                onClick={() => {
                                  setAddingConditionToStep(step.id);
                                  setNewConditionOperator('success');
                                  setNewConditionField('');
                                  setNewConditionValue('');
                                  setNewGroupOperator('and');
                                }}
                                className="mt-2 w-full p-1.5 border border-dashed border-blue-300 dark:border-blue-700 rounded text-xs text-blue-600 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/20 flex items-center justify-center gap-1"
                              >
                                <Plus className="w-3 h-3" />
                                <span>{t('toolChains.detail.addCondition')}</span>
                              </button>
                            )}
                          </div>

                          {/* THEN / ELSE branches */}
                          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                            {renderActions(step.then_actions, step.id, 'then')}
                            {renderActions(step.else_actions, step.id, 'else')}
                          </div>
                        </div>
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

                    {/* Position Type */}
                    <div className="p-3 bg-white dark:bg-gray-800 rounded border border-gray-200 dark:border-gray-700 space-y-2">
                      <label className="block text-xs font-medium text-gray-600 dark:text-gray-400">
                        {t('toolChains.detail.positionType')}
                      </label>
                      <select
                        value={newStepPositionType}
                        onChange={(e) => setNewStepPositionType(e.target.value as StepPositionType)}
                        className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded-lg"
                      >
                        <option value="middle">{t('toolChains.detail.positionMiddle')}</option>
                        <option value="end">{t('toolChains.detail.positionEnd')}</option>
                      </select>
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
