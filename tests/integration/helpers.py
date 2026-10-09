# Copyright 2026 sina.pahlavan@canonical.com
# See LICENSE file for licensing details.

"""Helpers shared by the integration tests."""

import json
import logging
import pathlib
import urllib.parse
import urllib.request
from typing import Any

import jubilant
import yaml
from tenacity import retry, retry_if_exception_type, stop_after_delay, wait_fixed

logger = logging.getLogger(__name__)

METADATA = yaml.safe_load(pathlib.Path("charmcraft.yaml").read_text())

IMMICH_APP = "immich"
IMMICH_CHARM_NAME = METADATA["name"]
RETRY_TIMEOUT_SECONDS = 60 * 30
RETRY_INTERVAL_SECONDS = 10


def retry_until_passing(func):
    """Retry a check until it passes or the timeout elapses.

    Retries on assertion failures and on network errors, since the endpoints may not be up yet.
    """
    return retry(
        retry=retry_if_exception_type((AssertionError, OSError)),
        stop=stop_after_delay(RETRY_TIMEOUT_SECONDS),
        wait=wait_fixed(RETRY_INTERVAL_SECONDS),
        reraise=True,
    )(func)


def deploy_immich_with_backends(juju: jubilant.Juju, charm: pathlib.Path) -> None:
    """Deploy Immich with PostgreSQL and Redis, and integrate them."""
    resources = {
        "immich-server-image": METADATA["resources"]["immich-server-image"]["upstream-source"]
    }
    juju.deploy(
        "postgresql-k8s",
        app="pg",
        channel="16/stable",
        trust=True,
        config={
            "plugin-cube-enable": True,
            "plugin-earthdistance-enable": True,
            "plugin-vector-enable": True,
        },
    )
    juju.deploy("redis-k8s", app="redis", channel="latest/edge", trust=True)
    juju.deploy(
        charm.resolve(),
        app=IMMICH_APP,
        resources=resources,
        trust=True,
        storage={"uploads": "1G"},
    )

    juju.integrate("redis:redis", f"{IMMICH_APP}:cache")
    juju.integrate("pg:database", f"{IMMICH_APP}:database")


@retry_until_passing
def assert_immich_active(juju: jubilant.Juju) -> None:
    """Assert that the backends and Immich are active and Immich's unit is idle."""
    status = juju.status()
    assert jubilant.all_active(status, "pg", "redis", IMMICH_APP)
    unit = status.apps[IMMICH_APP].units[f"{IMMICH_APP}/0"]
    assert unit.workload_status.current == "active"
    assert unit.juju_status.current == "idle"


def unit_address(juju: jubilant.Juju, app: str) -> str:
    """Return the pod address of the app's first unit."""
    address = juju.status().apps[app].units[f"{app}/0"].address
    assert address, f"no address yet for {app}/0"
    return address


def get_json(url: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    """GET a URL with query parameters and decode the JSON response."""
    full_url = url
    if params:
        full_url = f"{url}?{urllib.parse.urlencode(params)}"
    with urllib.request.urlopen(full_url, timeout=30) as response:
        return json.loads(response.read().decode())
