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

# Docker Desktop — must be running when building images and when running cdk deploy
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
- `DiscGolfApp.DataLakeBucket` — S3 bucket name
- `DiscGolfApp.EtlFunctionArn` — Lambda ARN for manual ETL invocation

### 3. Push the initial Docker image

GitHub Actions won't have run yet, so the ECR repo is empty and ECS can't
start tasks. Build and push manually:

```bash
# From repo root
make build-push
```

The site will be live at the `AlbUrl` output within ~1 minute.

### 4. Seed the database (legacy 2020-2025 data)

Run Alembic migrations from your local machine pointed at the new RDS instance.

**Get the RDS endpoint and password in one shot:**
```bash
aws cloudformation describe-stacks --stack-name DiscGolfDatabase \
    --query 'Stacks[0].Outputs' --output table

aws secretsmanager get-secret-value \
    --secret-id $(aws cloudformation describe-stacks --stack-name DiscGolfDatabase \
        --query 'Stacks[0].Outputs[?OutputKey==`DbSecretArn`].OutputValue' \
        --output text) \
    --query 'SecretString' --output text
# Copy the "password" field from the JSON output
```

**Run migrations:**
```bash
DATABASE_URL=postgresql+psycopg://postgres:<PASSWORD>@<RDS_ENDPOINT>:5432/pdga_data \
    alembic upgrade head
```

> **Gotcha:** You must prefix the command with `DATABASE_URL=...` as shown.
> Do not rely on sourcing `.env` first — `.env` points to `localhost` for local dev.
> Without the prefix, Alembic silently migrates the local DB and leaves RDS untouched.
> The site will show "relation tournament does not exist" until RDS is seeded.

This loads all three migrations (~10 minutes for 194 legacy rounds):
1. Creates the 5 base tables
2. Loads all legacy JSON data from `data/pdga/`
3. Creates the 4 reporting views

> **Important:** The PDGA JSON files in `data/pdga/` have been manually edited
> to fix data quality issues. Do not re-fetch and overwrite them without re-applying
> those fixes, or migration 2 will fail with NOT NULL constraint errors.

### 5. Upload legacy JSONs to S3 (one time only)

```bash
make upload-legacy
```

Syncs `data/pdga/` to `s3://disc-golf-data-lake-368365885895/raw/pdga/legacy/`.
Safe to re-run. The S3 bucket has `RemovalPolicy.RETAIN` and survives teardowns,
so this only needs to be run once ever (or after manually deleting the bucket).

### 6. Seed 2026 tournament metadata

Add any known 2026 tournament IDs to `data/seed/2026_tournaments.csv`, then:

```bash
DATABASE_URL=postgresql+psycopg://postgres:<PASSWORD>@<RDS_ENDPOINT>:5432/pdga_data \
    python scripts/enrich_2026_tournaments.py
```

Safe to re-run. If the CSV is empty, this step is a no-op.

### 7. Load available 2026 round data

```bash
make invoke-etl
```

The Lambda checks which rounds are already in RDS and fetches only new ones.
If no 2026 tournaments are registered or none have rounds yet, this is a no-op.

---

## Normal operation

You have two session patterns depending on how you ended your last session.

---

### Pattern A: Resuming after `make stop` (fast — ~3 min)

Use this if you ended the previous session with `make stop`. RDS data is intact.

```bash
make start
```

Done. The site is live within ~1 minute of RDS becoming available.

---

### Pattern B: Resuming after `make destroy` (full rebuild — ~20 min)

Use this if you ended with `make destroy`. Everything must be recreated and
the database re-seeded from scratch.

> **S3 bucket note:** The S3 data lake bucket has `RemovalPolicy.RETAIN` and
> survives `make destroy`. On the next `cdk deploy`, CloudFormation will try
> to create a bucket with the same fixed name and will fail if the bucket still
> exists. Delete it first if you want a clean deploy, or just leave it — CDK
> can be patched to import the existing bucket instead.
>
> Simplest workaround: before running `cdk deploy`, empty and delete the bucket:
> ```bash
> aws s3 rm s3://disc-golf-data-lake-368365885895 --recursive
> aws s3api delete-bucket --bucket disc-golf-data-lake-368365885895 --region us-east-1
> ```
> Then re-run `make upload-legacy` after deploying to restore the archive.

**Step 1 — Redeploy all stacks** (~10 min, Docker must be running for Lambda bundling):
```bash
cd infra && cdk deploy --all
```

