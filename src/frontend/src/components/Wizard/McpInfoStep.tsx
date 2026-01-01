import { Workflow } from 'lucide-react';
import InfoStepLayout from './InfoStepLayout';

export default function McpInfoStep() {
  return (
    <InfoStepLayout
      title="Serveur MCP"
      subtitle="Model Context Protocol"
      icon={Workflow}
      iconColor="bg-gradient-to-br from-emerald-500 to-teal-600"
      description="Le serveur MCP (Model Context Protocol) permet à votre IA d'interagir avec vos services homelab. C'est le pont entre l'assistant conversationnel et vos applications (Plex, Radarr, etc.)."
      steps={[
        { text: "Vérifiez que le serveur MCP est démarré et accessible" },
        { text: "Consultez les outils MCP disponibles pour chaque service" },
        { text: "Testez l'intégration avec votre client IA (Claude Desktop, etc.)" },
        { text: "Configurez les permissions par groupe si nécessaire" }
      ]}
      linkText="Voir la configuration MCP"
      linkUrl="/mcp"
      tip="Le serveur MCP s'exécute en arrière-plan et expose les outils que votre IA peut utiliser pour contrôler vos services."
    />
  );
}
