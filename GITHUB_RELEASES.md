# GitHub Releases - MCParr

> Copier-coller directement le contenu de chaque release dans GitHub

---

# v0.2.36

**Title:** `v0.2.36 - Release Notes Integration`

**Release Notes (copier ci-dessous):**

---

## 📝 What's New in v0.2.36

### 📋 Release Notes Management
- **GITHUB_RELEASES.md** - Centralized release notes file for automated releases
  - Pre-formatted release notes ready for GitHub
  - Tracked in git repository for CI/CD access
  - GitLab CI automatically extracts first section for new releases
  - Comprehensive documentation for v0.2.34, v0.2.35, and v0.2.36

### 🔧 Repository Improvements
- **Version History** - Full release notes for recent versions now available
- **CI/CD Ready** - Release automation fully functional with documented notes
- **Consistent Format** - Standardized release note structure across all versions

### 📚 Documentation
Complete release notes now include:
- v0.2.34: Modern Documentation & Release Automation
- v0.2.35: GitHub Release Automation
- v0.2.36: Release Notes Integration (this version)

---

**Full Changelog**: https://github.com/sharkhunterr/mcparr/compare/v0.2.35...v0.2.36

---
---

# v0.2.35

**Title:** `v0.2.35 - GitHub Release Automation`

**Release Notes (copier ci-dessous):**

---

## 🤖 What's New in v0.2.35

### 🚀 GitHub Release Automation
- **GitLab CI Integration** - Automatic GitHub release creation via GitLab CI pipeline
  - New `release:github` job that creates releases automatically
  - Extracts release notes from GITHUB_RELEASES.md (first section)
  - Uses GitHub API with GITHUB_TOKEN and GITHUB_REPO variables
  - Fallback to CHANGELOG.md if GITHUB_RELEASES.md unavailable
- **Enhanced Verification** - Verify job now checks both GitHub tags and releases
  - Direct URL to created GitHub release in CI logs
  - Comprehensive deployment verification across all platforms

### 🔧 Release Script Improvements
- **Environment Variables Support** - release.js adapted for GitLab CI workflow
  - No longer requires local `github` git remote
  - Uses GITHUB_TOKEN and GITHUB_REPO from environment
  - Informative messages when tools unavailable locally
  - Graceful fallback to GitLab CI for GitHub operations

### 🎯 Complete Deployment Flow
One command deploys everything:
```bash
npm run release:full
```
Automatically triggers:
- ✅ Version bump with standard-version
- ✅ Docker Hub deployment (multi-platform: amd64 + arm64)
- ✅ GitHub synchronization (code + tags)
- ✅ GitLab release creation
- ✅ GitHub release creation with formatted notes
- ✅ Full verification suite

---

**Full Changelog**: https://github.com/sharkhunterr/mcparr/compare/v0.2.34...v0.2.35

---
---

# v0.2.34

**Title:** `v0.2.34 - Modern Documentation & Release Automation`

**Release Notes (copier ci-dessous):**

---

## 📚 What's New in v0.2.34

### 📖 Documentation Overhaul
- **Modernized README** - Compact, professional design with modern badges and navigation
- **Docker Hub README** - Optimized documentation for Docker Hub display
- **Docker Deployment Guide** - Comprehensive guide in `docker/README.md`
- **Better Organization** - Table-based feature layout and collapsible sections
- **Version Badges** - GitHub releases, Docker pulls, and tech stack badges

### 🚀 Release Automation
- **Flexible Release Scripts** - New npm commands for automated releases
  - `npm run release` - Standard release with version bump
  - `npm run release:github` - Push to GitHub
  - `npm run release:deploy` - Trigger GitLab CI deployment
  - `npm run release:full` - Full release (GitHub + deploy)
- **Git Push Scripts** - Flexible push to GitLab and/or GitHub
  - `npm run push:github` - Push to GitHub only
  - `npm run push:all` - Push to both remotes
  - `npm run push:tags` - Push tags only
- **Docker Deployment** - Automated Docker Hub deployment
  - `npm run docker:build` - Build image locally
  - `npm run docker:deploy` - Build and push to Docker Hub
  - `npm run docker:deploy:multi` - Multi-platform build (amd64 + arm64)
- **Version Sync** - Automatic version syncing between package.json and Python version.py

### 🐛 Bug Fixes
- **Database Initialization** - Fixed fresh database setup with proper Alembic stamping
- **GitLab CI Health Checks** - Improved retry logic for container health checks (30 attempts × 2s)
- **Version Display** - Added nginx proxy rule for `/version` endpoint

### 📝 Content Updates
- **Vibe Code Story** - Simplified acknowledgments section explaining the project's origin
- **Project Context** - Clear explanation of the need, solution, and approach
- **Professional Tone** - Balanced documentation between technical and accessible

---

