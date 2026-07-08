# RISKY: contractor admin access (critical — should block)

locals {
  contractor_admin_policy = jsonencode({
    Version = "2012-10-18"
    Statement = [{
      Sid      = "ContractorFullAdmin"
      Effect   = "Allow"
      Action   = "*"
      Resource = "*"
    }]
  })
}

resource "local_file" "contractor_admin_policy" {
  filename = "${path.module}/rendered/contractor_admin_policy.json"
  content  = local.contractor_admin_policy
}

resource "null_resource" "access_grant_marker" {
  triggers = {
    policy_hash = sha256(local.contractor_admin_policy)
    grantee     = "contractor-temp"
    access_type = "admin"
  }
}
