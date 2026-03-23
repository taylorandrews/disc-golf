# Runbook

Day-to-day operations for the disc-golf AWS stack.

For architecture details see [architecture.md](architecture.md).
For ETL / data pipeline details see [etl.md](etl.md).

---

## Prerequisites

```bash
brew install awscli
npm install -g aws-cdk
# Docker Desktop must be running for cdk deploy (Lambda bundling)
aws sts get-caller-identity   # should return account 368365885895
```

---

## Starting a session

### After `make stop` (fast — ~3 min)

```bash
make start
```

This starts RDS, waits for it to be available, then scales ECS back to 1.
The Lambda ETL runs on its own schedule (06:00 UTC) — no action needed.

### After `make destroy` (full rebuild — ~20 min)

Docker must be running (Lambda bundling requires it).

```bash
# 1. Redeploy all stacks
cd infra && cdk deploy --all

# 2. Push Docker image + start ECS
make build-push

# 3. Run all schema migrations against RDS
make migrate-prod

# 4. Seed legacy data (~10 min, 194 rounds)
#    alembic upgrade head runs the legacy load migration automatically via migrate-prod

# 5. Seed 2026 tournament metadata + load available rounds
make seed-and-etl

# 6. Deploy Lambda code (CDK bundles it, but deploy-etl is faster for subsequent updates)
make deploy-etl
```

> **S3 bucket note:** The S3 data lake has `RemovalPolicy.RETAIN` and survives
> `make destroy`. On the next `cdk deploy`, CloudFormation will fail trying to
> create a bucket with the same name. Fix:
> ```bash
> aws s3 rm s3://disc-golf-data-lake-368365885895 --recursive
> aws s3api delete-bucket --bucket disc-golf-data-lake-368365885895 --region us-east-1
> # then after cdk deploy:
> make upload-legacy
> ```

> **Seeding gotcha:** `make migrate-prod` reads credentials from Secrets Manager using
> `DB_SECRET_ARN` and `DB_HOST` from your `.env` file. If those aren't set, run
> `make print-rds-config` to get the values and add them to `.env`.

---

## Ending a session

```bash
make stop       # scales ECS to 0, stops RDS — preserves all data, costs ~$16/month (ALB only)
make destroy    # tears down everything — costs $0, but requires full rebuild next session
```

`make stop` is strongly recommended for day-to-day. Use `make destroy` only for extended breaks.

---

## Check status

```bash
make status
```

---

## ETL operations

```bash
make invoke-etl    # manually trigger nightly Lambda (RDS must be running)
make logs-etl      # tail Lambda CloudWatch logs (last 30 min)
make deploy-etl    # repackage + upload Lambda code without Docker/CDK (fast — ~30 sec)
make migrate-prod  # run Alembic migrations against RDS (reads creds from Secrets Manager)
```

**Adding a 2026 tournament:**
1. Add a row to `data/seed/2026_tournaments.csv` (get ID from `pdga.com/tour/event/{id}`)
2. `make seed-and-etl` to enrich metadata + load any available rounds
3. After the event, add `jomez_playlist_url` to the CSV row and re-run `make seed-and-etl`

**After any ETL code change:**
```bash
make deploy-etl    # zip + upload to Lambda
make invoke-etl    # test immediately (no need to wait for 06:00 UTC cron)
```

**After any schema change (new Alembic migration):**
```bash
make migrate-prod  # runs against RDS via Secrets Manager
```

---

## Deploy app changes

```bash
git push origin main   # GitHub Actions builds + deploys ECS automatically
```

> Note: `git push` only deploys the Streamlit app (ECS). It does NOT redeploy the Lambda.
> Use `make deploy-etl` separately after ETL code changes.

---

## Teardown

```bash
make destroy
```

Destroys all infra except the S3 data lake bucket (RETAIN). See "After make destroy" above to rebuild.

---

## First-time setup (one time only)

```bash
cd infra
pip install -r requirements.txt
cdk bootstrap aws://368365885895/us-east-1
cdk deploy --all
make build-push
make migrate-prod    # runs all Alembic migrations (schema + legacy data load)
make seed-and-etl    # seed 2026 tournament metadata + load available rounds
make upload-legacy   # archive 2020-2025 JSONs to S3 (one time)
```

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| ECS tasks failing | Check CloudWatch `/ecs/disc-golf`. Usually ECR empty → `make build-push` |
| `cdk deploy` fails: bucket already exists | Delete S3 bucket (see S3 note above) |
| `cdk deploy` fails: OIDC provider exists | See comment in `infra/stacks/app_stack.py` |
| Site shows "relation tournament does not exist" | RDS not migrated — run `make migrate-prod` |
| `make migrate-prod` fails | Check `DB_SECRET_ARN` and `DB_HOST` in `.env` — run `make print-rds-config` to get values |
| Lambda logs "RDS unavailable" | Run `make start` first |
| `make invoke-etl` loads 0 rounds | Tournament not registered, round not started yet, or ETL code stale — try `make deploy-etl` first |
| Lambda logs "Parsed 0 videos from JomezPro playlist" | Check that `jomez_playlist_url` is set for the tournament and the URL is a valid YouTube playlist |
| New Lambda code not taking effect | Lambda update may be in progress — wait 30 sec and retry |
