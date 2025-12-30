# Intégration LLaMA-Factory pour le Fine-Tuning

Ce document décrit l'architecture proposée pour intégrer LLaMA-Factory comme service de fine-tuning dans ia-homelab.

## Pourquoi LLaMA-Factory ?

LLaMA-Factory est un framework de fine-tuning unifié qui supporte plus de 100 LLMs. C'est la solution recommandée car :

- **API REST native** : OpenAI-compatible, pas besoin de wrapper custom
- **Image Docker officielle** : Prêt à l'emploi avec GPU
- **WebUI Gradio** : Interface graphique pour le monitoring
- **CLI complète** : Automatisation via commandes
- **Méthodes de training** : LoRA, QLoRA, full fine-tuning
- **Export facile** : Convertible en GGUF pour Ollama
- **Projet actif** : Présenté à ACL 2024

## Architecture Proposée

```
┌─────────────────────────────────────────────────────────────┐
│                        PC IA (GPU)                          │
│  ┌─────────────────────────────────────────────────────┐   │
│  │           LLaMA-Factory Docker                       │   │
│  │   - Port 7860: WebUI Gradio                         │   │
│  │   - Port 8000: API REST OpenAI-compatible           │   │
│  │   - Volume: /data/models                            │   │
│  │   - Volume: /data/training                          │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ HTTP API / SSH
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      ia-homelab                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Backend: LLaMA-Factory Service                      │   │
│  │  - Envoie les prompts de training                   │   │
│  │  - Lance/monitor les sessions                       │   │
│  │  - Récupère le statut en temps réel                 │   │
│  │  - Déclenche l'export vers Ollama                   │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  MCP Tool: llamafactory_train                        │   │
│  │  - Piloter le training via LLM                      │   │
│  │  - "Entraîne le modèle avec les prompts homelab"    │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Installation sur le PC IA

### Prérequis

- Docker avec support GPU (nvidia-docker2)
- NVIDIA Driver compatible CUDA
- Minimum 8GB VRAM pour QLoRA, 16GB+ pour LoRA

### Déploiement Docker

```bash
# Créer les répertoires de données
mkdir -p /data/llamafactory/{models,datasets,outputs}

# Lancer le conteneur
docker run -dit --gpus=all \
    -p 7860:7860 \
    -p 8000:8000 \
    -v /data/llamafactory/models:/app/models \
    -v /data/llamafactory/datasets:/app/data \
    -v /data/llamafactory/outputs:/app/output \
    --name llamafactory \
    hiyouga/llamafactory:latest
```

### Docker Compose (recommandé)

```yaml
# docker-compose.yml
version: '3.8'

services:
  llamafactory:
    image: hiyouga/llamafactory:latest
    container_name: llamafactory
    runtime: nvidia
    environment:
      - NVIDIA_VISIBLE_DEVICES=all
    ports:
      - "7860:7860"  # WebUI
      - "8000:8000"  # API
    volumes:
      - ./models:/app/models
      - ./datasets:/app/data
      - ./outputs:/app/output
    restart: unless-stopped
```

## Workflow de Training

### 1. Préparation des données

Les prompts créés dans ia-homelab sont exportés au format Alpaca :

```json
[
  {
    "instruction": "Comment ajouter un film à ma liste Overseerr ?",
    "input": "",
    "output": "Pour ajouter un film à Overseerr, je vais utiliser l'outil request_media...",
    "system": "Tu es un assistant homelab spécialisé."
  }
]
```

### 2. Lancement du training via API

```bash
# Exemple de configuration YAML
curl -X POST http://pc-ia:8000/api/train \
  -H "Content-Type: application/json" \
  -d '{
    "model_name": "qwen2.5:7b",
    "dataset": "homelab_prompts",
    "training_method": "lora",
    "lora_rank": 16,
    "num_epochs": 3,
    "learning_rate": 2e-4
  }'
