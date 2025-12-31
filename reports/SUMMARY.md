# MCParr - Rapport de Qualité de Code

Généré le: 2025-12-31 14:42:20

## 📊 Backend (Python)

### Linting (Ruff)
- **Erreurs trouvées:** 1

```
src/adapters/audiobookshelf.py:307:101: E501 Line too long (111 > 100)
src/adapters/audiobookshelf.py:308:101: E501 Line too long (117 > 100)
src/adapters/audiobookshelf.py:317:101: E501 Line too long (111 > 100)
src/adapters/audiobookshelf.py:318:101: E501 Line too long (113 > 100)
src/adapters/audiobookshelf.py:372:101: E501 Line too long (110 > 100)
src/adapters/audiobookshelf.py:399:101: E501 Line too long (104 > 100)
src/adapters/audiobookshelf.py:423:101: E501 Line too long (123 > 100)
src/adapters/authentik.py:152:17: B904 Within an `except` clause, raise exceptions with `raise ... from err` or `raise ... from None` to distinguish them from errors in exception handling
src/adapters/authentik.py:153:13: B904 Within an `except` clause, raise exceptions with `raise ... from err` or `raise ... from None` to distinguish them from errors in exception handling
src/adapters/authentik.py:155:13: B904 Within an `except` clause, raise exceptions with `raise ... from err` or `raise ... from None` to distinguish them from errors in exception handling
src/adapters/authentik.py:234:101: E501 Line too long (101 > 100)
src/adapters/authentik.py:237:101: E501 Line too long (106 > 100)
src/adapters/authentik.py:326:101: E501 Line too long (105 > 100)
src/adapters/authentik.py:429:101: E501 Line too long (144 > 100)
src/adapters/authentik.py:430:101: E501 Line too long (111 > 100)
src/adapters/base.py:46:26: F821 Undefined name `ServiceConfig`
src/adapters/deluge.py:190:101: E501 Line too long (102 > 100)
src/adapters/jackett.py:70:101: E501 Line too long (103 > 100)
src/adapters/jackett.py:118:101: E501 Line too long (101 > 100)
src/adapters/jackett.py:132:101: E501 Line too long (102 > 100)
src/adapters/jackett.py:241:101: E501 Line too long (141 > 100)
src/adapters/jackett.py:252:101: E501 Line too long (103 > 100)
src/adapters/komga.py:54:101: E501 Line too long (108 > 100)
src/adapters/komga.py:55:101: E501 Line too long (108 > 100)
src/adapters/komga.py:188:101: E501 Line too long (106 > 100)
src/adapters/komga.py:216:101: E501 Line too long (104 > 100)
src/adapters/komga.py:307:101: E501 Line too long (101 > 100)
src/adapters/openwebui.py:147:101: E501 Line too long (109 > 100)
src/adapters/openwebui.py:153:17: B904 Within an `except` clause, raise exceptions with `raise ... from err` or `raise ... from None` to distinguish them from errors in exception handling
src/adapters/openwebui.py:154:13: B904 Within an `except` clause, raise exceptions with `raise ... from err` or `raise ... from None` to distinguish them from errors in exception handling
src/adapters/openwebui.py:156:13: B904 Within an `except` clause, raise exceptions with `raise ... from err` or `raise ... from None` to distinguish them from errors in exception handling
src/adapters/openwebui.py:186:101: E501 Line too long (115 > 100)
src/adapters/openwebui.py:221:101: E501 Line too long (107 > 100)
src/adapters/overseerr.py:139:101: E501 Line too long (122 > 100)
src/adapters/overseerr.py:146:17: B904 Within an `except` clause, raise exceptions with `raise ... from err` or `raise ... from None` to distinguish them from errors in exception handling
src/adapters/overseerr.py:147:13: B904 Within an `except` clause, raise exceptions with `raise ... from err` or `raise ... from None` to distinguish them from errors in exception handling
src/adapters/overseerr.py:149:13: B904 Within an `except` clause, raise exceptions with `raise ... from err` or `raise ... from None` to distinguish them from errors in exception handling
src/adapters/overseerr.py:241:101: E501 Line too long (117 > 100)
src/adapters/overseerr.py:312:101: E501 Line too long (109 > 100)
src/adapters/overseerr.py:355:101: E501 Line too long (126 > 100)
src/adapters/overseerr.py:356:101: E501 Line too long (128 > 100)
src/adapters/overseerr.py:357:101: E501 Line too long (130 > 100)
src/adapters/overseerr.py:364:101: E501 Line too long (103 > 100)
src/adapters/plex.py:134:17: B904 Within an `except` clause, raise exceptions with `raise ... from err` or `raise ... from None` to distinguish them from errors in exception handling
src/adapters/plex.py:135:13: B904 Within an `except` clause, raise exceptions with `raise ... from err` or `raise ... from None` to distinguish them from errors in exception handling
src/adapters/plex.py:137:13: B904 Within an `except` clause, raise exceptions with `raise ... from err` or `raise ... from None` to distinguish them from errors in exception handling
src/adapters/plex.py:239:101: E501 Line too long (116 > 100)
src/adapters/plex.py:250:101: E501 Line too long (120 > 100)
src/adapters/plex.py:333:101: E501 Line too long (114 > 100)
src/adapters/prowlarr.py:156:101: E501 Line too long (120 > 100)
```

