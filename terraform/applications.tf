
# -------------- # Immich model --------------

resource "juju_application" "immich" {
  name       = var.immich.app_name
  model_uuid = local.model_uuid
  trust      = true
  units      = var.immich.units

  charm {
    name     = "immich-k8s"
    channel  = var.immich.channel
    base     = local.bases.immich
    revision = var.immich.revision
  }

  config             = var.immich.config
  constraints        = var.immich.constraints
  resources          = var.immich.resources
  storage_directives = var.immich.storage_directives
}

resource "juju_application" "postgresql" {
  name       = var.postgresql.app_name
  model_uuid = local.model_uuid
  trust      = true
  units      = var.postgresql.units

  charm {
    name     = "postgresql-k8s"
    channel  = var.postgresql.channel
    base     = var.postgresql.base
    revision = var.postgresql.revision
  }

  config             = var.postgresql.config
  constraints        = var.postgresql.constraints
  resources          = var.postgresql.resources
  storage_directives = var.postgresql.storage_directives
}

resource "juju_application" "redis" {
  name       = var.redis.app_name
  model_uuid = local.model_uuid
  trust      = true
  units      = var.redis.units

  charm {
    name     = "redis-k8s"
    channel  = var.redis.channel
    base     = var.redis.base
    revision = var.redis.revision
  }

  config             = var.redis.config
  constraints        = var.redis.constraints
  resources          = var.redis.resources
  storage_directives = var.redis.storage_directives
}

module "traefik" {
  source = "git::https://github.com/canonical/traefik-k8s-operator//terraform"
  count  = local.traefik_enabled ? 1 : 0

  app_name           = var.traefik.app_name
  base               = local.bases.traefik
  channel            = local.channels.traefik
  config             = var.traefik.config
  constraints        = var.traefik.constraints
  model_uuid         = local.model_uuid
  resources          = var.traefik.resources
  revision           = var.traefik.revision
  storage_directives = var.traefik.storage_directives
  units              = var.traefik.units
}

module "ssc" {
  source = "git::https://github.com/canonical/self-signed-certificates-operator//terraform"
  count  = local.ssc_enabled ? 1 : 0

  app_name    = var.ssc.app_name
  base        = local.bases.ssc
  channel     = local.channels.ssc
  config      = var.ssc.config
  constraints = var.ssc.constraints
  model_uuid  = local.model_uuid
  revision    = var.ssc.revision
  units       = var.ssc.units
}

module "opentelemetry_collector" {
  source = "git::https://github.com/canonical/opentelemetry-collector-k8s-operator//terraform"
  count  = local.observability_on ? 1 : 0

  app_name           = var.opentelemetry_collector.app_name
  base               = local.bases.otelcol
  channel            = local.channels.otelcol
  config             = var.opentelemetry_collector.config
  constraints        = var.opentelemetry_collector.constraints
  model_uuid         = local.model_uuid
  resources          = var.opentelemetry_collector.resources
  revision           = var.opentelemetry_collector.revision
  storage_directives = var.opentelemetry_collector.storage_directives
  units              = var.opentelemetry_collector.units
}
