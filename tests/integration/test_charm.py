# Copyright 2026 sina.pahlavan@canonical.com
# See LICENSE file for licensing details.
#
# The integration tests use the Jubilant library. See https://documentation.ubuntu.com/jubilant/
# To learn more about testing, see https://documentation.ubuntu.com/ops/latest/explanation/testing/

import logging
import pathlib

import jubilant
import pytest
from helpers import IMMICH_APP, assert_immich_active, deploy_immich_with_backends

logger = logging.getLogger(__name__)


def test_deploy(charm: pathlib.Path, juju: jubilant.Juju):
    """Deploy Immich with its required PostgreSQL and Redis backends and integrate them."""
    deploy_immich_with_backends(juju, charm)


def test_active(juju: jubilant.Juju):
    """Check that Immich becomes active and idle once PostgreSQL and Redis are connected."""
    assert_immich_active(juju)


# If you implement immich.get_version in the charm source,
# remove the @pytest.mark.skip line to enable this test.
# Alternatively, remove this test if you don't need it.
@pytest.mark.skip(reason="immich.get_version is not implemented")
def test_workload_version_is_set(charm: pathlib.Path, juju: jubilant.Juju):
    """Check that the correct version of the workload is running."""
    version = juju.status().apps[IMMICH_APP].version
    assert version == "3.14"  # Replace 3.14 by the expected version of the workload.
