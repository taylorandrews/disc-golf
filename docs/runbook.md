# Runbook — disc-golf infrastructure

How to set up, deploy, operate, and tear down the AWS stack.

---

## Prerequisites

Install these once on your machine if not already present:

```bash
# AWS CLI
brew install awscli

# AWS CDK CLI
npm install -g aws-cdk

# Docker Desktop — must be running when building images
# https://www.docker.com/products/docker-desktop
```

Confirm your AWS credentials are working:
```bash
aws sts get-caller-identity
# Should return account 368365885895
```

---

## Initial setup (one time only)

### 1. Bootstrap CDK

CDK needs an S3 bucket and IAM roles in your account to manage deployments.
Run this once per account/region:

```bash
cd infra
pip install -r requirements.txt       # install CDK Python libraries
cdk bootstrap aws://368365885895/us-east-1
```

### 2. Deploy all stacks

```bash
cd infra
cdk deploy --all
```

This takes ~10 minutes (RDS provisioning is the slow part). CDK will print
progress for each stack: DiscGolfNetwork → DiscGolfDatabase → DiscGolfApp.

When complete, note the CloudFormation outputs — you'll need them shortly:
- `DiscGolfDatabase.DbEndpoint` — RDS hostname
- `DiscGolfDatabase.DbSecretArn` — Secrets Manager ARN for DB credentials
- `DiscGolfApp.AlbUrl` — public URL for the site
- `DiscGolfApp.GithubActionsRoleArn` — should be `arn:aws:iam::368365885895:role/disc-golf-github-actions`

### 3. Push the initial Docker image

GitHub Actions won't have run yet, so the ECR repo is empty and ECS can't
start tasks. Build and push manually:

```bash
# From repo root
make build-push
```

The site will be live at the `AlbUrl` output within ~1 minute.

### 4. Seed the database

Run Alembic migrations from your local machine pointed at the new RDS instance.

**Get the RDS endpoint** (already printed as `DiscGolfDatabase.DbEndpoint`):
```bash
aws cloudformation describe-stacks --stack-name DiscGolfDatabase \
    --query 'Stacks[0].Outputs[?OutputKey==`DbEndpoint`].OutputValue' \
    --output text
```

**Get the DB password from Secrets Manager:**
```bash
aws secretsmanager get-secret-value \
    --secret-id $(aws cloudformation describe-stacks --stack-name DiscGolfDatabase \
        --query 'Stacks[0].Outputs[?OutputKey==`DbSecretArn`].OutputValue' \
        --output text) \
    --query 'SecretString' \
    --output text
# Output is JSON — copy the "password" field value
```

**Run migrations:**
```bash
DATABASE_URL=postgresql://postgres:<PASSWORD>@<RDS_ENDPOINT>:5432/pdga_data \
    alembic upgrade head
```

This loads all three migrations:
1. Creates the 5 base tables
2. Loads all data from `data/pdga/` JSON files
3. Creates the 4 reporting views

> **Important:** The PDGA JSON files in `data/pdga/` have been manually edited
> to fix data quality issues (missing required fields, inconsistent formatting)
> from the raw API. Do not re-fetch and overwrite these files without re-applying
> those fixes, or migration 2 will fail with NOT NULL constraint errors.

---

## Normal operation

### Start a session

If you stopped the infrastructure at the end of a previous session:

```bash
make start
```

This starts the RDS instance (~3 min) and scales the ECS service back to 1.
The site will be live within ~1 minute of the command completing.

### Check current state

```bash
make status
```

### Stop at end of session (eliminates hourly charges)

```bash
make stop
```

This scales ECS to 0 tasks and stops the RDS instance. While stopped:
- No compute charges (ECS, RDS)
- ALB base charge still accrues (~$0.53/day)
- ECR storage accrues at minimal rate

Approximate cost while stopped: ~$16/month (ALB only).
Approximate cost while running: ~$50/month.

---

## Deploying code changes

Push to `main`. GitHub Actions builds the Docker image, pushes it to ECR,
and triggers a rolling ECS redeployment. The site stays live during the rollout.

```bash
git push origin main
```

Monitor the deployment:
```bash
# GitHub Actions progress
open https://github.com/taylorandrews/disc-golf/actions

# ECS service status
make status
```

---

## Tearing down completely

```bash
make destroy
```

This runs `cdk destroy --all` and removes:
- ECS cluster, service, and tasks
- ECR repository and all Docker images
- Application Load Balancer
- RDS instance and all data
- VPC, subnets, and security groups
- Secrets Manager secret
- IAM OIDC provider and role
- CloudWatch log groups

> Data can always be restored by re-running `alembic upgrade head` against a
> fresh RDS instance (step 4 of initial setup), provided you still have the
> `data/pdga/` JSON files locally.

To re-deploy after a destroy: start from step 2 of Initial setup.

---

## Adding a custom domain (disc-golf-data.com)

When ready to connect the domain (deferred from Phase 1):

1. Register `disc-golf-data.com` via GoDaddy or Route 53.
2. If using Route 53: create a hosted zone, request an ACM certificate.
3. If using an external registrar: request ACM cert via DNS validation,
   add the CNAME records your registrar provides.
4. Add an HTTPS listener (port 443) to the ALB in `app_stack.py` referencing
   the certificate ARN, then `cdk deploy DiscGolfApp`.
5. Point the domain's A record at the ALB DNS name.

---

## Troubleshooting

**ECS tasks keep failing to start**
- Check CloudWatch Logs: AWS Console → CloudWatch → Log groups → `/ecs/disc-golf`
- Most common cause: image not yet pushed to ECR → run `make build-push`
- Second most common: DB not yet available → run `make start` and wait for RDS

**`cdk deploy` fails with "already exists" on the GitHub OIDC provider**
- You have a GitHub OIDC provider from another project. See the comment in
  `infra/stacks/app_stack.py` for how to import the existing one instead.

**Migration fails with NOT NULL errors**
- A PDGA JSON file has a field that was null in the raw API response.
- Inspect the error to identify which file and field.
- Manually set the field to an appropriate default in the JSON and re-run.

**Can't connect to RDS from local machine**
- Confirm RDS is running: `make status`
- Confirm you're using the correct endpoint (from CloudFormation outputs)
- The security group allows all IPs on 5432 — connection issues are typically
  a wrong endpoint or wrong password, not a firewall issue
