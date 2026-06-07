# Immich K8s charm design

## Overview

The `immich-k8s` charm will operate Immich on Juju Kubernetes using the Ops framework and the sidecar pattern. It will manage the Immich application workload, optional machine-learning workload, storage mode validation, ingress-facing configuration, secrets, status reporting, logs, and metrics.

The charm will not embed PostgreSQL, Redis, or Valkey. Those services are required as external Juju relations.

## Repository
Expected structure of the repository:

```text
immich-k8s-operator/
  charmcraft.yaml # includes config and metadata
  lib # where the charm libraries for the necessary relations exist
  src/charm.py
  src/
  tests/unit/
  tests/integration/
  docs/design.md
  docs/relations.md
```

## Workload images

Use upstream Immich images from GitHub Container Registry:

```text
ghcr.io/immich-app/immich-server:<version>
ghcr.io/immich-app/immich-machine-learning:<version>
```

Images should be modeled as charm OCI resources so operators can override them. The default image version should be pinned through charm defaults or documented deployment guidance rather than floating silently.

The upstream Immich server and machine-learning images do not include PostgreSQL or Redis/Valkey. The official Immich Docker Compose deployment runs those as separate services.

## Workload topology

The first implementation is a single charm with one Juju application:

```text
immich-k8s
```

The pod should include:

```text
immich-server              required
immich-machine-learning    optional, enabled by config
```

The server container owns the web UI, API, upload handling, and background jobs expected by the selected Immich release. The machine-learning container is enabled or disabled through charm config.

Do not create a separate machine-learning charm for the initial implementation.

## Storage design

The charm supports two storage modes.

### Filesystem mode

Filesystem mode is the default monolithic deployment mode. The charm mounts Juju filesystem storage into the Immich server container for upload/library data.

Filesystem mode is single-unit only. If the application is scaled above one unit while filesystem mode is active, the charm should block with a clear status explaining that multi-unit deployments require S3-compatible storage.

### S3-compatible mode

Operators can configure an S3-compatible backend. When S3 settings are provided, Immich should use S3 for media storage instead of relying on local filesystem-backed media storage.

S3 mode is required for HA/multi-unit operation. Sensitive S3 values, such as access keys and secret keys, should be stored with Juju secrets where possible.

### Scaling rule

Default behavior:

```text
single unit + filesystem storage  allowed
single unit + S3 storage          allowed
multi unit + filesystem storage   blocked
multi unit + S3 storage           allowed when DB/cache relations are ready
```

## Database and cache

The charm requires external PostgreSQL and Redis/Valkey relations.

The official Immich release manifest uses a specialized PostgreSQL image with vector-related extensions. A standard PostgreSQL deployment may not satisfy Immich's requirements unless the required extensions are available.

The charm should verify PostgreSQL compatibility where possible and block early if required extensions or version constraints are not satisfied. It should not allow Immich to start and fail later with unclear runtime errors when the database is known to be incompatible.

## Ingress and external URL

The charm should support Traefik ingress through a Juju ingress relation. When ingress data is available, the charm should configure Immich's external URL accordingly.

Implementation and docs should account for:

- default Immich service port `2283`
- websocket behavior
- large upload/body-size requirements
- TLS termination being handled by ingress
- manual fallback behavior if ingress data is incomplete

## Secrets and auth scope

The charm manages required application secrets and sensitive environment values.

The first implementation does not manage:

- initial admin creation
- OIDC setup
- SSO setup
- user lifecycle

Those remain Immich application concerns configured through the Immich UI or documented Immich procedures.

## Feature scope

In scope for the first implementation:

- Immich web UI and API
- uploads and media library operation
- background jobs required by the selected Immich release
- optional machine-learning container
- filesystem and S3-compatible storage modes
- Traefik ingress integration
- log forwarding
- metrics integration when a stable endpoint or straightforward exporter path is available

Out of scope for the first implementation:

- GPU or hardware acceleration
- external library/import path support
- admin bootstrap automation
- OIDC/SSO automation
- dashboards and alert rules
- embedded PostgreSQL, Redis, or Valkey

## Status and validation

The charm should report clear statuses for:

- waiting for Pebble/container connectivity
- missing PostgreSQL relation
- missing Redis/Valkey relation
- incompatible PostgreSQL version or extensions
- invalid S3 configuration
- multi-unit deployment attempted without S3 storage
- missing or incomplete ingress data, where relevant
- active workload

## Testing

Unit tests should cover:

- Pebble layer generation
- config rendering
- ML enable/disable behavior
- filesystem vs S3 storage mode validation
- multi-unit blocking behavior without S3
- required relation readiness checks
- PostgreSQL compatibility blocking behavior
- status transitions

Integration tests should cover:

- deploying with PostgreSQL and Redis/Valkey relations
- deploying in filesystem mode as a single unit
- deploying with S3-compatible configuration
- relating to Traefik ingress
- smoke testing the Immich web/API endpoint
- validating logs and metrics integrations where available

