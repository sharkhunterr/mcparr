import { useTranslation } from 'react-i18next';
import { Settings } from 'lucide-react';
import InfoStepLayout from './InfoStepLayout';

export default function ConfigInfoStep() {
  const { t } = useTranslation(['wizard']);

  return (
    <InfoStepLayout
      title={t('steps.config.title')}
      subtitle={t('steps.config.subtitle')}
      icon={Settings}
      iconColor="bg-gradient-to-br from-slate-500 to-gray-600"
      description={t('steps.config.description')}
      steps={t('steps.config.steps', { returnObjects: true }).map((text: string) => ({ text }))}
      linkText={t('steps.config.linkText')}
      linkUrl="/configuration"
      tip={t('steps.config.tip')}
    />
  );
}
