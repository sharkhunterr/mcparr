import { Sparkles, ArrowRight, X } from 'lucide-react';
import { useWizard } from '../../contexts/WizardContext';

export default function WelcomeStep() {
  const { nextStep, skipWizard } = useWizard();

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-gray-900 dark:to-gray-800 flex items-center justify-center p-4">
      <div className="max-w-2xl w-full bg-white dark:bg-gray-800 rounded-2xl shadow-2xl p-8 md:p-12 relative">
        {/* Close button */}
        <button
          onClick={skipWizard}
          className="absolute top-4 right-4 p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 transition-colors"
          title="Passer le wizard"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Icon */}
        <div className="flex justify-center mb-6">
          <div className="p-4 rounded-full bg-gradient-to-br from-blue-500 to-indigo-600">
            <Sparkles className="w-12 h-12 text-white" />
          </div>
        </div>

        {/* Title */}
        <h1 className="text-3xl md:text-4xl font-bold text-center text-gray-900 dark:text-white mb-4">
          Bienvenue sur MCParr
        </h1>

        {/* Subtitle */}
        <p className="text-lg text-center text-gray-600 dark:text-gray-300 mb-8">
          Votre assistant IA pour gérer votre homelab
        </p>

        {/* Description */}
        <div className="space-y-4 mb-8 text-gray-700 dark:text-gray-300">
          <p>
            MCParr centralise le contrôle de tous vos services homelab (Plex, Radarr, Sonarr, Overseerr, etc.)
            via une interface conversationnelle alimentée par l'IA.
          </p>
          <p>
            Ce guide rapide vous aidera à configurer les éléments essentiels pour commencer :
          </p>
          <ul className="list-disc list-inside space-y-2 ml-4">
            <li>Connexion à vos services homelab</li>
            <li>Mapping des utilisateurs entre services</li>
            <li>Configuration des groupes et permissions</li>
          </ul>
          <p className="text-sm text-gray-500 dark:text-gray-400 italic">
            Vous pourrez toujours modifier ces paramètres plus tard dans les pages de configuration.
          </p>
        </div>

        {/* Actions */}
        <div className="flex flex-col sm:flex-row gap-4">
          <button
            onClick={nextStep}
            className="flex-1 flex items-center justify-center gap-2 px-6 py-3 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white rounded-lg font-medium transition-all shadow-lg hover:shadow-xl"
          >
            Commencer
            <ArrowRight className="w-5 h-5" />
          </button>
          <button
            onClick={skipWizard}
            className="px-6 py-3 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200 font-medium transition-colors"
          >
            Passer le guide
          </button>
        </div>
      </div>
    </div>
  );
}
