import { Shield, ArrowRight, ArrowLeft, ExternalLink } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useWizard } from '../../contexts/WizardContext';

export default function GroupsInfoStep() {
  const { nextStep, previousStep } = useWizard();
  const navigate = useNavigate();

  const handleGoToGroups = () => {
    navigate('/groups');
  };

  return (
    <div className="p-8 max-w-3xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 rounded-lg bg-orange-100 dark:bg-orange-900/30">
            <Shield className="w-6 h-6 text-orange-600 dark:text-orange-400" />
          </div>
          <div>
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
              Étape 3: Groupes et Permissions
            </h2>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Contrôlez l'accès aux outils MCP par groupe d'utilisateurs
            </p>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="space-y-6 mb-8">
        <div className="bg-orange-50 dark:bg-orange-900/20 border border-orange-200 dark:border-orange-800 rounded-lg p-6">
          <h3 className="font-semibold text-orange-900 dark:text-orange-100 mb-3">
            À quoi servent les groupes ?
          </h3>
          <p className="text-orange-800 dark:text-orange-200 mb-3">
            Les groupes permettent de définir quels outils MCP (Model Context Protocol) sont
            accessibles à quels utilisateurs.
          </p>
          <p className="text-orange-800 dark:text-orange-200">
            Par exemple, un groupe "Admin" pourrait avoir accès à tous les outils, tandis qu'un
            groupe "User" n'aurait accès qu'aux outils de consultation.
          </p>
        </div>

        <div className="bg-gray-50 dark:bg-gray-900/50 rounded-lg p-6 border border-gray-200 dark:border-gray-700">
          <h3 className="font-semibold text-gray-900 dark:text-white mb-4">
            Configuration des groupes
          </h3>
          <div className="space-y-3 text-gray-700 dark:text-gray-300">
            <div className="flex items-start gap-3">
              <div className="w-6 h-6 rounded-full bg-orange-100 dark:bg-orange-900/30 flex items-center justify-center flex-shrink-0 mt-0.5">
                <span className="text-sm font-semibold text-orange-600 dark:text-orange-400">1</span>
              </div>
              <p>
                Accédez à la <strong>page Groups</strong> via le menu de navigation
              </p>
            </div>
            <div className="flex items-start gap-3">
              <div className="w-6 h-6 rounded-full bg-orange-100 dark:bg-orange-900/30 flex items-center justify-center flex-shrink-0 mt-0.5">
                <span className="text-sm font-semibold text-orange-600 dark:text-orange-400">2</span>
              </div>
              <p>
                Créez des groupes (ex: Admin, User, Family) en cliquant sur <strong>"Create Group"</strong>
              </p>
            </div>
            <div className="flex items-start gap-3">
              <div className="w-6 h-6 rounded-full bg-orange-100 dark:bg-orange-900/30 flex items-center justify-center flex-shrink-0 mt-0.5">
                <span className="text-sm font-semibold text-orange-600 dark:text-orange-400">3</span>
              </div>
              <p>
                Assignez les permissions MCP à chaque groupe (lecture seule, modification, etc.)
              </p>
            </div>
            <div className="flex items-start gap-3">
              <div className="w-6 h-6 rounded-full bg-orange-100 dark:bg-orange-900/30 flex items-center justify-center flex-shrink-0 mt-0.5">
                <span className="text-sm font-semibold text-orange-600 dark:text-orange-400">4</span>
              </div>
              <p>
                Assignez vos utilisateurs aux groupes appropriés
              </p>
            </div>
          </div>

          <div className="mt-4 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
            <p className="text-sm text-blue-800 dark:text-blue-200">
              <strong>Note :</strong> Les outils MCP permettent à l'IA d'interagir avec vos services
              (rechercher un film, lancer un téléchargement, etc.). Les permissions contrôlent ce que
              chaque groupe peut faire.
            </p>
          </div>
        </div>

        {/* Action button */}
        <div className="flex justify-center">
          <button
            onClick={handleGoToGroups}
            className="flex items-center gap-2 px-6 py-3 bg-orange-600 hover:bg-orange-700 text-white rounded-lg font-medium transition-colors shadow-lg"
          >
            Ouvrir la page Groups
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
