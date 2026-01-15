import { useTranslation } from 'react-i18next';
import { Link2 } from 'lucide-react';
import InfoStepLayout from './InfoStepLayout';

export default function ChainsInfoStep() {
  const { t } = useTranslation(['wizard']);

  return (
    <InfoStepLayout
      title={t('steps.chains.title')}
      subtitle={t('steps.chains.subtitle')}
      icon={Link2}
      iconColor="bg-gradient-to-br from-purple-500 to-pink-600"
      description={t('steps.chains.description')}
      steps={(t('steps.chains.steps', { returnObjects: true }) as string[]).map((text: string) => ({ text }))}
      linkText={t('steps.chains.linkText')}
      linkUrl="/mcp?tab=chains"
      tip={t('steps.chains.tip')}
    />
  );
}
