import { useTranslation } from 'react-i18next';
import { Activity } from 'lucide-react';
import InfoStepLayout from './InfoStepLayout';

export default function MonitoringInfoStep() {
  const { t } = useTranslation(['wizard']);

  return (
    <InfoStepLayout
      title={t('steps.monitoring.title')}
      subtitle={t('steps.monitoring.subtitle')}
      icon={Activity}
      iconColor="bg-gradient-to-br from-cyan-500 to-blue-600"
      description={t('steps.monitoring.description')}
      steps={t('steps.monitoring.steps', { returnObjects: true }).map((text: string) => ({ text }))}
      linkText={t('steps.monitoring.linkText')}
      linkUrl="/monitoring"
      tip={t('steps.monitoring.tip')}
    />
  );
}
