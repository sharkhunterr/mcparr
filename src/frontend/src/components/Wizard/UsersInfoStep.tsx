import { useTranslation } from 'react-i18next';
import { Users } from 'lucide-react';
import InfoStepLayout from './InfoStepLayout';

export default function UsersInfoStep() {
  const { t } = useTranslation(['wizard']);

  return (
    <InfoStepLayout
      title={t('steps.users.title')}
      subtitle={t('steps.users.subtitle')}
      icon={Users}
      iconColor="bg-gradient-to-br from-purple-500 to-pink-600"
      description={t('steps.users.description')}
      steps={t('steps.users.steps', { returnObjects: true }).map((text: string) => ({ text }))}
      linkText={t('steps.users.linkText')}
      linkUrl="/users"
      tip={t('steps.users.tip')}
    />
  );
}
