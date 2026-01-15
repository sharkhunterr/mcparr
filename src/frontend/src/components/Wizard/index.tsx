import { useTranslation } from 'react-i18next';
import { useWizard } from '../../contexts/WizardContext';
import WelcomeStep from './WelcomeStep';
import ServicesInfoStep from './ServicesInfoStep';
import UsersInfoStep from './UsersInfoStep';
import GroupsInfoStep from './GroupsInfoStep';
import McpInfoStep from './McpInfoStep';
import ChainsInfoStep from './ChainsInfoStep';
import TrainingInfoStep from './TrainingInfoStep';
import MonitoringInfoStep from './MonitoringInfoStep';
import ConfigInfoStep from './ConfigInfoStep';
import HelpInfoStep from './HelpInfoStep';
import CompleteStep from './CompleteStep';

export default function Wizard() {
  const { t } = useTranslation(['wizard']);
  const { state } = useWizard();

  const renderStep = () => {
    switch (state.currentStep) {
      case 'welcome':
        return <WelcomeStep />;
      case 'services':
        return <ServicesInfoStep />;
      case 'users':
        return <UsersInfoStep />;
      case 'groups':
        return <GroupsInfoStep />;
      case 'mcp':
        return <McpInfoStep />;
      case 'chains':
        return <ChainsInfoStep />;
      case 'training':
        return <TrainingInfoStep />;
      case 'monitoring':
        return <MonitoringInfoStep />;
      case 'config':
        return <ConfigInfoStep />;
      case 'help':
        return <HelpInfoStep />;
      case 'complete':
        return <CompleteStep />;
      default:
        return <WelcomeStep />;
    }
  };

  // Get current step index for progress indicator
  const steps = ['services', 'users', 'groups', 'mcp', 'chains', 'training', 'monitoring', 'config', 'help'];
  const currentIndex = steps.indexOf(state.currentStep);
  const showProgress = currentIndex >= 0;

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Progress indicator */}
      {showProgress && (
        <div className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 sticky top-0 z-10">
          <div className="max-w-4xl mx-auto px-6 py-4">
            {/* Progress bar */}
            <div className="relative h-2 bg-gray-200 dark:bg-gray-700 rounded-full mb-3">
              <div
                className="absolute h-full bg-gradient-to-r from-blue-600 to-indigo-600 rounded-full transition-all duration-300"
                style={{ width: `${((currentIndex + 1) / steps.length) * 100}%` }}
              />
            </div>

            {/* Step labels */}
            <div className="flex items-center justify-between text-xs">
              {steps.map((step, index) => {
                const isActive = index === currentIndex;
                const isDone = index < currentIndex;
                return (
                  <div
                    key={step}
                    className={`flex flex-col items-center transition-colors ${
                      isActive
                        ? 'text-blue-600 dark:text-blue-400 font-semibold'
                        : isDone
                        ? 'text-gray-600 dark:text-gray-400'
                        : 'text-gray-400 dark:text-gray-600'
                    }`}
                  >
                    <span className="capitalize hidden sm:block">{t(`progress.stepLabels.${step}`)}</span>
                    <span className="sm:hidden">{index + 1}</span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* Current step */}
      {renderStep()}
    </div>
  );
}
