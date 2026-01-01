import { Server, ArrowRight, ArrowLeft, ExternalLink } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useWizard } from '../../contexts/WizardContext';

export default function ServicesInfoStep() {
  const { nextStep, previousStep } = useWizard();
  const navigate = useNavigate();

  const handleGoToServices = () => {
    navigate('/services');
  };

  return (
    <div className="p-8 max-w-3xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 rounded-lg bg-blue-100 dark:bg-blue-900/30">
            <Server className="w-6 h-6 text-blue-600 dark:text-blue-400" />
          </div>
          <div>
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
              Étape 1: Services Homelab
            </h2>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Connectez vos services pour les contrôler via MCParr
            </p>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="space-y-6 mb-8">
        <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-6">
          <h3 className="font-semibold text-blue-900 dark:text-blue-100 mb-3">
            Qu'est-ce qu'un service ?
          </h3>
          <p className="text-blue-800 dark:text-blue-200 mb-4">
            Un service est une application de votre homelab que MCParr peut contrôler :
            Plex, Radarr, Sonarr, Overseerr, Tautulli, Authentik, etc.
          </p>
          <p className="text-blue-800 dark:text-blue-200">
            Pour chaque service, vous devrez fournir son URL et sa clé API ou ses identifiants de connexion.
          </p>
        </div>

        <div className="bg-gray-50 dark:bg-gray-900/50 rounded-lg p-6 border border-gray-200 dark:border-gray-700">
          <h3 className="font-semibold text-gray-900 dark:text-white mb-4">
            Configuration des services
          </h3>
          <div className="space-y-3 text-gray-700 dark:text-gray-300">
            <div className="flex items-start gap-3">
              <div className="w-6 h-6 rounded-full bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center flex-shrink-0 mt-0.5">
                <span className="text-sm font-semibold text-blue-600 dark:text-blue-400">1</span>
              </div>
              <p>
                Accédez à la <strong>page Services</strong> via le menu de navigation
              </p>
            </div>
            <div className="flex items-start gap-3">
              <div className="w-6 h-6 rounded-full bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center flex-shrink-0 mt-0.5">
                <span className="text-sm font-semibold text-blue-600 dark:text-blue-400">2</span>
              </div>
              <p>
                Cliquez sur <strong>"Ajouter un service"</strong> et remplissez le formulaire
              </p>
            </div>
            <div className="flex items-start gap-3">
              <div className="w-6 h-6 rounded-full bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center flex-shrink-0 mt-0.5">
                <span className="text-sm font-semibold text-blue-600 dark:text-blue-400">3</span>
              </div>
              <p>
                Testez la connexion pour vérifier que MCParr peut communiquer avec le service
              </p>
            </div>
            <div className="flex items-start gap-3">
              <div className="w-6 h-6 rounded-full bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center flex-shrink-0 mt-0.5">
                <span className="text-sm font-semibold text-blue-600 dark:text-blue-400">4</span>
              </div>
              <p>
                Répétez l'opération pour tous vos services (recommandé : au moins 2 services)
              </p>
            </div>
          </div>
        </div>

        {/* Action button */}
        <div className="flex justify-center">
          <button
            onClick={handleGoToServices}
            className="flex items-center gap-2 px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors shadow-lg"
          >
            Ouvrir la page Services
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
