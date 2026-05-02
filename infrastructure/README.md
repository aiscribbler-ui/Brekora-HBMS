# Brekora BMS — AWS Infrastructure as Code

## Tool Choice

**Terraform** was selected over AWS CDK for this skeleton because:
- Universal DevOps tooling — no runtime dependencies beyond the Terraform binary.
- Explicit resource graphs make security review and cost estimation straightforward.
- Native support for `terraform plan` output in CI pipelines.
- CDK can be adopted later if the team prefers TypeScript/Python abstraction.

## Region

All resources target **ap-south-1 (Mumbai)**.

## Layout

```
infrastructure/
  providers.tf          # AWS provider, backend config
  variables.tf          # Input variables
  main.tf               # Root module wiring
  networking.tf         # VPC, subnets, routing
  compute.tf            # ECS Fargate (API + worker)
  data.tf               # RDS, ElastiCache
  storage.tf            # S3
  loadbalancer.tf       # ALB, Route 53, ACM
  outputs.tf            # Exported values
  environments/
    dev.tfvars
    staging.tfvars
    prod.tfvars
```

## Environments

| Environment | Workspace   | Purpose                     |
|-------------|-------------|-----------------------------|
| dev         | dev         | Developer sandbox           |
| staging     | staging     | QA / integration testing      |
| prod        | prod        | Production workload         |

## Quick Start

```bash
cd infrastructure

# Select environment
terraform workspace select dev || terraform workspace new dev

# Plan
terraform plan -var-file=environments/dev.tfvars

# Apply (when ready)
terraform apply -var-file=environments/dev.tfvars
```

## Cost Estimate (Monthly, skeleton stage)

> These are rough on-demand estimates. Use `terraform plan` + Infracost for precise numbers.

| Resource                 | Dev/Staging           | Production (initial) |
|--------------------------|-----------------------|----------------------|
| VPC (2 AZs)              | Free                  | Free                 |
| ALB                      | ~$20                  | ~$22                 |
| ECS Fargate (API)        | 0.25 vCPU / 0.5 GB    | 0.5 vCPU / 1 GB      |
| ECS Fargate (Worker)     | 0.25 vCPU / 0.5 GB    | 0.5 vCPU / 1 GB      |
| RDS PostgreSQL           | db.t3.micro (~$13)    | db.t3.small (~$26)   |
| ElastiCache Redis        | cache.t3.micro (~$11) | cache.t3.small (~$22)|
| S3                       | ~$0.50                | ~$2                  |
| Route 53 (1 hosted zone) | ~$0.50                | ~$0.50               |
| ACM (public TLS)         | Free                  | Free                 |
| **Estimated Total**      | **~$45–55**          | **~$75–100**        |

Free Tier eligible: db.t3.micro RDS for 12 months (new AWS accounts).

## Disaster Recovery Targets

| Metric | Target | Notes |
|--------|--------|-------|
| RPO    | < 1 hour | Automated RDS snapshots every 30 min + logical replication in future phase |
| RTO    | < 2 hours | Fargate tasks restart automatically; DB restore from snapshot for region failure |

## Security Notes

- All secrets (DB password, Redis auth, JWT secret) are injected via AWS Secrets Manager references in ECS task definitions.
- No hard-coded credentials in this repository.
- Private subnets host RDS and ElastiCache; only ALB and NAT Gateway egress live in public subnets.
- Security groups use least-privilege rules.

## Next Steps (Post-Skeleton)

1. Wire to CI/CD: `terraform plan` on PR, `terraform apply` on merge to main.
2. Add CloudWatch log groups + alarms.
3. Add S3 lifecycle rules for exports / photos.
4. Enable RDS encryption and automated backups in production.
5. Add WAF rules in front of ALB.
