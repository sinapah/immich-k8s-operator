# Immich K8s charm relations

## Overview

The `immich-k8s` charm depends on external Juju applications for database, cache, ingress, logs, and metrics integration. PostgreSQL and Redis/Valkey are required for Immich to run. Ingress, logging, and metrics are integration surfaces for operating the service.

The charm must not embed PostgreSQL, Redis, or Valkey in the Immich workload pod.

## Required relations

### PostgreSQL

Purpose:

```text
Provide Immich's relational database.
```

Expected direction:

```yaml
requires:
  database:
    interface: postgresql_client
```

The exact relation name can be `database` or `postgresql`; choose one and use it consistently in code, metadata, tests, and documentation.

Requirements:

- The relation must provide host, port, database name, username, password, and TLS information if applicable.
- The related database must satisfy Immich's PostgreSQL version and extension requirements.
- The charm should verify compatibility where possible before starting Immich.
- If required extensions are unavailable, the charm should enter blocked status with a clear message.

Important compatibility note:

The official Immich Docker Compose topology uses a specialized `ghcr.io/immich-app/postgres` image with vector-related extensions. A generic PostgreSQL charm may not be compatible unless those extensions are available.

Open implementation checks:

- Identify the exact extension set required by the selected Immich version.
- Determine whether the target Charmed PostgreSQL deployment can install or expose those extensions.
- Decide how the charm checks extension availability through relation data or a database query.

### Redis or Valkey

Purpose:

```text
Provide Immich's cache/queue backend.
```

Expected direction:

```yaml
requires:
  cache:
    interface: redis
```

The relation should support Redis-compatible endpoints. Valkey is acceptable if exposed through a Redis-compatible relation/interface.

Requirements:

- The relation must provide host, port, credentials if applicable, and TLS information if applicable.
- The charm should block or wait until the cache endpoint is ready.
- The charm should configure Immich server environment variables from relation data.

## Ingress relation

### Traefik ingress

Purpose:

```text
Expose Immich through Juju-managed ingress.
```

Expected direction:

```yaml
requires:
  ingress:
    interface: ingress
```

Expected behavior:

- The charm sends Immich service information to Traefik.
- The default workload port is `2283`.
- When ingress data is ready, the charm configures Immich's external URL from the ingress endpoint.
- TLS termination is expected to be handled by the ingress provider.

Implementation considerations:

- Immich needs large upload support, so ingress body-size/proxy limits must be documented or configured if the interface supports it.
- Websocket behavior should be validated through the selected ingress provider.
- If ingress is absent or incomplete, the charm should either use a documented manual external URL fallback or report a clear waiting/blocked status according to the final implementation choice.

## Observability relations

### Log forwarding

Purpose:

```text
Forward Immich workload logs to Loki.
```

Expected direction:

```yaml
requires:
  logging:
    interface: loki_push_api
    optional: true
```

Expected behavior:

- Forward logs from the Immich server container.
- Forward logs from the machine-learning container when enabled.
- Do not block Immich startup when logging is not related.

### Metrics

Purpose:

```text
Expose Immich metrics to Prometheus-compatible scraping.
```

Expected direction:

```yaml
provides:
  metrics-endpoint:
    interface: prometheus_scrape
```

Expected behavior:

- Expose a scrape target only if the selected Immich version provides a stable metrics endpoint or if the charm includes a straightforward exporter integration.
- Do not claim complete metrics support until the endpoint/exporter path is verified.
- Avoid dashboards and alert rules in the first implementation unless later added explicitly.

Open implementation checks:

- Confirm whether Immich exposes a stable metrics endpoint for the selected release.
- Confirm endpoint path, port, authentication behavior, and scrape labels.
- Decide whether metrics come directly from Immich or from a sidecar/exporter.

## Storage integration

### Filesystem storage

Filesystem storage is modeled as Juju storage, not a relation.

Expected metadata shape:

```yaml
storage:
  uploads:
    type: filesystem
```

Expected behavior:

- Mount the storage into the Immich server container at the path expected by the selected Immich version.
- Allow filesystem mode only for single-unit deployments.
- Block multi-unit deployments unless S3-compatible storage is configured.

### S3-compatible storage

S3-compatible storage is initially modeled as charm configuration plus Juju secrets for sensitive values.

Expected config fields may include:

```text
s3-endpoint
s3-bucket
s3-region
s3-access-key
s3-secret-key
s3-force-path-style
```

Sensitive values should be stored with Juju secrets where possible.

Future enhancement:

```yaml
requires:
  object-storage:
    interface: s3
    optional: true
```

The first implementation can defer an object-storage relation unless a compatible, agreed interface is selected before implementation.

## Peer relation

Purpose:

```text
Coordinate application-level state between Immich units if needed.
```

Expected direction:

```yaml
peers:
  peers:
    interface: immich_peers
```

Expected behavior:

- Store or coordinate charm-level state only if required.
- Do not use peer data as a substitute for shared media storage.
- Multi-unit support still requires S3-compatible storage plus external PostgreSQL and Redis/Valkey.

## Relation readiness rules

The charm may start Immich only when:

- PostgreSQL relation is present and compatible.
- Redis/Valkey relation is present and ready.
- Filesystem storage is available for single-unit filesystem mode, or S3 configuration is complete for S3 mode.
- If scaled above one unit, S3 mode is active.
- Required application secrets are available.

The charm should remain active without optional relations:

- logging
- metrics scraping consumer

Ingress behavior depends on the final external-access policy, but the preferred design is to support Traefik ingress and configure Immich's external URL from it.

