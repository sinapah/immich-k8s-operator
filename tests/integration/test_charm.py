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
    _assert_immich_active(juju)