```

### 3. Monitoring

- **WebUI** : http://pc-ia:7860 pour visualiser les métriques
- **API** : GET /api/status pour récupérer l'état

### 4. Export vers Ollama

Après le training, le modèle peut être :

1. **Mergé** : Les poids LoRA sont fusionnés avec le modèle de base
2. **Converti en GGUF** : Format compatible Ollama
3. **Importé dans Ollama** : `ollama create homelab-model -f Modelfile`

## Intégration Backend ia-homelab

### Nouveau service : `llamafactory_service.py`

```python
from typing import Optional
import httpx

class LlamaFactoryService:
    """Service pour piloter LLaMA-Factory à distance."""

    def __init__(self, base_url: str = "http://pc-ia:8000"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)

    async def start_training(
        self,
        model_name: str,
        dataset_path: str,
        method: str = "lora",  # lora, qlora, full
        epochs: int = 3,
        learning_rate: float = 2e-4
    ) -> dict:
        """Lance une session de training."""
        response = await self.client.post(
            f"{self.base_url}/api/train",
            json={
                "model_name": model_name,
                "dataset": dataset_path,
                "training_method": method,
                "num_epochs": epochs,
                "learning_rate": learning_rate
            }
        )
        return response.json()

    async def get_status(self, job_id: str) -> dict:
        """Récupère le statut d'un job de training."""
        response = await self.client.get(
            f"{self.base_url}/api/status/{job_id}"
        )
        return response.json()

    async def export_model(self, job_id: str, format: str = "gguf") -> dict:
        """Exporte le modèle entraîné."""
        response = await self.client.post(
            f"{self.base_url}/api/export",
            json={"job_id": job_id, "format": format}
        )
        return response.json()
```

### Nouveau MCP Tool

```python
@mcp_tool("llamafactory_train")
async def train_model(
    model: str = "qwen2.5:7b",
    method: str = "lora",
    dataset: str = "homelab"
) -> str:
    """
    Lance un fine-tuning du modèle avec LLaMA-Factory.

    Args:
        model: Modèle de base à fine-tuner
        method: Méthode de training (lora, qlora, full)
        dataset: Jeu de données à utiliser

    Returns:
        ID du job de training et statut
    """
    service = LlamaFactoryService()
    result = await service.start_training(
        model_name=model,
        dataset_path=f"/app/data/{dataset}.json",
        method=method
    )
    return f"Training démarré. Job ID: {result['job_id']}"
```

## Comparaison des méthodes de training

| Méthode | VRAM requise | Temps | Qualité | Cas d'usage |
|---------|--------------|-------|---------|-------------|
| Full fine-tuning | 24GB+ | Long | Excellente | 1000+ exemples, spécialisation forte |
| LoRA | 8-12GB | Modéré | Très bonne | 100-500 exemples, recommandé |
| QLoRA | 6-8GB | Plus long | Bonne | GPU limité, homelab typique |
| Prompt Tuning | 4-6GB | Rapide | Limitée | Ajustements de style |

## Recommandation pour le Homelab

Avec les ~50 prompts créés dans ia-homelab :

1. **Commencer par QLoRA** si GPU < 12GB VRAM
2. **Utiliser LoRA** si GPU >= 12GB VRAM
3. **Modèle de base** : Qwen2.5:7B ou Llama3.1:8B
4. **Epochs** : 3-5 pour commencer
5. **Learning rate** : 2e-4 (standard LoRA)

## Prochaines étapes

1. [ ] Déployer LLaMA-Factory sur le PC IA
2. [ ] Créer le service `llamafactory_service.py` dans le backend
3. [ ] Ajouter l'endpoint `/api/training/llamafactory/*`
4. [ ] Créer le MCP tool `llamafactory_train`
5. [ ] Ajouter l'UI de configuration dans la page Training
6. [ ] Tester le workflow complet avec les prompts existants

## Ressources

- [LLaMA-Factory GitHub](https://github.com/hiyouga/LLaMA-Factory)
- [Documentation officielle](https://llamafactory.readthedocs.io/)
- [Guide DataCamp](https://www.datacamp.com/tutorial/llama-factory-web-ui-guide-fine-tuning-llms)
- [Paper ACL 2024](https://aclanthology.org/2024.acl-demo.26/)
