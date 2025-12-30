import { useState } from 'react';
import type { FC } from 'react';
import { X, Shield, RefreshCw } from 'lucide-react';
import { api } from '../../lib/api';

interface GroupCreateModalProps {
  onClose: () => void;
  onCreated: () => void;
}

const GroupCreateModal: FC<GroupCreateModalProps> = ({ onClose, onCreated }) => {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [color, setColor] = useState('#6366f1');
  const [priority, setPriority] = useState(0);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      setError('Le nom est requis');
      return;
    }

    try {
      setSaving(true);
      setError(null);
      await api.groups.create({
        name: name.trim(),
        description: description.trim() || undefined,
        color,
        priority,
        enabled: true
      });
      onCreated();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create group');
    } finally {
      setSaving(false);
    }
  };

  const presetColors = [
    '#6366f1', // Indigo
    '#8b5cf6', // Violet
    '#ec4899', // Pink
    '#ef4444', // Red
    '#f97316', // Orange
    '#eab308', // Yellow
    '#22c55e', // Green
    '#14b8a6', // Teal
    '#0ea5e9', // Sky
    '#3b82f6', // Blue
  ];

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-md w-full">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center space-x-2">
            <Shield className="w-5 h-5 text-indigo-600" />
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
              Nouveau groupe
            </h2>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-4 space-y-4">
          {error && (
            <div className="p-3 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-800">
              <span className="text-sm text-red-700 dark:text-red-400">{error}</span>
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Nom *
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Ex: Admin, User, Beta..."
              className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
              autoFocus
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Description
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Description du groupe..."
              rows={3}
              className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Couleur
            </label>
            <div className="flex items-center space-x-2 mb-2">
              {presetColors.map((presetColor) => (
                <button
                  key={presetColor}
                  type="button"
                  onClick={() => setColor(presetColor)}
                  className={`w-6 h-6 rounded-full transition-transform ${
                    color === presetColor ? 'ring-2 ring-offset-2 ring-gray-400 scale-110' : ''
                  }`}
                  style={{ backgroundColor: presetColor }}
                />
              ))}
            </div>
            <div className="flex items-center space-x-2">
              <input
                type="color"
                value={color}
                onChange={(e) => setColor(e.target.value)}
                className="w-10 h-10 rounded cursor-pointer border border-gray-300 dark:border-gray-600"
              />
              <input
                type="text"
                value={color}
                onChange={(e) => setColor(e.target.value)}
                className="flex-1 px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded-lg"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Priorité
            </label>
            <input
              type="number"
              value={priority}
              onChange={(e) => setPriority(parseInt(e.target.value) || 0)}
              className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
            />
            <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
              Priorité plus élevée = permissions résolues en premier
            </p>
          </div>

          {/* Actions */}
          <div className="flex justify-end space-x-3 pt-4 border-t border-gray-200 dark:border-gray-700">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm text-gray-700 dark:text-gray-300 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
            >
              Annuler
            </button>
            <button
              type="submit"
              disabled={saving || !name.trim()}
              className="flex items-center space-x-2 px-4 py-2 bg-indigo-600 text-white text-sm rounded-lg hover:bg-indigo-700 disabled:opacity-50 transition-colors"
            >
              {saving ? (
                <RefreshCw className="w-4 h-4 animate-spin" />
              ) : (
                <Shield className="w-4 h-4" />
              )}
              <span>Créer</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default GroupCreateModal;
