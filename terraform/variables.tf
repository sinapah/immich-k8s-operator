# Constraints set AntiAffinity in K8s; see observability-stack/terraform/cos-lite.

variable "risk" {
  description = "Risk level that the external charms are deployed from (unless overwritten by individual channels)"
  type        = string
  default     = "edge"
}

variable "model" {
  description = "Immich model configuration. When `uuid` is set, an existing model is looked up; otherwise a new model is created with the given name."
  type = object({
    uuid = optional(string)
    name = optional(string, "immich")
  })
  default = {}

  validation {
    condition     = var.model.uuid == null || can(regex("^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$", var.model.uuid))
    error_message = "`model.uuid` must be a valid UUID."
  }

  validation {
    condition     = var.model.uuid != null || length(var.model.name) > 0
    error_message = "`model.name` must be non-empty when creating a model (i.e. when `model.uuid` is null)."
  }
}

variable "cos_model" {
  description = "COS Lite model configuration, used only when `observability` is true. Passed to the cos-lite module's `model` variable."
  type = object({
    uuid = optional(string)
    name = optional(string, "cos-lite")
  })
  default = {}
}

# -------------- # Feature toggles --------------

variable "tls" {
  description = "Enable TLS. When true, self-signed-certificates signs Traefik's certificates (requires `ingress`), and COS Lite runs with internal TLS when `observability` is true."
  type        = bool
  default     = false

  validation {
    condition     = !var.tls || var.ingress
    error_message = "`tls` requires `ingress` to be true, because the certificates are served by Traefik."
  }
}

variable "ingress" {
  description = "Deploy Traefik and relate it to Immich to expose it externally."
  type        = bool
  default     = true
}

variable "observability" {
  description = "Deploy COS Lite in a separate model and an OpenTelemetry Collector in the Immich model that forwards logs, metrics and dashboards to it."
  type        = bool
  default     = false
}

variable "cos_ingress" {
  description = "Expose COS Lite's components through its own Traefik (ingress). Requires `observability`. Immich reaches COS through offers, so this only affects external access to COS."
  type        = bool
  default     = false

  validation {
    condition     = !var.cos_ingress || var.observability
    error_message = "`cos_ingress` requires `observability` to be true."
  }
}

# -------------- # Immich and backends --------------

variable "immich" {
  description = "Application configuration for Immich. Only one unit is supported: media is stored on filesystem storage, which is single-unit only."
  type = object({
    app_name           = optional(string, "immich")
    channel            = optional(string, "latest/edge")
    config             = optional(map(string), {})
    constraints        = optional(string, "arch=amd64")
    resources          = optional(map(string), {})
    revision           = optional(number, null)
    storage_directives = optional(map(string), { uploads = "kubernetes,1,10G" })
    units              = optional(number, 1)
  })
  default = {}

  validation {
    condition     = var.immich.units == 1
    error_message = "immich.units must be 1: without S3 storage, Immich supports only filesystem media storage, which is single-unit."
  }
}

variable "postgresql" {
  description = "Application configuration for PostgreSQL (postgresql-k8s), deployed in the Immich model. The plugin options are required by Immich."
  type = object({
    app_name = optional(string, "postgresql")
    base     = optional(string, null)
    channel  = optional(string, "16/stable")
    config = optional(map(string), {
      plugin-cube-enable          = "true"
      plugin-earthdistance-enable = "true"
      plugin-vector-enable        = "true"
    })
    constraints = optional(string, "arch=amd64")
    resources   = optional(map(string), { postgresql-image = "207" })
    revision    = optional(number, 957)
    storage_directives = optional(map(string), {
      archive = "kubernetes,1,1024M"
      data    = "kubernetes,1,1024M"
      logs    = "kubernetes,1,1024M"
      temp    = "kubernetes,1,1024M"
    })
    units = optional(number, 1)
  })
  default = {}
}

variable "redis" {
  description = "Application configuration for Redis (redis-k8s), deployed in the Immich model as Immich's cache."
  type = object({
    app_name           = optional(string, "redis")
    base               = optional(string, null)
    channel            = optional(string, "latest/edge")
    config             = optional(map(string), {})
    constraints        = optional(string, "arch=amd64")
    resources          = optional(map(string), {})
    revision           = optional(number, null)
    storage_directives = optional(map(string), {})
    units              = optional(number, 1)
  })
  default = {}
}

# -------------- # Supporting charms --------------

variable "traefik" {
  description = "Application configuration for Traefik. For more details: https://registry.terraform.io/providers/juju/juju/latest/docs/resources/application"
  type = object({
    app_name           = optional(string, "traefik")
    config             = optional(map(string), {})
    constraints        = optional(string, "arch=amd64")
    resources          = optional(map(string), {})
    revision           = optional(number, null)
    storage_directives = optional(map(string), {})
    units              = optional(number, 1)
  })
  default = {}
}

variable "ssc" {
  description = "Application configuration for self-signed-certificates. For more details: https://registry.terraform.io/providers/juju/juju/latest/docs/resources/application"
  type = object({
    app_name           = optional(string, "ca")
    config             = optional(map(string), {})
    constraints        = optional(string, "arch=amd64")
    revision           = optional(number, null)
    storage_directives = optional(map(string), {})
    units              = optional(number, 1)
  })
  default = {}
}

variable "opentelemetry_collector" {
  description = "Application configuration for the OpenTelemetry Collector deployed in the Immich model. For more details: https://registry.terraform.io/providers/juju/juju/latest/docs/resources/application"
  type = object({
    app_name           = optional(string, "otelcol")
    config             = optional(map(string), {})
    constraints        = optional(string, "arch=amd64")
    resources          = optional(map(string), {})
    revision           = optional(number, null)
    storage_directives = optional(map(string), {})
    units              = optional(number, 1)
  })
  default = {}
}
