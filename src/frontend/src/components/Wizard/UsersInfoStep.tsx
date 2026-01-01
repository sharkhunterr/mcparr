import { Users, ArrowRight, ArrowLeft, ExternalLink } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useWizard } from '../../contexts/WizardContext';

export default function UsersInfoStep() {
  const { nextStep, previousStep } = useWizard();
  const navigate = useNavigate();

  const handleGoToUsers = () => {
    navigate('/users');
  };

  return (
    <div className="p-8 max-w-3xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 rounded-lg bg-purple-100 dark:bg-purple-900/30">
            <Users className="w-6 h-6 text-purple-600 dark:text-purple-400" />
          </div>
          <div>
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
              Étape 2: Mapping des Utilisateurs
            </h2>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Associez vos utilisateurs entre les différents services
            </p>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="space-y-6 mb-8">
        <div className="bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-800 rounded-lg p-6">
          <h3 className="font-semibold text-purple-900 dark:text-purple-100 mb-3">
            Pourquoi mapper les utilisateurs ?
          </h3>
          <p className="text-purple-800 dark:text-purple-200 mb-3">
            Le mapping des utilisateurs permet à MCParr de savoir quel compte dans Plex
            correspond au même utilisateur dans Overseerr, Radarr, etc.
          </p>
          <p className="text-purple-800 dark:text-purple-200">
            Cela permet de gérer les permissions et l'accès aux outils MCP en fonction de l'utilisateur.
          </p>
        </div>

        <div className="bg-gray-50 dark:bg-gray-900/50 rounded-lg p-6 border border-gray-200 dark:border-gray-700">
          <h3 className="font-semibold text-gray-900 dark:text-white mb-4">
            Configuration du mapping
          </h3>
          <div className="space-y-3 text-gray-700 dark:text-gray-300">
            <div className="flex items-start gap-3">
              <div className="w-6 h-6 rounded-full bg-purple-100 dark:bg-purple-900/30 flex items-center justify-center flex-shrink-0 mt-0.5">
                <span className="text-sm font-semibold text-purple-600 dark:text-purple-400">1</span>
              </div>
              <p>
                Accédez à la <strong>page Users</strong> via le menu de navigation
              </p>
            </div>
            <div className="flex items-start gap-3">
              <div className="w-6 h-6 rounded-full bg-purple-100 dark:bg-purple-900/30 flex items-center justify-center flex-shrink-0 mt-0.5">
                <span className="text-sm font-semibold text-purple-600 dark:text-purple-400">2</span>
              </div>
              <p>
                Utilisez la <strong>détection automatique</strong> dans l'onglet "Auto Detection" pour
                que MCParr scanne vos services et propose des correspondances
              </p>
            </div>
            <div className="flex items-start gap-3">
              <div className="w-6 h-6 rounded-full bg-purple-100 dark:bg-purple-900/30 flex items-center justify-center flex-shrink-0 mt-0.5">
                <span className="text-sm font-semibold text-purple-600 dark:text-purple-400">3</span>
              </div>
              <p>
                Validez les suggestions proposées ou créez des mappings manuels dans l'onglet "Manual Mapping"
              </p>
            </div>
          </div>

          <div className="mt-4 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
            <p className="text-sm text-blue-800 dark:text-blue-200">
              <strong>Astuce :</strong> La détection automatique fonctionne mieux si vous avez configuré
              au moins 2 services avec des utilisateurs (Plex, Overseerr, Tautulli, etc.)
            </p>
          </div>
        </div>

        {/* Action button */}
        <div className="flex justify-center">
          <button
            onClick={handleGoToUsers}
            className="flex items-center gap-2 px-6 py-3 bg-purple-600 hover:bg-purple-700 text-white rounded-lg font-medium transition-colors shadow-lg"
          >
            Ouvrir la page Users
            <ExternalLink className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Navigation */}
      <div className="flex items-center justify-between pt-6 border-t border-gray-200 dark:border-gray-700">
        <button
          onClick={previousStep}
          className="flex items-center gap-2 px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Précédent
        </button>
        <button
          onClick={nextStep}
          className="flex items-center gap-2 px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
        >
          Suivant
          <ArrowRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}
