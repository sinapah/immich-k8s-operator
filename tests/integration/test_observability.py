# Copyright 2026 sina.pahlavan@canonical.com
# See LICENSE file for licensing details.
#
# The integration tests use the Jubilant library. See https://documentation.ubuntu.com/jubilant/
# To learn more about testing, see https://documentation.ubuntu.com/ops/latest/explanation/testing/

import logging
import pathlib

import jubilant
from helpers import (
    IMMICH_APP,
    IMMICH_CHARM_NAME,
    assert_immich_active,
    deploy_immich_with_backends,
    get_json,
    retry_until_passing,
    unit_address,
)

logger = logging.getLogger(__name__)

OTELCOL_APP = "otelcol"
LOKI_APP = "loki"
PROMETHEUS_APP = "prometheus"

LOKI_PORT = 3100
PROMETHEUS_PORT = 9090

# Juju topology labels attached to the telemetry that Immich emits.
IMMICH_SELECTOR = f'{{juju_charm="{IMMICH_CHARM_NAME}",juju_application="{IMMICH_APP}"}}'


def test_deploy(charm: pathlib.Path, juju: jubilant.Juju):
    """Deploy Immich with backends, plus OpenTelemetry Collector, Loki and Prometheus."""
    deploy_immich_with_backends(juju, charm)

    juju.deploy("opentelemetry-collector-k8s", app=OTELCOL_APP, channel="dev/edge", trust=True)
    juju.deploy(
        "loki-k8s",
        app=LOKI_APP,
        channel="dev/edge",
        trust=True,
        storage={"active-index-directory": "1G", "loki-chunks": "1G"},
    )
    juju.deploy(
        "prometheus-k8s",
        app=PROMETHEUS_APP,
        channel="dev/edge",
        trust=True,
        storage={"database": "1G"},
    )

    # Immich logs and metrics go to the collector, which forwards them onward.
    juju.integrate(f"{IMMICH_APP}:logging", f"{OTELCOL_APP}:receive-loki-logs")
    juju.integrate(f"{IMMICH_APP}:metrics-endpoint", f"{OTELCOL_APP}:metrics-endpoint")
    juju.integrate(f"{OTELCOL_APP}:send-loki-logs", f"{LOKI_APP}:logging")
    juju.integrate(f"{OTELCOL_APP}:send-remote-write", f"{PROMETHEUS_APP}:receive-remote-write")


def test_active(juju: jubilant.Juju):
    """Check that Immich becomes active and idle with the observability stack attached."""
    assert_immich_active(juju)


@retry_until_passing
def test_logs_in_loki(juju: jubilant.Juju):
    """Check that Immich logs have arrived in Loki."""
    url = f"http://{unit_address(juju, LOKI_APP)}:{LOKI_PORT}/loki/api/v1/query_range"
    response = get_json(url, {"query": IMMICH_SELECTOR, "limit": 10})
    assert response["status"] == "success"
    streams = response["data"]["result"]
    assert streams, f"no Immich logs found in Loki for {IMMICH_SELECTOR}"
    logger.info("Found %d Immich log stream(s) in Loki", len(streams))


@retry_until_passing
def test_metrics_in_prometheus(juju: jubilant.Juju):
    """Check that Immich metrics have arrived in Prometheus."""
    url = f"http://{unit_address(juju, PROMETHEUS_APP)}:{PROMETHEUS_PORT}/api/v1/query"
    response = get_json(url, {"query": IMMICH_SELECTOR})
    assert response["status"] == "success"
    series = response["data"]["result"]
    assert series, f"no Immich metrics found in Prometheus for {IMMICH_SELECTOR}"
    logger.info("Found %d Immich metric series in Prometheus", len(series))
