import { useWizard } from '../../contexts/WizardContext';
import WelcomeStep from './WelcomeStep';
import ServicesInfoStep from './ServicesInfoStep';
import UsersInfoStep from './UsersInfoStep';
import GroupsInfoStep from './GroupsInfoStep';
import CompleteStep from './CompleteStep';

export default function Wizard() {
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
      case 'complete':
        return <CompleteStep />;
      default:
        return <WelcomeStep />;
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Progress indicator (only for info steps) */}
      {!['welcome', 'complete'].includes(state.currentStep) && (
        <div className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
          <div className="max-w-3xl mx-auto px-4 py-4">
            <div className="flex items-center justify-between">
              <div className={`flex-1 h-2 rounded-full ${
                state.currentStep === 'services' ? 'bg-blue-600' : 'bg-gray-200 dark:bg-gray-700'
              }`} />
              <div className="w-8" />
              <div className={`flex-1 h-2 rounded-full ${
                state.currentStep === 'users' ? 'bg-purple-600' :
                state.currentStep === 'groups' ? 'bg-gray-200 dark:bg-gray-700' :
                'bg-gray-200 dark:bg-gray-700'
              }`} />
              <div className="w-8" />
              <div className={`flex-1 h-2 rounded-full ${
                state.currentStep === 'groups' ? 'bg-orange-600' : 'bg-gray-200 dark:bg-gray-700'
              }`} />
            </div>
            <div className="flex items-center justify-between mt-2 text-xs text-gray-600 dark:text-gray-400">
              <span className={state.currentStep === 'services' ? 'font-semibold text-blue-600 dark:text-blue-400' : ''}>
                Services
              </span>
              <span className={state.currentStep === 'users' ? 'font-semibold text-purple-600 dark:text-purple-400' : ''}>
                Users
              </span>
              <span className={state.currentStep === 'groups' ? 'font-semibold text-orange-600 dark:text-orange-400' : ''}>
                Groups
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Current step */}
      {renderStep()}
    </div>
  );
}
