import { CheckCircle, Home, Sparkles } from 'lucide-react';
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
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center p-4">
      <div className="max-w-3xl w-full">
        <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl border border-gray-200 dark:border-gray-700 p-8 md:p-12">
          {/* Icon */}
          <div className="flex justify-center mb-6">
            <div className="relative">
              <div className="p-4 rounded-2xl bg-gradient-to-br from-emerald-500 to-teal-600 shadow-lg">
                <CheckCircle className="w-12 h-12 text-white" />
              </div>
              <div className="absolute -top-2 -right-2">
                <Sparkles className="w-6 h-6 text-yellow-400 animate-pulse" />
              </div>
            </div>
          </div>

          {/* Title */}
          <h1 className="text-3xl md:text-4xl font-bold text-center bg-gradient-to-r from-gray-900 to-gray-600 dark:from-white dark:to-gray-300 bg-clip-text text-transparent mb-4">
            Configuration terminée !
          </h1>

          {/* Subtitle */}
          <p className="text-lg text-center text-gray-600 dark:text-gray-400 mb-8">
            MCParr est prêt à être utilisé
          </p>

          {/* Next steps */}
          <div className="bg-gray-50 dark:bg-gray-900/50 rounded-xl p-6 mb-8">
            <h3 className="font-semibold text-gray-900 dark:text-white mb-4 text-center">
              Prochaines étapes recommandées
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {[
                { emoji: '🔌', text: 'Configurez vos services' },
                { emoji: '👥', text: 'Mappez vos utilisateurs' },
                { emoji: '🛡️', text: 'Créez des groupes' },
                { emoji: '🤖', text: 'Testez l\'interface IA' }
              ].map((item, i) => (
                <div key={i} className="flex items-center gap-3 p-3 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
                  <span className="text-xl">{item.emoji}</span>
                  <span className="text-sm text-gray-700 dark:text-gray-300">{item.text}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Info */}
          <p className="text-sm text-center text-gray-500 dark:text-gray-400 mb-8">
            Vous pouvez retrouver ce guide à tout moment depuis <br />
            <span className="font-medium">Configuration → General → Réinitialiser le guide</span>
          </p>

          {/* Action */}
          <div className="flex justify-center">
            <button
              onClick={handleFinish}
              className="flex items-center gap-2 px-8 py-3.5 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white rounded-xl font-medium transition-all shadow-lg hover:shadow-xl"
            >
              <Home className="w-5 h-5" />
              Accéder au Dashboard
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
