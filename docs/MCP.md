# 🛠️ MCP Integration Guide

Guide for integrating MCParr with AI assistants via Model Context Protocol (MCP).

## 🤔 What is MCP?

MCP (Model Context Protocol) is a standard for connecting AI assistants to external tools and data sources. MCParr implements an MCP server that exposes your homelab services as callable tools.

## 🏗️ Architecture

```
┌─────────────────┐     MCP Protocol     ┌─────────────────┐
│  AI Assistant   │◄───────────────────►│   MCParr MCP    │
│  (Claude, etc)  │                      │     Server      │
└─────────────────┘                      └────────┬────────┘
                                                  │
                                         ┌────────▼────────┐
                                         │  MCParr Backend │
                                         │    (FastAPI)    │
                                         └────────┬────────┘
                                                  │
                    ┌─────────────────────────────┼─────────────────────────────┐
                    │              │              │              │              │
              ┌─────▼─────┐ ┌─────▼─────┐ ┌─────▼─────┐ ┌─────▼─────┐ ┌─────▼─────┐
              │   Plex    │ │ Overseerr │ │  Radarr   │ │  Sonarr   │ │    ...    │
              └───────────┘ └───────────┘ └───────────┘ └───────────┘ └───────────┘
```

## 🚀 Quick Setup

### 1. Start MCParr

Ensure MCParr backend is running:
```bash
python -m uvicorn src.main:app --host 0.0.0.0 --port 8002
```

The MCP server runs on port **8001** by default.

### 2. Configure Your AI Assistant

#### Claude Desktop

Edit `~/.config/claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "mcparr": {
      "command": "curl",
      "args": ["-N", "http://YOUR_MCPARR_HOST:8001/sse"]
    }
  }
}
```

Restart Claude Desktop to apply changes.

#### Other MCP-Compatible Assistants

Use the SSE endpoint:
```
http://YOUR_MCPARR_HOST:8001/sse
```

Or the WebSocket endpoint:
```
ws://YOUR_MCPARR_HOST:8001/ws
```

## 🔧 Available Tools

### Media Tools

#### 🎬 plex_search
Search for media in your Plex library.

```json
{
  "name": "plex_search",
  "parameters": {
    "query": "Inception",
    "type": "movie"  // optional: movie, show, music
  }
}
```

#### 📥 overseerr_request_movie
Request a movie via Overseerr.

```json
{
  "name": "overseerr_request_movie",
  "parameters": {
    "tmdb_id": 27205,
    "quality_profile": "1080p"  // optional
  }
}
```

#### 📺 overseerr_request_tv
Request a TV show via Overseerr.

```json
{
  "name": "overseerr_request_tv",
  "parameters": {
    "tmdb_id": 1396,
    "seasons": [1, 2]  // optional, empty = all
  }
}
```

### Management Tools

#### 🎥 radarr_add_movie
Add a movie to Radarr.

```json
{
  "name": "radarr_add_movie",
  "parameters": {
    "tmdb_id": 27205,
    "quality_profile": "HD-1080p",
    "root_folder": "/movies"
  }
}
```

#### 📺 sonarr_add_series
Add a TV series to Sonarr.

```json
{
  "name": "sonarr_add_series",
  "parameters": {
    "tvdb_id": 81189,
    "quality_profile": "HD-1080p",
    "root_folder": "/tv"
  }
}
```

### System Tools

#### 📊 get_system_status
Get overall system health.

```json
{
  "name": "get_system_status",
  "parameters": {}
}
```

#### 🔍 get_service_status
Check a specific service status.

```json
{
  "name": "get_service_status",
  "parameters": {
    "service_name": "plex"
  }
}
```

## 🔐 Permissions

### Tool Access Control

MCParr uses group-based permissions to control tool access:

1. **Create groups** in the web interface
2. **Assign tools** to each group
3. **Map users** to groups

Example group configuration:

| Group | Allowed Tools |
|-------|---------------|
| Admins | `*` (all tools) |
| Media Users | `plex_search`, `overseerr_request_*` |
| Viewers | `plex_search` only |

### Configure in Web UI

1. Go to **Configuration** → **Groups**
2. Create/edit groups
3. Select allowed tools
4. Assign users to groups

## 📝 Example Conversations

### Request a Movie

**User:** "I want to watch Inception"

**AI (via MCParr):**
1. Calls `plex_search` to check if already available
2. If not found, calls `overseerr_request_movie`
3. Returns: "I've requested Inception for you. It should be available soon."

### Check System Status

**User:** "How are my services doing?"

**AI (via MCParr):**
1. Calls `get_system_status`
2. Returns: "All 10 services are healthy. Plex has 5 active streams."

### Search Library

**User:** "What sci-fi movies do I have?"

**AI (via MCParr):**
1. Calls `plex_search` with genre filter
2. Returns: "Found 45 sci-fi movies including Interstellar, The Matrix..."

## 🔄 Real-time Updates

MCParr can push real-time updates to the AI assistant:

- **Training progress**: When fine-tuning models
- **Service alerts**: When services go down
- **Request updates**: When media becomes available

## 🛠️ Custom Tools

### Adding New Tools

1. Create adapter in `backend/src/adapters/`
2. Create tool definitions in `backend/src/mcp/tools/`
3. Register in `backend/src/mcp/server.py`

Example tool definition:

```python
@tool("my_custom_tool")
async def my_custom_tool(param1: str, param2: int = 10):
    """
    Description of what this tool does.

    Args:
        param1: First parameter description
        param2: Second parameter with default

    Returns:
        Result of the operation
    """
    # Implementation
    return {"result": "success"}
```

## 🐛 Troubleshooting

### Connection Issues

```bash
# Test MCP server
curl http://localhost:8001/health

# Check SSE endpoint
curl -N http://localhost:8001/sse
```

### Tool Not Found

1. Check service is configured in MCParr
2. Verify service is enabled
3. Check user has permission for the tool

### Permission Denied

1. Check user is mapped to a group
2. Verify group has tool permission
3. Check group is enabled

## 📚 Next Steps

- [👥 User Guide](USER_GUIDE.md)
- [🔌 API Reference](API.md)
