import { Shield } from 'lucide-react';
import InfoStepLayout from './InfoStepLayout';

export default function GroupsInfoStep() {
  return (
    <InfoStepLayout
      title="Groupes & Permissions"
      subtitle="Contrôlez l'accès aux outils MCP"
      icon={Shield}
      iconColor="bg-gradient-to-br from-orange-500 to-red-600"
      description="Les groupes définissent quels outils MCP (Model Context Protocol) sont accessibles à vos utilisateurs. Par exemple, un groupe 'Admin' pourrait avoir accès à tous les outils, tandis qu'un groupe 'User' n'aurait accès qu'aux outils de consultation."
      steps={[
        { text: "Accédez à la page Groups via le menu" },
        { text: 'Créez des groupes (Admin, User, Family...) avec "Create Group"' },
        { text: "Assignez les permissions MCP à chaque groupe" },
        { text: "Assignez vos utilisateurs aux groupes appropriés" }
      ]}
      linkText="Gérer les groupes"
      linkUrl="/groups"
      tip="Les outils MCP permettent à l'IA d'interagir avec vos services. Les permissions contrôlent ce que chaque groupe peut faire."
    />
  );
}
