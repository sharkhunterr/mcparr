import { ArrowRight, ArrowLeft, ExternalLink } from 'lucide-react';
import { useWizard } from '../../contexts/WizardContext';
import type { FC } from 'react';

interface InfoStepLayoutProps {
  title: string;
  subtitle: string;
  icon: FC<{ className?: string }>;
  iconColor: string;
  description: string;
  steps: Array<{ text: string }>;
  linkText: string;
  linkUrl: string;
  tip?: string;
}

export default function InfoStepLayout({
  title,
  subtitle,
  icon: Icon,
  iconColor,
  description,
  steps,
  linkText,
  linkUrl,
  tip
}: InfoStepLayoutProps) {
  const { nextStep, previousStep } = useWizard();

  return (
    <div className="p-6 max-w-4xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-4 mb-3">
          <div className={`p-3 rounded-xl ${iconColor}`}>
            <Icon className="w-8 h-8 text-white" />
          </div>
          <div>
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
              {title}
            </h2>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              {subtitle}
            </p>
          </div>
        </div>
      </div>

      {/* Content Card */}
      <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-sm border border-gray-200 dark:border-gray-700 p-8 mb-6">
        {/* Description */}
        <p className="text-gray-700 dark:text-gray-300 mb-6 leading-relaxed">
          {description}
        </p>

        {/* Steps */}
        <div className="space-y-3 mb-6">
          {steps.map((step, index) => (
            <div key={index} className="flex items-start gap-3">
              <div className="flex-shrink-0 w-7 h-7 rounded-full bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center">
                <span className="text-xs font-semibold text-white">{index + 1}</span>
              </div>
              <p className="text-sm text-gray-700 dark:text-gray-300 pt-0.5">
                {step.text}
              </p>
            </div>
          ))}
        </div>

        {/* Tip */}
        {tip && (
          <div className="p-4 bg-blue-50 dark:bg-blue-900/20 rounded-xl border border-blue-200 dark:border-blue-800">
            <p className="text-sm text-blue-800 dark:text-blue-200">
              <span className="font-semibold">💡 Astuce :</span> {tip}
            </p>
          </div>
        )}
      </div>

      {/* Action button */}
      <div className="flex justify-center mb-8">
        <a
          href={linkUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white rounded-xl font-medium transition-all shadow-lg hover:shadow-xl"
        >
          {linkText}
          <ExternalLink className="w-4 h-4" />
        </a>
      </div>

      {/* Navigation */}
      <div className="flex items-center justify-between pt-6 border-t border-gray-200 dark:border-gray-700">
        <button
          onClick={previousStep}
          className="flex items-center gap-2 px-4 py-2 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Précédent
        </button>
        <button
          onClick={nextStep}
          className="flex items-center gap-2 px-6 py-2.5 bg-gray-900 dark:bg-white text-white dark:text-gray-900 hover:bg-gray-800 dark:hover:bg-gray-100 rounded-xl transition-colors font-medium"
        >
          Suivant
          <ArrowRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}
