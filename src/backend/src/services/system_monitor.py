"""System monitoring service for collecting metrics and status."""

import asyncio
import random
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import psutil
from loguru import logger

try:
    import docker

    DOCKER_AVAILABLE = True
except ImportError:
    DOCKER_AVAILABLE = False
    logger.warning("Docker library not available, Docker monitoring disabled")


class SystemMonitorService:
    """Service for collecting system metrics and status information."""

    def __init__(self):
        self.docker_client = None
        if DOCKER_AVAILABLE:
            try:
                self.docker_client = docker.from_env()
            except Exception as e:
                logger.warning(f"Failed to connect to Docker: {e}")

    async def get_current_system_status(self) -> Dict[str, Any]:
        """Get current system status including CPU, memory, disk usage."""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)

            # Memory usage
            memory = psutil.virtual_memory()
            memory_used_mb = int(memory.used / 1024 / 1024)
            memory_total_mb = int(memory.total / 1024 / 1024)
            memory_percent = memory.percent

            # Disk usage
            disk = psutil.disk_usage("/")
            disk_used_gb = round(disk.used / 1024 / 1024 / 1024, 2)
            disk_total_gb = round(disk.total / 1024 / 1024 / 1024, 2)
            disk_percent = round((disk.used / disk.total) * 100, 1)

            # System uptime
            boot_time = psutil.boot_time()
            uptime_seconds = int(time.time() - boot_time)

            # Network I/O
            network = psutil.net_io_counters()
            network_sent_mb = round(network.bytes_sent / 1024 / 1024, 2)
            network_recv_mb = round(network.bytes_recv / 1024 / 1024, 2)

            return {
                "cpu_percent": cpu_percent,
                "memory_used_mb": memory_used_mb,
                "memory_total_mb": memory_total_mb,
                "memory_percent": memory_percent,
                "disk_used_gb": disk_used_gb,
                "disk_total_gb": disk_total_gb,
                "disk_percent": disk_percent,
                "uptime_seconds": uptime_seconds,
                "network_sent_mb": network_sent_mb,
                "network_recv_mb": network_recv_mb,
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to get system status: {e}")
            return {
                "cpu_percent": 0.0,
                "memory_used_mb": 0,
                "memory_total_mb": 0,
                "memory_percent": 0.0,
                "disk_used_gb": 0.0,
                "disk_total_gb": 0.0,
                "disk_percent": 0.0,
                "uptime_seconds": 0,
                "network_sent_mb": 0.0,
                "network_recv_mb": 0.0,
                "timestamp": datetime.utcnow().isoformat(),
            }

    async def get_docker_status(self) -> Dict[str, Any]:
        """Get Docker container status information."""
        if not self.docker_client:
            return {
                "containers_running": 0,
                "containers_stopped": 0,
                "containers_paused": 0,
                "images_count": 0,
                "volumes_count": 0,
            }

        try:
            containers = self.docker_client.containers.list(all=True)
            images = self.docker_client.images.list()
            volumes = self.docker_client.volumes.list()

            running = sum(1 for c in containers if c.status == "running")
            stopped = sum(1 for c in containers if c.status in ["exited", "stopped"])
            paused = sum(1 for c in containers if c.status == "paused")

            return {
                "containers_running": running,
                "containers_stopped": stopped,
                "containers_paused": paused,
                "images_count": len(images),
                "volumes_count": len(volumes),
            }

        except Exception as e:
            logger.error(f"Failed to get Docker status: {e}")
            return {
                "containers_running": 0,
                "containers_stopped": 0,
                "containers_paused": 0,
                "images_count": 0,
                "volumes_count": 0,
            }

    async def get_process_list(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get list of running processes."""
        try:
            processes = []
            for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
                try:
                    processes.append(
                        {
                            "pid": proc.info["pid"],
                            "name": proc.info["name"],
                            "cpu_percent": proc.info["cpu_percent"] or 0,
                            "memory_percent": proc.info["memory_percent"] or 0,
                        }
                    )
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            # Sort by CPU usage and return top N
            processes.sort(key=lambda x: x["cpu_percent"], reverse=True)
            return processes[:limit]

        except Exception as e:
            logger.error(f"Failed to get process list: {e}")
            return []

    async def get_metrics_history(
        self, start_time: datetime, end_time: datetime, interval_seconds: int = 60
    ) -> Dict[str, List[float]]:
        """Get historical metrics data (mock implementation for now)."""
        # For now, generate realistic mock data
        # In a real implementation, this would query the database

        duration = end_time - start_time
        points = max(1, int(duration.total_seconds() / interval_seconds))

        # Generate realistic mock data with some variation
        base_cpu = random.uniform(20, 40)
        base_memory = random.uniform(40, 60)
        base_disk = random.uniform(30, 50)

        cpu_data = []
        memory_data = []
        disk_data = []
        network_sent_data = []
        network_recv_data = []

        for _i in range(points):
            # Add some realistic variation
            cpu_variation = random.uniform(-10, 10)
            memory_variation = random.uniform(-5, 5)

            cpu_data.append(max(0, min(100, base_cpu + cpu_variation)))
            memory_data.append(max(0, min(100, base_memory + memory_variation)))
            disk_data.append(base_disk + random.uniform(-2, 2))
            network_sent_data.append(random.uniform(0.5, 5.0))
            network_recv_data.append(random.uniform(0.5, 5.0))

        return {
            "cpu": cpu_data,
            "memory": memory_data,
            "disk": disk_data,
            "network_sent": network_sent_data,
            "network_recv": network_recv_data,
        }

    async def collect_metrics(self) -> Dict[str, Any]:
        """Collect current metrics for storage."""
        system_status = await self.get_current_system_status()
        docker_status = await self.get_docker_status()

        return {
            **system_status,
            **docker_status,
            "collected_at": datetime.utcnow().isoformat(),
        }

    async def start_metrics_collection(self, interval_seconds: int = 60, callback: Optional[callable] = None):
        """Start background metrics collection."""
        logger.info(f"Starting metrics collection with {interval_seconds}s interval")

        while True:
            try:
                metrics = await self.collect_metrics()

                if callback:
                    await callback(metrics)

                logger.debug(
                    "Metrics collected",
                    extra={
                        "component": "system_monitor",
                        "action": "metrics_collected",
                        "cpu_percent": metrics.get("cpu_percent"),
                        "memory_percent": metrics.get("memory_percent"),
                    },
                )

            except Exception as e:
                logger.error(f"Error collecting metrics: {e}")

            await asyncio.sleep(interval_seconds)