### Couverture de tests
```
Name                                    Stmts   Miss  Cover
-----------------------------------------------------------
src/adapters/__init__.py                   16     16     0%
src/adapters/audiobookshelf.py            159    159     0%
src/adapters/authentik.py                 183    183     0%
src/adapters/base.py                      164    164     0%
src/adapters/deluge.py                    119    119     0%
src/adapters/jackett.py                   120    120     0%
src/adapters/komga.py                     115    115     0%
src/adapters/ollama.py                     88     88     0%
src/adapters/openwebui.py                 152    152     0%
src/adapters/overseerr.py                 205    205     0%
src/adapters/plex.py                      198    198     0%
src/adapters/prowlarr.py                  117    117     0%
src/adapters/radarr.py                    124    124     0%
src/adapters/romm.py                      105    105     0%
src/adapters/sonarr.py                    125    125     0%
src/adapters/tautulli.py                  253    253     0%
src/adapters/wikijs.py                    149    149     0%
src/adapters/zammad.py                    208    208     0%
src/config/__init__.py                      0      0   100%
src/config/settings.py                     61     61     0%
src/database.py                            10     10     0%
src/database/__init__.py                    0      0   100%
src/database/connection.py                 52     52     0%
src/main.py                                94     94     0%
src/mcp/__init__.py                         2      2     0%
src/mcp/main.py                            30     30     0%
src/mcp/server.py                         156    156     0%
src/mcp/tools/__init__.py                  14     14     0%
src/mcp/tools/audiobookshelf_tools.py      81     81     0%
src/mcp/tools/authentik_tools.py           97     97     0%
src/mcp/tools/base.py                      78     78     0%
src/mcp/tools/deluge_tools.py              60     60     0%
src/mcp/tools/jackett_tools.py             63     63     0%
src/mcp/tools/komga_tools.py               62     62     0%
src/mcp/tools/openwebui_tools.py           62     62     0%
src/mcp/tools/overseerr_tools.py          105    105     0%
src/mcp/tools/plex_tools.py                68     68     0%
src/mcp/tools/prowlarr_tools.py            69     69     0%
src/mcp/tools/radarr_tools.py              71     71     0%
src/mcp/tools/romm_tools.py                60     60     0%
src/mcp/tools/sonarr_tools.py              71     71     0%
src/mcp/tools/system_tools.py             172    172     0%
src/mcp/tools/tautulli_tools.py           279    279     0%
src/mcp/tools/wikijs_tools.py              89     89     0%
src/mcp/tools/zammad_tools.py              98     98     0%
src/middleware/__init__.py                  0      0   100%
src/middleware/correlation_id.py           11     11     0%
src/middleware/logging.py                  68     68     0%
src/models/__init__.py                     13     13     0%
src/models/alert_config.py                 63     63     0%
src/models/base.py                        111    111     0%
src/models/configuration.py                46     46     0%
src/models/group.py                        52     52     0%
src/models/log_entry.py                    27     27     0%
src/models/mcp_request.py                  62     62     0%
src/models/service_config.py               91     91     0%
src/models/system_metrics.py               18     18     0%
src/models/training_prompt.py             109    109     0%
src/models/training_session.py            155    155     0%
src/models/training_worker.py              55     55     0%
src/models/user_mapping.py                 88     88     0%
src/routers/__init__.py                     0      0   100%
src/routers/alerts.py                     151    151     0%
src/routers/backup.py                     287    287     0%
src/routers/config.py                     131    131     0%
src/routers/dashboard.py                   51     51     0%
src/routers/groups.py                     258    258     0%
src/routers/health.py                      32     32     0%
src/routers/logs.py                        97     97     0%
src/routers/mcp.py                        290    290     0%
src/routers/openapi_tools.py              783    783     0%
src/routers/services.py                   142    142     0%
src/routers/system.py                      98     98     0%
src/routers/training.py                  1209   1209     0%
src/routers/users.py                      296    296     0%
src/routers/workers.py                    326    326     0%
src/services/__init__.py                    0      0   100%
src/services/alert_service.py             135    135     0%
src/services/circuit_breaker.py           144    144     0%
src/services/health_scheduler.py           94     94     0%
src/services/log_exporter.py               62     62     0%
src/services/log_service.py               101    101     0%
src/services/mcp_audit.py                  78     78     0%
src/services/ollama_service.py            216    216     0%
src/services/permission_service.py         80     80     0%
src/services/service_registry.py          119    119     0%
src/services/service_tester.py            123    123     0%
src/services/system_monitor.py            103    103     0%
src/services/training_service.py          286    286     0%
src/services/training_ws.py               155    155     0%
src/services/user_centralization.py       146    146     0%
src/services/user_mapper.py               474    474     0%
src/services/user_sync.py                 195    195     0%
src/services/worker_client.py             215    215     0%
src/utils/__init__.py                       0      0   100%
src/utils/logging.py                       30     30     0%
src/websocket/__init__.py                   0      0   100%
src/websocket/logs.py                      98     98     0%
src/websocket/manager.py                   64     64     0%
src/websocket/system.py                    82     82     0%
src/websocket/training.py                 178    178     0%
-----------------------------------------------------------
TOTAL                                   12902  12902     0%
```

