# SCOPED: contractor read access to one bucket (medium — may need review)

locals {
  contractor_scoped_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid      = "ContractorReportsRead"
      Effect   = "Allow"
      Action   = ["s3:GetObject"]
      Resource = "arn:aws:s3:::company-reports-bucket/reports/*"
    }]
  })
}

resource "local_file" "contractor_scoped_policy" {
  filename = "${path.module}/rendered/contractor_scoped_policy.json"
  content  = local.contractor_scoped_policy
}

resource "null_resource" "access_grant_marker" {
  triggers = {
    policy_hash = sha256(local.contractor_scoped_policy)
    grantee     = "contractor-temp"
    access_type = "read-scoped"
  }
}
