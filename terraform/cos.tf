# COS Lite, deployed in its own model when `observability` is enabled.
# Immich's OpenTelemetry Collector reaches it through the cross-model offers below.

module "cos_lite" {
  # Pinned: the ingress object and offers used below match this tag's interface.
  source = "git::https://github.com/canonical/observability-stack//terraform/cos-lite?ref=tf-cos-lite-3.0.1"
  count  = local.observability_on ? 1 : 0

  model        = var.cos_model
  risk         = var.risk
  internal_tls = var.tls

  # Immich reaches COS through offers, so COS's own Traefik is only needed for external access.
  ingress = {
    alertmanager            = var.cos_ingress
    catalogue               = var.cos_ingress
    grafana                 = var.cos_ingress
    loki                    = var.cos_ingress
    opentelemetry_collector = var.cos_ingress
    prometheus              = var.cos_ingress
  }
}

# With internal TLS on, the Immich-side collector must trust COS's CA.
# COS Lite does not offer its CA today, so it is offered here from the COS model.
resource "juju_offer" "cos_send_ca_cert" {
  count = local.observability_on && var.tls ? 1 : 0

  name             = "ca-send-ca-cert"
  model_uuid       = module.cos_lite[0].model_uuid
  application_name = module.cos_lite[0].components.ssc.app_name
  endpoints        = [module.cos_lite[0].components.ssc.provides.send-ca-cert.endpoint]
}
