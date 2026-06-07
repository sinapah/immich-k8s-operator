#!/usr/bin/env python3
# Copyright 2026 sina.pahlavan@canonical.com
# See LICENSE file for licensing details.

"""Charm for Immich on Juju Kubernetes."""

import logging
from typing import Any
from urllib.parse import urlparse
from charms.traefik_k8s.v2.ingress import IngressPerAppReadyEvent, IngressPerAppRequirer
import ops

logger = logging.getLogger(__name__)

SERVER_CONTAINER = "immich-server"
ML_CONTAINER = "immich-machine-learning"
SERVER_SERVICE = "immich-server"
ML_SERVICE = "immich-machine-learning"
SERVER_PORT = 2283
ML_PORT = 3003
UPLOAD_LOCATION = "/usr/src/app/upload"
SUPPORTED_STORAGE_MODES = {"filesystem", "s3"}


class ImmichK8SOperatorCharm(ops.CharmBase):
    """Charm for operating Immich."""

    def __init__(self, framework: ops.Framework):
        super().__init__(framework)
        framework.observe(self.on.config_changed, self._reconcile)
        framework.observe(self.on[SERVER_CONTAINER].pebble_ready, self._reconcile)
        framework.observe(self.on[ML_CONTAINER].pebble_ready, self._reconcile)

        self.ingress = IngressPerAppRequirer(
            charm=self,
            strip_prefix=True,
            scheme=lambda: urlparse(self.internal_url).scheme,
        )
    
        for relation_name in ("database", "cache", "ingress"):
            relation_events = self.on[relation_name]
            framework.observe(relation_events.relation_changed, self._reconcile)
            framework.observe(relation_events.relation_broken, self._reconcile)
            framework.observe(relation_events.relation_departed, self._reconcile)
            framework.observe(relation_events.relation_joined, self._reconcile)

    def _reconcile(self, _: ops.EventBase) -> None:
        """Validate charm state and render Pebble layers when dependencies are ready."""
        server = self.unit.get_container(SERVER_CONTAINER)
        if not server.can_connect():
            self.unit.status = ops.WaitingStatus("waiting for Immich server container")
            return

        validation_status = self._validate_storage_config()
        if validation_status:
            self.unit.status = validation_status
            return

        database_env = self._database_environment()
        if database_env is None:
            self.unit.status = ops.WaitingStatus("waiting for PostgreSQL relation")
            return

        cache_env = self._cache_environment()
        if cache_env is None:
            self.unit.status = ops.WaitingStatus("waiting for Redis-compatible relation")
            return

        server.add_layer(
            "immich-server",
            self._server_layer(database_env=database_env, cache_env=cache_env),
            combine=True,
        )
        server.replan()

        if self.config["enable-machine-learning"]:
            machine_learning = self.unit.get_container(ML_CONTAINER)
            if not machine_learning.can_connect():
                self.unit.status = ops.WaitingStatus(
                    "waiting for Immich machine-learning container"
                )
                return
            machine_learning.add_layer(
                "immich-machine-learning",
                self._machine_learning_layer(),
                combine=True,
            )
            machine_learning.replan()
        else:
            self._stop_machine_learning()

        self.unit.status = ops.ActiveStatus()

    def _validate_storage_config(self) -> ops.BlockedStatus | None:
        """Validate media storage settings."""
        storage_mode = self._storage_mode()
        if storage_mode not in SUPPORTED_STORAGE_MODES:
            return ops.BlockedStatus(
                f"unsupported storage-mode {storage_mode!r}; use filesystem or s3"
            )

        if storage_mode == "filesystem" and self._unit_count() > 1:
            return ops.BlockedStatus("multi-unit deployments require S3-compatible storage")

        if storage_mode == "s3":
            missing = [
                key
                for key in ("s3-endpoint", "s3-bucket", "s3-access-key", "s3-secret-key")
                if not self.config[key]
            ]
            if missing:
                return ops.BlockedStatus(
                    "missing required S3 configuration: " + ", ".join(missing)
                )

        return None

    def _server_layer(
        self,
        database_env: dict[str, str],
        cache_env: dict[str, str],
    ) -> ops.pebble.LayerDict:
        """Build the Immich server Pebble layer."""
        environment = {
            "IMMICH_HOST": "0.0.0.0",
            "IMMICH_PORT": str(SERVER_PORT),
            "IMMICH_MACHINE_LEARNING_URL": f"http://localhost:{ML_PORT}",
            "LOG_LEVEL": str(self.config["log-level"]),
            "UPLOAD_LOCATION": UPLOAD_LOCATION,
            **database_env,
            **cache_env,
            **self._external_url_environment(),
            **self._s3_environment(),
        }

        return {
            "summary": "Immich server layer",
            "description": "Pebble layer for the Immich server workload.",
            "services": {
                SERVER_SERVICE: {
                    "override": "replace",
                    "summary": "Immich server",
                    "command": "start.sh immich",
                    "startup": "enabled",
                    "environment": environment,
                }
            },
            "checks": {
                "immich-server-ready": {
                    "override": "replace",
                    "level": "ready",
                    "http": {"url": f"http://localhost:{SERVER_PORT}/api/server/ping"},
                }
            },
        }

    def _machine_learning_layer(self) -> ops.pebble.LayerDict:
        """Build the Immich machine-learning Pebble layer."""
        return {
            "summary": "Immich machine-learning layer",
            "description": "Pebble layer for the Immich machine-learning workload.",
            "services": {
                ML_SERVICE: {
                    "override": "replace",
                    "summary": "Immich machine learning",
                    "command": "start.sh machine-learning",
                    "startup": "enabled",
                    "environment": {
                        "MACHINE_LEARNING_HOST": "0.0.0.0",
                        "MACHINE_LEARNING_PORT": str(ML_PORT),
                    },
                }
            },
            "checks": {
                "immich-machine-learning-ready": {
                    "override": "replace",
                    "level": "ready",
                    "http": {"url": f"http://localhost:{ML_PORT}/ping"},
                }
            },
        }

    def _database_environment(self) -> dict[str, str] | None:
        """Return Immich database environment variables when relation data is ready."""
        data = self._remote_app_data("database")
        if not data:
            return None

        host, port = self._host_port_from_data(data, default_port="5432")
        database = data.get("database") or data.get("database_name") or data.get("dbname")
        username = data.get("username") or data.get("user")
        password = data.get("password")
        if not all((host, port, database, username, password)):
            logger.info("PostgreSQL relation data is incomplete")
            return None

        return {
            "DB_HOSTNAME": host,
            "DB_PORT": port,
            "DB_DATABASE_NAME": database,
            "DB_USERNAME": username,
            "DB_PASSWORD": password,
        }

    def _cache_environment(self) -> dict[str, str] | None:
        """Return Immich cache environment variables when relation data is ready."""
        data = self._remote_app_data("cache")
        if not data:
            return None

        host, port = self._host_port_from_data(data, default_port="6379")
        if not host:
            logger.info("Redis-compatible relation data is incomplete")
            return None

        environment = {
            "REDIS_HOSTNAME": host,
            "REDIS_PORT": port,
        }
        if username := data.get("username") or data.get("user"):
            environment["REDIS_USERNAME"] = username
        if password := data.get("password"):
            environment["REDIS_PASSWORD"] = password
        return environment

    def _external_url_environment(self) -> dict[str, str]:
        """Return external URL environment when config or ingress data provides one."""
        external_url = str(self.config["external-url"]).strip()
        if not external_url:
            ingress_data = self._remote_app_data("ingress")
            external_url = (
                ingress_data.get("url")
                or ingress_data.get("external-url")
                or ingress_data.get("ingress")
            )

        if not external_url:
            return {}

        return {"IMMICH_SERVER_URL": external_url}

    def _s3_environment(self) -> dict[str, str]:
        """Return S3-related environment variables when S3 storage is configured."""
        if self._storage_mode() != "s3":
            return {}

        return {
            "S3_ENDPOINT": str(self.config["s3-endpoint"]),
            "S3_BUCKET": str(self.config["s3-bucket"]),
            "S3_REGION": str(self.config["s3-region"]),
            "S3_ACCESS_KEY": str(self.config["s3-access-key"]),
            "S3_SECRET_KEY": str(self.config["s3-secret-key"]),
            "S3_FORCE_PATH_STYLE": str(self.config["s3-force-path-style"]).lower(),
        }

    def _stop_machine_learning(self) -> None:
        """Stop the machine-learning Pebble service when it is disabled."""
        machine_learning = self.unit.get_container(ML_CONTAINER)
        if not machine_learning.can_connect():
            return
        if ML_SERVICE in machine_learning.get_services():
            machine_learning.stop(ML_SERVICE)

    def _remote_app_data(self, relation_name: str) -> dict[str, str]:
        """Return remote application data for a relation."""
        relation = self.model.get_relation(relation_name)
        if relation is None or relation.app is None:
            return {}
        return dict(relation.data[relation.app])

    def _host_port_from_data(
        self,
        data: dict[str, str],
        default_port: str,
    ) -> tuple[str, str]:
        """Extract host and port from common relation data field names."""
        host = data.get("host") or data.get("hostname")
        port = data.get("port") or default_port

        endpoint = data.get("endpoint") or data.get("endpoints")
        if endpoint and not host:
            first_endpoint = endpoint.split(",", maxsplit=1)[0]
            host, separator, endpoint_port = first_endpoint.rpartition(":")
            if not separator:
                host = first_endpoint
            elif endpoint_port:
                port = endpoint_port

        return host or "", port

    def _storage_mode(self) -> str:
        """Return the normalized storage mode."""
        return str(self.config["storage-mode"]).strip().lower()

    def _unit_count(self) -> int:
        """Return the current Juju application unit count."""
        return len(self.model.app.units) + 1


if __name__ == "__main__":  # pragma: nocover
    ops.main(ImmichK8SOperatorCharm)
