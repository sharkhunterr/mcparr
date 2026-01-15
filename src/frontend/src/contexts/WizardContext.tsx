import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';

export type WizardStep = 'welcome' | 'services' | 'users' | 'groups' | 'mcp' | 'chains' | 'training' | 'monitoring' | 'config' | 'help' | 'complete';

interface WizardState {
  currentStep: WizardStep;
  hasCompletedWizard: boolean;
}

interface WizardContextType {
  state: WizardState;
  nextStep: () => void;
  previousStep: () => void;
  skipWizard: () => void;
  completeWizard: () => void;
  resetWizard: () => void;
}

const WizardContext = createContext<WizardContextType | undefined>(undefined);

const WIZARD_KEY = 'mcparr-wizard-completed';

const stepOrder: WizardStep[] = ['welcome', 'services', 'users', 'groups', 'mcp', 'chains', 'training', 'monitoring', 'config', 'help', 'complete'];

const defaultState: WizardState = {
  currentStep: 'welcome',
  hasCompletedWizard: false,
};

export function WizardProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<WizardState>(() => {
    if (typeof window === 'undefined') return defaultState;
    try {
      const completed = localStorage.getItem(WIZARD_KEY) === 'true';
      return { ...defaultState, hasCompletedWizard: completed };
    } catch {
      return defaultState;
    }
  });

  useEffect(() => {
    localStorage.setItem(WIZARD_KEY, state.hasCompletedWizard.toString());
  }, [state.hasCompletedWizard]);

  const nextStep = () => {
    const currentIndex = stepOrder.indexOf(state.currentStep);
    if (currentIndex < stepOrder.length - 1) {
      setState(prev => ({ ...prev, currentStep: stepOrder[currentIndex + 1] }));
    }
  };

  const previousStep = () => {
    const currentIndex = stepOrder.indexOf(state.currentStep);
    if (currentIndex > 0) {
      setState(prev => ({ ...prev, currentStep: stepOrder[currentIndex - 1] }));
    }
  };

  const skipWizard = () => {
    setState(prev => ({ ...prev, hasCompletedWizard: true, currentStep: 'complete' }));
  };

  const completeWizard = () => {
    setState(prev => ({ ...prev, hasCompletedWizard: true, currentStep: 'complete' }));
  };

  const resetWizard = () => {
    setState(defaultState);
    localStorage.removeItem(WIZARD_KEY);
  };

  return (
    <WizardContext.Provider
      value={{
        state,
        nextStep,
        previousStep,
        skipWizard,
        completeWizard,
        resetWizard,
      }}
    >
      {children}
    </WizardContext.Provider>
  );
}

export function useWizard() {
  const context = useContext(WizardContext);
  if (!context) {
    throw new Error('useWizard must be used within WizardProvider');
  }
  return context;
}
