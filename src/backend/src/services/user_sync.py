"""User Synchronization Service for Authentik.

This service handles synchronizing user data between Authentik and other
homelab services, ensuring consistent user management across the system.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..adapters.authentik import AuthentikAdapter
from ..models.service_config import ServiceConfig, ServiceType
from ..models.user_mapping import MappingStatus, UserMapping
from ..services.service_registry import service_registry

logger = logging.getLogger(__name__)


class UserSyncService:
    """Service for synchronizing users between Authentik and other services."""

    def __init__(self):
        """Initialize the user sync service."""
        self.max_sync_attempts = 3
        self.sync_timeout = 300  # 5 minutes per sync operation

    async def sync_all_users(
        self, db: AsyncSession, force: bool = False, service_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """Sync all user mappings across services.

        Args:
            db: Database session
            force: If True, sync even recently synced users
            service_type: Optional service type filter

        Returns:
            Dictionary with sync results and statistics
        """
        logger.info("Starting user synchronization across all services")

        # Get all user mappings that need syncing
        query = select(UserMapping).where(UserMapping.sync_enabled is True)

        if service_type:
            query = query.join(ServiceConfig).where(ServiceConfig.service_type == ServiceType(service_type))

        result = await db.execute(query)
        mappings = result.scalars().all()

        if not force:
            # Filter to only mappings that need syncing
            mappings = [mapping for mapping in mappings if mapping.needs_sync()]

        sync_results = {
            "total_mappings": len(mappings),
            "successful_syncs": 0,
            "failed_syncs": 0,
            "skipped_syncs": 0,
            "sync_details": [],
            "started_at": datetime.utcnow(),
            "completed_at": None,
        }

        # Group mappings by service to sync efficiently
        mappings_by_service = {}
        for mapping in mappings:
            service_id = mapping.service_config_id
            if service_id not in mappings_by_service:
                mappings_by_service[service_id] = []
            mappings_by_service[service_id].append(mapping)

        # Sync each service
        for service_id, service_mappings in mappings_by_service.items():
            service_result = await self._sync_service_users(db, service_id, service_mappings, force)
            sync_results["sync_details"].append(service_result)
            sync_results["successful_syncs"] += service_result["successful_syncs"]
            sync_results["failed_syncs"] += service_result["failed_syncs"]
            sync_results["skipped_syncs"] += service_result["skipped_syncs"]

        sync_results["completed_at"] = datetime.utcnow()
        logger.info(
            f"User synchronization completed. "
            f"Success: {sync_results['successful_syncs']}, "
            f"Failed: {sync_results['failed_syncs']}, "
            f"Skipped: {sync_results['skipped_syncs']}"
        )

        return sync_results

    async def _sync_service_users(
        self, db: AsyncSession, service_id: str, mappings: List[UserMapping], force: bool = False
    ) -> Dict[str, Any]:
        """Sync users for a specific service.

        Args:
            db: Database session
            service_id: Service configuration ID
            mappings: List of user mappings for this service
            force: Force sync even if recently synced

        Returns:
            Sync results for this service
        """
        logger.info(f"Syncing {len(mappings)} user mappings for service {service_id}")

        # Get service configuration
        service_result = await db.execute(select(ServiceConfig).where(ServiceConfig.id == service_id))
        service = service_result.scalar_one_or_none()

        if not service or not service.enabled:
            logger.warning(f"Service {service_id} not found or disabled, skipping sync")
            return {
                "service_id": service_id,
                "service_name": service.name if service else "Unknown",
                "successful_syncs": 0,
                "failed_syncs": 0,
                "skipped_syncs": len(mappings),
                "error": "Service not found or disabled",
            }

        result = {
            "service_id": service_id,
            "service_name": service.name,
            "service_type": (
                service.service_type.value if hasattr(service.service_type, "value") else service.service_type
            ),
            "successful_syncs": 0,
            "failed_syncs": 0,
            "skipped_syncs": 0,
            "errors": [],
        }

        # Get the appropriate adapter
        adapter = await service_registry.create_adapter(service)
        if not adapter:
            service_type_str = (
                service.service_type.value if hasattr(service.service_type, "value") else service.service_type
            )
            error_msg = f"No adapter available for service type: {service_type_str}"
            logger.error(error_msg)
            result["failed_syncs"] = len(mappings)
            result["error"] = error_msg
            return result

        try:
            async with adapter:
                # Test connection first
                connection_test = await adapter.test_connection()
                if not connection_test.success:
                    error_msg = f"Service connection failed: {connection_test.message}"
                    logger.error(error_msg)
                    result["failed_syncs"] = len(mappings)
                    result["error"] = error_msg
                    return result

                # Sync each user mapping
                for mapping in mappings:
                    try:
                        if not force and not mapping.needs_sync():
                            result["skipped_syncs"] += 1
                            continue

                        sync_success = await self._sync_user_mapping(db, mapping, adapter)

                        if sync_success:
                            result["successful_syncs"] += 1
                            mapping.update_sync_result(True)
                        else:
                            result["failed_syncs"] += 1
                            mapping.update_sync_result(False, "Sync operation failed")

                    except Exception as e:
                        logger.error(f"Error syncing user mapping {mapping.id}: {e}")
                        result["failed_syncs"] += 1
                        result["errors"].append(f"User {mapping.central_user_id}: {str(e)}")
                        mapping.update_sync_result(False, str(e))

        except Exception as e:
            logger.error(f"Error during service sync for {service_id}: {e}")
            result["failed_syncs"] = len(mappings)
            result["error"] = str(e)

        # Commit all mapping updates
        await db.commit()

        return result

    async def _sync_user_mapping(self, db: AsyncSession, mapping: UserMapping, adapter: Any) -> bool:
        """Sync a specific user mapping.

        Args:
            db: Database session
            mapping: User mapping to sync
            adapter: Service adapter instance

        Returns:
            True if sync was successful, False otherwise
        """
        logger.debug(f"Syncing user mapping {mapping.id} for user {mapping.central_user_id}")

        try:
            # For Authentik, we sync user data from Authentik to other services
            if hasattr(adapter, "service_type") and adapter.service_type == "authentik":
                return await self._sync_from_authentik(db, mapping, adapter)
            else:
                return await self._sync_to_service(db, mapping, adapter)

        except Exception as e:
            logger.error(f"Error during user mapping sync: {e}")
            return False

    async def _sync_from_authentik(
        self, db: AsyncSession, mapping: UserMapping, authentik_adapter: AuthentikAdapter
    ) -> bool:
        """Sync user data from Authentik to update mapping.

        Args:
            db: Database session
            mapping: User mapping to sync
            authentik_adapter: Authentik adapter instance

        Returns:
            True if sync was successful
        """
        try:
            # Search for the user in Authentik
            users = await authentik_adapter.search_users(mapping.central_user_id)

            if not users:
                logger.warning(f"User {mapping.central_user_id} not found in Authentik")
                return False

            user_data = users[0]  # Take the first match

            # Update mapping with latest Authentik data
            mapping.service_user_id = str(user_data.get("pk"))
            mapping.service_username = user_data.get("username")
            mapping.service_email = user_data.get("email")

            # Update metadata with additional user info
            if not mapping.metadata:
                mapping.metadata = {}

            mapping.metadata.update(
                {
                    "authentik_user_id": user_data.get("pk"),
                    "name": user_data.get("name"),
                    "is_active": user_data.get("is_active"),
                    "is_superuser": user_data.get("is_superuser"),
                    "groups": user_data.get("groups", []),
                    "last_sync_from_authentik": datetime.utcnow().isoformat(),
                }
            )

            if mapping.status == MappingStatus.PENDING:
                mapping.status = MappingStatus.ACTIVE

            return True

        except Exception as e:
            logger.error(f"Error syncing from Authentik: {e}")
            return False

    async def _sync_to_service(self, db: AsyncSession, mapping: UserMapping, adapter: Any) -> bool:
        """Sync user data to a service.

        Args:
            db: Database session
            mapping: User mapping to sync
            adapter: Service adapter instance

        Returns:
            True if sync was successful
        """
        try:
            # This is service-specific logic
            # For now, we just verify the user exists in the target service

            if hasattr(adapter, "get_users"):
                users = await adapter.get_users()
                # Try to find the user by username or email
                user_found = any(
                    user.get("username") == mapping.service_username or user.get("email") == mapping.service_email
                    for user in users
                )

                if user_found:
                    if mapping.status == MappingStatus.PENDING:
                        mapping.status = MappingStatus.ACTIVE
                    return True
                else:
                    logger.warning(f"User {mapping.central_user_id} not found in service " f"{adapter.service_type}")
                    return False

            # If service doesn't support user enumeration, assume success
            return True

        except Exception as e:
            logger.error(f"Error syncing to service: {e}")
            return False

    async def sync_user(self, db: AsyncSession, central_user_id: str, force: bool = False) -> Dict[str, Any]:
        """Sync a specific user across all their mapped services.

        Args:
            db: Database session
            central_user_id: Central user ID to sync
            force: Force sync even if recently synced

        Returns:
            Sync results for this user
        """
        logger.info(f"Syncing user {central_user_id} across all services")

        # Get all mappings for this user
        result = await db.execute(
            select(UserMapping)
            .where(UserMapping.central_user_id == central_user_id)
            .where(UserMapping.sync_enabled is True)
        )
        mappings = result.scalars().all()

        if not mappings:
            return {"central_user_id": central_user_id, "success": False, "error": "No mappings found for user"}

        # Filter mappings that need syncing
        if not force:
            mappings = [mapping for mapping in mappings if mapping.needs_sync()]

        sync_result = {
            "central_user_id": central_user_id,
            "total_mappings": len(mappings),
            "successful_syncs": 0,
            "failed_syncs": 0,
            "sync_details": [],
        }

        for mapping in mappings:
            try:
                # Get service config
                service_result = await db.execute(
                    select(ServiceConfig).where(ServiceConfig.id == mapping.service_config_id)
                )
                service = service_result.scalar_one_or_none()

                if not service or not service.enabled:
                    sync_result["failed_syncs"] += 1
                    sync_result["sync_details"].append(
                        {
                            "service_id": mapping.service_config_id,
                            "success": False,
                            "error": "Service not found or disabled",
                        }
                    )
                    continue

                # Create adapter and sync
                adapter = await service_registry.create_adapter(service)
                if adapter:
                    async with adapter:
                        success = await self._sync_user_mapping(db, mapping, adapter)
                        if success:
                            sync_result["successful_syncs"] += 1
                            mapping.update_sync_result(True)
                        else:
                            sync_result["failed_syncs"] += 1
                            mapping.update_sync_result(False, "Sync failed")

                        sync_result["sync_details"].append(
                            {"service_id": mapping.service_config_id, "service_name": service.name, "success": success}
                        )
                else:
                    sync_result["failed_syncs"] += 1
                    sync_result["sync_details"].append(
                        {"service_id": mapping.service_config_id, "success": False, "error": "No adapter available"}
                    )

            except Exception as e:
                logger.error(f"Error syncing mapping {mapping.id}: {e}")
                sync_result["failed_syncs"] += 1
                sync_result["sync_details"].append(
                    {"service_id": mapping.service_config_id, "success": False, "error": str(e)}
                )
                mapping.update_sync_result(False, str(e))

        # Commit all updates
        await db.commit()

        sync_result["success"] = sync_result["failed_syncs"] == 0
        return sync_result

    async def discover_users_from_authentik(self, db: AsyncSession, authentik_service_id: str) -> Dict[str, Any]:
        """Discover users from Authentik and create mapping suggestions.

        Args:
            db: Database session
            authentik_service_id: ID of the Authentik service config

        Returns:
            Discovery results with user suggestions
        """
        logger.info(f"Discovering users from Authentik service {authentik_service_id}")

        # Get Authentik service config
        service_result = await db.execute(select(ServiceConfig).where(ServiceConfig.id == authentik_service_id))
        service = service_result.scalar_one_or_none()

        if not service or service.service_type != ServiceType.AUTHENTIK:
            return {"success": False, "error": "Invalid Authentik service configuration"}

        try:
            adapter = await service_registry.create_adapter(service)
            if not adapter:
                return {"success": False, "error": "Could not create Authentik adapter"}

            async with adapter:
                # Test connection
                test_result = await adapter.test_connection()
                if not test_result.success:
                    return {"success": False, "error": f"Authentik connection failed: {test_result.message}"}

                # Get all users from Authentik
                users_data = await adapter.get_users(page_size=100)
                users = users_data.get("users", [])

                # Find existing mappings
                existing_mappings = await db.execute(
                    select(UserMapping).where(UserMapping.service_config_id == authentik_service_id)
                )
                existing_users = {mapping.service_user_id for mapping in existing_mappings.scalars().all()}

                # Create suggestions for unmapped users
                suggestions = []
                for user in users:
                    user_id = str(user.get("pk"))
                    if user_id not in existing_users:
                        suggestions.append(
                            {
                                "authentik_user_id": user_id,
                                "username": user.get("username"),
                                "email": user.get("email"),
                                "name": user.get("name"),
                                "is_active": user.get("is_active"),
                                "is_superuser": user.get("is_superuser"),
                                "groups": user.get("groups", []),
                            }
                        )

                return {
                    "success": True,
                    "total_users": len(users),
                    "existing_mappings": len(existing_users),
                    "new_suggestions": len(suggestions),
                    "user_suggestions": suggestions,
                }

        except Exception as e:
            logger.error(f"Error discovering users from Authentik: {e}")
            return {"success": False, "error": str(e)}


# Global user sync service instance
user_sync_service = UserSyncService()


async def get_user_sync_service() -> UserSyncService:
    """Get the global user sync service instance."""
    return user_sync_service
