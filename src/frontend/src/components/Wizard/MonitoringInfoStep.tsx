import { Activity } from 'lucide-react';
import InfoStepLayout from './InfoStepLayout';

export default function MonitoringInfoStep() {
  return (
    <InfoStepLayout
      title="Monitoring"
      subtitle="Surveillez votre système"
      icon={Activity}
      iconColor="bg-gradient-to-br from-cyan-500 to-blue-600"
      description="Le monitoring vous permet de surveiller en temps réel l'état de vos services, les performances du système, et l'historique des interactions avec l'IA. Détectez rapidement les problèmes et optimisez votre infrastructure."
      steps={[
        { text: "Consultez le dashboard de monitoring en temps réel" },
        { text: "Vérifiez l'état de santé de chaque service" },
        { text: "Analysez les métriques de performance (CPU, RAM, réseau)" },
        { text: "Configurez des alertes pour être notifié des problèmes" }
      ]}
      linkText="Voir le Monitoring"
      linkUrl="/monitoring"
      tip="Le monitoring proactif vous aide à identifier et résoudre les problèmes avant qu'ils n'impactent vos utilisateurs."
    />
  );
}
