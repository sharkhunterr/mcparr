import { Server } from 'lucide-react';
import InfoStepLayout from './InfoStepLayout';

export default function ServicesInfoStep() {
  return (
    <InfoStepLayout
      title="Services Homelab"
      subtitle="Connectez vos applications"
      icon={Server}
      iconColor="bg-gradient-to-br from-blue-500 to-indigo-600"
      description="Configurez les services de votre homelab que MCParr pourra contrôler : Plex, Radarr, Sonarr, Overseerr, Tautulli, etc. Pour chaque service, vous devrez fournir son URL et sa clé API ou ses identifiants."
      steps={[
        { text: "Accédez à la page Services via le menu de navigation" },
        { text: 'Cliquez sur "Ajouter un service" et remplissez le formulaire' },
        { text: "Testez la connexion pour vérifier la communication" },
        { text: "Répétez pour tous vos services (recommandé : au moins 2)" }
      ]}
      linkText="Configurer les services"
      linkUrl="/services"
    />
  );
}
