"""Automatic User Mapping Detection Service.

This service automatically detects and suggests user mappings between
different homelab services based on common identifiers like email,
username, and other user attributes.
"""

import difflib
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.service_config import ServiceConfig, ServiceType
from ..models.user_mapping import MappingStatus, UserMapping, UserRole
from ..services.service_registry import service_registry

logger = logging.getLogger(__name__)


@dataclass
class UserSuggestion:
    """A suggested user mapping between services."""

    central_user_id: str
    service_config_id: str
    service_user_id: Optional[str] = None
    service_username: Optional[str] = None
    service_email: Optional[str] = None
    confidence_score: float = 0.0
    matching_attributes: List[str] = None
    role: str = "user"
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.matching_attributes is None:
            self.matching_attributes = []
        if self.metadata is None:
            self.metadata = {}


class UserMappingDetector:
    """Service for automatically detecting user mappings across services."""

    def __init__(self):
        """Initialize the user mapping detector."""
        self.min_confidence_score = 0.5  # Minimum confidence for auto-suggestions
        self.fuzzy_match_threshold = 0.8  # Threshold for fuzzy string matching

    async def detect_all_mappings(self, db: AsyncSession, authentik_service_id: str) -> Dict[str, Any]:
        """Detect user mappings across all services using Authentik as the source.

        Args:
            db: Database session
            authentik_service_id: ID of the Authentik service to use as source

        Returns:
            Dictionary with detection results and suggestions
        """
        logger.info("Starting automatic user mapping detection")

        # Get Authentik service and users
        authentik_result = await self._get_authentik_users(db, authentik_service_id)
        if not authentik_result["success"]:
            return authentik_result

        authentik_users = authentik_result["users"]

        # Get all other enabled services
        services_result = await db.execute(
            select(ServiceConfig).where(ServiceConfig.enabled is True).where(ServiceConfig.id != authentik_service_id)
        )
        other_services = services_result.scalars().all()

        detection_results = {
            "authentik_service_id": authentik_service_id,
            "total_authentik_users": len(authentik_users),
            "services_scanned": len(other_services),
            "suggestions": [],
            "high_confidence_suggestions": [],
            "medium_confidence_suggestions": [],
            "low_confidence_suggestions": [],
            "errors": [],
            "started_at": datetime.utcnow(),
            "completed_at": None,
        }

        # Process each service
        for service in other_services:
            try:
                service_suggestions = await self._detect_mappings_for_service(db, service, authentik_users)
                detection_results["suggestions"].extend(service_suggestions)

                # Categorize by confidence
                for suggestion in service_suggestions:
                    if suggestion.confidence_score >= 0.9:
                        detection_results["high_confidence_suggestions"].append(suggestion)
                    elif suggestion.confidence_score >= 0.7:
                        detection_results["medium_confidence_suggestions"].append(suggestion)
                    else:
                        detection_results["low_confidence_suggestions"].append(suggestion)

            except Exception as e:
                error_msg = f"Error detecting mappings for service {service.name}: {str(e)}"
                logger.error(error_msg)
                detection_results["errors"].append(error_msg)

        detection_results["completed_at"] = datetime.utcnow()
        detection_results["total_suggestions"] = len(detection_results["suggestions"])

        logger.info(
            f"User mapping detection completed. "
            f"Found {detection_results['total_suggestions']} suggestions "
            f"across {len(other_services)} services"
        )

        return detection_results

    async def auto_detect_all_mappings(self, db: AsyncSession) -> Dict[str, Any]:
        """Automatically detect user mappings across all configured services.

        This method scans all enabled services and detects potential user mappings
        by comparing users across all services using email, username, and name matching.
        Uses Union-Find clustering to group users transitively.

        Args:
            db: Database session

        Returns:
            Dict containing detection results and suggestions
        """
        logger.info("Starting automatic user mapping detection across all services")

        # Services that don't have user management (skip them)
        SERVICES_WITHOUT_USERS = {"ollama"}

        # Get all enabled services
        services_result = await db.execute(select(ServiceConfig).where(ServiceConfig.enabled is True))
        all_services_raw = services_result.scalars().all()

        # Filter out services without user management
        all_services = [
            s
            for s in all_services_raw
            if (s.service_type.value if hasattr(s.service_type, "value") else s.service_type).lower()
            not in SERVICES_WITHOUT_USERS
        ]
        logger.debug(f"Filtered out {len(all_services_raw) - len(all_services)} services without user management")

        if len(all_services) < 2:
            return {
                "total_services": len(all_services),
                "services_scanned": 0,
                "total_suggestions": 0,
                "suggestions": [],
                "high_confidence_suggestions": [],
                "medium_confidence_suggestions": [],
                "low_confidence_suggestions": [],
                "errors": ["Need at least 2 enabled services to detect mappings"],
                "started_at": datetime.utcnow(),
                "completed_at": datetime.utcnow(),
            }

        detection_results = {
            "total_services": len(all_services),
            "services_scanned": 0,
            "suggestions": [],
            "high_confidence_suggestions": [],
            "medium_confidence_suggestions": [],
            "low_confidence_suggestions": [],
            "errors": [],
            "service_combinations": [],
            "started_at": datetime.utcnow(),
            "completed_at": None,
        }

        # Get all users from all services
        services_with_users = {}

        for service in all_services:
            try:
                service_users = await self._get_all_service_users(service)
                if service_users:
                    services_with_users[service.id] = {"service": service, "users": service_users}
                    detection_results["services_scanned"] += 1
                    logger.info(f"Found {len(service_users)} users in service {service.name}")
                else:
                    logger.warning(f"No users found in service {service.name}")

            except Exception as e:
                error_msg = f"Error getting users from service {service.name}: {str(e)}"
                logger.error(error_msg)
                detection_results["errors"].append(error_msg)

        # Build a mapping of all users with unique keys
        # Key format: "service_id:user_id"
        # Use primary ID from various field names (id, user_id, username as fallback)
        all_users_map: Dict[str, Dict[str, Any]] = {}
        for service_id, service_data in services_with_users.items():
            seen_ids = set()
            for user in service_data["users"]:
                # Get user ID from various possible fields (Plex uses 'id', Tautulli uses 'user_id')
                user_id = str(user.get("id") or user.get("user_id") or user.get("username") or "")
                if not user_id or user_id in seen_ids:
                    continue
                seen_ids.add(user_id)
                key = f"{service_id}:{user_id}"
                all_users_map[key] = {
                    "service": service_data["service"],
                    "user": user,
                    "service_id": service_id,
                    "user_id": user_id,
                }

        # Union-Find data structure for clustering
        parent: Dict[str, str] = {key: key for key in all_users_map.keys()}

        def find(x: str) -> str:
            if parent[x] != x:
                parent[x] = find(parent[x])
            return parent[x]

        def union(x: str, y: str):
            if x not in parent:
                logger.error(f"union() called with x={x} not in parent")
                raise KeyError(f"Key not in parent: {x}")
            if y not in parent:
                logger.error(f"union() called with y={y} not in parent")
                raise KeyError(f"Key not in parent: {y}")
            px, py = find(x), find(y)
            if px != py:
                parent[px] = py

        # Compare users across all service pairs and build clusters
        service_ids = list(services_with_users.keys())

        for i, service_id_1 in enumerate(service_ids):
            for service_id_2 in service_ids[i + 1 :]:
                try:
                    service_1_data = services_with_users[service_id_1]
                    service_2_data = services_with_users[service_id_2]

                    combination = {
                        "service_1": service_1_data["service"].name,
                        "service_2": service_2_data["service"].name,
                        "suggestions_found": 0,
                    }

                    match_count = 0

                    # Compare all users between the two services
                    for user_1 in service_1_data["users"]:
                        # Use same ID extraction logic as all_users_map
                        user_1_id = str(user_1.get("id") or user_1.get("user_id") or user_1.get("username") or "")
                        key_1 = f"{service_id_1}:{user_1_id}"

                        # Skip if this user wasn't added to the map (filtered as duplicate)
                        if key_1 not in all_users_map:
                            continue

                        for user_2 in service_2_data["users"]:
                            # Use same ID extraction logic as all_users_map
                            user_2_id = str(user_2.get("id") or user_2.get("user_id") or user_2.get("username") or "")
                            key_2 = f"{service_id_2}:{user_2_id}"

                            # Skip if this user wasn't added to the map (filtered as duplicate)
                            if key_2 not in all_users_map:
                                continue

                            score, matching_attrs = self._calculate_user_match_score(user_1, user_2)

                            if score >= self.min_confidence_score:
                                # For services that share the same ID system (Plex/Tautulli),
                                # only union if IDs match to prevent false positives from name-only matches
                                user_1_primary_id = user_1.get("id") or user_1.get("user_id")
                                user_2_primary_id = user_2.get("id") or user_2.get("user_id")

                                # Check if both services use Plex-style IDs (large integers > 1000000)
                                # Plex/Tautulli use the same large numeric IDs
                                # Overseerr uses small sequential IDs (1, 2, 3...)
                                both_use_plex_ids = (
                                    user_1_primary_id
                                    and user_2_primary_id
                                    and isinstance(user_1_primary_id, int)
                                    and isinstance(user_2_primary_id, int)
                                    and user_1_primary_id > 1000000
                                    and user_2_primary_id > 1000000
                                )

                                if both_use_plex_ids and user_1_primary_id != user_2_primary_id:
                                    # Both have Plex-style IDs but they don't match - skip this union
                                    continue

                                # Union these two users into the same cluster
                                union(key_1, key_2)
                                match_count += 1

                    combination["suggestions_found"] = match_count
                    detection_results["service_combinations"].append(combination)

                    logger.info(
                        f"Found {match_count} matches between "
                        f"{service_1_data['service'].name} and {service_2_data['service'].name}"
                    )

                except Exception as e:
                    error_msg = (
                        f"Error comparing {service_1_data['service'].name} "
                        f"and {service_2_data['service'].name}: {str(e)}"
                    )
                    logger.error(error_msg)
                    detection_results["errors"].append(error_msg)

        # Group users by cluster
        clusters: Dict[str, List[str]] = {}
        for key in all_users_map.keys():
            root = find(key)
            if root not in clusters:
                clusters[root] = []
            clusters[root].append(key)

        # Get existing mappings to avoid duplicates
        existing_mappings = {}
        for service_id in services_with_users.keys():
            existing_mappings[service_id] = await self._get_existing_mappings(db, service_id)

        # Generate suggestions from clusters (only clusters with 2+ users from different services)
        for cluster_root, cluster_members in clusters.items():
            if len(cluster_members) < 2:
                continue

            # Check if cluster spans multiple services
            services_in_cluster = set()
            for key in cluster_members:
                service_id = key.split(":")[0]
                services_in_cluster.add(service_id)

            if len(services_in_cluster) < 2:
                continue

            # Determine the best central_user_id for this cluster
            # Priority: email > username/friendly_name (never use numeric IDs)
            central_user_id = None
            best_email = None
            best_username = None

            for key in cluster_members:
                user_data = all_users_map[key]["user"]
                email = user_data.get("email")
                # Get username from various fields
                username = (
                    user_data.get("username")
                    or user_data.get("login")
                    or user_data.get("friendly_name")
                    or user_data.get("name")
                    or user_data.get("display_name")
                )

                if email and not best_email:
                    best_email = email.lower().strip()
                if username and not best_username:
                    # Make sure username is not a numeric ID
                    username_str = str(username).strip()
                    if username_str and not username_str.isdigit():
                        best_username = username_str.lower()

            # Use email first, then username, fallback to a generated ID
            central_user_id = best_email or best_username
            if not central_user_id:
                # Generate a readable ID from the first available username
                for key in cluster_members:
                    user_data = all_users_map[key]["user"]
                    fallback_name = user_data.get("friendly_name") or user_data.get("name") or user_data.get("username")
                    if fallback_name:
                        central_user_id = str(fallback_name).lower().strip()
                        break
            if not central_user_id:
                central_user_id = f"user_{cluster_root.split(':')[-1]}"

            # For each service, keep only the best matching user (highest score)
            # This prevents duplicates when multiple users from same service match by name
            best_user_per_service: Dict[str, Tuple[str, float]] = {}  # service_id -> (key, score)

            for key in cluster_members:
                user_info = all_users_map[key]
                service_id = user_info["service_id"]
                user = user_info["user"]

                # Calculate score for this user
                max_score = 0.0
                for other_key in cluster_members:
                    if other_key == key:
                        continue
                    other_user = all_users_map[other_key]["user"]
                    score, _ = self._calculate_user_match_score(user, other_user)
                    if score > max_score:
                        max_score = score

                # Keep only the best user per service
                if service_id not in best_user_per_service or max_score > best_user_per_service[service_id][1]:
                    best_user_per_service[service_id] = (key, max_score)

            # Create suggestions only for the best user per service
            for key in [k for k, _ in best_user_per_service.values()]:
                user_info = all_users_map[key]
                service = user_info["service"]
                user = user_info["user"]
                user_id = user_info["user_id"]

                # Skip if already has a mapping
                if user_id in existing_mappings.get(service.id, {}):
                    continue

                # Calculate score by comparing with other users in cluster
                max_score = 0.0
                all_matching_attrs = set()

                for other_key in cluster_members:
                    if other_key == key:
                        continue
                    other_user = all_users_map[other_key]["user"]
                    score, attrs = self._calculate_user_match_score(user, other_user)
                    if score > max_score:
                        max_score = score
                    all_matching_attrs.update(attrs)

                suggestion = UserSuggestion(
                    central_user_id=central_user_id,
                    service_config_id=service.id,
                    service_user_id=user_id,
                    service_username=user.get("username", user.get("login", user.get("friendly_name"))),
                    service_email=user.get("email"),
                    confidence_score=max_score,
                    matching_attributes=list(all_matching_attrs),
                    role=self._determine_user_role_from_service_user(user),
                    metadata={
                        "detection_method": "cluster_analysis",
                        "cluster_size": len(cluster_members),
                        "services_in_cluster": list(services_in_cluster),
                        "target_service": service.name,
                        "target_user": user,
                        "detected_at": datetime.utcnow().isoformat(),
                    },
                )

                detection_results["suggestions"].append(suggestion)

                # Categorize by confidence
                if suggestion.confidence_score >= 0.9:
                    detection_results["high_confidence_suggestions"].append(suggestion)
                elif suggestion.confidence_score >= 0.7:
                    detection_results["medium_confidence_suggestions"].append(suggestion)
                else:
                    detection_results["low_confidence_suggestions"].append(suggestion)

        detection_results["completed_at"] = datetime.utcnow()
        detection_results["total_suggestions"] = len(detection_results["suggestions"])

        logger.info(
            f"Automatic user mapping detection completed. "
            f"Found {detection_results['total_suggestions']} suggestions "
            f"across {detection_results['services_scanned']} services"
        )

        return detection_results

    async def _get_authentik_users(self, db: AsyncSession, authentik_service_id: str) -> Dict[str, Any]:
        """Get users from Authentik service.

        Args:
            db: Database session
            authentik_service_id: Authentik service ID

        Returns:
            Result with users list or error
        """
        # Get Authentik service config
        service_result = await db.execute(select(ServiceConfig).where(ServiceConfig.id == authentik_service_id))
        service = service_result.scalar_one_or_none()

        if not service or service.service_type != ServiceType.AUTHENTIK:
            return {"success": False, "error": "Invalid or missing Authentik service configuration"}

        try:
            adapter = await service_registry.create_adapter(service)
            if not adapter:
                return {"success": False, "error": "Could not create Authentik adapter"}

            async with adapter:
                # Test connection first
                test_result = await adapter.test_connection()
                if not test_result.success:
                    return {"success": False, "error": f"Authentik connection failed: {test_result.message}"}

                # Get all users
                users_data = await adapter.get_users(page_size=200)
                users = users_data.get("users", [])

                return {"success": True, "users": users}

        except Exception as e:
            logger.error(f"Error getting Authentik users: {e}")
            return {"success": False, "error": str(e)}

    async def _detect_mappings_for_service(
        self, db: AsyncSession, service: ServiceConfig, authentik_users: List[Dict[str, Any]]
    ) -> List[UserSuggestion]:
        """Detect user mappings for a specific service.

        Args:
            db: Database session
            service: Service configuration
            authentik_users: List of users from Authentik

        Returns:
            List of user suggestions for this service
        """
        logger.debug(f"Detecting mappings for service: {service.name}")

        suggestions = []

        # Skip if we don't have an adapter for this service type
        service_type_str = (
            service.service_type.value if hasattr(service.service_type, "value") else service.service_type
        )
        if not service_registry.has_adapter(service_type_str):
            logger.warning(f"No adapter available for service type: {service_type_str}")
            return suggestions

        try:
            adapter = await service_registry.create_adapter(service)
            if not adapter:
                logger.warning(f"Could not create adapter for service: {service.name}")
                return suggestions

            async with adapter:
                # Test connection
                test_result = await adapter.test_connection()
                if not test_result.success:
                    logger.warning(f"Service {service.name} connection failed: {test_result.message}")
                    return suggestions

                # Get existing mappings to avoid duplicates
                existing_mappings_result = await db.execute(
                    select(UserMapping).where(UserMapping.service_config_id == service.id)
                )
                existing_mappings = {
                    mapping.central_user_id: mapping for mapping in existing_mappings_result.scalars().all()
                }

                # Get service users if adapter supports it
                service_users = await self._get_service_users(adapter)

                # Compare Authentik users with service users
                for authentik_user in authentik_users:
                    central_user_id = authentik_user.get("username")
                    if not central_user_id:
                        continue

                    # Skip if mapping already exists
                    if central_user_id in existing_mappings:
                        continue

                    # Find the best match in the service
                    best_match = await self._find_best_user_match(authentik_user, service_users, service)

                    if best_match:
                        suggestions.append(best_match)

        except Exception as e:
            logger.error(f"Error detecting mappings for service {service.name}: {e}")

        return suggestions

    async def _get_service_users(self, adapter: Any) -> List[Dict[str, Any]]:
        """Get users from a service adapter.

        Args:
            adapter: Service adapter instance

        Returns:
            List of users from the service
        """
        try:
            if hasattr(adapter, "get_users"):
                users = await adapter.get_users()
                if isinstance(users, list):
                    return users
                elif isinstance(users, dict) and "users" in users:
                    return users["users"]

            # If no user enumeration is available, return empty list
            return []

        except Exception as e:
            logger.warning(f"Could not get users from service: {e}")
            return []

    async def _get_all_service_users(self, service: ServiceConfig) -> List[Dict[str, Any]]:
        """Get all users from a specific service.

        Args:
            service: Service configuration

        Returns:
            List of users from the service
        """
        try:
            adapter = await service_registry.create_adapter(service)
            if not adapter:
                logger.warning(f"Could not create adapter for service: {service.name}")
                return []

            async with adapter:
                # Test connection
                test_result = await adapter.test_connection()
                if not test_result.success:
                    logger.warning(f"Service {service.name} connection failed: {test_result.message}")
                    return []

                return await self._get_service_users(adapter)

        except Exception as e:
            logger.error(f"Error getting users from service {service.name}: {e}")
            return []

    async def _compare_service_users(
        self,
        db: AsyncSession,
        service_1: ServiceConfig,
        users_1: List[Dict[str, Any]],
        service_2: ServiceConfig,
        users_2: List[Dict[str, Any]],
        already_matched_users: Dict[str, Dict[str, Any]] = None,
    ) -> Tuple[List[UserSuggestion], Dict[str, Dict[str, Any]]]:
        """Compare users between two services to find potential mappings.

        Args:
            db: Database session
            service_1: First service configuration
            users_1: Users from first service
            service_2: Second service configuration
            users_2: Users from second service
            already_matched_users: Dict tracking users already matched (central_user_id -> service_ids set)

        Returns:
            Tuple of (list of user suggestions, updated already_matched_users dict)
        """
        suggestions = []
        if already_matched_users is None:
            already_matched_users = {}

        # Get existing mappings to avoid duplicates
        existing_mappings_1 = await self._get_existing_mappings(db, service_1.id)
        existing_mappings_2 = await self._get_existing_mappings(db, service_2.id)

        for user_1 in users_1:
            user_1_id = str(user_1.get("id", user_1.get("user_id", user_1.get("username"))))

            # Skip if this user already has a mapping
            if user_1_id in existing_mappings_1:
                continue

            best_match_data = None
            best_score = 0.0

            for user_2 in users_2:
                user_2_id = str(user_2.get("id", user_2.get("user_id", user_2.get("username"))))

                # Skip if this user already has a mapping
                if user_2_id in existing_mappings_2:
                    continue

                # Calculate match score
                score, matching_attrs = self._calculate_user_match_score(user_1, user_2)

                if score > best_score and score >= self.min_confidence_score:
                    best_score = score
                    best_match_data = {
                        "score": score,
                        "matching_attrs": matching_attrs,
                        "user_1": user_1,
                        "user_2": user_2,
                        "user_1_id": user_1_id,
                        "user_2_id": user_2_id,
                    }

            # Create suggestions for the best match found
            if best_match_data and best_score >= self.min_confidence_score:
                data = best_match_data

                # Use the more reliable identifier as central_user_id
                # Prefer email, then username, then ID
                central_user_id = (
                    data["user_1"].get("email")
                    or data["user_2"].get("email")
                    or data["user_1"].get("username")
                    or data["user_1"].get("login")
                    or data["user_2"].get("username")
                    or data["user_2"].get("login")
                    or str(data["user_1_id"])
                    or str(data["user_2_id"])
                )

                # Debug logging
                logger.info(
                    f"Found match: central_user_id={central_user_id}, "
                    f"user_1({service_1.name})={data['user_1'].get('username')}, "
                    f"user_2({service_2.name})={data['user_2'].get('username')}, "
                    f"score={data['score']}"
                )

                # Track which services we've already created suggestions for this user
                if central_user_id not in already_matched_users:
                    already_matched_users[central_user_id] = {"service_ids": set()}

                # Create suggestion for service_1 only if not already matched
                if service_1.id not in already_matched_users[central_user_id]["service_ids"]:
                    suggestion_1 = UserSuggestion(
                        central_user_id=central_user_id,
                        service_config_id=service_1.id,
                        service_user_id=str(data["user_1_id"]),
                        service_username=data["user_1"].get("username", data["user_1"].get("login")),
                        service_email=data["user_1"].get("email"),
                        confidence_score=data["score"],
                        matching_attributes=data["matching_attrs"],
                        role=self._determine_user_role_from_service_user(data["user_1"]),
                        metadata={
                            "detection_method": "cross_service_comparison",
                            "source_service": service_2.name,
                            "target_service": service_1.name,
                            "source_user": data["user_2"],
                            "target_user": data["user_1"],
                            "detected_at": datetime.utcnow().isoformat(),
                        },
                    )
                    suggestions.append(suggestion_1)
                    already_matched_users[central_user_id]["service_ids"].add(service_1.id)

                # Create suggestion for service_2 only if not already matched
                if service_2.id not in already_matched_users[central_user_id]["service_ids"]:
                    suggestion_2 = UserSuggestion(
                        central_user_id=central_user_id,
                        service_config_id=service_2.id,
                        service_user_id=str(data["user_2_id"]),
                        service_username=data["user_2"].get("username", data["user_2"].get("login")),
                        service_email=data["user_2"].get("email"),
                        confidence_score=data["score"],
                        matching_attributes=data["matching_attrs"],
                        role=self._determine_user_role_from_service_user(data["user_2"]),
                        metadata={
                            "detection_method": "cross_service_comparison",
                            "source_service": service_1.name,
                            "target_service": service_2.name,
                            "source_user": data["user_1"],
                            "target_user": data["user_2"],
                            "detected_at": datetime.utcnow().isoformat(),
                        },
                    )
                    suggestions.append(suggestion_2)
                    already_matched_users[central_user_id]["service_ids"].add(service_2.id)

        return suggestions, already_matched_users

    async def _get_existing_mappings(self, db: AsyncSession, service_id: str) -> Dict[str, UserMapping]:
        """Get existing mappings for a service.

        Args:
            db: Database session
            service_id: Service ID

        Returns:
            Dict mapping service_user_id to UserMapping
        """
        result = await db.execute(select(UserMapping).where(UserMapping.service_config_id == service_id))
        mappings = result.scalars().all()

        return {mapping.service_user_id: mapping for mapping in mappings if mapping.service_user_id}

    def _determine_user_role_from_service_user(self, service_user: Dict[str, Any]) -> str:
        """Determine user role from service user data.

        Args:
            service_user: User data from service

        Returns:
            String representing the user role
        """
        if service_user.get("is_superuser") or service_user.get("is_admin"):
            return "admin"
        elif service_user.get("is_staff") or service_user.get("is_moderator"):
            return "moderator"
        else:
            return "user"

    async def _find_best_user_match(
        self, authentik_user: Dict[str, Any], service_users: List[Dict[str, Any]], service: ServiceConfig
    ) -> Optional[UserSuggestion]:
        """Find the best matching user in a service for an Authentik user.

        Args:
            authentik_user: User data from Authentik
            service_users: List of users from the target service
            service: Service configuration

        Returns:
            UserSuggestion if a good match is found, None otherwise
        """
        if not service_users:
            # If we can't enumerate users, create a suggestion based on Authentik data
            return self._create_suggestion_from_authentik(authentik_user, service)

        authentik_username = authentik_user.get("username", "").lower()
        authentik_user.get("email", "").lower()
        authentik_user.get("name", "").lower()

        best_match = None
        best_score = 0.0

        for service_user in service_users:
            score, matching_attrs = self._calculate_user_match_score(authentik_user, service_user)

            if score > best_score and score >= self.min_confidence_score:
                best_score = score
                best_match = UserSuggestion(
                    central_user_id=authentik_username,
                    service_config_id=service.id,
                    service_user_id=str(service_user.get("id", service_user.get("user_id"))),
                    service_username=service_user.get("username", service_user.get("login")),
                    service_email=service_user.get("email"),
                    confidence_score=score,
                    matching_attributes=matching_attrs,
                    role=self._determine_user_role(authentik_user),
                    metadata={
                        "detection_method": "user_enumeration",
                        "service_user_data": service_user,
                        "detected_at": datetime.utcnow().isoformat(),
                    },
                )

        return best_match

    def _create_suggestion_from_authentik(
        self, authentik_user: Dict[str, Any], service: ServiceConfig
    ) -> UserSuggestion:
        """Create a user suggestion based only on Authentik data.

        Args:
            authentik_user: User data from Authentik
            service: Target service configuration

        Returns:
            UserSuggestion with medium confidence
        """
        return UserSuggestion(
            central_user_id=authentik_user.get("username"),
            service_config_id=service.id,
            service_username=authentik_user.get("username"),
            service_email=authentik_user.get("email"),
            confidence_score=0.6,  # Medium confidence since we can't verify
            matching_attributes=["username", "email"],
            role=self._determine_user_role(authentik_user),
            metadata={
                "detection_method": "authentik_only",
                "note": "Service does not support user enumeration",
                "detected_at": datetime.utcnow().isoformat(),
            },
        )

    def _calculate_user_match_score(self, user_1: Dict[str, Any], user_2: Dict[str, Any]) -> Tuple[float, List[str]]:
        """Calculate match score between two users from different services.

        Args:
            user_1: User from first service
            user_2: User from second service

        Returns:
            Tuple of (score, list of matching attributes)
        """
        score = 0.0
        matching_attrs = []

        # Get IDs for exact ID matching (highest priority)
        user_1_id = user_1.get("id", user_1.get("user_id"))
        user_2_id = user_2.get("id", user_2.get("user_id"))

        # Get usernames - handle different field names across services
        user_1_username = (
            str(user_1.get("username", user_1.get("login", ""))).lower()
            if user_1.get("username", user_1.get("login"))
            else ""
        )
        user_2_username = (
            str(user_2.get("username", user_2.get("login", ""))).lower()
            if user_2.get("username", user_2.get("login"))
            else ""
        )

        # Get emails
        user_1_email = str(user_1.get("email", "")).lower() if user_1.get("email") else ""
        user_2_email = str(user_2.get("email", "")).lower() if user_2.get("email") else ""

        # Get display names / friendly names (separate from username)
        user_1_friendly = (
            str(user_1.get("friendly_name", user_1.get("name", ""))).lower()
            if user_1.get("friendly_name", user_1.get("name"))
            else ""
        )
        user_2_friendly = (
            str(user_2.get("friendly_name", user_2.get("name", ""))).lower()
            if user_2.get("friendly_name", user_2.get("name"))
            else ""
        )

        # 1. Exact ID match (highest weight) - very reliable for Plex/Tautulli
        if user_1_id is not None and user_2_id is not None and user_1_id == user_2_id and user_1_id != 0:
            score += 0.8
            matching_attrs.append("id_exact")

        # 2. Exact username match (high weight)
        if user_1_username and user_2_username and user_1_username == user_2_username:
            score += 0.5
            matching_attrs.append("username_exact")

        # 3. Exact email match (high weight)
        if user_1_email and user_2_email and user_1_email == user_2_email:
            score += 0.5
            matching_attrs.append("email_exact")

        # 4. Exact friendly_name match (medium weight) - useful for Plex/Tautulli
        if user_1_friendly and user_2_friendly and user_1_friendly == user_2_friendly:
            score += 0.4
            matching_attrs.append("friendly_name_exact")

        # 5. Username matches friendly_name (cross-field matching)
        if user_1_username and user_2_friendly and user_1_username == user_2_friendly:
            score += 0.4
            matching_attrs.append("username_friendly_match")
        elif user_2_username and user_1_friendly and user_2_username == user_1_friendly:
            score += 0.4
            matching_attrs.append("username_friendly_match")

        # 6. Fuzzy username match
        if user_1_username and user_2_username and user_1_username != user_2_username:
            username_similarity = difflib.SequenceMatcher(None, user_1_username, user_2_username).ratio()
            if username_similarity >= self.fuzzy_match_threshold:
                score += 0.3 * username_similarity
                matching_attrs.append("username_fuzzy")

        # 7. Fuzzy email match (if different from exact)
        if user_1_email and user_2_email and user_1_email != user_2_email:
            email_similarity = difflib.SequenceMatcher(None, user_1_email, user_2_email).ratio()
            if email_similarity >= self.fuzzy_match_threshold:
                score += 0.3 * email_similarity
                matching_attrs.append("email_fuzzy")

        # 8. Fuzzy friendly_name match
        if user_1_friendly and user_2_friendly and user_1_friendly != user_2_friendly:
            name_similarity = difflib.SequenceMatcher(None, user_1_friendly, user_2_friendly).ratio()
            if name_similarity >= self.fuzzy_match_threshold:
                score += 0.2 * name_similarity
                matching_attrs.append("name_fuzzy")

        return min(score, 1.0), matching_attrs

    def _determine_user_role(self, authentik_user: Dict[str, Any]) -> str:
        """Determine user role based on Authentik user data.

        Args:
            authentik_user: User data from Authentik

        Returns:
            String representing the user role
        """
        if authentik_user.get("is_superuser"):
            return "admin"
        elif authentik_user.get("is_staff"):
            return "moderator"
        else:
            return "user"

    async def create_mappings_from_suggestions(
        self, db: AsyncSession, suggestions: List[Dict[str, Any]], auto_approve_high_confidence: bool = False
    ) -> Dict[str, Any]:
        """Create user mappings from approved suggestions.

        Args:
            db: Database session
            suggestions: List of suggestion dictionaries to create mappings for
            auto_approve_high_confidence: Auto-approve suggestions with high confidence

        Returns:
            Results of mapping creation
        """
        logger.info(f"Creating user mappings from {len(suggestions)} suggestions")

        results = {
            "total_suggestions": len(suggestions),
            "created_mappings": 0,
            "skipped_mappings": 0,
            "errors": [],
            "created_mapping_ids": [],
        }

        for suggestion_data in suggestions:
            try:
                logger.info(f"Processing suggestion: {suggestion_data}")

                # Extract and validate required fields
                central_user_id = suggestion_data.get("central_user_id")
                service_config_id = suggestion_data.get("service_config_id")
                service_user_id = suggestion_data.get("service_user_id")

                logger.info(
                    f"Extracted fields - central_user_id: {central_user_id}, "
                    f"service_config_id: {service_config_id}, "
                    f"service_user_id: {service_user_id}"
                )

                if not central_user_id or not service_config_id:
                    error_msg = (
                        f"Missing required fields: central_user_id={central_user_id}, "
                        f"service_config_id={service_config_id}"
                    )
                    logger.error(error_msg)
                    raise ValueError(error_msg)

                # Check if mapping already exists
                from sqlalchemy import and_, select

                existing_result = await db.execute(
                    select(UserMapping).where(
                        and_(
                            UserMapping.central_user_id == central_user_id,
                            UserMapping.service_config_id == service_config_id,
                        )
                    )
                )
                existing_mapping = existing_result.scalar_one_or_none()
                if existing_mapping:
                    error_msg = (
                        f"Mapping already exists for central_user_id={central_user_id}, "
                        f"service_config_id={service_config_id}"
                    )
                    logger.warning(error_msg)
                    results["errors"].append(error_msg)
                    results["skipped_mappings"] += 1
                    continue

                # Convert service_user_id to string if needed
                if service_user_id is not None:
                    service_user_id = str(service_user_id)

                # Determine role from suggestion
                role_mapping = {
                    "admin": UserRole.ADMIN,
                    "user": UserRole.USER,
                    "moderator": UserRole.MODERATOR,
                    "viewer": UserRole.VIEWER,
                }
                role_str = suggestion_data.get("role", "user").lower()
                role = role_mapping.get(role_str, UserRole.USER)

                # Extract service_username from multiple possible sources
                metadata = suggestion_data.get("metadata", {})
                target_user = metadata.get("target_user", {})
                source_user = metadata.get("source_user", {})

                service_username = (
                    suggestion_data.get("service_username")
                    or target_user.get("username")
                    or target_user.get("login")
                    or target_user.get("name")
                    or target_user.get("friendly_name")
                    or source_user.get("username")
                    or source_user.get("name")
                    or central_user_id
                    or f"user_{service_user_id}"
                )

                service_email = (
                    suggestion_data.get("service_email") or target_user.get("email") or source_user.get("email")
                )

                logger.info(f"About to create mapping with role: {role}, " f"service_username: {service_username}")

                # Create UserMapping from suggestion - always ACTIVE
                # (no more pending status per user request)
                # Ensure we have a valid central_username
                central_username = service_username

                logger.info(f"Using central_username: {central_username}")

                mapping = UserMapping(
                    central_user_id=central_user_id,
                    central_username=central_username,
                    central_email=service_email,
                    service_config_id=service_config_id,
                    service_user_id=service_user_id,
                    service_username=service_username,
                    service_email=service_email,
                    role=role,
                    status=MappingStatus.ACTIVE,  # Always active as requested by user
                    sync_enabled=True,
                    metadata=metadata,
                )

                db.add(mapping)
                await db.flush()  # Get the ID

                results["created_mappings"] += 1
                results["created_mapping_ids"].append(str(mapping.id))
                logger.info(f"Created mapping {mapping.id} for user {central_user_id}")

            except Exception as e:
                error_msg = f"Error creating mapping for {suggestion_data.get('central_user_id')}: {str(e)}"
                logger.error(error_msg)
                results["errors"].append(error_msg)
                results["skipped_mappings"] += 1

        # Commit all changes
        try:
            await db.commit()
            logger.info(f"Successfully committed {results['created_mappings']} user mappings")
        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to commit mappings: {str(e)}")
            results["errors"].append(f"Failed to commit changes: {str(e)}")
            results["created_mappings"] = 0
            results["created_mapping_ids"] = []

        logger.info(f"Created {results['created_mappings']} user mappings, " f"skipped {results['skipped_mappings']}")

        return results


# Global user mapper instance
user_mapper = UserMappingDetector()


async def get_user_mapper() -> UserMappingDetector:
    """Get the global user mapping detector instance."""
    return user_mapper
