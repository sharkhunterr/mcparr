import { useTranslation } from 'react-i18next';
import { Shield } from 'lucide-react';
import InfoStepLayout from './InfoStepLayout';

export default function GroupsInfoStep() {
  const { t } = useTranslation(['wizard']);

  return (
    <InfoStepLayout
      title={t('steps.groups.title')}
      subtitle={t('steps.groups.subtitle')}
      icon={Shield}
      iconColor="bg-gradient-to-br from-orange-500 to-red-600"
      description={t('steps.groups.description')}
      steps={t('steps.groups.steps', { returnObjects: true }).map((text: string) => ({ text }))}
      linkText={t('steps.groups.linkText')}
      linkUrl="/groups"
      tip={t('steps.groups.tip')}
    />
  );
}
