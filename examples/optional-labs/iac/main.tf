terraform {
  required_version = ">= 1.4.0"
}

variable "desired_version" {
  type    = string
  default = "v1"
}

resource "terraform_data" "platform_state" {
  input = {
    external_id     = "env/checkout-staging"
    desired_version = var.desired_version
    observed_sha256 = filesha256("${path.module}/observed.txt")
  }
}

output "state_contract" {
  value = terraform_data.platform_state.output
}
