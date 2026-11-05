# -------------- # Tailscale OAuth credentials --------------
# Stored as a Juju secret in the tailscale model and granted to tailscale-k8s.
# tailscale-k8s reads it through its `credentials` config option.

resource "juju_secret" "tailscale_credentials" {
  count = local.tailscale_enabled ? 1 : 0

  model_uuid = local.tailscale_model_uuid
  name       = "tailscale-oauth"
  value = {
    client-id     = var.tailscale_credentials.client_id
    client-secret = var.tailscale_credentials.client_secret
  }
}

# The grant uses the app name from variables, not module output, to avoid a cycle:
# module.tailscale depends on this grant.
resource "juju_access_secret" "tailscale_credentials" {
  count = local.tailscale_enabled ? 1 : 0

  model_uuid   = local.tailscale_model_uuid
  secret_id    = juju_secret.tailscale_credentials[0].secret_id
  applications = [var.tailscale.app_name]
}
