# 🔌 API Reference

Complete API documentation for MCParr AI Gateway.

## 📍 Base URL

```
http://localhost:8002
```

## 📖 Interactive Documentation

- **Swagger UI**: http://localhost:8002/docs
- **ReDoc**: http://localhost:8002/redoc

---

## 🏥 Health & Status

### Health Check

```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "database": "connected",
  "uptime": 3600
}
```

### System Metrics

```http
GET /api/system/metrics
```

**Response:**
```json
{
  "cpu_percent": 25.5,
  "memory_percent": 45.2,
  "disk_percent": 60.0,
  "services_healthy": 8,
  "services_total": 10
}
```

---

## 🔧 Services

### List Services

```http
GET /api/services
```

**Response:**
```json
[
  {
    "id": 1,
    "name": "Plex",
    "type": "plex",
    "url": "http://192.168.1.100:32400",
    "enabled": true,
    "is_healthy": true,
    "last_check": "2025-12-11T10:00:00Z"
  }
]
```

### Create Service

```http
POST /api/services
Content-Type: application/json

{
  "name": "Plex Media Server",
  "type": "plex",
  "url": "http://192.168.1.100:32400",
  "api_key": "your-plex-token",
  "enabled": true
}
```

### Update Service

```http
PUT /api/services/{service_id}
Content-Type: application/json

{
  "name": "Plex (Updated)",
  "enabled": true
}
```

### Delete Service

```http
DELETE /api/services/{service_id}
```

### Test Service Connection

```http
POST /api/services/{service_id}/test
```

**Response:**
```json
{
  "success": true,
  "message": "Connection successful",
  "response_time_ms": 125
}
```

---

## 👥 Users & Groups

### List User Mappings

```http
GET /api/users/mappings
```

### Create User Mapping

```http
POST /api/users/mappings
Content-Type: application/json

{
  "canonical_name": "john",
  "email": "john@example.com",
  "service_mappings": {
    "plex": "john_plex",
    "overseerr": "john@example.com"
  }
}
```

### List Groups

```http
GET /api/groups
```

### Create Group

```http
POST /api/groups
Content-Type: application/json

{
  "name": "Admins",
  "description": "Full access to all tools",
  "tool_permissions": ["*"]
}
```

### Update Group Permissions

```http
PUT /api/groups/{group_id}/permissions
Content-Type: application/json

{
  "tools": ["plex_search", "overseerr_request", "radarr_add_movie"]
}
```

---

## 🧠 Training

### List Training Sessions

```http
GET /api/training/sessions
```

### Create Training Session

```http
POST /api/training/sessions
Content-Type: application/json

{
  "name": "Custom Assistant v1",
  "description": "Homelab-specific training",
  "base_model": "unsloth/llama-3.2-1b-instruct-bnb-4bit",
  "config": {
    "num_epochs": 3,
    "learning_rate": 2e-4,
    "batch_size": 4
  }
}
```

### Start Training

```http
POST /api/training/sessions/{session_id}/start
Content-Type: application/json

{
  "worker_id": 1,
  "prompt_ids": [1, 2, 3, 4, 5]
}
```

### Get Training Status

```http
GET /api/training/sessions/{session_id}/status
```

**Response:**
```json
{
  "session_id": "abc123",
  "status": "training",
  "progress": 45.5,
  "current_epoch": 2,
  "total_epochs": 3,
  "loss": 0.125,
  "gpu_utilization": 85.0
}
```

### Cancel Training

```http
POST /api/training/sessions/{session_id}/cancel
```

### List Prompts

```http
GET /api/training/prompts
```

### Create Prompt

```http
POST /api/training/prompts
Content-Type: application/json

{
  "name": "Movie Request Example",
  "category": "media",
  "system_prompt": "You are a helpful homelab assistant.",
  "user_input": "I want to watch Inception",
  "expected_output": "I'll request Inception for you via Overseerr.",
  "tags": ["movies", "requests"]
}
```

---

## 🛠️ MCP

### List Available Tools

```http
GET /api/mcp/tools
```

**Response:**
```json
[
  {
    "name": "plex_search",
    "description": "Search for media in Plex library",
    "parameters": {
      "query": {"type": "string", "required": true},
      "type": {"type": "string", "enum": ["movie", "show", "music"]}
    }
  }
]
```

### MCP Request History

```http
GET /api/mcp/history
```

**Query Parameters:**
- `limit` (int): Number of results (default: 50)
- `offset` (int): Pagination offset
- `tool_name` (string): Filter by tool
- `status` (string): Filter by status (success, failed, pending)

---

## 💾 Backup & Restore

### Export Configuration

```http
POST /api/backup/export
Content-Type: application/json

{
  "services": true,
  "user_mappings": true,
  "groups": true,
  "training_prompts": true,
  "training_workers": true,
  "site_config": true
}
```

**Response:** JSON file with all configuration data.

### Import Configuration

```http
POST /api/backup/import
Content-Type: application/json

{
  "version": "1.0",
  "data": { ... },
  "options": {
    "merge_mode": false
  }
}
```

### Preview Export

```http
GET /api/backup/preview
```

**Response:**
```json
{
  "services": 10,
  "user_mappings": 5,
  "groups": 3,
  "training_prompts": 50,
  "training_workers": 1
}
```

---

## 🔄 WebSocket Endpoints

### System Metrics (Real-time)

```javascript
const ws = new WebSocket('ws://localhost:8002/ws/system');

ws.onmessage = (event) => {
  const metrics = JSON.parse(event.data);
  console.log(metrics);
  // { cpu_percent: 25, memory_percent: 45, ... }
};
```

### Training Progress (Real-time)

```javascript
const ws = new WebSocket('ws://localhost:8002/ws/training/SESSION_ID');

ws.onmessage = (event) => {
  const progress = JSON.parse(event.data);
  console.log(progress);
  // { status: "training", progress: 45.5, loss: 0.125, ... }
};
```

### Logs (Real-time)

```javascript
const ws = new WebSocket('ws://localhost:8002/ws/logs');

ws.onmessage = (event) => {
  const log = JSON.parse(event.data);
  console.log(log);
  // { timestamp: "...", level: "INFO", message: "...", ... }
};
```

---

## ⚠️ Error Responses

All errors follow this format:

```json
{
  "detail": "Error message description",
  "error_code": "SERVICE_NOT_FOUND",
  "timestamp": "2025-12-11T10:00:00Z"
}
```

### Common HTTP Status Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 201 | Created |
| 400 | Bad Request |
| 404 | Not Found |
| 422 | Validation Error |
| 500 | Internal Server Error |

---

## 📚 Next Steps

- [🛠️ MCP Integration](MCP.md)
- [👥 User Guide](USER_GUIDE.md)
