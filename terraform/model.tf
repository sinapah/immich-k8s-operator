# Immich model: created internally, or looked up by UUID.
# The COS Lite model is created by the cos-lite module (see cos.tf).

resource "juju_model" "immich" {
  count = local.create_model ? 1 : 0

  name = var.model.name
}

data "juju_model" "immich" {
  count = local.create_model ? 0 : 1

  uuid = var.model.uuid
}
