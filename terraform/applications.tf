
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

# -------------- # Tailscale ingress --------------

module "tailscale" {
  source = "git::https://github.com/canonical/service-mesh//charms/tailscale-k8s/terraform?depth=1"
  count  = local.tailscale_enabled ? 1 : 0

  app_name           = var.tailscale.app_name
  channel            = local.channels.tailscale
  config             = merge(var.tailscale.config, { credentials = juju_secret.tailscale_credentials[0].secret_id })
  constraints        = var.tailscale.constraints
  model_uuid         = local.tailscale_model_uuid
  revision           = var.tailscale.revision
  storage_directives = var.tailscale.storage_directives
  units              = var.tailscale.units

  # The grant must exist before tailscale-k8s starts reading the secret.
  depends_on = [juju_access_secret.tailscale_credentials]
}

module "tailscale_beacon" {
  source = "git::https://github.com/canonical/service-mesh//charms/tailscale-beacon-k8s/terraform?depth=1"
  count  = local.tailscale_enabled ? 1 : 0

  app_name    = var.tailscale_beacon.app_name
  channel     = local.channels.tailscale_beacon
  config      = var.tailscale_beacon.config
  constraints = var.tailscale_beacon.constraints
  model_uuid  = local.model_uuid
  revision    = var.tailscale_beacon.revision
  units       = var.tailscale_beacon.units

  # Destroy ordering: the beacon owns the LoadBalancer Services that tailscale-k8s
  # reconciles. Terraform destroys dependents first, so depending on module.tailscale
  # makes the beacon go before tailscale-k8s, which avoids stuck Service finalizers.
  depends_on = [module.tailscale]
}
