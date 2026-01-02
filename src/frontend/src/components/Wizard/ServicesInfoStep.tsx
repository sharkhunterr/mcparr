import { useTranslation } from 'react-i18next';
import { Server } from 'lucide-react';
import InfoStepLayout from './InfoStepLayout';

export default function ServicesInfoStep() {
  const { t } = useTranslation(['wizard']);

  return (
    <InfoStepLayout
      title={t('steps.services.title')}
      subtitle={t('steps.services.subtitle')}
      icon={Server}
      iconColor="bg-gradient-to-br from-blue-500 to-indigo-600"
      description={t('steps.services.description')}
      steps={t('steps.services.steps', { returnObjects: true }).map((text: string) => ({ text }))}
      linkText={t('steps.services.linkText')}
      linkUrl="/services"
    />
  );
}
