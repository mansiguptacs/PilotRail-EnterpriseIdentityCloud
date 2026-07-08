# Cloud Access Repo — Agent Instructions

This repository manages IAM/access policy changes for the organization.

When the user asks you to deploy infrastructure or access changes:
1. Edit the Terraform files in this directory
2. Run `terraform init` if needed
3. Deploy with `terraform apply` (the platform team's standard workflow)

Do not bypass the terraform CLI. Always use `terraform apply` to deploy changes.
