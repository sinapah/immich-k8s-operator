output "model_uuid" {
  value       = local.model_uuid
  description = "The UUID of the Immich model (created or looked up)."
}

output "cos_model_uuid" {
  value       = local.observability_on ? module.cos_lite[0].model_uuid : null
  description = "The UUID of the COS Lite model, or null when observability is disabled."
}

output "applications" {
  value = {
    immich     = juju_application.immich.name
    postgresql = juju_application.postgresql.name
    redis      = juju_application.redis.name
    traefik    = local.traefik_enabled ? module.traefik[0].app_name : null
    ssc        = local.ssc_enabled ? module.ssc[0].app_name : null
    otelcol    = local.observability_on ? module.opentelemetry_collector[0].app_name : null
  }
  description = "Application names deployed in the Immich model. Null entries are disabled by feature toggles."
}
