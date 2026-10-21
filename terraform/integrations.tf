# -------------- # Immich model: data backends --------------

resource "juju_integration" "immich_database" {
  model_uuid = local.model_uuid

  application {
    name     = juju_application.immich.name
    endpoint = "database"
  }

  application {
    name     = juju_application.postgresql.name
    endpoint = "database"
  }
}

resource "juju_integration" "immich_cache" {
  model_uuid = local.model_uuid

  application {
    name     = juju_application.immich.name
    endpoint = "cache"
  }

  application {
    name     = juju_application.redis.name
    endpoint = "redis"
  }
}

# -------------- # Ingress and TLS --------------

resource "juju_integration" "immich_ingress" {
  count      = local.traefik_enabled ? 1 : 0
  model_uuid = local.model_uuid

  application {
    name     = juju_application.immich.name
    endpoint = "ingress"
  }

  application {
    name     = module.traefik[0].app_name
    endpoint = module.traefik[0].endpoints.ingress
  }
}

resource "juju_integration" "traefik_certificates" {
  count      = local.traefik_enabled && local.ssc_enabled ? 1 : 0
  model_uuid = local.model_uuid

  application {
    name     = module.ssc[0].provides.certificates.name
    endpoint = module.ssc[0].provides.certificates.endpoint
  }

  application {
    name     = module.traefik[0].app_name
    endpoint = module.traefik[0].endpoints.certificates
  }
}

resource "juju_integration" "traefik_receive_ca_certificate" {
  count      = local.traefik_enabled && local.ssc_enabled ? 1 : 0
  model_uuid = local.model_uuid

  application {
    name     = module.ssc[0].provides.send-ca-cert.name
    endpoint = module.ssc[0].provides.send-ca-cert.endpoint
  }

  application {
    name     = module.traefik[0].app_name
    endpoint = module.traefik[0].endpoints.receive_ca_cert
  }
}

# -------------- # Observability: local to the Immich model --------------

resource "juju_integration" "immich_logging" {
  count      = local.observability_on ? 1 : 0
  model_uuid = local.model_uuid

  application {
    name     = juju_application.immich.name
    endpoint = "logging"
  }

  application {
    name     = module.opentelemetry_collector[0].app_name
    endpoint = module.opentelemetry_collector[0].provides.receive_loki_logs
  }
}

resource "juju_integration" "immich_metrics" {
  count      = local.observability_on ? 1 : 0
  model_uuid = local.model_uuid

  application {
    name     = juju_application.immich.name
    endpoint = "metrics-endpoint"
  }

  application {
    name     = module.opentelemetry_collector[0].app_name
    endpoint = module.opentelemetry_collector[0].requires.metrics_endpoint
  }
}

resource "juju_integration" "immich_dashboards" {
  count      = local.observability_on ? 1 : 0
  model_uuid = local.model_uuid

  application {
    name     = juju_application.immich.name
    endpoint = "grafana-dashboard"
  }

  application {
    name     = module.opentelemetry_collector[0].app_name
    endpoint = module.opentelemetry_collector[0].requires.grafana_dashboards_consumer
  }
}

# -------------- # Observability: otelcol to COS Lite (cross-model) --------------

resource "juju_integration" "otelcol_send_loki_logs" {
  count      = local.observability_on ? 1 : 0
  model_uuid = local.model_uuid

  application {
    name     = module.opentelemetry_collector[0].app_name
    endpoint = module.opentelemetry_collector[0].requires.send_loki_logs
  }

  application {
    offer_url = module.cos_lite[0].offers.loki_logging.url
  }
}

resource "juju_integration" "otelcol_send_remote_write" {
  count      = local.observability_on ? 1 : 0
  model_uuid = local.model_uuid

  application {
    name     = module.opentelemetry_collector[0].app_name
    endpoint = module.opentelemetry_collector[0].requires.send_remote_write
  }

  application {
    offer_url = module.cos_lite[0].offers.prometheus_receive_remote_write.url
  }
}

resource "juju_integration" "otelcol_grafana_dashboards" {
  count      = local.observability_on ? 1 : 0
  model_uuid = local.model_uuid

  application {
    name     = module.opentelemetry_collector[0].app_name
    endpoint = module.opentelemetry_collector[0].provides.grafana_dashboards_provider
  }

  application {
    offer_url = module.cos_lite[0].offers.grafana_dashboards.url
  }
}

resource "juju_integration" "otelcol_receive_ca_cert" {
  count      = local.observability_on && var.tls ? 1 : 0
  model_uuid = local.model_uuid

  application {
    name     = module.opentelemetry_collector[0].app_name
    endpoint = module.opentelemetry_collector[0].requires.receive_ca_cert
  }

  application {
    offer_url = juju_offer.cos_send_ca_cert[0].url
  }
}
