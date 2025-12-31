"""User Centralization Service for aggregating user data across services.

This service handles centralizing user information from all services
linked to a central user, providing a unified view of user data.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.service_config import ServiceConfig
from ..models.user_mapping import MappingStatus, UserMapping
from ..services.service_registry import service_registry

logger = logging.getLogger(__name__)


class CentralizedUserData:
    """Centralized representation of a user across all services."""

    def __init__(self, central_user_id: str):
        self.central_user_id = central_user_id
        self.emails: Set[str] = set()
        self.usernames: Set[str] = set()
        self.display_names: Set[str] = set()
        self.service_data: Dict[str, Dict[str, Any]] = {}
        self.active_services: List[str] = []
        self.roles: Dict[str, str] = {}
        self.last_updated = datetime.utcnow()

    def add_service_data(self, service_id: str, service_name: str, service_type: str, user_data: Dict[str, Any]):
        """Add user data from a specific service."""
        # Extract and normalize common fields
        if user_data.get("email"):
            self.emails.add(user_data["email"])

        if user_data.get("username"):
            self.usernames.add(user_data["username"])

        if user_data.get("display_name") or user_data.get("name") or user_data.get("friendly_name"):
            display_name = user_data.get("display_name") or user_data.get("name") or user_data.get("friendly_name")
            self.display_names.add(display_name)

        # Store complete service data
        self.service_data[service_id] = {
            "service_name": service_name,
            "service_type": service_type,
            "user_data": user_data,
            "updated_at": datetime.utcnow().isoformat(),
        }

        # Track active services
        if service_id not in self.active_services:
            self.active_services.append(service_id)

        # Store role information
        role = "admin" if user_data.get("is_admin") or user_data.get("is_superuser") else "user"
        self.roles[service_id] = role

    def get_primary_email(self) -> Optional[str]:
        """Get the primary email (first available)."""
        return list(self.emails)[0] if self.emails else None

    def get_primary_username(self) -> Optional[str]:
        """Get the primary username (first available)."""
        return list(self.usernames)[0] if self.usernames else None

    def get_primary_display_name(self) -> Optional[str]:
        """Get the primary display name (first available)."""
        return list(self.display_names)[0] if self.display_names else None

    def is_admin_anywhere(self) -> bool:
        """Check if user has admin role in any service."""
        return "admin" in self.roles.values()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "central_user_id": self.central_user_id,
            "emails": list(self.emails),
            "usernames": list(self.usernames),
            "display_names": list(self.display_names),
            "primary_email": self.get_primary_email(),
            "primary_username": self.get_primary_username(),
            "primary_display_name": self.get_primary_display_name(),
            "service_data": self.service_data,
            "active_services": self.active_services,
            "service_count": len(self.active_services),
            "roles": self.roles,
            "is_admin_anywhere": self.is_admin_anywhere(),
            "last_updated": self.last_updated.isoformat(),
        }


class UserCentralizationService:
    """Service for centralizing user information across all services."""

    def __init__(self):
        """Initialize the user centralization service."""
        pass

    async def get_centralized_user_data(self, db: AsyncSession, central_user_id: str) -> Optional[CentralizedUserData]:
        """Get centralized user data for a specific central user ID.

        Args:
            db: Database session
            central_user_id: Central user ID to get data for

        Returns:
            CentralizedUserData object if found, None otherwise
        """
        logger.info(f"Getting centralized data for user {central_user_id}")

        # Get all mappings for this central user
        result = await db.execute(
            select(UserMapping)
            .where(UserMapping.central_user_id == central_user_id)
            .where(UserMapping.status == MappingStatus.ACTIVE)
        )
        mappings = result.scalars().all()

        if not mappings:
            logger.warning(f"No active mappings found for user {central_user_id}")
            return None

        centralized_data = CentralizedUserData(central_user_id)

        # Process each mapping
        for mapping in mappings:
            try:
                # Get service config
                service_result = await db.execute(
                    select(ServiceConfig).where(ServiceConfig.id == mapping.service_config_id)
                )
                service = service_result.scalar_one_or_none()

                if not service:
                    logger.warning(f"Service config not found for mapping {mapping.id}")
                    continue

                # Build user data from mapping and metadata
                user_data = {
                    "user_id": mapping.service_user_id,
                    "username": mapping.service_username,
                    "email": mapping.service_email,
                    "role": mapping.role.value if hasattr(mapping.role, "value") else mapping.role,
                    "mapping_status": mapping.status.value if hasattr(mapping.status, "value") else mapping.status,
                    "last_sync_at": mapping.last_sync_at.isoformat() if mapping.last_sync_at else None,
                    "sync_enabled": mapping.sync_enabled,
                }

                # Add metadata if available
                if mapping.service_metadata:
                    user_data.update(mapping.service_metadata)

                # Add to centralized data
                centralized_data.add_service_data(
                    service_id=str(service.id),
                    service_name=service.name,
                    service_type=service.service_type.value
                    if hasattr(service.service_type, "value")
                    else service.service_type,
                    user_data=user_data,
                )

            except Exception as e:
                logger.error(f"Error processing mapping {mapping.id}: {e}")
                continue

        return centralized_data

    async def update_centralized_data_from_services(
        self, db: AsyncSession, central_user_id: str
    ) -> Optional[CentralizedUserData]:
        """Update centralized data by fetching fresh data from all services.

        Args:
            db: Database session
            central_user_id: Central user ID to update

        Returns:
            Updated CentralizedUserData object
        """
        logger.info(f"Updating centralized data from services for user {central_user_id}")

        # Get all mappings for this central user
        result = await db.execute(
            select(UserMapping)
            .where(UserMapping.central_user_id == central_user_id)
            .where(UserMapping.status == MappingStatus.ACTIVE)
        )
        mappings = result.scalars().all()

        if not mappings:
            return None

        centralized_data = CentralizedUserData(central_user_id)
        updated_mappings = []

        for mapping in mappings:
            try:
                # Get service config
                service_result = await db.execute(
                    select(ServiceConfig).where(ServiceConfig.id == mapping.service_config_id)
                )
                service = service_result.scalar_one_or_none()

                if not service or not service.enabled:
                    continue

                # Try to get fresh data from the service
                adapter = await service_registry.create_adapter(service)
                if not adapter:
                    logger.warning(f"No adapter available for service {service.name}")
                    continue

                async with adapter:
                    # Test connection first
                    test_result = await adapter.test_connection()
                    if not test_result.success:
                        logger.warning(f"Service {service.name} connection failed")
                        continue

                    # Try to get fresh user data
                    fresh_user_data = None
                    if hasattr(adapter, "get_user_by_id") and mapping.service_user_id:
                        fresh_user_data = await adapter.get_user_by_id(mapping.service_user_id)
                    elif hasattr(adapter, "search_users") and mapping.service_username:
                        users = await adapter.search_users(mapping.service_username)
                        if users:
                            fresh_user_data = users[0]

                    if fresh_user_data:
                        # Update mapping metadata with fresh data
                        mapping.service_metadata = {
                            **mapping.service_metadata,
                            "fresh_data": fresh_user_data,
                            "last_fetched": datetime.utcnow().isoformat(),
                        }

                        # Update basic fields if they've changed
                        if fresh_user_data.get("email") and fresh_user_data["email"] != mapping.service_email:
                            mapping.service_email = fresh_user_data["email"]

                        updated_mappings.append(mapping)

                        # Add to centralized data
                        centralized_data.add_service_data(
                            service_id=str(service.id),
                            service_name=service.name,
                            service_type=service.service_type.value
                            if hasattr(service.service_type, "value")
                            else service.service_type,
                            user_data=fresh_user_data,
                        )
                    else:
                        # Use existing mapping data
                        user_data = {
                            "user_id": mapping.service_user_id,
                            "username": mapping.service_username,
                            "email": mapping.service_email,
                            "role": mapping.role.value if hasattr(mapping.role, "value") else mapping.role,
                        }

                        centralized_data.add_service_data(
                            service_id=str(service.id),
                            service_name=service.name,
                            service_type=service.service_type.value
                            if hasattr(service.service_type, "value")
                            else service.service_type,
                            user_data=user_data,
                        )

            except Exception as e:
                logger.error(f"Error updating mapping {mapping.id}: {e}")
                continue

        # Commit any updated mappings
        if updated_mappings:
            await db.commit()
            logger.info(f"Updated {len(updated_mappings)} mappings with fresh data")

        return centralized_data

    async def get_all_centralized_users(self, db: AsyncSession) -> List[CentralizedUserData]:
        """Get centralized data for all users.

        Args:
            db: Database session

        Returns:
            List of CentralizedUserData objects
        """
        logger.info("Getting centralized data for all users")

        # Get all unique central user IDs
        result = await db.execute(
            select(UserMapping.central_user_id).where(UserMapping.status == MappingStatus.ACTIVE).distinct()
        )
        central_user_ids = result.scalars().all()

        centralized_users = []
        for central_user_id in central_user_ids:
            try:
                centralized_data = await self.get_centralized_user_data(db, central_user_id)
                if centralized_data:
                    centralized_users.append(centralized_data)
            except Exception as e:
                logger.error(f"Error getting centralized data for user {central_user_id}: {e}")
                continue

        return centralized_users

    async def sync_centralized_user_metadata(self, db: AsyncSession, central_user_id: str) -> Dict[str, Any]:
        """Sync and update metadata for a centralized user.

        Args:
            db: Database session
            central_user_id: Central user ID to sync

        Returns:
            Sync results
        """
        logger.info(f"Syncing centralized metadata for user {central_user_id}")

        try:
            # Update centralized data from services
            centralized_data = await self.update_centralized_data_from_services(db, central_user_id)

            if not centralized_data:
                return {"success": False, "error": "No active mappings found for user"}

            # Store centralized metadata in each mapping
            result = await db.execute(
                select(UserMapping)
                .where(UserMapping.central_user_id == central_user_id)
                .where(UserMapping.status == MappingStatus.ACTIVE)
            )
            mappings = result.scalars().all()

            centralized_dict = centralized_data.to_dict()

            for mapping in mappings:
                # Add centralized data to metadata
                mapping.service_metadata = {
                    **mapping.service_metadata,
                    "centralized_data": centralized_dict,
                    "centralized_updated_at": datetime.utcnow().isoformat(),
                }

            await db.commit()

            return {
                "success": True,
                "central_user_id": central_user_id,
                "services_count": len(centralized_data.active_services),
                "emails_count": len(centralized_data.emails),
                "usernames_count": len(centralized_data.usernames),
                "centralized_data": centralized_dict,
            }

        except Exception as e:
            logger.error(f"Error syncing centralized metadata for user {central_user_id}: {e}")
            return {"success": False, "error": str(e)}


# Global user centralization service instance
user_centralization_service = UserCentralizationService()


async def get_user_centralization_service() -> UserCentralizationService:
    """Get the global user centralization service instance."""
    return user_centralization_service
