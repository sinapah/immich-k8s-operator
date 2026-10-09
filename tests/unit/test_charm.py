# Copyright 2026 sina.pahlavan@canonical.com
# See LICENSE file for licensing details.
#
# To learn more about testing, see https://documentation.ubuntu.com/ops/latest/explanation/testing/

from ops import pebble, testing

from charm import SERVER_SERVICE, ImmichK8SOperatorCharm


def _server_environment(layer: pebble.LayerDict) -> dict[str, str]:
    """Return the environment of the Immich server service in a Pebble layer."""
    services = layer.get("services", {})
    return dict(services[SERVER_SERVICE].get("environment", {}))


def test_metrics_scrape_jobs_ports():
    harness = testing.Harness(ImmichK8SOperatorCharm)
    harness.begin()
    jobs = harness.charm._metrics_scrape_jobs

    assert len(jobs) == 2

    api_job = jobs[0]
    assert api_job["job_name"] == "immich_api"
    assert api_job["metrics_path"] == "/metrics"
    assert api_job["static_configs"][0]["targets"][0].endswith(":8081")
    assert api_job["scheme"] == "http"

    micro_job = jobs[1]
    assert micro_job["job_name"] == "immich_microservices"
    assert micro_job["metrics_path"] == "/metrics"
    assert micro_job["static_configs"][0]["targets"][0].endswith(":8082")
    assert micro_job["scheme"] == "http"

    harness.cleanup()


def test_server_layer_sets_telemetry_when_metrics_relation_exists():
    harness = testing.Harness(ImmichK8SOperatorCharm)
    harness.add_relation("metrics-endpoint", "prometheus")
    harness.begin()
    env = _server_environment(harness.charm._server_layer(database_env={}, cache_env={}))

    assert env["IMMICH_TELEMETRY_INCLUDE"] == "all"

    harness.cleanup()


def test_server_layer_omits_telemetry_without_metrics_relation():
    harness = testing.Harness(ImmichK8SOperatorCharm)
    harness.begin()
    env = _server_environment(harness.charm._server_layer(database_env={}, cache_env={}))

    assert "IMMICH_TELEMETRY_INCLUDE" not in env

    harness.cleanup()


def test_metrics_scrape_jobs_scheme_matches_charm_scheme():
    harness = testing.Harness(ImmichK8SOperatorCharm)
    harness.begin()
    jobs = harness.charm._metrics_scrape_jobs

    for job in jobs:
        assert job["scheme"] == "http"

    harness.cleanup()
