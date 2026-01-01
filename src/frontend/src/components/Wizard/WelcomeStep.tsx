import { Sparkles, ArrowRight, X } from 'lucide-react';
import { useWizard } from '../../contexts/WizardContext';

export default function WelcomeStep() {
  const { nextStep, skipWizard } = useWizard();

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center p-4">
      <div className="max-w-3xl w-full">
        {/* Skip button */}
        <div className="flex justify-end mb-4">
          <button
            onClick={skipWizard}
            className="flex items-center gap-2 px-4 py-2 text-sm text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 transition-colors"
          >
            <X className="w-4 h-4" />
            Passer le guide
          </button>
        </div>

        {/* Main card */}
        <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl border border-gray-200 dark:border-gray-700 p-8 md:p-12">
          {/* Icon */}
          <div className="flex justify-center mb-6">
            <div className="p-4 rounded-2xl bg-gradient-to-br from-blue-500 to-indigo-600 shadow-lg">
              <Sparkles className="w-12 h-12 text-white" />
            </div>
          </div>

          {/* Title */}
          <h1 className="text-3xl md:text-4xl font-bold text-center bg-gradient-to-r from-gray-900 to-gray-600 dark:from-white dark:to-gray-300 bg-clip-text text-transparent mb-4">
            Bienvenue sur MCParr
          </h1>

          {/* Subtitle */}
          <p className="text-lg text-center text-gray-600 dark:text-gray-400 mb-8">
            Votre gateway IA pour contrôler votre homelab
          </p>

          {/* Description */}
          <div className="space-y-4 mb-8 text-gray-700 dark:text-gray-300">
            <p className="text-center max-w-2xl mx-auto leading-relaxed">
              MCParr centralise le contrôle de tous vos services homelab via une interface
              conversationnelle alimentée par l'IA.
            </p>
          </div>

          {/* Features grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
            {[
              { emoji: '🔌', text: 'Connexion à vos services' },
              { emoji: '👥', text: 'Mapping utilisateurs' },
              { emoji: '🛡️', text: 'Gestion des permissions' },
              { emoji: '🤖', text: 'Serveur MCP intégré' },
            ].map((item, i) => (
              <div key={i} className="flex items-center gap-3 p-4 bg-gray-50 dark:bg-gray-900/50 rounded-xl">
                <span className="text-2xl">{item.emoji}</span>
                <span className="text-sm font-medium text-gray-700 dark:text-gray-300">{item.text}</span>
              </div>
            ))}
          </div>

          <p className="text-sm text-center text-gray-500 dark:text-gray-400 mb-8">
            Ce guide vous accompagne dans la configuration initiale.
            Vous pourrez modifier tous ces paramètres ultérieurement.
          </p>

          {/* Action */}
          <div className="flex justify-center">
            <button
              onClick={nextStep}
              className="flex items-center gap-2 px-8 py-3.5 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white rounded-xl font-medium transition-all shadow-lg hover:shadow-xl"
            >
              Commencer la configuration
              <ArrowRight className="w-5 h-5" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
