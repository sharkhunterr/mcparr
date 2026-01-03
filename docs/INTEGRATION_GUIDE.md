# Service Integration Guide - MCParr AI Gateway

This technical guide details the steps required to integrate a new service into the MCParr AI Gateway platform.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Prerequisites](#2-prerequisites)
3. [Step 1: Add the Service Type](#3-step-1-add-the-service-type)
4. [Step 2: Create the Service Adapter](#4-step-2-create-the-service-adapter)
5. [Step 3: Register the Adapter](#5-step-3-register-the-adapter)
6. [Step 4: Create MCP Tools](#6-step-4-create-mcp-tools)
7. [Step 5: Integrate MCP Tools](#7-step-5-integrate-mcp-tools)
8. [Step 6: Expose for Open WebUI](#8-step-6-expose-for-open-webui)
9. [Step 7: Backend Configuration](#9-step-7-backend-configuration)
10. [Step 8: Frontend Configuration](#10-step-8-frontend-configuration)
11. [Step 9: Internationalization (i18n)](#11-step-9-internationalization-i18n)
12. [Step 10: User Mapping](#12-step-10-user-mapping)
13. [Step 11: Testing and Validation](#13-step-11-testing-and-validation)
14. [Complete Checklist](#14-complete-checklist)
15. [File Reference](#15-file-reference)
16. [Troubleshooting](#16-troubleshooting)

---

## 1. Architecture Overview

### 1.1 Global Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              Open WebUI                                  │
│                        (AI User Interface)                              │
└─────────────────────────────────┬───────────────────────────────────────┘
                                  │ JWT Token (Session Auth)
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                       MCParr AI Gateway                                  │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────┐  │
│  │  OpenAPI Tools  │  │   MCP Server    │  │   REST API              │  │
│  │  Router         │  │   (port 8001)   │  │   (port 8000)           │  │
│  │  /tools/*       │  │                 │  │   /api/*                │  │
│  └────────┬────────┘  └────────┬────────┘  └───────────┬─────────────┘  │
│           │                    │                       │                │
│           ▼                    ▼                       ▼                │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                       Tool Registry                               │   │
│  │                (Centralized tool management)                     │   │
│  └──────────────────────────────┬───────────────────────────────────┘   │
│                                 │                                       │
│  ┌──────────────────────────────▼───────────────────────────────────┐   │
│  │                    Service Adapters                               │   │
│  │  ┌─────────┐ ┌──────────┐ ┌────────┐ ┌──────────┐ ┌───────────┐  │   │
│  │  │  Plex   │ │ Overseerr│ │ Zammad │ │ Tautulli │ │ Authentik │  │   │
│  │  └────┬────┘ └────┬─────┘ └───┬────┘ └────┬─────┘ └─────┬─────┘  │   │
│  └───────│───────────│───────────│───────────│─────────────│────────┘   │
└──────────│───────────│───────────│───────────│─────────────│────────────┘
           ▼           ▼           ▼           ▼             ▼
     ┌──────────────────────────────────────────────────────────────┐
     │                   External Services                          │
     │  Plex  Overseerr  Zammad  Tautulli  Authentik  Open WebUI    │
     └──────────────────────────────────────────────────────────────┘
```

### 1.2 Data Flow

```
Open WebUI User
        │
        │ 1. AI request with tool call
        ▼
    Open WebUI
        │
        │ 2. POST /tools/{tool_name}/call + JWT
        ▼
  OpenAPI Tools Router
        │
        │ 3. User resolution (decode JWT + Open WebUI API)
        ▼
   Tool Registry
        │
        │ 4. Tool execution
        ▼
  Service Adapter
        │
        │ 5. External service API call
        ▼
  External Service (Plex, etc.)
        │
        │ 6. Response
        ▼
   MCP Request Log (audit)
        │
        │ 7. Formatted response
        ▼
    Open WebUI → User
```

### 1.3 Adapter Hierarchy

```
BaseServiceAdapter (abstract class)
├── AuthenticatedAdapter (services with authentication)
│   └── TokenAuthAdapter (token authentication)
│       ├── PlexAdapter
│       ├── TautulliAdapter
│       ├── OverseerrAdapter
│       ├── ZammadAdapter
│       ├── AuthentikAdapter
│       └── OpenWebUIAdapter
└── (BasicAuthAdapter for username/password - not implemented)
```

### 1.4 MCP Tool Categories

MCP tools are organized by category for easier management:

| Category | Description | Examples |
|----------|-------------|----------|
| `system` | Monitoring, system health, statuses | `system_get_health`, `newservice_get_status` |
| `media` | Multimedia content (movies, series, music) | `plex_get_libraries`, `tautulli_get_activity` |
| `requests` | User requests and demands | `overseerr_get_requests`, `overseerr_request_movie` |
| `support` | Tickets and technical support | `zammad_search_tickets`, `zammad_create_ticket` |
| `users` | User management | `newservice_get_users`, `openwebui_get_users` |
| `chat` | AI conversation interface | `openwebui_get_models`, `openwebui_get_chats` |

---

## 2. Prerequisites

### 2.1 Required Service Information

Before starting, gather this information:

- [ ] Service API documentation
- [ ] Authentication method (API key, Bearer token, etc.)
- [ ] Main endpoints to expose
- [ ] User data structure (for mapping)
- [ ] Service capabilities (user management, content, tickets, etc.)

### 2.2 Directory Structure

```
src/backend/src/
├── adapters/
│   ├── __init__.py
│   ├── base.py              # Base classes
│   ├── plex.py              # Example: PlexAdapter
│   └── [newservice].py      # ◄── Your new adapter
├── mcp/
│   ├── server.py            # MCP Server
│   └── tools/
│       ├── __init__.py
│       ├── base.py          # Tool base classes
│       ├── plex_tools.py    # Example: PlexTools
│       └── [newservice]_tools.py  # ◄── Your new tools
├── models/
│   ├── service_config.py    # ServiceType enum
│   └── user_mapping.py      # Mapping models
├── routers/
│   ├── openapi_tools.py     # Open WebUI exposure
│   └── services.py          # Services REST API
├── services/
│   ├── service_registry.py  # Adapter registry
│   ├── user_mapper.py       # Mapping detection
│   └── user_sync.py         # User synchronization
└── config/
    └── settings.py          # Configuration

src/frontend/src/
├── i18n/
│   └── locales/
│       ├── en/              # English translations
│       ├── fr/              # French translations
│       ├── de/              # German translations
│       ├── es/              # Spanish translations
│       └── it/              # Italian translations
├── components/
│   └── ServiceForm.tsx      # Service form configuration
├── pages/
│   └── Training.tsx         # AI Training module
├── lib/
│   └── serviceColors.ts     # Service colors/icons
└── types/
    └── api.ts               # TypeScript types
```

---

## 3. Step 1: Add the Service Type

### 3.1 Modify the ServiceType Enum

**File:** `src/backend/src/models/service_config.py`

```python
class ServiceType(str, Enum):
    PLEX = "plex"
    OVERSEERR = "overseerr"
    ZAMMAD = "zammad"
    TAUTULLI = "tautulli"
    AUTHENTIK = "authentik"
    MONITORING = "monitoring"
    CUSTOM = "custom"
    # Add your new service here
    NEWSERVICE = "newservice"  # ◄── ADD
```

### 3.2 Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| ServiceType | UPPERCASE | `NEWSERVICE` |
| Enum value | lowercase | `"newservice"` |
| Adapter class | PascalCase + Adapter | `NewServiceAdapter` |
| Tools class | PascalCase + Tools | `NewServiceTools` |
| Adapter file | snake_case | `newservice.py` |
| Tools file | snake_case + _tools | `newservice_tools.py` |

---

## 4. Step 2: Create the Service Adapter

### 4.1 Base Structure

**File:** `src/backend/src/adapters/newservice.py`

```python
"""
Adapter for the NewService service.
Handles communication with the NewService API.
"""

from typing import Any, Dict, List, Optional
from .base import TokenAuthAdapter, ServiceCapability, ConnectionTestResult


class NewServiceAdapter(TokenAuthAdapter):
    """
    Adapter for NewService integration.

    Capabilities:
        - API_ACCESS: API access
        - USER_MANAGEMENT: User management (if applicable)
        - [Other capabilities based on service]

    Auth:
        API token via Authorization: Bearer {token}
        or X-Api-Key: {token} depending on service
    """

    # ══════════════════════════════════════════════════════════════════
    # REQUIRED PROPERTIES
    # ══════════════════════════════════════════════════════════════════

    @property
    def service_type(self) -> str:
        """Unique identifier for the service type."""
        return "newservice"

    @property
    def supported_capabilities(self) -> List[ServiceCapability]:
        """List of capabilities supported by this service."""
        return [
            ServiceCapability.API_ACCESS,
            # Add based on features:
            # ServiceCapability.USER_MANAGEMENT,
            # ServiceCapability.MEDIA_CONTENT,
            # ServiceCapability.TICKET_SYSTEM,
            # ServiceCapability.MONITORING,
            # ServiceCapability.AUTHENTICATION,
        ]

    @property
    def token_config_key(self) -> str:
        """Configuration key for the API token."""
        return "api_key"  # or "token", depending on your config

    # ══════════════════════════════════════════════════════════════════
    # AUTHENTICATION
    # ══════════════════════════════════════════════════════════════════

    def _format_token_header(self, token: str) -> Dict[str, str]:
        """
        Formats the authentication header.

        Common options:
        - Bearer token: {"Authorization": f"Bearer {token}"}
        - API Key header: {"X-Api-Key": token}
        - Custom header: {"X-NewService-Token": token}
        """
        return {"Authorization": f"Bearer {token}"}

    # ══════════════════════════════════════════════════════════════════
    # REQUIRED METHODS
    # ══════════════════════════════════════════════════════════════════

    async def test_connection(self) -> ConnectionTestResult:
        """
        Tests connection to the service.

        Should verify:
        1. Service is accessible
        2. Authentication works
        3. Return version info if possible
        """
        try:
            response = await self._make_request("GET", "/api/v1/status")

            if response.get("success") or response.get("version"):
                return ConnectionTestResult(
                    success=True,
                    message="Connection successful",
                    version=response.get("version", "unknown"),
                    details={
                        "server_name": response.get("name"),
                        "api_version": response.get("api_version"),
                    }
                )
            else:
                return ConnectionTestResult(
                    success=False,
                    message="Unexpected server response",
                    details={"response": response}
                )

        except Exception as e:
            return ConnectionTestResult(
                success=False,
                message=f"Connection error: {str(e)}",
                error=str(e)
            )

    async def get_service_info(self) -> Dict[str, Any]:
        """
        Retrieves service information.

        Returns a dict with at minimum:
        - name: Service name
        - version: Version
        - status: State (online/offline)
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
    # BUSINESS METHODS (SERVICE-SPECIFIC)
    # ══════════════════════════════════════════════════════════════════

    async def get_users(self) -> List[Dict[str, Any]]:
        """
        Retrieves the user list.

        Important for user mapping.
        Normalize returned fields:
        - id: Unique identifier
        - username: Username
        - email: Email (if available)
        - name/display_name: Display name
        """
        response = await self._make_request("GET", "/api/v1/users")
        users = response.get("users", response.get("data", []))

        return [
            {
                "id": str(user.get("id")),
                "username": user.get("username", user.get("login")),
                "email": user.get("email"),
                "name": user.get("display_name", user.get("name")),
                "role": user.get("role", "user"),
                "_raw": user
            }
            for user in users
        ]

    async def get_items(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Example business method."""
        response = await self._make_request(
            "GET",
            "/api/v1/items",
            params={"limit": limit}
        )
        return response.get("items", [])
```

### 4.2 Service Capabilities (ServiceCapability)

Choose appropriate capabilities:

```python
class ServiceCapability(str, Enum):
    USER_MANAGEMENT = "user_management"   # User management
    MEDIA_CONTENT = "media_content"       # Multimedia content
    TICKET_SYSTEM = "ticket_system"       # Ticket system
    MONITORING = "monitoring"             # Monitoring/metrics
    AUTHENTICATION = "authentication"     # Centralized authentication
    API_ACCESS = "api_access"            # Generic API access
```

---

## 5. Step 3: Register the Adapter

### 5.1 Modify the Service Registry

**File:** `src/backend/src/services/service_registry.py`

```python
from ..adapters.newservice import NewServiceAdapter  # ◄── ADD import

class ServiceRegistry:
    def _register_default_adapters(self) -> None:
        """Registers default adapters."""
        # ... existing imports ...
        from ..adapters.newservice import NewServiceAdapter  # ◄── ADD

        self.register_adapter("plex", PlexAdapter)
        # ... existing registrations ...
        self.register_adapter("newservice", NewServiceAdapter)  # ◄── ADD
```

### 5.2 Export the Adapter

**File:** `src/backend/src/adapters/__init__.py`

```python
from .newservice import NewServiceAdapter  # ◄── ADD

__all__ = [
    # ... existing exports ...
    "NewServiceAdapter",  # ◄── ADD
]
```

### 5.3 Register in Service Tester

**File:** `src/backend/src/services/service_tester.py`

> **Important**: This file has its own `ADAPTER_REGISTRY` separate from `ServiceRegistry`. It's used for connection tests.

```python
from ..adapters.newservice import NewServiceAdapter  # ◄── ADD import

class ServiceTester:
    ADAPTER_REGISTRY = {
        # ... existing adapters ...
        "newservice": NewServiceAdapter  # ◄── ADD
    }
```

---

## 6. Step 4: Create MCP Tools

### 6.1 Tools Structure

**File:** `src/backend/src/mcp/tools/newservice_tools.py`

```python
"""
MCP tools for NewService.
These tools are exposed to AI to interact with NewService.
"""

from typing import Any, Dict, List, Optional
from .base import BaseTool, ToolDefinition, ToolParameter


class NewServiceTools(BaseTool):
    """
    MCP tools for NewService.

    Category: Define the main category of tools
    - "media" for multimedia content
    - "requests" for request management
    - "support" for tickets/support
    - "system" for system/monitoring
    - "users" for user management
    """

    @property
    def definitions(self) -> List[ToolDefinition]:
        """Definitions of all available tools."""
        return [
            ToolDefinition(
                name="newservice_get_status",
                description=(
                    "Retrieves the current status of NewService. "
                    "Returns version, health, and basic statistics."
                ),
                parameters=[],
                category="system",
                is_mutation=False,
                requires_service="newservice"
            ),
            ToolDefinition(
                name="newservice_list_items",
                description=(
                    "Lists items available in NewService. "
                    "Can filter by category and limit results."
                ),
                parameters=[
                    ToolParameter(
                        name="category",
                        description="Category of items to list (optional)",
                        type="string",
                        required=False,
                        enum=["all", "active", "archived"],
                        default="all"
                    ),
                    ToolParameter(
                        name="limit",
                        description="Maximum number of items to return",
                        type="number",
                        required=False,
                        default=20
                    ),
                ],
                category="system",
                is_mutation=False,
                requires_service="newservice"
            ),
            # Add more tool definitions...
        ]

    async def execute(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool by name."""
        if not self.service_config:
            return {"success": False, "error": "NewService not configured"}

        method_map = {
            "newservice_get_status": self._get_status,
            "newservice_list_items": self._list_items,
        }

        if tool_name not in method_map:
            return {"success": False, "error": f"Unknown tool: {tool_name}"}

        try:
            return await method_map[tool_name](arguments)
        except Exception as e:
            return {"success": False, "error": str(e), "tool": tool_name}

    async def _get_status(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Retrieves service status."""
        adapter = self._get_adapter()
        info = await adapter.get_service_info()
        return {
            "success": True,
            "status": info.get("status", "unknown"),
            "version": info.get("version"),
            "name": info.get("name"),
        }

    async def _list_items(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Lists items."""
        adapter = self._get_adapter()
        items = await adapter.get_items(limit=args.get("limit", 20))
        return {"success": True, "count": len(items), "items": items}

    def _get_adapter(self):
        """Creates an adapter instance."""
        from ...adapters.newservice import NewServiceAdapter

        # CRITICAL: ServiceConfigProxy for multi-source compatibility
        class ServiceConfigProxy:
            def __init__(self, config: dict):
                self._config = config
                self.api_key = config.get("api_key")
                self.base_url = config.get("base_url") or config.get("url", "")
                self.port = config.get("port")  # ◄── REQUIRED
                self.config = config.get("config") or config.get("extra_config", {})

            def get_config_value(self, key: str, default=None):
                return self.config.get(key, default)

        return NewServiceAdapter(ServiceConfigProxy(self.service_config))
```

> **CRITICAL: Port Management**
>
> The `self.port = config.get("port")` line is **required**. If set to `None`, tools will return empty results or connection errors because the base adapter combines URL and port.

---

## 7. Step 5: Integrate MCP Tools

### 7.1 Modify the MCP Server

**File:** `src/backend/src/mcp/server.py`

```python
from .tools.newservice_tools import NewServiceTools  # ◄── ADD

class MCPServer:
    async def initialize(self, service_configs: Optional[List[dict]] = None) -> None:
        # ... existing code ...

        # ◄── ADD: Register NewService
        if "newservice" in configs_by_type:
            self.registry.register(NewServiceTools, configs_by_type.get("newservice"))
```

### 7.2 Export the Tools

**File:** `src/backend/src/mcp/tools/__init__.py`

```python
from .newservice_tools import NewServiceTools  # ◄── ADD

__all__ = [
    # ... existing exports ...
    "NewServiceTools",  # ◄── ADD
]
```

---

## 8. Step 6: Expose for Open WebUI

### 8.1 Modify the OpenAPI Tools Router

**File:** `src/backend/src/routers/openapi_tools.py`

```python
from src.mcp.tools.newservice_tools import NewServiceTools  # ◄── ADD

async def get_tool_registry(session: AsyncSession) -> ToolRegistry:
    # ... existing code ...

    # ◄── ADD: NewService
    if "newservice" in configs_by_type:
        registry.register(NewServiceTools, configs_by_type["newservice"])

    return registry
```

### 8.2 Modify the MCP Router

**File:** `src/backend/src/routers/mcp.py`

> **CRITICAL**: This file contains **3 separate occurrences** of `service_tools_map` that must **all** be updated.

```python
from src.mcp.tools.newservice_tools import NewServiceTools  # ◄── ADD

# Update ALL 3 occurrences of service_tools_map:
service_tools_map = {
    "plex": PlexTools,
    # ... existing services ...
    "newservice": NewServiceTools,  # ◄── ADD in all 3 places
}
```

---

## 9. Step 7: Backend Configuration

### 9.1 Add Environment Variables

**File:** `src/backend/src/config/settings.py`

```python
class Settings(BaseSettings):
    # NewService Configuration
    newservice_url: str = Field(default="", alias="NEWSERVICE_URL")
    newservice_api_key: str = Field(default="", alias="NEWSERVICE_API_KEY")
```

### 9.2 .env File

```env
# NewService
NEWSERVICE_URL=http://localhost:8080
NEWSERVICE_API_KEY=your-api-key-here
```

---

## 10. Step 8: Frontend Configuration

### 10.1 Add TypeScript Service Type

**File:** `src/frontend/src/types/api.ts`

```typescript
export enum ServiceType {
  // ... existing services ...
  NEWSERVICE = 'newservice',  // ◄── ADD
}
```

### 10.2 Configure Service Form

**File:** `src/frontend/src/components/ServiceForm.tsx`

```typescript
const SERVICE_CONFIGS: ServiceTypeConfig[] = [
  // ... existing services ...
  {
    value: 'newservice',
    label: 'NewService',
    description: 'Service description for user',
    fields: ['api_key'],
    defaultPort: '8080',
    authType: 'bearer',
    urlPlaceholder: 'http://newservice.local'
  },
];
```

### 10.3 Add Service to AI Training

**File:** `src/frontend/src/pages/Training.tsx`

```typescript
const AVAILABLE_SERVICES = [
  // ... existing services ...
  { id: 'newservice', label: 'NewService', icon: '🔧', color: 'bg-blue-500' },
];

const SERVICE_ICONS: Record<string, string> = {
  // ... existing icons ...
  newservice: '🔧',
};

const SERVICE_COLORS: Record<string, string> = {
  // ... existing colors ...
  newservice: 'bg-blue-500',
};
```

### 10.4 Add Service Colors

**File:** `src/frontend/src/lib/serviceColors.ts`

```typescript
const SERVICE_CONFIGS: Record<string, ServiceColorConfig> = {
  // ... existing services ...
  newservice: {
    bg: 'bg-blue-50 dark:bg-blue-900/20',
    border: 'border-blue-200 dark:border-blue-800',
    text: 'text-blue-700 dark:text-blue-300',
    badge: 'bg-blue-100 text-blue-700',
    badgeDark: 'dark:bg-blue-900 dark:text-blue-300',
    icon: Wrench,  // Import from lucide-react
  },
};
```

---

## 11. Step 9: Internationalization (i18n)

MCParr supports multiple languages. When adding a new service, you should add translations to all locale files.

### 11.1 Supported Languages

| Language | Code | Locale Path |
|----------|------|-------------|
| English | `en` | `src/frontend/src/i18n/locales/en/` |
| French | `fr` | `src/frontend/src/i18n/locales/fr/` |
| German | `de` | `src/frontend/src/i18n/locales/de/` |
| Spanish | `es` | `src/frontend/src/i18n/locales/es/` |
| Italian | `it` | `src/frontend/src/i18n/locales/it/` |

### 11.2 Files to Update

For each language, update the relevant JSON files:

#### services.json - Service Labels

```json
{
  "types": {
    "newservice": "NewService"
  },
  "descriptions": {
    "newservice": "Description of your service"
  }
}
```

#### mcp.json - MCP Tool Categories (if adding new category)

```json
{
  "categories": {
    "newservice": "NewService Tools"
  }
}
```

#### training.json - AI Training Module

If your service appears in training prompts:

```json
{
  "services": {
    "newservice": "NewService"
  }
}
```

### 11.3 Translation Process

1. **Start with English** (`en/`) as the reference
2. **Copy to other locales** and translate
3. **Use consistent terminology** across files
4. **Preserve interpolation variables** like `{{count}}`, `{{name}}`

### 11.4 Example: Adding Translations

**English** (`en/services.json`):
```json
{
  "types": {
    "newservice": "NewService"
  },
  "descriptions": {
    "newservice": "Connect to your NewService instance"
  }
}
```

**French** (`fr/services.json`):
```json
{
  "types": {
    "newservice": "NewService"
  },
  "descriptions": {
    "newservice": "Connectez-vous à votre instance NewService"
  }
}
```

**German** (`de/services.json`):
```json
{
  "types": {
    "newservice": "NewService"
  },
  "descriptions": {
    "newservice": "Verbinden Sie sich mit Ihrer NewService-Instanz"
  }
}
```

### 11.5 Using Translations in Components

```typescript
import { useTranslation } from 'react-i18next';

function MyComponent() {
  const { t } = useTranslation('services');

  return (
    <div>
      <h1>{t('types.newservice')}</h1>
      <p>{t('descriptions.newservice')}</p>
    </div>
  );
}
```

### 11.6 i18n Checklist for New Services

- [ ] Add translations to `en/services.json` (required)
- [ ] Add translations to `fr/services.json`
- [ ] Add translations to `de/services.json`
- [ ] Add translations to `es/services.json`
- [ ] Add translations to `it/services.json`
- [ ] Update `mcp.json` if adding new tool categories
- [ ] Update `training.json` if service appears in training prompts
- [ ] Test with different language settings

---

## 12. Step 10: User Mapping

### 12.1 Automatic Mapping Support

For automatic mapping detection, the adapter must:

1. **Implement `get_users()`** with normalized fields:

```python
async def get_users(self) -> List[Dict[str, Any]]:
    """
    Returns users with these fields:
    - id: Unique identifier (string)
    - username: Username
    - email: Email (optional)
    - name: Display name (optional)
    - friendly_name: Friendly name (optional)
    """
```

2. **Have USER_MANAGEMENT capability**:

```python
@property
def supported_capabilities(self) -> List[ServiceCapability]:
    return [
        ServiceCapability.USER_MANAGEMENT,  # ◄── Required
        ServiceCapability.API_ACCESS,
    ]
```

### 12.2 Detection Algorithm

The `UserMappingDetector` compares users by:

| Criterion | Weight | Description |
|-----------|--------|-------------|
| Exact ID | 0.8 | ID match (note: IDs differ between services) |
| Exact email | 0.5 | Email match |
| Exact username | 0.5 | Username match |
| Fuzzy email | 0.3 | Partial email match |
| Fuzzy username | 0.3 | Partial username match |
| Friendly name | 0.4 | Match on friendly_name/display_name |

**Confidence thresholds:**
- **High** (>0.9): Automatic mapping recommended
- **Medium** (>0.7): Manual verification suggested
- **Low** (<0.7): Manual mapping required

---

## 13. Step 11: Testing and Validation

### 13.1 Adapter Tests

```python
# tests/adapters/test_newservice.py
import pytest
from src.adapters.newservice import NewServiceAdapter

@pytest.fixture
def adapter():
    config = {"base_url": "http://localhost:8080", "api_key": "test-key"}
    return NewServiceAdapter(config)

@pytest.mark.asyncio
async def test_connection(adapter):
    result = await adapter.test_connection()
    assert result.success is True
```

### 13.2 API Testing

```bash
# 1. Create the service
curl -X POST http://localhost:8000/api/services/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test NewService",
    "service_type": "newservice",
    "base_url": "http://localhost:8080",
    "api_key": "your-key",
    "enabled": true
  }'

# 2. Test connection
curl -X POST http://localhost:8000/api/services/1/test

# 3. Check MCP tools
curl http://localhost:8000/api/mcp/status

# 4. List tools (Open WebUI format)
curl http://localhost:8000/tools

# 5. Execute a tool
curl -X POST http://localhost:8000/tools/newservice_get_status/call \
  -H "Content-Type: application/json" \
  -d '{}'
```

---

## 14. Complete Checklist

### Phase 1: Backend Model and Adapter

- [ ] Add `NEWSERVICE` to `ServiceType` enum
- [ ] Create `src/backend/src/adapters/newservice.py`
- [ ] Implement `service_type` property
- [ ] Implement `supported_capabilities` property
- [ ] Implement `token_config_key` property
- [ ] Implement `_format_token_header()`
- [ ] Implement `test_connection()`
- [ ] Implement `get_service_info()`
- [ ] Implement `get_users()` (if USER_MANAGEMENT)
- [ ] Export in `adapters/__init__.py`
- [ ] Register in `ServiceRegistry`
- [ ] Register in `ServiceTester.ADAPTER_REGISTRY`

### Phase 2: MCP Tools

- [ ] Create `src/backend/src/mcp/tools/newservice_tools.py`
- [ ] Define `ToolDefinition` with clear descriptions
- [ ] Choose correct category
- [ ] Implement `execute()` with routing
- [ ] Implement each tool method
- [ ] Handle errors properly
- [ ] Export in `mcp/tools/__init__.py`
- [ ] Register in `MCPServer.initialize()`
- [ ] Add import in `openapi_tools.py`
- [ ] Register in `get_tool_registry()` in `openapi_tools.py`
- [ ] Add import in `mcp.py`
- [ ] Register in all 3 `service_tools_map` in `mcp.py`

### Phase 3: Backend Configuration

- [ ] Add variables in `settings.py`
- [ ] Document .env variables

### Phase 4: Frontend - Services

- [ ] Add ServiceType in TypeScript enum
- [ ] Configure service form in `ServiceForm.tsx`

### Phase 5: Frontend - UI

- [ ] Add in `AVAILABLE_SERVICES` (Training.tsx)
- [ ] Add in `SERVICE_ICONS` (Training.tsx)
- [ ] Add in `SERVICE_COLORS` (Training.tsx)
- [ ] Add color configuration (serviceColors.ts)

### Phase 6: Internationalization

- [ ] Add translations to `en/` (required)
- [ ] Add translations to `fr/`
- [ ] Add translations to `de/`
- [ ] Add translations to `es/`
- [ ] Add translations to `it/`

### Phase 7: User Mapping

- [ ] Implement `get_users()` with normalized fields
- [ ] Verify `USER_MANAGEMENT` capability
- [ ] Test automatic detection
- [ ] Test manual mapping

### Phase 8: Testing

- [ ] Write adapter unit tests
- [ ] Write tools unit tests
- [ ] Test via REST API
- [ ] Test via Open WebUI
- [ ] Verify appearance in Groups tab
- [ ] Verify appearance in Training module
- [ ] Test with different languages

---

## 15. File Reference

### Backend

| File | Description |
|------|-------------|
| `models/service_config.py` | ServiceType enum, ServiceConfig model |
| `adapters/base.py` | Adapter base classes |
| `adapters/{service}.py` | Per-service adapters |
| `services/service_registry.py` | Adapter factory |
| `services/service_tester.py` | Connection tester with ADAPTER_REGISTRY |
| `mcp/server.py` | MCP Server |
| `mcp/tools/base.py` | Tool base classes |
| `mcp/tools/{service}_tools.py` | Per-service tools |
| `routers/mcp.py` | MCP REST API + service_tools_map (3x) |
| `routers/openapi_tools.py` | Open WebUI exposure + Groups API |

### Frontend

| File | Description |
|------|-------------|
| `types/api.ts` | TypeScript types (ServiceType enum) |
| `components/ServiceForm.tsx` | Service form |
| `pages/Training.tsx` | AI Training module |
| `lib/serviceColors.ts` | Service colors and icons |
| `i18n/locales/{lang}/*.json` | Translation files |

---

## 16. Troubleshooting

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| "Service type not found" | ServiceType not added | Add to enum |
| "Adapter not registered" | Not registered in registry | Add in `_register_default_adapters` |
| "Tool not found" | Tools not registered | Check `MCPServer.initialize()` |
| "Connection failed" | Incorrect config | Verify base_url and credentials |
| **Tools return empty results** | `self.port = None` in ServiceConfigProxy | **Change to `self.port = config.get("port")`** |
| "No adapter available for service type" | Not registered in ServiceTester | Add in `ADAPTER_REGISTRY` |

### Common Issue: Missing Port

**Symptom**: Connection test succeeds but MCP tools return empty lists or errors.

**Cause**: In `*_tools.py`, the `ServiceConfigProxy` class has `self.port = None` instead of `self.port = config.get("port")`.

**Solution**:
```python
# In each src/mcp/tools/*_tools.py file, verify:
class ServiceConfigProxy:
    def __init__(self, config: dict):
        # ...
        self.port = config.get("port")  # ✅ REQUIRED
        # ...
```

**Quick check**:
```bash
grep -n "self.port" src/backend/src/mcp/tools/*_tools.py
# All files should have: self.port = config.get("port")
```

---

*Documentation for MCParr AI Gateway*
