import { useTranslation } from 'react-i18next';
import { Brain } from 'lucide-react';
import InfoStepLayout from './InfoStepLayout';

export default function TrainingInfoStep() {
  const { t } = useTranslation(['wizard']);

  return (
    <InfoStepLayout
      title={t('steps.training.title')}
      subtitle={t('steps.training.subtitle')}
      icon={Brain}
      iconColor="bg-gradient-to-br from-violet-500 to-purple-600"
      description={t('steps.training.description')}
      steps={(t('steps.training.steps', { returnObjects: true }) as string[]).map((text: string) => ({ text }))}
      linkText={t('steps.training.linkText')}
      linkUrl="/training"
      tip={t('steps.training.tip')}
    />
  );
}
