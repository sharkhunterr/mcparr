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
python -m uvicorn src.main:app --host 0.0.0.0 --port 8000
```

MCParr exposes tools via:
- **OpenAPI** (port 8000): For Open WebUI and other OpenAPI-compatible tools
- **MCP Server** (port 8001): For Claude Desktop and MCP-compatible assistants

### 2. Configure Your AI Assistant

#### Open WebUI (Recommended - OpenAPI Integration)

Open WebUI is the primary use case for MCParr. It uses the **OpenAPI** endpoint to integrate tools.

**Step 1: Add Open WebUI Service to MCParr**

1. Go to **Services** → **Add Service**
2. Select **Open WebUI** as service type
3. Enter URL and **admin API key**
4. Test connection

**Step 2: Auto-Configure (Recommended)**

1. Go to **MCP** → **Configuration** tab
2. Use the **Auto-Configuration** section
3. Select endpoint mode:
   - **Group**: One endpoint per service category (media, books, download, etc.)
   - **Service Group**: One endpoint per custom service group
   - **Service**: One endpoint per service
   - **All**: Single endpoint with all tools
4. Choose categories/services to include
5. Click **Configure** - tools are registered automatically!

**Step 3: Manual Setup (Alternative)**

1. Go to **Open WebUI** → **Settings** → **Admin Settings** → **Tools**
2. Click **"+ Add Tool"**
3. Configure:
   - **Type**: Select **"OpenAPI"**
   - **URL**: `http://YOUR_MCPARR_HOST:8000`
   - **OpenAPI Spec**: `/tools/openapi.json`
   - **Auth**: Select **"Session"**
4. Click **Save**

**Step 4: Enable Tools in Chat**

1. Start a new chat in Open WebUI
2. Click the **Tools** icon (wrench) in the chat input
3. Enable MCParr tools you want to use
4. Start chatting with access to your homelab!

**Example Chat:**
```
User: Search for science fiction movies in Plex
Assistant: [Uses plex_search tool] Found 42 sci-fi movies including...

User: Request the latest season of The Expanse
Assistant: [Uses overseerr_request_tv tool] I've requested Season 6...
```

#### Claude Desktop (MCP Integration)

For Claude Desktop, use the **MCP** endpoint on port 8001.

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

#### 📊 system_get_health
Get overall system health.

```json
{
  "name": "system_get_health",
  "parameters": {}
}
```

#### 🔍 system_get_service_status
Check a specific service status.

```json
{
  "name": "system_get_service_status",
  "parameters": {
    "service_name": "plex"
  }
}
```

#### 🔎 system_global_search
Search across all enabled services simultaneously.

```json
{
  "name": "system_global_search",
  "parameters": {
    "query": "Inception",
    "categories": "media",  // optional: all, media, indexers, books, wiki, support
    "limit": 5  // optional: max results per service
  }
}
```

**Supported Categories:**
| Category | Services |
|----------|----------|
| media | Overseerr, Radarr, Sonarr, Plex |
| indexers | Jackett, Prowlarr |
| books | Komga, Audiobookshelf |
| wiki | Wiki.js |
| support | Zammad |

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

## ⛓️ Tool Chains

Tool chains allow you to create automated workflows with conditional logic (IF/THEN/ELSE).

### Creating a Chain

1. Go to **MCP** → **Chains** tab
2. Click **New Chain**
3. Add steps with:
   - **Source Tool**: The trigger tool
   - **Conditions**: IF logic (equals, contains, is_empty, etc.)
   - **THEN Actions**: What to do when condition is true
   - **ELSE Actions**: What to do when condition is false

### Example Chain: Smart Media Request

```
IF plex_search("Inception") returns empty
  THEN overseerr_request_movie(tmdb_id=27205)
  ELSE return "Movie already in library"
```

### Condition Operators

| Operator | Description |
|----------|-------------|
| `eq` | Equals |
| `ne` | Not equals |
| `contains` | String contains |
| `is_empty` | Field is empty/null |
| `success` | Tool execution succeeded |
| `failed` | Tool execution failed |
| `regex` | Regular expression match |

### Context Variables

Pass data between chain steps:

```json
{
  "save_to_context": {
    "movie_id": "result.tmdbId",
    "movie_title": "result.title"
  }
}
```

Use in next step:

```json
{
  "argument_mappings": {
    "mediaId": "{context.movie_id}"
  }
}
```

---

## 🔎 Global Search Configuration

Configure which services are included in the `system_global_search` tool.

### Via Web Interface

1. Go to **MCP** → **Configuration** tab
2. In **Global Search** section, toggle services on/off
3. Set priority order for search results

### Searchable Services

| Service | Search Tool | Content Type |
|---------|-------------|--------------|
| Overseerr | `overseerr_search_media` | Movies & TV (TMDB) |
| Radarr | `radarr_search_movie` | Movies in library |
| Sonarr | `sonarr_search_series` | TV series in library |
| Plex | `plex_search` | All media content |
| Jackett | `jackett_search` | Torrent indexers |
| Prowlarr | `prowlarr_search` | Torrent indexers |
| Komga | `komga_search` | Comics/Manga |
| Audiobookshelf | `audiobookshelf_search` | Audiobooks/Podcasts |
| Wiki.js | `wikijs_search` | Wiki pages |
| Zammad | `zammad_search_tickets` | Support tickets |

---

## 📦 Service Groups

Service Groups allow you to organize services for Open WebUI auto-configuration.

### Creating Service Groups

1. Go to **Services** → **Groups** tab
2. Click **New Group**
3. Name your group (e.g., "Media Services", "Download Tools")
4. Select services to include
5. Save the group

### Using in Auto-Configuration

When using **Service Group** mode in auto-configuration:
- One OpenAPI endpoint is created per service group
- Each endpoint contains only tools from that group
- Useful for organizing tools by function or access level

---

## 🔄 Real-time Updates

MCParr can push real-time updates to the AI assistant:

- **Training progress**: When fine-tuning models
- **Service alerts**: When services go down
- **Request updates**: When media becomes available

---

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