**Full Changelog**: https://github.com/sharkhunterr/mcparr/compare/v0.2.33...v0.2.34

---
---

# v0.2.27

**Title:** `v0.2.27 - Session Control & Library Management`

**Release Notes (copier ci-dessous):**

---

## 🎬 What's New in v0.2.27

### 🎛️ Session & Stream Control
- **Tautulli Session Termination** - Terminate active Plex streaming sessions directly via MCP tools with optional user message

### 📚 Library Management
- **Audiobookshelf Library Scan** - Trigger library scans with optional force mode for audiobooks/podcasts
- **Audiobookshelf Progress Management** - Update listening progress, mark as finished, or reset progress
- **RomM Platform Scan** - Scan specific platforms or all platforms for new ROMs

### ⚡ Improvements
- Enhanced session data with `session_id` for stream control operations
- Smart platform/library name resolution with partial matching

---

**Full Changelog**: https://github.com/sharkhunterr/mcparr/compare/v0.2.26...v0.2.27

---
---

# v0.2.26

**Title:** `v0.2.26 - Version Display & Update Detection`

**Release Notes (copier ci-dessous):**

---

## ✨ What's New in v0.2.26

### 🔄 Version & Updates
- **Version Display** - Current version now displayed in sidebar footer
- **Update Detection** - Automatic check for new releases from GitHub
- **About Tab** - New Configuration tab with full version info and update status
- **GitHub Integration** - Direct links to repository and releases

### 🔗 Tool Chains
- **Step Reordering** - Move up/down buttons for easy step reorganization
- **Drag & Drop Alternative** - Quick reordering without drag gestures

### 🛠️ Content Management Tools
- **Plex Library Scan** - Trigger library scans with refresh status
- **Queue Match Tools** - New Radarr/Sonarr queue matching capabilities
- **Automatic Tool Sync** - Tool permissions now sync automatically

### 🐛 Bug Fixes
- Fixed SQLAlchemy transaction rollback errors in tool logging
- Improved database concurrency with WAL mode

---

**Full Changelog**: https://github.com/sharkhunterr/mcparr/compare/v0.2.25...v0.2.26

---
---

# v0.2.25

**Title:** `v0.2.25 - Tool Chains, Global Search & Service Groups`

**Release Notes (copier ci-dessous):**

---

## 🚀 What's New in v0.2.25

This is a major release introducing powerful new features for automation and organization!

### 🔗 Tool Chains
Build complex multi-tool workflows with our new visual chain editor:
- **Step-based Architecture** - Create sequential tool workflows
- **Conditional Logic** - IF/THEN/ELSE branching based on tool results
- **Nested Conditions** - Support for complex decision trees
- **Context Variables** - Persist data across chain execution with `save_to_context`
- **Argument Mappings** - Map outputs from previous steps to next tool inputs
- **Chain Flow Detection** - Automatic detection of chain triggers with multi-user support

### 🔍 Global Search
- **Cross-Service Search** - Search across all configured services at once
- **Configurable Limits** - Set result limits per search
- **Service Settings** - Enable/disable services for global search

### 📁 Service Groups
- **Custom Groups** - Organize services into logical groups
- **Flexible Organization** - Group tools by function, project, or any criteria
- **Group Management UI** - Easy creation and management of service groups

### 🎨 UI/UX Improvements
- **Help System** - Contextual help tooltips throughout the application
- **Help Page** - Centralized documentation and guidance
- **Wizard Updates** - Tool chains and help steps added to setup wizard
- **Mobile Responsive** - Improved layouts for mobile devices
- **Unified Styling** - Consistent button styles and colors across components

### 🛠️ New Service Tools
- **Dynamic Endpoints** - Support for custom service endpoints
- **Radarr/Sonarr Tools** - Additional queue and media management tools
- **Overseerr Improvements** - Better media info handling and availability checks

### 🐛 Bug Fixes
- Fixed SQLite concurrency issues with WAL mode and busy timeout
- Fixed Sonarr queue response to include series and episode data
- Restored SQLAlchemy boolean comparisons
- Resolved all linting errors for backend and frontend

### 💾 Backup & Restore
- Added support for new models (Tool Chains, Service Groups, Global Search)

---

**Full Changelog**: https://github.com/sharkhunterr/mcparr/compare/v0.2.24...v0.2.25

---
---

# 📋 Instructions

1. Aller sur https://github.com/sharkhunterr/mcparr/releases/new
2. **Tag**: Correspond au tag de version
3. **Target**: `master`
4. **Title**: Copier le titre de la version concernée
5. **Description**: Copier tout depuis `## 📚 What's New` (ou `## 🚀 What's New`) jusqu'à `**Full Changelog**` inclus
6. **Publish release**

> ⚠️ Le script `npm run release:full` prend automatiquement la PREMIÈRE section de version (celle du haut)
