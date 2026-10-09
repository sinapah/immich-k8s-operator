# Copyright 2026 sina.pahlavan@canonical.com
# See LICENSE file for licensing details.
#
# The integration tests use the Jubilant library. See https://documentation.ubuntu.com/jubilant/
# To learn more about testing, see https://documentation.ubuntu.com/ops/latest/explanation/testing/

import logging
import pathlib

import jubilant
import yaml
from tenacity import retry, retry_if_exception_type, stop_after_delay, wait_fixed

logger = logging.getLogger(__name__)

METADATA = yaml.safe_load(pathlib.Path("charmcraft.yaml").read_text())

ACTIVE_TIMEOUT_SECONDS = 60 * 30
ACTIVE_RETRY_INTERVAL_SECONDS = 10


def test_deploy(charm: pathlib.Path, juju: jubilant.Juju):
    """Deploy Immich with its required PostgreSQL and Redis backends and integrate them."""
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
        app="immich",
        resources=resources,
        trust=True,
        storage={"uploads": "1G"},
    )

    juju.integrate("redis:redis", "immich:cache")
    juju.integrate("pg:database", "immich:database")


@retry(
    retry=retry_if_exception_type(AssertionError),
    stop=stop_after_delay(ACTIVE_TIMEOUT_SECONDS),
    wait=wait_fixed(ACTIVE_RETRY_INTERVAL_SECONDS),
    reraise=True,
)
def _assert_immich_active(juju: jubilant.Juju) -> None:
    """Assert that the apps are active and the Immich unit is active and idle."""
    status = juju.status()
    assert jubilant.all_active(status, "pg", "redis", "immich")
    unit = status.apps["immich"].units["immich/0"]
    assert unit.workload_status.current == "active"
    assert unit.juju_status.current == "idle"


def test_active(juju: jubilant.Juju):
    """Check that Immich becomes active and idle once PostgreSQL and Redis are connected."""
    _assert_immich_active(juju)
