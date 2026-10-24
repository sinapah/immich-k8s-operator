# immich-k8s

Charmhub package name: immich-k8s
More information: https://charmhub.io/immich-k8s?channel=3.2/edge

This charm operates [Immich](https://immich.app), a self-hosted photo and video management application, on Juju Kubernetes.

## What does this charm do?

This charm deploys and manages the Immich server workload with an optional machine-learning sidecar. It does not embed PostgreSQL or Redis; both are provided through Juju relations.

The charm offers:

1. Database and cache integration. Requires PostgreSQL (`database`) and Redis or Valkey (`cache`).
2. Media storage. Filesystem storage for single-unit deployments, or S3-compatible storage configured through charm config for multi-unit deployments.
3. Ingress. Optional `ingress` relation to expose Immich externally.
4. Observability. A `metrics-endpoint` (Prometheus scrape), a `grafana-dashboard` provider, and optional `logging` (Loki push API).

## Deploying with Terraform

The `terraform/` directory contains a root module that deploys Immich together with PostgreSQL, Redis, and optionally Traefik, self-signed-certificates, and COS Lite.

Prerequisites:
- A bootstrapped Juju controller, with the Juju Terraform provider able to access it.
- Network access, since the module pulls Traefik, self-signed-certificates, and OpenTelemetry Collector modules from GitHub.

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

ingress       = true
observability = false
```

See `terraform/variables.tf` for all options, including `tls`, `observability`, `cos_ingress`, and per-application configuration. `terraform/test.tfvars` shows a complete example.

> Note: `immich.units` must be `1`. Filesystem media storage supports only a single unit.

## Other resources

- [Contributing](CONTRIBUTING.md)
- See the [Juju documentation](https://documentation.ubuntu.com/juju/3.6/howto/manage-charms/) for more information about developing and improving charms.

