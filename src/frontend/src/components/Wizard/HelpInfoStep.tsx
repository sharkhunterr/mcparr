import { useTranslation } from 'react-i18next';
import { HelpCircle } from 'lucide-react';
import InfoStepLayout from './InfoStepLayout';

export default function HelpInfoStep() {
  const { t } = useTranslation(['wizard']);

  return (
    <InfoStepLayout
      title={t('steps.help.title')}
      subtitle={t('steps.help.subtitle')}
      icon={HelpCircle}
      iconColor="bg-gradient-to-br from-cyan-500 to-blue-600"
      description={t('steps.help.description')}
      steps={(t('steps.help.steps', { returnObjects: true }) as string[]).map((text: string) => ({ text }))}
      linkText={t('steps.help.linkText')}
      linkUrl="/help"
      tip={t('steps.help.tip')}
    />
  );
}
