import { Users } from 'lucide-react';
import InfoStepLayout from './InfoStepLayout';

export default function UsersInfoStep() {
  return (
    <InfoStepLayout
      title="Mapping Utilisateurs"
      subtitle="Associez vos comptes entre services"
      icon={Users}
      iconColor="bg-gradient-to-br from-purple-500 to-pink-600"
      description="Le mapping des utilisateurs permet à MCParr de savoir quel compte dans Plex correspond au même utilisateur dans Overseerr, Radarr, etc. Cela permet de gérer les permissions et l'accès aux outils MCP."
      steps={[
        { text: "Accédez à la page Users via le menu" },
        { text: 'Utilisez l\'onglet "Auto Detection" pour scanner vos services' },
        { text: "Validez les suggestions ou créez des mappings manuels" }
      ]}
      linkText="Mapper les utilisateurs"
      linkUrl="/users"
      tip="La détection automatique fonctionne mieux avec au moins 2 services configurés ayant des utilisateurs."
    />
  );
}
