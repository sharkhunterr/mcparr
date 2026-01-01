import { CheckCircle, Home } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useWizard } from '../../contexts/WizardContext';

export default function CompleteStep() {
  const { completeWizard } = useWizard();
  const navigate = useNavigate();

  const handleFinish = () => {
    completeWizard();
    navigate('/');
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-green-50 to-emerald-100 dark:from-gray-900 dark:to-gray-800 flex items-center justify-center p-4">
      <div className="max-w-2xl w-full bg-white dark:bg-gray-800 rounded-2xl shadow-2xl p-8 md:p-12">
        {/* Icon */}
        <div className="flex justify-center mb-6">
          <div className="p-4 rounded-full bg-gradient-to-br from-green-500 to-emerald-600">
            <CheckCircle className="w-12 h-12 text-white" />
          </div>
        </div>

        {/* Title */}
        <h1 className="text-3xl md:text-4xl font-bold text-center text-gray-900 dark:text-white mb-4">
          Guide terminé !
        </h1>

        {/* Subtitle */}
        <p className="text-lg text-center text-gray-600 dark:text-gray-300 mb-8">
          Vous avez maintenant toutes les informations pour configurer MCParr
        </p>

        {/* Next steps */}
        <div className="bg-gray-50 dark:bg-gray-900/50 rounded-lg p-6 border border-gray-200 dark:border-gray-700 mb-8">
          <h3 className="font-semibold text-gray-900 dark:text-white mb-4">
            Prochaines étapes recommandées :
          </h3>
          <div className="space-y-3 text-gray-700 dark:text-gray-300">
            <div className="flex items-start gap-3">
              <span className="text-lg">📝</span>
              <p>
                Configurez vos <strong>services</strong> dans la page Services
              </p>
            </div>
            <div className="flex items-start gap-3">
              <span className="text-lg">👥</span>
              <p>
                Créez les <strong>mappings utilisateurs</strong> dans la page Users
              </p>
            </div>
            <div className="flex items-start gap-3">
              <span className="text-lg">🛡️</span>
              <p>
                Définissez les <strong>groupes et permissions</strong> dans la page Groups
              </p>
            </div>
            <div className="flex items-start gap-3">
              <span className="text-lg">🤖</span>
              <p>
                Testez l'<strong>interface conversationnelle</strong> avec votre IA
              </p>
            </div>
          </div>
        </div>

        {/* Action */}
        <div className="flex justify-center">
          <button
            onClick={handleFinish}
            className="flex items-center gap-2 px-8 py-4 bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700 text-white rounded-lg font-medium transition-all shadow-lg hover:shadow-xl"
          >
            <Home className="w-5 h-5" />
            Aller au Dashboard
          </button>
        </div>

        {/* Reset link */}
        <div className="mt-6 text-center">
          <button
            onClick={() => navigate('/settings')}
            className="text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition-colors"
          >
            Vous pouvez réafficher ce guide depuis les paramètres
          </button>
        </div>
      </div>
    </div>
  );
}
