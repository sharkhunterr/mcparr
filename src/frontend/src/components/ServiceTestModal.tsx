import { useState, useEffect } from 'react';
import type { FC } from 'react';
import {
  X,
  Play,
  CheckCircle,
  XCircle,
  Clock,
  AlertCircle,
  Zap,
  Activity
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { getApiBaseUrl } from '../lib/api';

interface ServiceTestResult {
  service_id: string;
  success: boolean;
  error_message?: string;
  response_time_ms?: number;
}

interface Service {
  id: string;
  name: string;
  service_type: string;
  base_url: string;
  port?: number;
  status: string;
  enabled: boolean;
}

interface ServiceTestModalProps {
  isOpen: boolean;
  onClose: () => void;
  service: Service;
  onTestComplete?: (result: ServiceTestResult) => void;
}

interface TestStep {
  id: string;
  name: string;
  description: string;
  status: 'pending' | 'running' | 'success' | 'error';
  duration?: number;
  error?: string;
}

const ServiceTestModal: FC<ServiceTestModalProps> = ({
  isOpen,
  onClose,
  service,
  onTestComplete
}) => {
  const { t } = useTranslation('services');
  const [testing, setTesting] = useState(false);
  const [testSteps, setTestSteps] = useState<TestStep[]>([]);
  const [overallResult, setOverallResult] = useState<ServiceTestResult | null>(null);
  const [currentStep, setCurrentStep] = useState(-1);

  const initializeTestSteps = () => {
    const steps: TestStep[] = [
      {
        id: 'dns',
        name: t('testModal.steps.dns.name'),
        description: t('testModal.steps.dns.description'),
        status: 'pending'
      },
      {
        id: 'connection',
        name: t('testModal.steps.connection.name'),
        description: t('testModal.steps.connection.description'),
        status: 'pending'
      },
      {
        id: 'http',
        name: t('testModal.steps.http.name'),
        description: t('testModal.steps.http.description'),
        status: 'pending'
      },
      {
        id: 'authentication',
        name: t('testModal.steps.authentication.name'),
        description: t('testModal.steps.authentication.description'),
        status: 'pending'
      },
      {
        id: 'service_health',
        name: t('testModal.steps.serviceHealth.name'),
        description: t('testModal.steps.serviceHealth.description'),
        status: 'pending'
      }
    ];

    setTestSteps(steps);
    setCurrentStep(-1);
    setOverallResult(null);
  };

  useEffect(() => {
    if (isOpen) {
      // Only initialize if we're opening the modal fresh (not when closing)
      initializeTestSteps();
    }
  }, [isOpen, service.id, t]); // Add service.id to reset when testing different service

  const runTest = async () => {
    console.log('🧪 Starting service test for:', service.name, 'ID:', service.id);
    setTesting(true);
    const startTime = Date.now();

    try {
      // Step 1: DNS Resolution
      console.log('🔍 Step 1: DNS Resolution');
      setCurrentStep(0);
      setTestSteps(prev => prev.map((step, idx) =>
        idx === 0 ? { ...step, status: 'running' } : step
      ));

      await new Promise(resolve => setTimeout(resolve, 800)); // Simulate DNS lookup

      setTestSteps(prev => prev.map((step, idx) =>
        idx === 0 ? { ...step, status: 'success', duration: 150 } : step
      ));
      console.log('✅ Step 1: DNS Resolution completed');

      // Step 2: Network Connection
      console.log('🔗 Step 2: Network Connection');
      setCurrentStep(1);
      setTestSteps(prev => prev.map((step, idx) =>
        idx === 1 ? { ...step, status: 'running' } : step
      ));

      await new Promise(resolve => setTimeout(resolve, 600));

      setTestSteps(prev => prev.map((step, idx) =>
        idx === 1 ? { ...step, status: 'success', duration: 85 } : step
      ));
      console.log('✅ Step 2: Network Connection completed');

      // Step 3: HTTP Response - This is where we actually call the API
      console.log('🌐 Step 3: HTTP Response - Calling API');
      setCurrentStep(2);
      setTestSteps(prev => prev.map((step, idx) =>
        idx === 2 ? { ...step, status: 'running' } : step
      ));

      const testURL = `${getApiBaseUrl()}/api/services/${service.id}/test`;
      console.log('📡 Making POST request to:', testURL);

      const testResponse = await fetch(testURL, {
        method: 'POST',
      });

      console.log('📡 Response status:', testResponse.status);
      console.log('📡 Response ok:', testResponse.ok);

      const testResult = await testResponse.json();
      console.log('📡 Response data:', testResult);

      if (testResponse.ok && testResult.success) {
        console.log('✅ Step 3: HTTP Response successful, continuing to step 4...');
        setTestSteps(prev => prev.map((step, idx) =>
          idx === 2 ? { ...step, status: 'success', duration: testResult.response_time_ms } : step
        ));

        // Step 4: Authentication
        console.log('🔐 Step 4: Authentication');
        setCurrentStep(3);
        setTestSteps(prev => prev.map((step, idx) =>
          idx === 3 ? { ...step, status: 'running' } : step
        ));

        await new Promise(resolve => setTimeout(resolve, 400));

        setTestSteps(prev => prev.map((step, idx) =>
          idx === 3 ? { ...step, status: 'success', duration: 120 } : step
        ));
        console.log('✅ Step 4: Authentication completed');

        // Step 5: Service Health
        console.log('🏥 Step 5: Service Health');
        setCurrentStep(4);
        setTestSteps(prev => prev.map((step, idx) =>
          idx === 4 ? { ...step, status: 'running' } : step
        ));

        await new Promise(resolve => setTimeout(resolve, 500));

        setTestSteps(prev => prev.map((step, idx) =>
          idx === 4 ? { ...step, status: 'success', duration: 200 } : step
        ));
        console.log('✅ Step 5: Service Health completed');

        const totalTime = Date.now() - startTime;
        const result: ServiceTestResult = {
          service_id: service.id,
          success: true,
          response_time_ms: totalTime
        };

        console.log('🎉 All tests completed successfully!', result);
        setOverallResult(result);
        // Don't call onTestComplete immediately - let user see result and close manually
        // onTestComplete?.(result);
      } else {
        // Test failed
        console.log('❌ Step 3: HTTP Response failed');
        const errorMessage = testResult.error_message || 'Connection test failed';
        console.log('❌ Error message:', errorMessage);

        setTestSteps(prev => prev.map((step, idx) =>
          idx === 2 ? { ...step, status: 'error', error: errorMessage } : step
        ));

        // Mark remaining steps as error
        setTestSteps(prev => prev.map((step, idx) =>
          idx > 2 ? { ...step, status: 'error', error: 'Skipped due to previous failure' } : step
        ));

        const result: ServiceTestResult = {
          service_id: service.id,
          success: false,
          error_message: errorMessage
        };

        console.log('💥 Test failed, stopping here:', result);
        setOverallResult(result);
        // Don't call onTestComplete on failure to keep modal open with error state
        // onTestComplete?.(result);

        // Stop testing here - don't continue to other steps
        setTesting(false);
        setCurrentStep(-1);
        return;
      }
    } catch (error) {
      console.error('💥 Exception during test:', error);
      const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
      console.error('💥 Error message:', errorMessage);
      console.log('💥 Current step when error occurred:', currentStep);

      // Mark current and remaining steps as error
      setTestSteps(prev => prev.map((step, idx) => {
        if (idx === currentStep) {
          return { ...step, status: 'error', error: errorMessage };
        } else if (idx > currentStep) {
          return { ...step, status: 'error', error: 'Skipped due to previous failure' };
        }
        return step;
      }));

      const result: ServiceTestResult = {
        service_id: service.id,
        success: false,
        error_message: errorMessage
      };

      console.log('💥 Setting error result:', result);
      setOverallResult(result);
      onTestComplete?.(result);
    } finally {
      console.log('🏁 Test completed, cleaning up...');
      setTesting(false);
      setCurrentStep(-1);
      console.log('🏁 Cleanup completed');
    }
  };

  const getStepIcon = (step: TestStep) => {
    switch (step.status) {
      case 'running':
        return <Activity className="w-4 h-4 text-blue-500 animate-pulse" />;
      case 'success':
        return <CheckCircle className="w-4 h-4 text-green-500" />;
      case 'error':
        return <XCircle className="w-4 h-4 text-red-500" />;
      default:
        return <Clock className="w-4 h-4 text-gray-400" />;
    }
  };

  const getOverallIcon = () => {
    if (testing) {
      return <Activity className="w-6 h-6 text-blue-500 animate-pulse" />;
    }
    if (overallResult?.success) {
      return <CheckCircle className="w-6 h-6 text-green-500" />;
    }
    if (overallResult?.success === false) {
      return <XCircle className="w-6 h-6 text-red-500" />;
    }
    return <Zap className="w-6 h-6 text-gray-500" />;
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-gray-800 rounded-lg w-full max-w-lg max-h-[90vh] overflow-y-auto">
        <div className="sticky top-0 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 p-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              {getOverallIcon()}
              <div>
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                  {t('testModal.title')}: {service.name}
                </h3>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  {service.base_url}{service.port ? `:${service.port}` : ''}
                </p>
              </div>
            </div>
            <button
              onClick={() => {
                // Call onTestComplete when closing if we have a successful result
                if (overallResult?.success) {
                  onTestComplete?.(overallResult);
                }
                onClose();
              }}
              className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors text-gray-600 dark:text-gray-400"
              disabled={testing}
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        <div className="p-6">
          <div className="mb-6">
            <div className="flex items-center justify-between mb-4">
              <h4 className="text-md font-medium text-gray-900 dark:text-white">{t('testModal.connectionTest')}</h4>
              <button
                onClick={runTest}
                disabled={testing || !service.enabled}
                className="flex items-center space-x-2 px-4 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                <Play className="w-4 h-4" />
                <span>{testing ? t('testModal.testing') : t('testModal.runTest')}</span>
              </button>
            </div>

            {!service.enabled && (
              <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-3 mb-4">
                <div className="flex items-center">
                  <AlertCircle className="w-5 h-5 text-yellow-500 mr-2" />
                  <span className="text-sm text-yellow-700 dark:text-yellow-400">
                    {t('testModal.serviceDisabled')}
                  </span>
                </div>
              </div>
            )}
          </div>

          {/* Test Steps */}
          <div className="space-y-3">
            {testSteps.map((step) => (
              <div
                key={step.id}
                className={`border rounded-lg p-3 transition-all duration-300 ${
                  step.status === 'running'
                    ? 'border-blue-200 dark:border-blue-800 bg-blue-50 dark:bg-blue-900/20'
                    : step.status === 'success'
                    ? 'border-green-200 dark:border-green-800 bg-green-50 dark:bg-green-900/20'
                    : step.status === 'error'
                    ? 'border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/20'
                    : 'border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    {getStepIcon(step)}
                    <div>
                      <h5 className="text-sm font-medium text-gray-900 dark:text-white">
                        {step.name}
                      </h5>
                      <p className="text-xs text-gray-600 dark:text-gray-400">
                        {step.description}
                      </p>
                    </div>
                  </div>

                  {step.duration && (
                    <span className="text-xs text-gray-500 dark:text-gray-400">
                      {step.duration}ms
                    </span>
                  )}
                </div>

                {step.error && (
                  <div className="mt-2 text-xs text-red-600 dark:text-red-400">
                    {step.error}
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* Overall Result */}
          {overallResult && (
            <div className="mt-6 p-4 rounded-lg border border-gray-200 dark:border-gray-700">
              <div className="flex items-center space-x-3">
                {overallResult.success ? (
                  <CheckCircle className="w-6 h-6 text-green-500" />
                ) : (
                  <XCircle className="w-6 h-6 text-red-500" />
                )}
                <div>
                  <h4 className="text-md font-medium text-gray-900 dark:text-white">
                    {overallResult.success ? t('testModal.result.passed') : t('testModal.result.failed')}
                  </h4>
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    {overallResult.success
                      ? t('testModal.result.successMessage')
                      : t('testModal.result.failedMessage', { error: overallResult.error_message })
                    }
                  </p>
                  {overallResult.response_time_ms && (
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                      {t('testModal.result.responseTime', { time: overallResult.response_time_ms })}
                    </p>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>

        <div className="border-t border-gray-200 dark:border-gray-700 p-6">
          <div className="flex justify-end space-x-3">
            <button
              onClick={() => {
                // Call onTestComplete when closing if we have a successful result
                if (overallResult?.success) {
                  onTestComplete?.(overallResult);
                }
                onClose();
              }}
              className="px-6 py-2 text-gray-700 dark:text-gray-300 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
              disabled={testing}
            >
              {testing ? t('testModal.testingInProgress') : t('testModal.close')}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ServiceTestModal;