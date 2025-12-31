# 👥 User Guide

Complete guide to using MCParr AI Gateway.

## 🏠 Dashboard

The dashboard provides an overview of your homelab:

### 📊 Widgets

- **Service Status**: Health of all connected services
- **System Metrics**: CPU, memory, disk usage
- **Recent Activity**: Latest MCP tool calls
- **Training Status**: Active training sessions

### 🔄 Real-time Updates

The dashboard updates automatically via WebSocket. No manual refresh needed.

---

## 🔧 Services

### Adding a Service

1. Go to **Services** tab
2. Click **Add Service**
3. Fill in:
   - **Name**: Display name
   - **Type**: Service type (Plex, Radarr, etc.)
   - **URL**: Service URL with port
   - **API Key**: Service authentication
4. Click **Test Connection**
5. If successful, click **Save**

### Service Types

| Type | Required Config |
|------|-----------------|
| Plex | URL, Token |
| Overseerr | URL, API Key |
| Radarr | URL, API Key |
| Sonarr | URL, API Key |
| Tautulli | URL, API Key |
| Prowlarr | URL, API Key |
| Deluge | URL, Password |
| Komga | URL, Username, Password |
| Audiobookshelf | URL, API Key |
| Wiki.js | URL, Token |
| Zammad | URL, Token |
| Authentik | URL, Token |
| Open WebUI | URL, API Key |

### Testing Services

Click the **Test** button on any service to verify connectivity. Results show:
- ✅ Connection successful
- ❌ Connection failed (with error details)
- ⏱️ Response time

---

## 👥 User Management

### User Mappings

Map users across different services for unified identity:

1. Go to **Users** tab
2. Click **Add User Mapping**
3. Enter:
   - **Canonical Name**: Main identifier
   - **Email**: User's email
   - **Service Mappings**: Username in each service

Example:
```
Canonical: john
Email: john@example.com
Plex: john_plex_user
Overseerr: john@example.com
Tautulli: john
```

### Groups

Create groups to manage permissions:

1. Go to **Users** → **Groups**
2. Click **Create Group**
3. Configure:
   - **Name**: Group name
   - **Description**: Purpose
   - **Tool Permissions**: Which MCP tools are allowed

#### Permission Levels

- `*` - All tools allowed
- `plex_*` - All Plex tools
- `plex_search` - Specific tool only

### Assigning Users to Groups

1. Edit a user mapping
2. Select groups in the **Groups** field
3. Save changes

---

## 🧠 AI Training

### Overview

Train custom AI models on your homelab-specific data.

### Training Workflow

```
1. Create Prompts → 2. Create Session → 3. Select Worker → 4. Start Training → 5. Export Model
```

### Creating Prompts

1. Go to **Training** → **Prompts**
2. Click **Add Prompt**
3. Fill in:
   - **Name**: Descriptive name
   - **Category**: general, media, system, etc.
   - **System Prompt**: AI behavior instructions
   - **User Input**: Example user message
   - **Expected Output**: Ideal AI response

Example prompt:
```
Name: Movie Request
Category: media
System: You are a helpful homelab assistant.
User: I want to watch Inception
Output: I'll check if Inception is in your library. If not, I can request it via Overseerr.
```

### Creating a Training Session

1. Go to **Training** → **Sessions**
2. Click **New Session**
3. Configure:
   - **Name**: Session identifier
   - **Base Model**: Starting model (e.g., Llama 3.2)
   - **Prompts**: Select training prompts
   - **Config**: Training parameters

### Training Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| Epochs | 3 | Training iterations |
| Learning Rate | 2e-4 | Step size |
| Batch Size | 4 | Samples per step |
| LoRA Rank | 16 | Adaptation complexity |

### Starting Training

1. Select a **Worker** (GPU machine)
2. Click **Start Training**
3. Monitor progress in real-time:
   - Loss graph
   - GPU utilization
   - Estimated time

### Exporting Models

After training completes:

1. Click **Export to Ollama**
2. Choose quantization (Q4_K_M, Q5_K_M, Q8_0)
3. Model appears in your Ollama instance

---

## 🛠️ MCP (AI Tools)

### History

View all MCP tool calls:

1. Go to **MCP** tab
2. Browse history with filters:
   - Tool name
   - Status (success/failed)
   - Date range

### Tool Details

Click any request to see:
- Input parameters
- Output response
- Execution time
- Error details (if failed)

### Configuration

Manage MCP server settings:

1. Go to **MCP** → **Config**
2. Configure:
   - Enabled tools
   - Default behaviors
   - Rate limits

---

## ⚙️ Configuration

### Site Settings

Global application settings:

- **App Name**: Displayed in UI
- **Theme**: Light/Dark mode
- **Language**: Interface language

### Backup & Restore

#### Export Data

1. Go to **Configuration** → **Backup**
2. Select what to export:
   - ✅ Services
   - ✅ User mappings
   - ✅ Groups
   - ✅ Training prompts
   - ✅ Workers
3. Click **Export**
4. Save the JSON file

#### Import Data

1. Click **Import**
2. Select JSON backup file
3. Choose import mode:
   - **Replace**: Overwrite existing
   - **Merge**: Add new, keep existing
4. Click **Import**

---

## 📊 Monitoring

### Logs

View application logs:

1. Go to **Monitoring** → **Logs**
2. Filter by:
   - Level (INFO, WARNING, ERROR)
   - Source
   - Time range

### Alerts

Configure alerts for issues:

1. Go to **Monitoring** → **Alerts**
2. Create alert rules:
   - Service down
   - High resource usage
   - Training failure

---

## 🔑 Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+K` | Quick search |
| `Ctrl+/` | Show shortcuts |
| `Esc` | Close modal |

---

## 🐛 Troubleshooting

### Service Won't Connect

1. Verify URL is correct (include port)
2. Check API key is valid
3. Ensure service is running
4. Check firewall rules

### Training Stuck

1. Check worker status
2. Verify GPU availability
3. Check worker logs
4. Try reducing batch size

### UI Not Loading

1. Clear browser cache
2. Check backend is running
3. Verify CORS configuration
4. Check browser console for errors

---

## 📚 More Resources

- [📦 Installation Guide](INSTALLATION.md)
- [⚙️ Configuration Guide](CONFIGURATION.md)
- [🔌 API Reference](API.md)
- [🛠️ MCP Integration](MCP.md)