## 🎨 Frontend (React/TypeScript)

### Linting (ESLint)
```

> frontend@0.0.0 lint
> eslint . --format stylish


/home/jeremie/Documents/Developpement/mcparr/src/frontend/src/components/Groups/GroupDetail.tsx
   61:6  warning  React Hook useEffect has a missing dependency: 'fetchGroupDetail'. Either include it or remove the dependency array                            react-hooks/exhaustive-deps
   70:6  warning  React Hook useEffect has missing dependencies: 'availableTools' and 'centralUsers.length'. Either include them or remove the dependency array  react-hooks/exhaustive-deps
  306:6  warning  React Hook useMemo has a missing dependency: 'isToolPermitted'. Either include it or remove the dependency array                               react-hooks/exhaustive-deps

/home/jeremie/Documents/Developpement/mcparr/src/frontend/src/components/Groups/GroupList.tsx
  34:6  warning  React Hook useEffect has a missing dependency: 'fetchGroups'. Either include it or remove the dependency array  react-hooks/exhaustive-deps

/home/jeremie/Documents/Developpement/mcparr/src/frontend/src/components/Layout.tsx
  22:18  error  Unexpected any. Specify a different type  @typescript-eslint/no-explicit-any

/home/jeremie/Documents/Developpement/mcparr/src/frontend/src/components/Observability/AlertManager.tsx
  18:39  error  Unexpected any. Specify a different type  @typescript-eslint/no-explicit-any
  41:40  error  Unexpected any. Specify a different type  @typescript-eslint/no-explicit-any

/home/jeremie/Documents/Developpement/mcparr/src/frontend/src/components/Observability/LogViewer.tsx
  16:30  error  Unexpected any. Specify a different type  @typescript-eslint/no-explicit-any

/home/jeremie/Documents/Developpement/mcparr/src/frontend/src/components/ServiceForm.tsx
  227:6  warning  React Hook useEffect has a missing dependency: 'formData.port'. Either include it or remove the dependency array  react-hooks/exhaustive-deps

/home/jeremie/Documents/Developpement/mcparr/src/frontend/src/components/ServiceStatus/ServiceStatusDashboard.tsx
  73:54  error  Unexpected any. Specify a different type  @typescript-eslint/no-explicit-any
  74:53  error  Unexpected any. Specify a different type  @typescript-eslint/no-explicit-any
  77:21  error  Unexpected any. Specify a different type  @typescript-eslint/no-explicit-any
  78:18  error  Unexpected any. Specify a different type  @typescript-eslint/no-explicit-any
  84:89  error  Unexpected any. Specify a different type  @typescript-eslint/no-explicit-any

/home/jeremie/Documents/Developpement/mcparr/src/frontend/src/components/SystemMetrics/MetricsCard.tsx
  7:12  error  Unexpected any. Specify a different type  @typescript-eslint/no-explicit-any

/home/jeremie/Documents/Developpement/mcparr/src/frontend/src/components/Training/SessionDetailsModal.tsx
  261:7  error  Error: Calling setState synchronously within an effect can trigger cascading renders

Effects are intended to synchronize state between React and external systems such as manually updating the DOM, state management libraries, or other platform APIs. In general, the body of an effect should do one or both of the following:
* Update external systems with the latest state from React.
* Subscribe for updates from some external system, calling setState in a callback function when external state changes.

Calling setState synchronously within an effect body causes cascading renders that can hurt performance, and is not recommended. (https://react.dev/learn/you-might-not-need-an-effect).

/home/jeremie/Documents/Developpement/mcparr/src/frontend/src/components/Training/SessionDetailsModal.tsx:261:7
  259 |   useEffect(() => {
  260 |     if (isOpen && sessionId) {
> 261 |       setLoading(true);
      |       ^^^^^^^^^^ Avoid calling setState() directly within an effect
```