**Step 2 — Push Docker image and start ECS**:
```bash
make build-push
```

**Step 3 — Get fresh RDS credentials** (new secret ARN each deploy):
```bash
aws secretsmanager get-secret-value \
    --secret-id $(aws cloudformation describe-stacks --stack-name DiscGolfDatabase \
        --query 'Stacks[0].Outputs[?OutputKey==`DbSecretArn`].OutputValue' \
        --output text) \
    --query 'SecretString' --output text
```

**Step 4 — Seed the database** (takes ~10 min for 194 legacy rounds):
```bash
DATABASE_URL=postgresql+psycopg://postgres:<PASSWORD>@<RDS_ENDPOINT>:5432/pdga_data \
    alembic upgrade head
```

**Step 5 — Seed 2026 tournament metadata**:
```bash
DATABASE_URL=postgresql+psycopg://postgres:<PASSWORD>@<RDS_ENDPOINT>:5432/pdga_data \
    python scripts/enrich_2026_tournaments.py
```

**Step 6 — Upload legacy JSONs to S3** (if you deleted the bucket in the workaround above):
```bash
make upload-legacy
```

**Step 7 — Load any new 2026 rounds**:
```bash
make invoke-etl
```

---

### Choosing between patterns

| | `make stop` / `make start` | `make destroy` / full rebuild |
|---|---|---|
| Resume time | ~3 min | ~20 min |
| Data preserved | Yes | No — must re-seed |
| Cost while inactive | ~$16/month (ALB) | $0 |
| S3 data preserved | Yes | Yes (RETAIN) — but see bucket note above |

For active development sessions, `make stop` is strongly recommended.
`make destroy` makes sense for longer breaks (weeks+) where the $16/month ALB
cost is worth avoiding.

---

### Check current state

```bash
make status
```

### End a session (recommended — stops RDS + ECS, preserves data)

```bash
make stop
```

This scales ECS to 0 tasks and stops the RDS instance. While stopped:
- No compute or RDS charges
- ALB base charge still accrues (~$0.53/day = ~$16/month)
- Data is fully preserved — resume with `make start`

---

## ETL operations (2026 season)

### Manually trigger the nightly ETL

Useful during a tournament weekend to pull in rounds as they complete.
RDS must be running (`make start`) before invoking.

```bash
make invoke-etl
```

Output is streamed from the Lambda log. The response body shows how many
new rounds were loaded.

### View ETL logs

```bash
make logs-etl
```

Tails the Lambda CloudWatch log group for the last 30 minutes.

### Add a new 2026 tournament

1. Find the tournament ID from the PDGA URL: `pdga.com/tour/event/{id}`
2. Add a row to `data/seed/2026_tournaments.csv`:
   ```
   tournament_id,name,start_date,classification,is_worlds,total_rounds,has_finals
   99999,My Tournament,2026-04-01,Elite Series,0,4,1
   ```
3. Run the enrichment script (auto-fills `long_name` from PDGA API):
   ```bash
   DATABASE_URL=postgresql+psycopg://postgres:<pw>@<host>:5432/pdga_data \
       python scripts/enrich_2026_tournaments.py
   ```
4. The nightly Lambda will pick up rounds automatically. Or run `make invoke-etl` now.

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
- RDS instance and **all database data**
- VPC, subnets, and security groups
- Secrets Manager secret
- IAM OIDC provider and role
- Lambda function and EventBridge rule
- CloudWatch log groups

**Not removed** (RemovalPolicy.RETAIN):
- S3 data lake bucket and all archived JSON files

To resume after a destroy, follow Pattern B above.

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

**`cdk deploy` fails with "already exists" on the S3 bucket**
- The data lake bucket was retained from a previous `make destroy`.
- Delete it first: `aws s3 rm s3://disc-golf-data-lake-368365885895 --recursive && aws s3api delete-bucket --bucket disc-golf-data-lake-368365885895 --region us-east-1`
- Then re-run `cdk deploy --all` and `make upload-legacy` afterward.

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

**ETL Lambda logs "RDS unavailable"**
- RDS is stopped. Run `make start` to bring it up, then `make invoke-etl`.

**ETL loads 0 new rounds despite a tournament being in progress**
- The round may not have scores yet (pre-round). Try again after tee times.
- Check if the tournament is registered in `data/seed/2026_tournaments.csv`
  and seeded via `scripts/enrich_2026_tournaments.py`.
