import { useTranslation } from 'react-i18next';
import { Workflow } from 'lucide-react';
import InfoStepLayout from './InfoStepLayout';

export default function McpInfoStep() {
  const { t } = useTranslation(['wizard']);

  return (
    <InfoStepLayout
      title={t('steps.mcp.title')}
      subtitle={t('steps.mcp.subtitle')}
      icon={Workflow}
      iconColor="bg-gradient-to-br from-emerald-500 to-teal-600"
      description={t('steps.mcp.description')}
      steps={t('steps.mcp.steps', { returnObjects: true }).map((text: string) => ({ text }))}
      linkText={t('steps.mcp.linkText')}
      linkUrl="/mcp"
      tip={t('steps.mcp.tip')}
    />
  );
}