---

## 📁 Fichiers de rapports

### Backend
- `ruff-report.json` - Rapport Ruff au format JSON
- `ruff-report.txt` - Rapport Ruff au format texte
- `ruff-fixes.txt` - Suggestions de corrections Ruff
- `ruff-fixes.patch` - Fichier patch pour appliquer les corrections
- `black-report.txt` - Rapport Black (formatage)
- `coverage.xml` - Couverture de code (format Cobertura)
- `htmlcov/` - Rapport de couverture HTML
- `junit.xml` - Résultats de tests (format JUnit)

### Frontend
- `eslint-report.json` - Rapport ESLint au format JSON
- `eslint-report.txt` - Rapport ESLint au format texte
- `eslint-fixes.txt` - Suggestions de corrections ESLint

## 🔧 Commandes pour appliquer les corrections

### Backend
```bash
# Appliquer les corrections automatiques Ruff
cd src/backend && poetry run ruff check src/ --fix --unsafe-fixes

# Appliquer le formatage Black
cd src/backend && poetry run black src/

# Ou appliquer le patch généré
patch -p1 < reports/ruff-fixes.patch
```

### Frontend
```bash
# Appliquer les corrections automatiques ESLint
cd src/frontend && npm run lint -- --fix
```

### Les deux
```bash
# Utiliser le script d'auto-fix
npm run fix
# ou
bash scripts/ci-auto-fix.sh
```
