import { Brain } from 'lucide-react';
import InfoStepLayout from './InfoStepLayout';

export default function TrainingInfoStep() {
  return (
    <InfoStepLayout
      title="Training IA"
      subtitle="Personnalisez votre assistant"
      icon={Brain}
      iconColor="bg-gradient-to-br from-violet-500 to-purple-600"
      description="Le module de training permet d'entraîner et de personnaliser votre assistant IA en fonction de vos préférences et de votre utilisation. Créez des prompts personnalisés et affinez le comportement de l'IA."
      steps={[
        { text: "Consultez les prompts système actuels" },
        { text: "Créez vos propres prompts personnalisés pour des tâches spécifiques" },
        { text: "Testez et affinez les réponses de l'IA" },
        { text: "Gérez l'historique et les exemples d'entraînement" }
      ]}
      linkText="Accéder au Training"
      linkUrl="/training"
      tip="Les prompts personnalisés permettent d'adapter le comportement de l'IA à vos besoins spécifiques et à votre style d'interaction."
    />
  );
}
