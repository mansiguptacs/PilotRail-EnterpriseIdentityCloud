# SAFE: marketing read-only access (auto-approve expected)

locals {
  marketing_readonly_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid      = "MarketingReportsReadOnly"
      Effect   = "Allow"
      Action   = ["s3:GetObject", "s3:ListBucket"]
      Resource = ["arn:aws:s3:::company-reports-bucket1", "arn:aws:s3:::company-reports-bucket/*"]
    }]
  })
}

resource "local_file" "marketing_access_policy" {
  filename = "${path.module}/rendered/marketing_readonly_policy.json"
  content  = local.marketing_readonly_policy
}

resource "null_resource" "access_grant_marker" {
  triggers = {
    policy_hash = sha256(local.marketing_readonly_policy)
    grantee     = "marketing-service"
    access_type = "read-only"
  }
}
