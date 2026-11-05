locals {
  create_model           = var.model.uuid == null
  model_uuid             = local.create_model ? juju_model.immich[0].uuid : data.juju_model.immich[0].uuid
  create_tailscale_model = var.tailscale_model.uuid == null
  tailscale_model_uuid   = local.tailscale_enabled ? (local.create_tailscale_model ? juju_model.tailscale[0].uuid : data.juju_model.tailscale[0].uuid) : null
  observability_on       = var.observability
  traefik_enabled        = var.ingress_provider == "traefik"
  tailscale_enabled      = var.ingress_provider == "tailscale"
  ssc_enabled            = var.tls

  bases = {
    immich  = "ubuntu@24.04"
    traefik = "ubuntu@26.04"
    ssc     = "ubuntu@24.04"
    otelcol = "ubuntu@26.04"
  }

  channels = {
    traefik          = "latest/${var.risk}"
    ssc              = "1/${var.risk}"
    otelcol          = "dev/${var.risk}"
    tailscale_beacon = "dev/edge"
    tailscale        = "dev/edge"
  }
}
