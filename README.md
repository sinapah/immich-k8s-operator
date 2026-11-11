# immich-k8s

Charmhub package name: immich-k8s
More information: https://charmhub.io/immich-k8s?channel=3.2/edge

This charm operates [Immich](https://immich.app), a self-hosted photo and video management application, on Juju Kubernetes.

## What does this charm do?

This charm deploys and manages the Immich server workload with an optional machine-learning sidecar. It does not embed PostgreSQL or Redis; both are provided through Juju relations.

The charm offers:

1. Database and cache integration. Requires PostgreSQL (`database`) and Redis or Valkey (`cache`).
2. Media storage. Filesystem storage for single-unit deployments, or S3-compatible storage configured through charm config for multi-unit deployments.
3. Ingress. Optional ingress to expose Immich externally: Traefik (`ingress` relation), or Tailscale via tailscale-beacon-k8s (`ingress` relation) with tailscale-k8s in a separate model.
4. Observability. A `metrics-endpoint` (Prometheus scrape), a `grafana-dashboard` provider, and optional `logging` (Loki push API).

## Deploying with Terraform

The `terraform/` directory contains a root module that deploys Immich together with PostgreSQL, Redis, and optionally Traefik or Tailscale ingress, self-signed-certificates, and COS Lite.

Prerequisites:
- A bootstrapped Juju controller, with the Juju Terraform provider able to access it.
- Network access, since the module pulls Traefik, self-signed-certificates, OpenTelemetry Collector, and Tailscale modules from GitHub.

Steps:

```bash
cd terraform
terraform init
terraform apply -var-file=my.tfvars
```

A minimal `my.tfvars`:

```hcl
model = {
  name = "immich"
}

ingress_provider = "traefik" # or "tailscale", or "none"
observability = false
```

See `terraform/variables.tf` for all options, including `ingress_provider`, `tls`, `observability`, `cos_ingress`, and per-application configuration. `terraform/test.tfvars` shows a complete example.

### Tailscale ingress

Set `ingress_provider = "tailscale"` and pass the OAuth client credentials. The module stores them in a Juju secret in the tailscale model, grants it to tailscale-k8s, and deploys tailscale-beacon-k8s in the Immich model.

```hcl
ingress_provider = "tailscale"
tailscale_credentials = {
  client_id     = "..."
  client_secret = "..."
}
# tailscale_model = { name = "tailscale" }   # default; or { uuid = "..." } to reuse a model
```

The OAuth client needs the `devices:core` (read and write) and `auth_keys` scopes and must carry the `tag:k8s-operator` tag. Immich is then reachable at the tailnet URL (`http://<tailnet-hostname>[:<port>]/`); TLS is not provided on this path, so `tls` requires `ingress_provider = "traefik"`.

Teardown: the tailscale-k8s application must not be removed while `loadBalancerClass: tailscale` Services exist, or their finalizers get stuck. The module orders destroy so the beacon goes first, but if a manual teardown is needed, wait for those Services to disappear before destroying.

> Note: `immich.units` must be `1`. Filesystem media storage supports only a single unit.

## Other resources

- [Contributing](CONTRIBUTING.md)
- See the [Juju documentation](https://documentation.ubuntu.com/juju/3.6/howto/manage-charms/) for more information about developing and improving charms.

