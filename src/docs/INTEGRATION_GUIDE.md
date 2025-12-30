# Guide d'Intégration de Nouveaux Services - MCParr AI Gateway

Ce guide technique détaille les étapes nécessaires pour intégrer un nouveau service dans la plateforme MCParr AI Gateway.

---

## Table des Matières

1. [Vue d'Ensemble de l'Architecture](#1-vue-densemble-de-larchitecture)
2. [Prérequis](#2-prérequis)
3. [Étape 1 : Ajouter le Type de Service](#3-étape-1--ajouter-le-type-de-service)
4. [Étape 2 : Créer l'Adaptateur de Service](#4-étape-2--créer-ladaptateur-de-service)
5. [Étape 3 : Enregistrer l'Adaptateur](#5-étape-3--enregistrer-ladaptateur)
6. [Étape 4 : Créer les Outils MCP](#6-étape-4--créer-les-outils-mcp)
7. [Étape 5 : Intégrer les Outils MCP](#7-étape-5--intégrer-les-outils-mcp)
8. [Étape 6 : Exposer pour Open WebUI](#8-étape-6--exposer-pour-open-webui)
9. [Étape 7 : Configuration](#9-étape-7--configuration)
10. [Étape 8 : Mapping Utilisateur](#10-étape-8--mapping-utilisateur)
11. [Étape 9 : Tests et Validation](#11-étape-9--tests-et-validation)
12. [Checklist Complète](#12-checklist-complète)
13. [Référence des Fichiers](#13-référence-des-fichiers)

---

## 1. Vue d'Ensemble de l'Architecture

### 1.1 Architecture Globale

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              Open WebUI                                  │
│                    (Interface utilisateur IA)                           │
└─────────────────────────────────┬───────────────────────────────────────┘
                                  │ JWT Token (Session Auth)
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                       MCParr AI Gateway                               │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────┐  │
│  │  OpenAPI Tools  │  │   MCP Server    │  │   REST API              │  │
│  │  Router         │  │   (port 8001)   │  │   (port 8002)           │  │
│  │  /tools/*       │  │                 │  │   /api/*                │  │
│  └────────┬────────┘  └────────┬────────┘  └───────────┬─────────────┘  │
│           │                    │                       │                │
│           ▼                    ▼                       ▼                │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                       Tool Registry                               │   │
│  │            (Gestion centralisée des outils)                      │   │
│  └──────────────────────────────┬───────────────────────────────────┘   │
│                                 │                                       │
│  ┌──────────────────────────────▼───────────────────────────────────┐   │
│  │                    Service Adapters                               │   │
│  │  ┌─────────┐ ┌──────────┐ ┌────────┐ ┌──────────┐ ┌───────────┐  │   │
│  │  │  Plex   │ │ Overseerr│ │ Zammad │ │ Tautulli │ │ Authentik │  │   │
│  │  └────┬────┘ └────┬─────┘ └───┬────┘ └────┬─────┘ └─────┬─────┘  │   │
│  │       │           │           │           │             │        │   │
│  │                        ┌───────────┐                             │   │
│  │                        │ Open WebUI│                             │   │
│  │                        └─────┬─────┘                             │   │
│  └──────────────────────────────│───────────────────────────────────┘   │
└─────────────────────────────────│───────────────────────────────────────┘
                                  ▼
     ┌──────────────────────────────────────────────────────────────┐
     │                   Services Externes                          │
     │  Plex  Overseerr  Zammad  Tautulli  Authentik  Open WebUI    │
     └──────────────────────────────────────────────────────────────┘
```

### 1.2 Flux de Données

```
Utilisateur Open WebUI
        │
        │ 1. Requête IA avec tool call
        ▼
    Open WebUI
        │
        │ 2. POST /tools/{tool_name}/call + JWT
        ▼
  OpenAPI Tools Router
        │
        │ 3. Résolution utilisateur (decode JWT + API Open WebUI)
        ▼
   Tool Registry
        │
        │ 4. Exécution de l'outil
        ▼
  Service Adapter
        │
        │ 5. Appel API service externe
        ▼
  Service Externe (Plex, etc.)
        │
        │ 6. Réponse
        ▼
   MCP Request Log (audit)
        │
        │ 7. Réponse formatée
        ▼
    Open WebUI → Utilisateur
```

### 1.3 Hiérarchie des Adaptateurs

```
BaseServiceAdapter (classe abstraite)
├── AuthenticatedAdapter (services avec authentification)
│   └── TokenAuthAdapter (authentification par token)
│       ├── PlexAdapter
│       ├── TautulliAdapter
│       ├── OverseerrAdapter
│       ├── ZammadAdapter
│       ├── AuthentikAdapter
│       └── OpenWebUIAdapter
└── (BasicAuthAdapter pour username/password - non implémenté)
```

### 1.4 Catégories d'Outils MCP

Les outils MCP sont organisés par catégorie pour faciliter leur gestion :

| Catégorie | Description | Exemples |
|-----------|-------------|----------|
| `system` | Monitoring, santé système, statuts | `system_get_health`, `newservice_get_status` |
| `media` | Contenu multimédia (films, séries, musique) | `plex_get_libraries`, `tautulli_get_activity` |
| `requests` | Demandes et requêtes utilisateurs | `overseerr_get_requests`, `overseerr_request_movie` |
| `support` | Tickets et support technique | `zammad_search_tickets`, `zammad_create_ticket` |
| `users` | Gestion des utilisateurs | `newservice_get_users`, `openwebui_get_users` |
| `chat` | Interface de conversation IA | `openwebui_get_models`, `openwebui_get_chats` |

---

## 2. Prérequis

### 2.1 Informations Nécessaires sur le Service

Avant de commencer, rassemblez ces informations :

- [ ] Documentation de l'API du service
- [ ] Méthode d'authentification (API key, Bearer token, etc.)
- [ ] Endpoints principaux à exposer
- [ ] Structure des données utilisateur (pour le mapping)
- [ ] Capacités du service (gestion utilisateurs, contenu, tickets, etc.)

### 2.2 Structure des Dossiers

```
ia-homelab/backend/src/
├── adapters/
│   ├── __init__.py
│   ├── base.py              # Classes de base
│   ├── plex.py              # Exemple: PlexAdapter
│   └── [newservice].py      # ◄── Votre nouvel adaptateur
├── mcp/
│   ├── server.py            # Serveur MCP
│   └── tools/
│       ├── __init__.py
│       ├── base.py          # Classes de base des outils
│       ├── plex_tools.py    # Exemple: PlexTools
│       └── [newservice]_tools.py  # ◄── Vos nouveaux outils
├── models/
│   ├── service_config.py    # ServiceType enum
│   └── user_mapping.py      # Modèles de mapping
├── routers/
│   ├── openapi_tools.py     # Exposition Open WebUI
│   └── services.py          # API REST services
├── services/
│   ├── service_registry.py  # Registre des adaptateurs
│   ├── user_mapper.py       # Détection de mapping
│   └── user_sync.py         # Synchronisation utilisateurs
└── config/
    └── settings.py          # Configuration
```

---

## 3. Étape 1 : Ajouter le Type de Service

### 3.1 Modifier l'Enum ServiceType

**Fichier:** `backend/src/models/service_config.py`

```python
class ServiceType(str, Enum):
    PLEX = "plex"
    OVERSEERR = "overseerr"
    ZAMMAD = "zammad"
    TAUTULLI = "tautulli"
    AUTHENTIK = "authentik"
    MONITORING = "monitoring"
    CUSTOM = "custom"
    # Ajouter votre nouveau service ici
    NEWSERVICE = "newservice"  # ◄── AJOUT
```

### 3.2 Conventions de Nommage

| Élément | Convention | Exemple |
|---------|------------|---------|
| ServiceType | UPPERCASE | `NEWSERVICE` |
| Valeur enum | lowercase | `"newservice"` |
| Classe Adapter | PascalCase + Adapter | `NewServiceAdapter` |
| Classe Tools | PascalCase + Tools | `NewServiceTools` |
| Fichier adapter | snake_case | `newservice.py` |
| Fichier tools | snake_case + _tools | `newservice_tools.py` |

---

## 4. Étape 2 : Créer l'Adaptateur de Service

### 4.1 Structure de Base

**Fichier:** `backend/src/adapters/newservice.py`

```python
"""
Adaptateur pour le service NewService.
Gère la communication avec l'API NewService.
"""

from typing import Any, Dict, List, Optional
from .base import TokenAuthAdapter, ServiceCapability, ConnectionTestResult


class NewServiceAdapter(TokenAuthAdapter):
    """
    Adaptateur pour l'intégration avec NewService.

    Capabilities:
        - API_ACCESS: Accès à l'API
        - USER_MANAGEMENT: Gestion des utilisateurs (si applicable)
        - [Autres capacités selon le service]

    Auth:
        Token API via header Authorization: Bearer {token}
        ou X-Api-Key: {token} selon le service
    """

    # ══════════════════════════════════════════════════════════════════
    # PROPRIÉTÉS REQUISES
    # ══════════════════════════════════════════════════════════════════

    @property
    def service_type(self) -> str:
        """Identifiant unique du type de service."""
        return "newservice"

    @property
    def supported_capabilities(self) -> List[ServiceCapability]:
        """Liste des capacités supportées par ce service."""
        return [
            ServiceCapability.API_ACCESS,
            # Ajouter selon les fonctionnalités:
            # ServiceCapability.USER_MANAGEMENT,
            # ServiceCapability.MEDIA_CONTENT,
            # ServiceCapability.TICKET_SYSTEM,
            # ServiceCapability.MONITORING,
            # ServiceCapability.AUTHENTICATION,
        ]

    @property
    def token_config_key(self) -> str:
        """Clé de configuration pour le token API."""
        return "api_key"  # ou "token", selon votre config

    # ══════════════════════════════════════════════════════════════════
    # AUTHENTIFICATION
    # ══════════════════════════════════════════════════════════════════

    def _format_token_header(self, token: str) -> Dict[str, str]:
        """
        Formate le header d'authentification.

        Options courantes:
        - Bearer token: {"Authorization": f"Bearer {token}"}
        - API Key header: {"X-Api-Key": token}
        - Custom header: {"X-NewService-Token": token}
        """
        return {"Authorization": f"Bearer {token}"}

    # ══════════════════════════════════════════════════════════════════
    # MÉTHODES REQUISES
    # ══════════════════════════════════════════════════════════════════

    async def test_connection(self) -> ConnectionTestResult:
        """
        Teste la connexion au service.

        Doit vérifier:
        1. Que le service est accessible
        2. Que l'authentification fonctionne
        3. Retourner des infos de version si possible
        """
        try:
            # Appeler un endpoint de status/health/version
            response = await self._make_request("GET", "/api/v1/status")

            if response.get("success") or response.get("version"):
                return ConnectionTestResult(
                    success=True,
                    message="Connexion réussie",
                    version=response.get("version", "unknown"),
                    details={
                        "server_name": response.get("name"),
                        "api_version": response.get("api_version"),
                    }
                )
            else:
                return ConnectionTestResult(
                    success=False,
                    message="Réponse inattendue du serveur",
                    details={"response": response}
                )

        except Exception as e:
            return ConnectionTestResult(
                success=False,
                message=f"Erreur de connexion: {str(e)}",
                error=str(e)
            )

    async def get_service_info(self) -> Dict[str, Any]:
        """
        Récupère les informations sur le service.

        Retourne un dict avec au minimum:
        - name: Nom du service
        - version: Version
        - status: État (online/offline)
        """
        try:
            response = await self._make_request("GET", "/api/v1/info")
            return {
                "name": response.get("name", "NewService"),
                "version": response.get("version", "unknown"),
                "status": "online",
                "details": response
            }
        except Exception as e:
            return {
                "name": "NewService",
                "version": "unknown",
                "status": "error",
                "error": str(e)
            }

    # ══════════════════════════════════════════════════════════════════
    # MÉTHODES MÉTIER (SPÉCIFIQUES AU SERVICE)
    # ══════════════════════════════════════════════════════════════════

    async def get_users(self) -> List[Dict[str, Any]]:
        """
        Récupère la liste des utilisateurs.

        Important pour le mapping utilisateur.
        Normaliser les champs retournés:
        - id: Identifiant unique
        - username: Nom d'utilisateur
        - email: Email (si disponible)
        - name/display_name: Nom affiché
        """
        response = await self._make_request("GET", "/api/v1/users")

        # Normaliser la structure si nécessaire
        users = response.get("users", response.get("data", []))

        return [
            {
                "id": str(user.get("id")),
                "username": user.get("username", user.get("login")),
                "email": user.get("email"),
                "name": user.get("display_name", user.get("name")),
                "role": user.get("role", "user"),
                # Garder les données brutes pour référence
                "_raw": user
            }
            for user in users
        ]

    async def get_items(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Exemple de méthode métier.
        Adapter selon les fonctionnalités du service.
        """
        response = await self._make_request(
            "GET",
            "/api/v1/items",
            params={"limit": limit}
        )
        return response.get("items", [])

    async def create_item(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Exemple de méthode de mutation.
        """
        return await self._make_request(
            "POST",
            "/api/v1/items",
            json=data
        )

    # ══════════════════════════════════════════════════════════════════
    # MÉTHODES UTILITAIRES (OPTIONNELLES)
    # ══════════════════════════════════════════════════════════════════

    async def search(self, query: str) -> List[Dict[str, Any]]:
        """Recherche dans le service."""
        return await self._make_request(
            "GET",
            "/api/v1/search",
            params={"q": query}
        )

    async def get_statistics(self) -> Dict[str, Any]:
        """Récupère les statistiques du service."""
        return await self._safe_request("GET", "/api/v1/stats") or {}
```

### 4.2 Capacités de Service (ServiceCapability)

Choisissez les capacités appropriées :

```python
class ServiceCapability(str, Enum):
    USER_MANAGEMENT = "user_management"   # Gestion des utilisateurs
    MEDIA_CONTENT = "media_content"       # Contenu multimédia
    TICKET_SYSTEM = "ticket_system"       # Système de tickets
    MONITORING = "monitoring"             # Surveillance/métriques
    AUTHENTICATION = "authentication"     # Authentification centralisée
    API_ACCESS = "api_access"            # Accès API générique
```

### 4.3 Méthodes Utilitaires Héritées

La classe `BaseServiceAdapter` fournit ces méthodes :

```python
# Requête HTTP avec gestion d'erreurs
await self._make_request(method, endpoint, params=None, json=None, timeout=30)

# Requête qui ne lève pas d'exception (retourne None en cas d'erreur)
await self._safe_request(method, endpoint, ...)

# Validation de configuration
def validate_config(self) -> List[str]:  # Retourne liste d'erreurs

# Accès aux valeurs de config
def get_config_value(self, key: str, default: Any = None) -> Any

# Vérification de capacité
def has_capability(self, capability: ServiceCapability) -> bool
```

---

## 5. Étape 3 : Enregistrer l'Adaptateur

### 5.1 Modifier le Service Registry

**Fichier:** `backend/src/services/service_registry.py`

```python
# Ajouter l'import
from ..adapters.newservice import NewServiceAdapter

class ServiceRegistry:
    def _register_default_adapters(self) -> None:
        """Enregistre les adaptateurs par défaut."""
        from ..adapters.plex import PlexAdapter
        from ..adapters.overseerr import OverseerrAdapter
        from ..adapters.zammad import ZammadAdapter
        from ..adapters.tautulli import TautulliAdapter
        from ..adapters.authentik import AuthentikAdapter
        from ..adapters.newservice import NewServiceAdapter  # ◄── AJOUT

        self.register_adapter("plex", PlexAdapter)
        self.register_adapter("overseerr", OverseerrAdapter)
        self.register_adapter("zammad", ZammadAdapter)
        self.register_adapter("tautulli", TautulliAdapter)
        self.register_adapter("authentik", AuthentikAdapter)
        self.register_adapter("newservice", NewServiceAdapter)  # ◄── AJOUT
```

### 5.2 Exporter l'Adaptateur

**Fichier:** `backend/src/adapters/__init__.py`

```python
from .base import (
    BaseServiceAdapter,
    TokenAuthAdapter,
    ServiceCapability,
    ConnectionTestResult,
)
from .plex import PlexAdapter
from .overseerr import OverseerrAdapter
from .zammad import ZammadAdapter
from .tautulli import TautulliAdapter
from .authentik import AuthentikAdapter
from .newservice import NewServiceAdapter  # ◄── AJOUT

__all__ = [
    "BaseServiceAdapter",
    "TokenAuthAdapter",
    "ServiceCapability",
    "ConnectionTestResult",
    "PlexAdapter",
    "OverseerrAdapter",
    "ZammadAdapter",
    "TautulliAdapter",
    "AuthentikAdapter",
    "NewServiceAdapter",  # ◄── AJOUT
]
```

### 5.3 Enregistrer dans le Service Tester

**Fichier:** `backend/src/services/service_tester.py`

⚠️ **Important**: Ce fichier possède son propre `ADAPTER_REGISTRY` séparé du `ServiceRegistry`. Il est utilisé pour les tests de connexion.

```python
from ..adapters.newservice import NewServiceAdapter  # ◄── AJOUT import

class ServiceTester:
    """Service for testing connections to homelab services."""

    # Registry of available adapters
    ADAPTER_REGISTRY = {
        "plex": PlexAdapter,
        "overseerr": OverseerrAdapter,
        "zammad": ZammadAdapter,
        "tautulli": TautulliAdapter,
        "authentik": AuthentikAdapter,
        "newservice": NewServiceAdapter  # ◄── AJOUT
    }
```

> **Note**: Si vous oubliez cette étape, le test de connexion retournera l'erreur "No adapter available for service type: newservice".

---

## 6. Étape 4 : Créer les Outils MCP

### 6.1 Structure des Outils

**Fichier:** `backend/src/mcp/tools/newservice_tools.py`

```python
"""
Outils MCP pour le service NewService.
Ces outils sont exposés à l'IA pour interagir avec NewService.
"""

from typing import Any, Dict, List, Optional
from .base import BaseTool, ToolDefinition, ToolParameter


class NewServiceTools(BaseTool):
    """
    Outils MCP pour NewService.

    Catégorie: Définir la catégorie principale des outils
    - "media" pour contenu multimédia
    - "requests" pour gestion de demandes
    - "support" pour tickets/support
    - "system" pour système/monitoring
    - "users" pour gestion utilisateurs
    """

    @property
    def definitions(self) -> List[ToolDefinition]:
        """Définitions de tous les outils disponibles."""
        return [
            # ══════════════════════════════════════════════════════════
            # OUTIL 1: Lecture (non-mutation)
            # ══════════════════════════════════════════════════════════
            ToolDefinition(
                name="newservice_get_status",
                description=(
                    "Récupère l'état actuel du service NewService. "
                    "Retourne des informations sur la version, l'état de santé, "
                    "et les statistiques de base."
                ),
                parameters=[],  # Aucun paramètre requis
                category="system",
                is_mutation=False,
                requires_service="newservice"
            ),

            # ══════════════════════════════════════════════════════════
            # OUTIL 2: Lecture avec paramètres
            # ══════════════════════════════════════════════════════════
            ToolDefinition(
                name="newservice_list_items",
                description=(
                    "Liste les éléments disponibles dans NewService. "
                    "Permet de filtrer par catégorie et de limiter le nombre de résultats."
                ),
                parameters=[
                    ToolParameter(
                        name="category",
                        description="Catégorie des éléments à lister (optionnel)",
                        type="string",
                        required=False,
                        enum=["all", "active", "archived"],  # Si enum applicable
                        default="all"
                    ),
                    ToolParameter(
                        name="limit",
                        description="Nombre maximum d'éléments à retourner",
                        type="number",
                        required=False,
                        default=20
                    ),
                ],
                category="system",
                is_mutation=False,
                requires_service="newservice"
            ),

            # ══════════════════════════════════════════════════════════
            # OUTIL 3: Recherche
            # ══════════════════════════════════════════════════════════
            ToolDefinition(
                name="newservice_search",
                description=(
                    "Recherche dans NewService. "
                    "Permet de trouver des éléments par mot-clé."
                ),
                parameters=[
                    ToolParameter(
                        name="query",
                        description="Terme de recherche",
                        type="string",
                        required=True
                    ),
                    ToolParameter(
                        name="type",
                        description="Type d'élément à rechercher",
                        type="string",
                        required=False,
                        enum=["all", "items", "users"],
                        default="all"
                    ),
                ],
                category="system",
                is_mutation=False,
                requires_service="newservice"
            ),

            # ══════════════════════════════════════════════════════════
            # OUTIL 4: Mutation (modification de données)
            # ══════════════════════════════════════════════════════════
            ToolDefinition(
                name="newservice_create_item",
                description=(
                    "Crée un nouvel élément dans NewService. "
                    "⚠️ Cette action modifie les données."
                ),
                parameters=[
                    ToolParameter(
                        name="name",
                        description="Nom de l'élément",
                        type="string",
                        required=True
                    ),
                    ToolParameter(
                        name="description",
                        description="Description de l'élément",
                        type="string",
                        required=False,
                        default=""
                    ),
                    ToolParameter(
                        name="priority",
                        description="Priorité de l'élément",
                        type="string",
                        required=False,
                        enum=["low", "medium", "high"],
                        default="medium"
                    ),
                ],
                category="system",
                is_mutation=True,  # ◄── Important pour les mutations
                requires_service="newservice"
            ),

            # ══════════════════════════════════════════════════════════
            # OUTIL 5: Liste des utilisateurs (pour mapping)
            # ══════════════════════════════════════════════════════════
            ToolDefinition(
                name="newservice_get_users",
                description=(
                    "Récupère la liste des utilisateurs NewService. "
                    "Utile pour le mapping d'utilisateurs."
                ),
                parameters=[],
                category="users",
                is_mutation=False,
                requires_service="newservice"
            ),
        ]

    async def execute(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Exécute un outil par son nom.

        Args:
            tool_name: Nom de l'outil à exécuter
            arguments: Arguments passés à l'outil

        Returns:
            Résultat de l'exécution sous forme de dict
        """
        # Vérifier que la config service existe
        if not self.service_config:
            return {
                "success": False,
                "error": "NewService non configuré"
            }

        # Router vers la méthode appropriée
        method_map = {
            "newservice_get_status": self._get_status,
            "newservice_list_items": self._list_items,
            "newservice_search": self._search,
            "newservice_create_item": self._create_item,
            "newservice_get_users": self._get_users,
        }

        if tool_name not in method_map:
            return {
                "success": False,
                "error": f"Outil inconnu: {tool_name}"
            }

        try:
            return await method_map[tool_name](arguments)
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "tool": tool_name
            }

    # ══════════════════════════════════════════════════════════════════
    # IMPLÉMENTATION DES OUTILS
    # ══════════════════════════════════════════════════════════════════

    async def _get_status(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Récupère l'état du service."""
        adapter = self._get_adapter()
        info = await adapter.get_service_info()

        return {
            "success": True,
            "status": info.get("status", "unknown"),
            "version": info.get("version"),
            "name": info.get("name"),
            "details": info.get("details", {})
        }

    async def _list_items(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Liste les éléments."""
        adapter = self._get_adapter()

        category = args.get("category", "all")
        limit = args.get("limit", 20)

        items = await adapter.get_items(limit=limit)

        # Filtrer par catégorie si nécessaire
        if category != "all":
            items = [i for i in items if i.get("category") == category]

        return {
            "success": True,
            "count": len(items),
            "items": items
        }

    async def _search(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Recherche dans le service."""
        adapter = self._get_adapter()

        query = args.get("query", "")
        if not query:
            return {"success": False, "error": "Query requis"}

        results = await adapter.search(query)

        return {
            "success": True,
            "query": query,
            "count": len(results),
            "results": results
        }

    async def _create_item(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Crée un nouvel élément."""
        adapter = self._get_adapter()

        name = args.get("name")
        if not name:
            return {"success": False, "error": "Nom requis"}

        data = {
            "name": name,
            "description": args.get("description", ""),
            "priority": args.get("priority", "medium")
        }

        result = await adapter.create_item(data)

        return {
            "success": True,
            "message": f"Élément '{name}' créé",
            "item": result
        }

    async def _get_users(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Récupère les utilisateurs."""
        adapter = self._get_adapter()
        users = await adapter.get_users()

        return {
            "success": True,
            "count": len(users),
            "users": users
        }

    # ══════════════════════════════════════════════════════════════════
    # MÉTHODES UTILITAIRES
    # ══════════════════════════════════════════════════════════════════

    def _get_adapter(self):
        """
        Crée une instance de l'adaptateur.
        Utilise la configuration du service fournie.
        """
        from ...adapters.newservice import NewServiceAdapter

        # ⚠️ CRITIQUE: ServiceConfigProxy pour compatibilité multi-sources
        # La config peut venir de différentes sources avec des clés différentes:
        # - Route /tools/test (mcp.py): utilise 'url' (sans port) + 'port' séparé + 'extra_config'
        # - Route /tools/{name} (openapi_tools.py): utilise 'base_url' et 'config'
        #
        # Le base adapter combine URL et port: url = f"{url}:{self.service_config.port}"
        # Si self.port est None, la connexion échouera ou retournera des données vides!
        class ServiceConfigProxy:
            def __init__(self, config: dict):
                self._config = config
                self.api_key = config.get("api_key")
                self.username = config.get("username")
                self.password = config.get("password")
                # Support both 'base_url' and 'url' keys for compatibility
                self.base_url = config.get("base_url") or config.get("url", "")
                # ⚠️ OBLIGATOIRE: Le port est passé séparément par /api/mcp/tools/test
                # Ne JAMAIS mettre None ici, toujours utiliser config.get("port")
                self.port = config.get("port")
                self.config = config.get("config") or config.get("extra_config", {})

            def get_config_value(self, key: str, default=None):
                return self.config.get(key, default)

        service_proxy = ServiceConfigProxy(self.service_config)
        return NewServiceAdapter(service_proxy)
```

> **⚠️ CRITIQUE: Pattern ServiceConfigProxy et Gestion du Port**
>
> Le `ServiceConfigProxy` est **obligatoire** pour que les outils fonctionnent correctement dans tous les contextes:
> - **Test manuel depuis le frontend** (`/api/mcp/tools/test`): utilise `url` (sans port) + `port` séparé + `extra_config`
> - **Appels Open WebUI** (`/tools/{tool_name}`): utilise `base_url` et `config`
>
> **Erreur fréquente**: Si `self.port = None` au lieu de `self.port = config.get("port")`:
> - Les outils retourneront des **listes vides** ou des **erreurs de connexion**
> - L'API du service sera appelée sans le port correct (ex: `http://192.168.1.24` au lieu de `http://192.168.1.24:5055`)
> - Le test de connexion peut réussir mais les outils renvoient des données vides
>
> **Vérification**: Assurez-vous que chaque fichier `*_tools.py` contient bien:
> ```python
> self.port = config.get("port")  # ✅ Correct
> # et NON:
> self.port = None  # ❌ ERREUR - causera des échecs silencieux
> ```

### 6.2 Types de Paramètres

| Type | Description | Exemple |
|------|-------------|---------|
| `string` | Chaîne de caractères | `"hello"` |
| `number` | Nombre (int ou float) | `42`, `3.14` |
| `boolean` | Booléen | `true`, `false` |
| `array` | Liste | `["a", "b"]` |
| `object` | Objet JSON | `{"key": "value"}` |

### 6.3 Bonnes Pratiques pour les Outils

1. **Nommage clair**: `service_action_object` (ex: `plex_get_libraries`)
2. **Descriptions détaillées**: L'IA utilise ces descriptions pour comprendre l'outil
3. **Paramètres explicites**: Inclure enum pour les choix limités
4. **Gestion des erreurs**: Toujours retourner `{"success": false, "error": "..."}` en cas d'erreur
5. **is_mutation**: Marquer `True` pour les outils qui modifient des données

---

## 7. Étape 5 : Intégrer les Outils MCP

### 7.1 Modifier le Serveur MCP

**Fichier:** `backend/src/mcp/server.py`

```python
# Ajouter l'import
from .tools.newservice_tools import NewServiceTools

class MCPServer:
    async def initialize(self, service_configs: Optional[List[dict]] = None) -> None:
        """Initialise le serveur avec les services configurés."""
        # ... code existant ...

        # Grouper les configs par type
        configs_by_type = {}
        for config in service_configs or []:
            if config.get("enabled"):
                service_type = config.get("service_type")
                configs_by_type[service_type] = config

        # Enregistrer les outils existants...
        if "plex" in configs_by_type:
            self.registry.register(PlexTools, configs_by_type.get("plex"))
        # ... autres services ...

        # ◄── AJOUT: Enregistrer NewService
        if "newservice" in configs_by_type:
            self.registry.register(NewServiceTools, configs_by_type.get("newservice"))
```

### 7.2 Exporter les Outils

**Fichier:** `backend/src/mcp/tools/__init__.py`

```python
from .base import BaseTool, ToolDefinition, ToolParameter, ToolRegistry
from .system_tools import SystemTools
from .plex_tools import PlexTools
from .overseerr_tools import OverseerrTools
from .zammad_tools import ZammadTools
from .tautulli_tools import TautulliTools
from .newservice_tools import NewServiceTools  # ◄── AJOUT

__all__ = [
    "BaseTool",
    "ToolDefinition",
    "ToolParameter",
    "ToolRegistry",
    "SystemTools",
    "PlexTools",
    "OverseerrTools",
    "ZammadTools",
    "TautulliTools",
    "NewServiceTools",  # ◄── AJOUT
]
```

---

## 8. Étape 6 : Exposer pour Open WebUI et l'API des Groupes

### 8.1 Modifier le Router OpenAPI Tools

**Fichier:** `backend/src/routers/openapi_tools.py`

Ce fichier expose les outils pour Open WebUI et est **aussi utilisé par l'API `/api/groups/available-tools`** pour lister les outils dans l'interface de gestion des groupes.

```python
# 1. Ajouter l'import en haut du fichier
from src.mcp.tools.newservice_tools import NewServiceTools

# 2. Dans la fonction get_tool_registry(), ajouter l'enregistrement:
async def get_tool_registry(session: AsyncSession) -> ToolRegistry:
    """Get tool registry with enabled services."""
    # ... code existant pour récupérer configs_by_type ...

    registry = ToolRegistry()
    registry.register(SystemTools)

    if "plex" in configs_by_type:
        registry.register(PlexTools, configs_by_type["plex"])
    # ... autres services existants ...

    # ◄── AJOUT: NewService
    if "newservice" in configs_by_type:
        registry.register(NewServiceTools, configs_by_type["newservice"])

    return registry
```

> **⚠️ Important**: Si vous oubliez cette étape, les outils du nouveau service n'apparaîtront pas dans :
> - L'onglet "Groupes" de la page Users (gestion des permissions)
> - L'interface Open WebUI pour l'exécution des outils

### 8.2 Modifier le Router MCP

**Fichier:** `backend/src/routers/mcp.py`

⚠️ **CRITIQUE**: Ce fichier contient **3 occurrences distinctes** de `service_tools_map` qui doivent **toutes** être mises à jour. Si vous oubliez cette étape, les outils n'apparaîtront pas dans la page MCP du frontend.

```python
# 1. Ajouter l'import en haut du fichier
from src.mcp.tools.newservice_tools import NewServiceTools

# 2. Mettre à jour les 3 occurrences de service_tools_map dans le fichier:
# (Rechercher "service_tools_map" pour les trouver)

service_tools_map = {
    "plex": PlexTools,
    "tautulli": TautulliTools,
    "overseerr": OverseerrTools,
    "zammad": ZammadTools,
    "authentik": AuthentikTools,
    "openwebui": OpenWebUITools,
    "komga": KomgaTools,
    "romm": RommTools,
    "audiobookshelf": AudiobookshelfTools,
    "newservice": NewServiceTools,  # ◄── AJOUT dans les 3 occurrences
}
```

> **Pourquoi 3 occurrences ?** Le fichier `mcp.py` contient plusieurs fonctions (`get_available_tools()`, etc.) qui ont chacune leur propre copie du mapping. C'est une dette technique à corriger, mais en attendant, les 3 doivent être synchronisées.

> **⚠️ Important**: Si vous oubliez cette étape, les outils du nouveau service n'apparaîtront pas dans :
> - La page MCP du frontend (`/api/mcp/tools`)
> - Les statistiques MCP

---

## 9. Étape 7 : Configuration

### 9.1 Ajouter les Variables d'Environnement

**Fichier:** `backend/src/config/settings.py`

```python
class Settings(BaseSettings):
    # ... existant ...

    # NewService Configuration
    newservice_url: str = Field(default="", alias="NEWSERVICE_URL")
    newservice_api_key: str = Field(default="", alias="NEWSERVICE_API_KEY")
    # ou pour auth basique:
    # newservice_username: str = Field(default="", alias="NEWSERVICE_USERNAME")
    # newservice_password: str = Field(default="", alias="NEWSERVICE_PASSWORD")
```

### 9.2 Fichier .env

```env
# NewService
NEWSERVICE_URL=http://localhost:8080
NEWSERVICE_API_KEY=your-api-key-here
```

### 9.3 Configuration via API

Le service peut aussi être configuré via l'API REST:

```bash
curl -X POST http://localhost:8002/api/services/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Mon NewService",
    "service_type": "newservice",
    "base_url": "http://localhost:8080",
    "api_key": "your-api-key",
    "enabled": true
  }'
```

### 9.4 Configuration Frontend

Pour que le service apparaisse dans l'interface d'administration, deux fichiers frontend doivent être mis à jour :

#### 9.4.1 Ajouter le Type de Service (TypeScript)

**Fichier:** `frontend/src/types/api.ts`

```typescript
export enum ServiceType {
  PLEX = 'plex',
  TAUTULLI = 'tautulli',
  OVERSEERR = 'overseerr',
  ZAMMAD = 'zammad',
  AUTHENTIK = 'authentik',
  OPENWEBUI = 'openwebui',
  MONITORING = 'monitoring',
  NEWSERVICE = 'newservice',  // ◄── AJOUT
}
```

#### 9.4.2 Configurer le Formulaire de Service

**Fichier:** `frontend/src/components/ServiceForm.tsx`

Ajouter la configuration du nouveau service dans le tableau `SERVICE_CONFIGS` :

```typescript
const SERVICE_CONFIGS: ServiceTypeConfig[] = [
  // ... services existants ...
  {
    value: 'newservice',
    label: 'NewService',
    description: 'Description du service pour l\'utilisateur',
    fields: ['api_key'],  // Champs requis: 'api_key', 'username', 'password'
    defaultPort: '8080',  // Port par défaut du service
    authType: 'bearer',   // Type d'auth: 'bearer', 'api_key', 'basic'
    urlPlaceholder: 'http://newservice.local'
  },
];
```

**Options de configuration :**

| Propriété | Description | Valeurs possibles |
|-----------|-------------|-------------------|
| `value` | Identifiant technique (doit correspondre au ServiceType backend) | `'newservice'` |
| `label` | Nom affiché dans l'interface | `'New Service'` |
| `description` | Description courte du service | Texte libre |
| `fields` | Champs de formulaire requis | `['api_key']`, `['username', 'password']`, `['api_key', 'username']` |
| `defaultPort` | Port par défaut suggéré | `'8080'`, `'443'`, etc. |
| `authType` | Type d'authentification | `'bearer'`, `'api_key'`, `'basic'` |
| `urlPlaceholder` | Exemple d'URL pour l'utilisateur | `'http://service.local'` |

> **Note**: Si vous oubliez cette étape, le service n'apparaîtra pas dans la liste déroulante lors de la création d'un nouveau service.

#### 9.4.3 Ajouter le Service dans AI Training

**Fichier:** `frontend/src/pages/Training.tsx`

Le module AI Training utilise sa propre liste de services disponibles pour les prompts d'entraînement :

```typescript
// 1. Ajouter dans AVAILABLE_SERVICES (liste statique des services pour les prompts)
const AVAILABLE_SERVICES = [
  { id: 'plex', label: 'Plex', icon: '🎬', color: 'bg-amber-500' },
  { id: 'tautulli', label: 'Tautulli', icon: '📊', color: 'bg-orange-500' },
  // ... autres services existants ...
  { id: 'newservice', label: 'NewService', icon: '🔧', color: 'bg-blue-500' },  // ◄── AJOUT
];

// 2. Ajouter dans SERVICE_ICONS (pour l'affichage des badges)
const SERVICE_ICONS: Record<string, string> = {
  plex: '🎬', tautulli: '📊', overseerr: '🎯', radarr: '🎥', sonarr: '📺',
  prowlarr: '🔍', jackett: '🧥', zammad: '🎫', komga: '📚', romm: '🎮',
  ollama: '🤖', openwebui: '💬', authentik: '🔐', deluge: '🌊', system: '⚙️',
  newservice: '🔧',  // ◄── AJOUT
};

// 3. Ajouter dans SERVICE_COLORS (pour les couleurs des badges)
const SERVICE_COLORS: Record<string, string> = {
  plex: 'bg-amber-500', tautulli: 'bg-orange-500', overseerr: 'bg-violet-500',
  // ... autres ...
  newservice: 'bg-blue-500',  // ◄── AJOUT
};
```

> **Note**: Ces configurations sont indépendantes de l'API. Elles permettent au module Training de proposer le service dans le formulaire de création de prompts.

#### 9.4.4 Ajouter les Couleurs du Service

**Fichier:** `frontend/src/lib/serviceColors.ts`

Ce fichier définit les couleurs et icônes pour l'affichage uniforme des services dans toute l'application :

```typescript
// Ajouter la configuration du nouveau service
const SERVICE_CONFIGS: Record<string, ServiceColorConfig> = {
  // ... services existants ...
  newservice: {
    bg: 'bg-blue-50 dark:bg-blue-900/20',
    border: 'border-blue-200 dark:border-blue-800',
    text: 'text-blue-700 dark:text-blue-300',
    badge: 'bg-blue-100 text-blue-700',
    badgeDark: 'dark:bg-blue-900 dark:text-blue-300',
    icon: Wrench,  // Import depuis lucide-react
  },
};
```

---

## 10. Étape 8 : Mapping Utilisateur

### 10.1 Support du Mapping Automatique

Pour que le service supporte la détection automatique de mapping, l'adaptateur doit:

1. **Implémenter `get_users()`** avec les champs normalisés:

```python
async def get_users(self) -> List[Dict[str, Any]]:
    """
    Retourne les utilisateurs avec ces champs:
    - id: Identifiant unique (string)
    - username: Nom d'utilisateur
    - email: Email (optionnel)
    - name: Nom affiché (optionnel)
    - friendly_name: Nom amical (optionnel)
    """
    response = await self._make_request("GET", "/api/users")

    return [
        {
            "id": str(user["id"]),
            "username": user.get("login") or user.get("username"),
            "email": user.get("email"),
            "name": user.get("display_name") or user.get("name"),
            "friendly_name": user.get("friendly_name"),
        }
        for user in response.get("users", [])
    ]
```

2. **Avoir la capacité USER_MANAGEMENT**:

```python
@property
def supported_capabilities(self) -> List[ServiceCapability]:
    return [
        ServiceCapability.USER_MANAGEMENT,  # ◄── Requis
        ServiceCapability.API_ACCESS,
    ]
```

### 10.2 Algorithme de Détection

Le `UserMappingDetector` compare les utilisateurs selon:

| Critère | Poids | Description |
|---------|-------|-------------|
| ID exact | 0.8 | Match sur l'ID (attention: IDs différents selon services) |
| Email exact | 0.5 | Match sur l'email |
| Username exact | 0.5 | Match sur le username |
| Email fuzzy | 0.3 | Match partiel sur l'email |
| Username fuzzy | 0.3 | Match partiel sur le username |
| Nom amical | 0.4 | Match sur friendly_name/display_name |

**Seuils de confiance:**
- **High** (>0.9): Mapping automatique recommandé
- **Medium** (>0.7): Vérification manuelle suggérée
- **Low** (<0.7): Mapping manuel requis

### 10.3 API de Mapping

```bash
# Lister les utilisateurs de tous les services
GET /api/users/enumerate-users

# Détecter les mappings automatiquement
POST /api/users/detect-mappings

# Créer un mapping manuel
POST /api/users/
{
  "central_user_id": "user-123",
  "central_username": "john.doe",
  "central_email": "john@example.com",
  "service_config_id": 1,
  "service_user_id": "456",
  "service_username": "johnd",
  "role": "user",
  "enabled": true
}

# Synchroniser les mappings
POST /api/users/sync-all
```

---

## 11. Étape 9 : Tests et Validation

### 11.1 Test de l'Adaptateur

```python
# tests/adapters/test_newservice.py
import pytest
from src.adapters.newservice import NewServiceAdapter

@pytest.fixture
def adapter():
    config = {
        "base_url": "http://localhost:8080",
        "api_key": "test-key"
    }
    return NewServiceAdapter(config)

@pytest.mark.asyncio
async def test_connection(adapter):
    result = await adapter.test_connection()
    assert result.success is True

@pytest.mark.asyncio
async def test_get_users(adapter):
    users = await adapter.get_users()
    assert isinstance(users, list)
```

### 11.2 Test des Outils MCP

```python
# tests/mcp/tools/test_newservice_tools.py
import pytest
from src.mcp.tools.newservice_tools import NewServiceTools

@pytest.fixture
def tools():
    config = {
        "base_url": "http://localhost:8080",
        "api_key": "test-key"
    }
    return NewServiceTools(config)

def test_tool_definitions(tools):
    defs = tools.definitions
    assert len(defs) > 0
    assert all(d.requires_service == "newservice" for d in defs)

@pytest.mark.asyncio
async def test_get_status(tools):
    result = await tools.execute("newservice_get_status", {})
    assert "success" in result
```

### 11.3 Test via API

```bash
# 1. Créer le service
curl -X POST http://localhost:8002/api/services/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test NewService",
    "service_type": "newservice",
    "base_url": "http://localhost:8080",
    "api_key": "your-key",
    "enabled": true
  }'

# 2. Tester la connexion
curl -X POST http://localhost:8002/api/services/1/test

# 3. Vérifier les outils MCP
curl http://localhost:8002/api/mcp/status

# 4. Lister les outils (format Open WebUI)
curl http://localhost:8002/tools

# 5. Exécuter un outil
curl -X POST http://localhost:8002/tools/newservice_get_status/call \
  -H "Content-Type: application/json" \
  -d '{}'
```

---

## 12. Checklist Complète

### Phase 1: Modèle et Adaptateur Backend

- [ ] Ajouter `NEWSERVICE` à `ServiceType` enum (`models/service_config.py`)
- [ ] Créer `backend/src/adapters/newservice.py`
- [ ] Implémenter `service_type` property
- [ ] Implémenter `supported_capabilities` property
- [ ] Implémenter `token_config_key` property
- [ ] Implémenter `_format_token_header()`
- [ ] Implémenter `test_connection()`
- [ ] Implémenter `get_service_info()`
- [ ] Implémenter `get_users()` (si USER_MANAGEMENT)
- [ ] Implémenter méthodes métier spécifiques
- [ ] Exporter dans `adapters/__init__.py`
- [ ] Enregistrer dans `ServiceRegistry` (`services/service_registry.py`)
- [ ] **⚠️ Enregistrer dans `ServiceTester.ADAPTER_REGISTRY`** (`services/service_tester.py`)

### Phase 2: Outils MCP

- [ ] Créer `backend/src/mcp/tools/newservice_tools.py`
- [ ] Définir les `ToolDefinition` avec descriptions claires
- [ ] Choisir la bonne catégorie (`system`, `media`, `requests`, `support`, `users`, `chat`)
- [ ] Implémenter `execute()` avec routage
- [ ] Implémenter chaque méthode d'outil
- [ ] Gérer les erreurs proprement
- [ ] Exporter dans `mcp/tools/__init__.py`
- [ ] Enregistrer dans `MCPServer.initialize()` (`mcp/server.py`)
- [ ] **⚠️ Ajouter import dans `openapi_tools.py`** (en haut du fichier)
- [ ] **⚠️ Enregistrer dans `get_tool_registry()`** dans `openapi_tools.py` - Requis pour l'onglet Groupes et Open WebUI
- [ ] **⚠️ CRITIQUE: Ajouter import dans `mcp.py`** (en haut du fichier)
- [ ] **⚠️ CRITIQUE: Enregistrer dans les 3 `service_tools_map`** de `mcp.py` - Requis pour la page MCP

### Phase 3: Configuration Backend

- [ ] Ajouter variables dans `settings.py`
- [ ] Documenter les variables .env
- [ ] Tester la configuration via API

### Phase 4: Configuration Frontend - Services

- [ ] **⚠️ Ajouter ServiceType dans l'enum TypeScript** (`frontend/src/types/api.ts`)
- [ ] **⚠️ Configurer le formulaire de service** (`frontend/src/components/ServiceForm.tsx`)
- [ ] Vérifier que le service apparaît dans la liste déroulante

### Phase 5: Configuration Frontend - UI

- [ ] **⚠️ Ajouter dans `AVAILABLE_SERVICES`** (`frontend/src/pages/Training.tsx`) - Pour le module AI Training
- [ ] **⚠️ Ajouter dans `SERVICE_ICONS`** (`frontend/src/pages/Training.tsx`)
- [ ] **⚠️ Ajouter dans `SERVICE_COLORS`** (`frontend/src/pages/Training.tsx`)
- [ ] **⚠️ Ajouter la configuration de couleurs** (`frontend/src/lib/serviceColors.ts`) - Pour l'affichage uniforme

### Phase 6: Mapping Utilisateur

- [ ] Implémenter `get_users()` avec champs normalisés (id, username, email, name)
- [ ] Vérifier la capacité `USER_MANAGEMENT`
- [ ] Tester la détection automatique
- [ ] Tester le mapping manuel
- [ ] Vérifier l'affichage des noms mappés dans Request History

### Phase 7: Tests et Validation

- [ ] Écrire tests unitaires adaptateur
- [ ] Écrire tests unitaires outils
- [ ] Tester via API REST
- [ ] Tester via Open WebUI
- [ ] **Vérifier l'apparition dans l'onglet Groupes** de la page Users
- [ ] **Vérifier l'apparition dans le formulaire de prompt** du module AI Training
- [ ] Documenter l'intégration

---

## 13. Référence des Fichiers

### Backend

| Fichier | Description |
|---------|-------------|
| `models/service_config.py` | Enum ServiceType, modèle ServiceConfig |
| `models/user_mapping.py` | Modèles UserMapping, UserSync |
| `adapters/base.py` | Classes de base des adaptateurs |
| `adapters/{service}.py` | Adaptateurs par service |
| `services/service_registry.py` | Factory des adaptateurs |
| `services/user_mapper.py` | Détection de mapping |
| `services/user_sync.py` | Synchronisation utilisateurs |
| `mcp/server.py` | Serveur MCP |
| `mcp/tools/base.py` | Classes de base des outils |
| `mcp/tools/{service}_tools.py` | Outils par service |
| `routers/services.py` | API REST services |
| `routers/users.py` | API REST mapping |
| `routers/mcp.py` | API REST MCP + service_tools_map (3x) |
| `routers/openapi_tools.py` | Exposition Open WebUI + Groupes API |
| `config/settings.py` | Configuration |

### Frontend

| Fichier | Description |
|---------|-------------|
| `pages/Services.tsx` | Gestion des services |
| `pages/Users.tsx` | Gestion du mapping et des groupes |
| `pages/MCP.tsx` | Interface MCP |
| `pages/Training.tsx` | Module AI Training (prompts, sessions) |
| `components/ServiceForm.tsx` | Formulaire de service |
| `components/Groups/GroupDetail.tsx` | Gestion des permissions par groupe |
| `lib/serviceColors.ts` | Couleurs et icônes des services |
| `types/api.ts` | Types TypeScript (ServiceType enum)

---

## Annexe A: Exemple Complet - Service Fictif "TaskManager"

Voir le dossier `docs/examples/taskmanager/` pour un exemple complet d'intégration d'un service fictif de gestion de tâches.

---

## Annexe B: Dépannage

### Erreurs Courantes

| Erreur | Cause | Solution |
|--------|-------|----------|
| "Service type not found" | ServiceType non ajouté | Ajouter à l'enum |
| "Adapter not registered" | Non enregistré dans registry | Ajouter dans `_register_default_adapters` |
| "Tool not found" | Outils non enregistrés | Vérifier `MCPServer.initialize()` |
| "Connection failed" | Config incorrecte | Vérifier base_url et credentials |
| "No users found" | `get_users()` non implémenté | Implémenter ou vérifier l'endpoint |
| **Outils renvoient des listes/résultats vides** | `self.port = None` dans ServiceConfigProxy | **Changer en `self.port = config.get("port")`** |
| Test connexion OK mais outils échouent | Port manquant dans la config tools | Vérifier `ServiceConfigProxy.port` dans `*_tools.py` |
| "No adapter available for service type" | Non enregistré dans ServiceTester | Ajouter dans `ADAPTER_REGISTRY` de `service_tester.py` |

### Problème Fréquent: Port Manquant

**Symptôme**: Le test de connexion du service fonctionne, mais les outils MCP retournent des listes vides ou des erreurs.

**Cause**: Dans le fichier `*_tools.py`, la classe `ServiceConfigProxy` a `self.port = None` au lieu de `self.port = config.get("port")`.

**Explication**:
- La route `/api/mcp/tools/test` envoie le port séparément de l'URL
- L'adaptateur de base combine URL et port: `url = f"{url}:{self.service_config.port}"`
- Si port est `None`, l'URL finale sera incorrecte (ex: `http://192.168.1.24` au lieu de `http://192.168.1.24:5055`)

**Solution**:
```python
# Dans chaque fichier src/mcp/tools/*_tools.py, vérifier:
class ServiceConfigProxy:
    def __init__(self, config: dict):
        # ...
        self.port = config.get("port")  # ✅ OBLIGATOIRE
        # ...
```

**Vérification rapide**:
```bash
grep -n "self.port" backend/src/mcp/tools/*_tools.py
# Tous les fichiers doivent avoir: self.port = config.get("port")
```

### Logs Utiles

```bash
# Logs backend
tail -f logs/backend.log

# Logs MCP
tail -f logs/mcp.log

# Debug mode
LOG_LEVEL=DEBUG uvicorn src.main:app --reload
```

---

*Documentation générée pour MCParr AI Gateway v1.0*
