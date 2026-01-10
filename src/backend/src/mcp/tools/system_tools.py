"""MCP tools for system monitoring and management."""

from typing import List

from .base import BaseTool, ToolDefinition, ToolParameter


class SystemTools(BaseTool):
    """MCP tools for system monitoring and homelab management."""

    @property
    def definitions(self) -> List[ToolDefinition]:
        return [
            ToolDefinition(
                name="system_list_tools",
                description="ALWAYS CALL THIS FIRST. Lists all available tools grouped by service/category to help you choose the right tool.",
                parameters=[],
                category="system",
                is_mutation=False,
            ),
            ToolDefinition(
                name="system_get_health",
                description="Get overall system health status including all services",
                parameters=[],
                category="system",
                is_mutation=False,
            ),
            ToolDefinition(
                name="system_get_metrics",
                description="Get current system resource metrics (CPU, memory, disk, network)",
                parameters=[],
                category="system",
                is_mutation=False,
            ),
            ToolDefinition(
                name="system_get_services",
                description="Get list of all configured homelab services with their status",
                parameters=[
                    ToolParameter(
                        name="status_filter",
                        description="Filter by service status",
                        type="string",
                        required=False,
                        enum=["active", "error", "unknown", "all"],
                        default="all",
                    ),
                ],
                category="system",
                is_mutation=False,
            ),
            ToolDefinition(
                name="system_test_service",
                description="Test connection to a specific service",
                parameters=[
                    ToolParameter(
                        name="service_name",
                        description="Name of the service to test",
                        type="string",
                        required=True,
                    ),
                ],
                category="system",
                is_mutation=False,
            ),
            ToolDefinition(
                name="system_get_logs",
                description="Get recent system logs with optional filtering",
                parameters=[
                    ToolParameter(
                        name="level",
                        description="Filter by log level",
                        type="string",
                        required=False,
                        enum=["debug", "info", "warning", "error", "critical"],
                    ),
                    ToolParameter(
                        name="source",
                        description="Filter by log source/service",
                        type="string",
                        required=False,
                    ),
                    ToolParameter(
                        name="limit",
                        description="Maximum number of logs to return",
                        type="number",
                        required=False,
                        default=20,
                    ),
                    ToolParameter(
                        name="search",
                        description="Search term in log messages",
                        type="string",
                        required=False,
                    ),
                ],
                category="system",
                is_mutation=False,
            ),
            ToolDefinition(
                name="system_get_alerts",
                description="Get active alerts and recent alert history",
                parameters=[
                    ToolParameter(
                        name="active_only",
                        description="Only return currently active alerts",
                        type="boolean",
                        required=False,
                        default=True,
                    ),
                    ToolParameter(
                        name="limit",
                        description="Maximum number of alerts to return",
                        type="number",
                        required=False,
                        default=20,
                    ),
                ],
                category="system",
                is_mutation=False,
            ),
            ToolDefinition(
                name="system_get_users",
                description="Get list of users with their service mappings",
                parameters=[
                    ToolParameter(
                        name="search",
                        description="Search by username or email",
                        type="string",
                        required=False,
                    ),
                    ToolParameter(
                        name="limit",
                        description="Maximum number of users to return",
                        type="number",
                        required=False,
                        default=50,
                    ),
                ],
                category="users",
                is_mutation=False,
            ),
        ]

    async def execute(self, tool_name: str, arguments: dict) -> dict:
        """Execute a system tool."""
        try:
            if tool_name == "system_list_tools":
                return await self._list_available_tools()
            elif tool_name == "system_get_health":
                return await self._get_health()
            elif tool_name == "system_get_metrics":
                return await self._get_metrics()
            elif tool_name == "system_get_services":
                return await self._get_services(arguments)
            elif tool_name == "system_test_service":
                return await self._test_service(arguments)
            elif tool_name == "system_get_logs":
                return await self._get_logs(arguments)
            elif tool_name == "system_get_alerts":
                return await self._get_alerts(arguments)
            elif tool_name == "system_get_users":
                return await self._get_users(arguments)
            else:
                return {"success": False, "error": f"Unknown tool: {tool_name}"}

        except Exception as e:
            return {"success": False, "error": str(e), "error_type": type(e).__name__}

    async def _list_available_tools(self) -> dict:
        """List all available tools grouped by service/category."""
        try:
            from sqlalchemy import select

            from src.database.connection import async_session_maker
            from src.mcp.tools.audiobookshelf_tools import AudiobookshelfTools
            from src.mcp.tools.authentik_tools import AuthentikTools
            from src.mcp.tools.deluge_tools import DelugeTools
            from src.mcp.tools.jackett_tools import JackettTools
            from src.mcp.tools.komga_tools import KomgaTools
            from src.mcp.tools.openwebui_tools import OpenWebUITools
            from src.mcp.tools.overseerr_tools import OverseerrTools
            from src.mcp.tools.plex_tools import PlexTools
            from src.mcp.tools.prowlarr_tools import ProwlarrTools
            from src.mcp.tools.radarr_tools import RadarrTools
            from src.mcp.tools.romm_tools import RommTools
            from src.mcp.tools.sonarr_tools import SonarrTools
            from src.mcp.tools.tautulli_tools import TautulliTools
            from src.mcp.tools.wikijs_tools import WikiJSTools
            from src.mcp.tools.zammad_tools import ZammadTools
            from src.models.service_config import ServiceConfig

            # Get enabled services
            async with async_session_maker() as session:
                result = await session.execute(
                    select(ServiceConfig).where(ServiceConfig.enabled == True)
                )
                services = result.scalars().all()
                enabled_services = [
                    (s.service_type.value if hasattr(s.service_type, 'value') else str(s.service_type)).lower()
                    for s in services
                ]

            # Map service types to tool classes and categories
            service_config = {
                "plex": {"class": PlexTools, "category": "📺 MEDIA (regarder/chercher du contenu)", "desc": "Bibliothèque multimédia"},
                "tautulli": {"class": TautulliTools, "category": "📺 MEDIA (regarder/chercher du contenu)", "desc": "Stats et activité Plex"},
                "komga": {"class": KomgaTools, "category": "📚 LECTURE (livres, BD, manga)", "desc": "BD/Manga/Comics"},
                "audiobookshelf": {"class": AudiobookshelfTools, "category": "📚 LECTURE (livres, BD, manga)", "desc": "Livres audio/Podcasts"},
                "romm": {"class": RommTools, "category": "🎮 JEUX", "desc": "ROMs/Jeux rétro"},
                "radarr": {"class": RadarrTools, "category": "⬇️ TÉLÉCHARGEMENT", "desc": "Téléchargement films"},
                "sonarr": {"class": SonarrTools, "category": "⬇️ TÉLÉCHARGEMENT", "desc": "Téléchargement séries"},
                "prowlarr": {"class": ProwlarrTools, "category": "⬇️ TÉLÉCHARGEMENT", "desc": "Indexers"},
                "jackett": {"class": JackettTools, "category": "⬇️ TÉLÉCHARGEMENT", "desc": "Indexers (legacy)"},
                "deluge": {"class": DelugeTools, "category": "⬇️ TÉLÉCHARGEMENT", "desc": "Client torrent"},
                "overseerr": {"class": OverseerrTools, "category": "📝 DEMANDES", "desc": "Demandes de contenu"},
                "zammad": {"class": ZammadTools, "category": "🎫 SUPPORT", "desc": "Tickets support"},
                "authentik": {"class": AuthentikTools, "category": "🔐 AUTHENTIFICATION", "desc": "SSO/Utilisateurs"},
                "openwebui": {"class": OpenWebUITools, "category": "🤖 IA", "desc": "Open WebUI"},
                "wikijs": {"class": WikiJSTools, "category": "📖 DOCUMENTATION", "desc": "Wiki"},
            }

            # Build categories with actual tools from enabled services
            categories = {}

            # Always add system tools
            system_tools = []
            for tool_def in self.definitions:
                if tool_def.name != "system_list_tools":  # Exclude self
                    system_tools.append(f"{tool_def.name} - {tool_def.description}")
            categories["⚙️ SYSTÈME"] = {"system": system_tools}

            # Add tools for each enabled service
            for service_name in enabled_services:
                if service_name in service_config:
                    config = service_config[service_name]
                    category = config["category"]
                    tool_class = config["class"]

                    # Get tools from the class
                    try:
                        tool_instance = tool_class({})
                        tools_list = [
                            f"{t.name} - {t.description[:80]}{'...' if len(t.description) > 80 else ''}"
                            for t in tool_instance.definitions
                        ]

                        if category not in categories:
                            categories[category] = {}
                        categories[category][service_name] = tools_list
                    except Exception:
                        pass  # Skip if tool class fails to instantiate

            return {
                "success": True,
                "result": {
                    "message": "Voici les outils disponibles par catégorie. Choisis l'outil approprié selon la demande de l'utilisateur.",
                    "categories": categories,
                },
            }

        except Exception as e:
            return {"success": False, "error": f"Failed to list tools: {str(e)}"}

    async def _get_health(self) -> dict:
        """Get system health status."""
        import psutil

        # Get basic system health
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")

        health_status = "healthy"
        issues = []

        if cpu_percent > 90:
            health_status = "degraded"
            issues.append(f"High CPU usage: {cpu_percent}%")
        if memory.percent > 90:
            health_status = "degraded"
            issues.append(f"High memory usage: {memory.percent}%")
        if disk.percent > 90:
            health_status = "degraded"
            issues.append(f"Low disk space: {100 - disk.percent}% free")

        # Get service status from database
        service_status = {"active": 0, "error": 0, "unknown": 0}
        try:
            from sqlalchemy import select

            from src.database.connection import async_session_maker
            from src.models.service_config import ServiceConfig

            async with async_session_maker() as session:
                result = await session.execute(select(ServiceConfig).where(ServiceConfig.enabled == True))
                services = result.scalars().all()
                for svc in services:
                    status = svc.status.value if hasattr(svc.status, "value") else str(svc.status)
                    if status == "active":
                        service_status["active"] += 1
                    elif status == "error":
                        service_status["error"] += 1
                        if health_status == "healthy":
                            health_status = "degraded"
                            issues.append(f"Service '{svc.name}' is in error state")
                    else:
                        service_status["unknown"] += 1
        except Exception as e:
            issues.append(f"Could not check service status: {str(e)}")

        return {
            "success": True,
            "result": {
                "status": health_status,
                "issues": issues,
                "summary": {
                    "cpu_usage": f"{cpu_percent}%",
                    "memory_usage": f"{memory.percent}%",
                    "disk_usage": f"{disk.percent}%",
                },
                "services": service_status,
            },
        }

    async def _get_metrics(self) -> dict:
        """Get current system metrics."""
        import time

        import psutil

        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        network = psutil.net_io_counters()
        boot_time = psutil.boot_time()
        uptime = time.time() - boot_time

        # Format uptime
        days = int(uptime // 86400)
        hours = int((uptime % 86400) // 3600)
        minutes = int((uptime % 3600) // 60)
        uptime_str = f"{days}d {hours}h {minutes}m" if days > 0 else f"{hours}h {minutes}m"

        return {
            "success": True,
            "result": {
                "cpu": {
                    "usage_percent": cpu_percent,
                    "cores": psutil.cpu_count(),
                },
                "memory": {
                    "usage_percent": memory.percent,
                    "used_gb": round(memory.used / (1024**3), 2),
                    "total_gb": round(memory.total / (1024**3), 2),
                    "available_gb": round(memory.available / (1024**3), 2),
                },
                "disk": {
                    "usage_percent": disk.percent,
                    "used_gb": round(disk.used / (1024**3), 2),
                    "total_gb": round(disk.total / (1024**3), 2),
                    "free_gb": round(disk.free / (1024**3), 2),
                },
                "network": {
                    "bytes_sent": network.bytes_sent,
                    "bytes_recv": network.bytes_recv,
                    "sent_gb": round(network.bytes_sent / (1024**3), 2),
                    "recv_gb": round(network.bytes_recv / (1024**3), 2),
                },
                "uptime": uptime_str,
            },
        }

    async def _get_services(self, arguments: dict) -> dict:
        """Get list of configured services."""
        status_filter = arguments.get("status_filter", "all")

        try:
            from sqlalchemy import select

            from src.database.connection import async_session_maker
            from src.models.service_config import ServiceConfig

            async with async_session_maker() as session:
                query = select(ServiceConfig)

                # Apply status filter
                if status_filter != "all":
                    query = query.where(ServiceConfig.status == status_filter)

                result = await session.execute(query.order_by(ServiceConfig.name))
                services = result.scalars().all()

                services_list = []
                for svc in services:
                    services_list.append(
                        {
                            "id": str(svc.id),
                            "name": svc.name,
                            "type": svc.service_type.value
                            if hasattr(svc.service_type, "value")
                            else str(svc.service_type),
                            "status": svc.status.value if hasattr(svc.status, "value") else str(svc.status),
                            "enabled": svc.enabled,
                            "url": svc.full_url,
                            "version": svc.version,
                            "last_test_at": svc.last_test_at.isoformat() if svc.last_test_at else None,
                            "last_test_success": svc.last_test_success,
                            "last_error": svc.last_error,
                        }
                    )

                return {
                    "success": True,
                    "result": {
                        "count": len(services_list),
                        "filter": status_filter,
                        "services": services_list,
                    },
                }

        except Exception as e:
            return {"success": False, "error": f"Failed to get services: {str(e)}"}

    async def _test_service(self, arguments: dict) -> dict:
        """Test a service connection."""
        service_name = arguments.get("service_name")

        if not service_name:
            return {"success": False, "error": "service_name is required"}

        try:
            from sqlalchemy import func, select

            from src.database.connection import async_session_maker
            from src.models.service_config import ServiceConfig
            from src.services.service_tester import ServiceTester

            async with async_session_maker() as session:
                # Find service by name (case-insensitive)
                result = await session.execute(
                    select(ServiceConfig).where(func.lower(ServiceConfig.name) == service_name.lower())
                )
                service = result.scalar_one_or_none()

                if not service:
                    # List available services to help user
                    all_services = await session.execute(select(ServiceConfig.name))
                    available = [s[0] for s in all_services.fetchall()]
                    return {
                        "success": False,
                        "error": f"Service '{service_name}' not found. Available services: {', '.join(available)}",
                    }

                # Test the service using the class method
                # Use a retry mechanism for SQLite locking issues
                max_retries = 3
                last_error = None
                for attempt in range(max_retries):
                    try:
                        test_result = await ServiceTester.test_service_connection(service, session)
                        return {
                            "success": True,
                            "result": {
                                "service": service_name,
                                "test_success": test_result.success,
                                "message": test_result.message,
                                "response_time_ms": test_result.response_time_ms,
                                "details": test_result.details,
                            },
                        }
                    except Exception as e:
                        last_error = e
                        error_str = str(e)
                        if "database is locked" in error_str or "rolled back" in error_str:
                            # Rollback and retry
                            await session.rollback()
                            import asyncio
                            await asyncio.sleep(0.5 * (attempt + 1))  # Exponential backoff
                            continue
                        raise  # Re-raise if not a locking issue

                # All retries failed
                return {"success": False, "error": f"Database busy after {max_retries} retries: {str(last_error)}"}

        except Exception as e:
            return {"success": False, "error": f"Failed to test service: {str(e)}"}

    async def _get_logs(self, arguments: dict) -> dict:
        """Get recent logs."""
        level = arguments.get("level")
        source = arguments.get("source")
        limit = int(arguments.get("limit", 20))
        search = arguments.get("search")

        try:
            from src.database.connection import async_session_maker
            from src.services.log_service import log_service

            async with async_session_maker() as session:
                logs, total = await log_service.get_logs(
                    session,
                    level=level,
                    source=source,
                    search=search,
                    limit=limit,
                )

                logs_list = []
                for log in logs:
                    logs_list.append(
                        {
                            "id": str(log.id),
                            "level": log.level,
                            "message": log.message,
                            "source": log.source,
                            "component": log.component,
                            "logged_at": log.logged_at.isoformat() if log.logged_at else None,
                            "service_type": log.service_type,
                            "exception_type": log.exception_type,
                            "exception_message": log.exception_message,
                        }
                    )

                return {
                    "success": True,
                    "result": {
                        "count": len(logs_list),
                        "total": total,
                        "filters": {
                            "level": level,
                            "source": source,
                            "search": search,
                        },
                        "logs": logs_list,
                    },
                }

        except Exception as e:
            return {"success": False, "error": f"Failed to get logs: {str(e)}"}

    async def _get_alerts(self, arguments: dict) -> dict:
        """Get alerts."""
        active_only = arguments.get("active_only", True)
        limit = int(arguments.get("limit", 20))

        try:
            from src.database.connection import async_session_maker
            from src.services.alert_service import alert_service

            async with async_session_maker() as session:
                if active_only:
                    # Get active (unresolved) alerts
                    alerts = await alert_service.get_active_alerts(session)
                    alerts_list = []
                    for alert in alerts[:limit]:
                        alerts_list.append(
                            {
                                "id": str(alert.id),
                                "alert_name": alert.alert_name,
                                "severity": alert.severity,
                                "triggered_at": alert.triggered_at.isoformat() if alert.triggered_at else None,
                                "is_resolved": alert.is_resolved,
                                "metric_value": alert.metric_value,
                                "threshold_value": alert.threshold_value,
                                "message": alert.message,
                            }
                        )
                else:
                    # Get recent alert history
                    history, total = await alert_service.get_alert_history(
                        session,
                        limit=limit,
                    )
                    alerts_list = []
                    for alert in history:
                        alerts_list.append(
                            {
                                "id": str(alert.id),
                                "alert_name": alert.alert_name,
                                "severity": alert.severity,
                                "triggered_at": alert.triggered_at.isoformat() if alert.triggered_at else None,
                                "resolved_at": alert.resolved_at.isoformat() if alert.resolved_at else None,
                                "is_resolved": alert.is_resolved,
                                "metric_value": alert.metric_value,
                                "threshold_value": alert.threshold_value,
                                "message": alert.message,
                            }
                        )

                # Get stats
                stats = await alert_service.get_alert_stats(session, hours=24)

                return {
                    "success": True,
                    "result": {
                        "count": len(alerts_list),
                        "active_only": active_only,
                        "alerts": alerts_list,
                        "stats": {
                            "total_triggered_24h": stats.get("total_triggered", 0),
                            "active_count": stats.get("active_count", 0),
                            "by_severity": stats.get("by_severity", {}),
                        },
                    },
                }

        except Exception as e:
            return {"success": False, "error": f"Failed to get alerts: {str(e)}"}

    async def _get_users(self, arguments: dict) -> dict:
        """Get users list with their service mappings."""
        search = arguments.get("search")
        limit = int(arguments.get("limit", 50))

        try:
            from sqlalchemy import or_, select
            from sqlalchemy.orm import selectinload

            from src.database.connection import async_session_maker
            from src.models.user_mapping import UserMapping

            async with async_session_maker() as session:
                # Query to get unique central users with their mappings count
                query = select(UserMapping).options(selectinload(UserMapping.service_config))

                if search:
                    query = query.where(
                        or_(
                            UserMapping.central_username.ilike(f"%{search}%"),
                            UserMapping.central_email.ilike(f"%{search}%"),
                            UserMapping.service_username.ilike(f"%{search}%"),
                        )
                    )

                result = await session.execute(query.order_by(UserMapping.central_username).limit(limit * 10))
                mappings = result.scalars().all()

                # Group by central_user_id
                users_dict = {}
                for mapping in mappings:
                    user_id = mapping.central_user_id
                    if user_id not in users_dict:
                        users_dict[user_id] = {
                            "central_user_id": user_id,
                            "central_username": mapping.central_username,
                            "central_email": mapping.central_email,
                            "mappings": [],
                        }
                    users_dict[user_id]["mappings"].append(
                        {
                            "service_name": mapping.service_config.name if mapping.service_config else "Unknown",
                            "service_type": mapping.service_config.service_type.value
                            if mapping.service_config
                            else "unknown",
                            "service_username": mapping.service_username,
                            "status": mapping.status.value if hasattr(mapping.status, "value") else str(mapping.status),
                            "role": mapping.role.value if hasattr(mapping.role, "value") else str(mapping.role),
                        }
                    )

                users_list = list(users_dict.values())[:limit]

                return {
                    "success": True,
                    "result": {
                        "count": len(users_list),
                        "search": search,
                        "users": users_list,
                    },
                }

        except Exception as e:
            return {"success": False, "error": f"Failed to get users: {str(e)}"}
