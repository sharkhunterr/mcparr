import { Settings } from 'lucide-react';
import InfoStepLayout from './InfoStepLayout';

export default function ConfigInfoStep() {
  return (
    <InfoStepLayout
      title="Configuration"
      subtitle="Personnalisez MCParr"
      icon={Settings}
      iconColor="bg-gradient-to-br from-slate-500 to-gray-600"
      description="La page de configuration centralise tous les paramètres de l'application : apparence, notifications, logs, dashboard, et sauvegarde. Personnalisez MCParr selon vos préférences et exportez votre configuration."
      steps={[
        { text: "Ajustez le thème (clair, sombre, système)" },
        { text: "Configurez les notifications et alertes" },
        { text: "Définissez le niveau de logs et l'actualisation automatique" },
        { text: "Exportez/importez votre configuration pour la sauvegarder" }
      ]}
      linkText="Ouvrir la Configuration"
      linkUrl="/configuration"
      tip="Pensez à exporter régulièrement votre configuration pour pouvoir la restaurer facilement en cas de besoin."
    />
  );
}
