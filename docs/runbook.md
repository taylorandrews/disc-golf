# Runbook

Day-to-day operations for the disc-golf AWS stack.

For architecture details see [architecture.md](architecture.md).
For ETL / data pipeline details see [etl.md](etl.md).

---

## Prerequisites

```bash
brew install awscli
npm install -g aws-cdk
# Docker Desktop must be running for image builds and cdk deploy
aws sts get-caller-identity   # should return account 368365885895
```

---

## Starting a session

### After `make stop` (fast — ~3 min)

```bash
make start
```

### After `make destroy` (full rebuild — ~20 min)

Docker must be running (Lambda bundling requires it).

```bash
# 1. Redeploy all stacks
cd infra && cdk deploy --all

# 2. Push Docker image + start ECS
make build-push

# 3. Get fresh DB credentials
aws secretsmanager get-secret-value \
    --secret-id $(aws cloudformation describe-stacks --stack-name DiscGolfDatabase \
        --query 'Stacks[0].Outputs[?OutputKey==`DbSecretArn`].OutputValue' \
        --output text) \
    --query 'SecretString' --output text
# copy the "password" field

# 4. Seed legacy data (~10 min, 194 rounds)
DATABASE_URL=postgresql+psycopg://postgres:<PASSWORD>@<RDS_ENDPOINT>:5432/pdga_data \
    alembic upgrade head

# 5. Seed 2026 tournament metadata
DATABASE_URL=postgresql+psycopg://postgres:<PASSWORD>@<RDS_ENDPOINT>:5432/pdga_data \
    python scripts/enrich_2026_tournaments.py

# 6. Load any 2026 rounds already available
make invoke-etl
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

> **Seeding gotcha:** Always prefix `alembic upgrade head` with `DATABASE_URL=...`.
> Without it, Alembic silently hits localhost (already at head) and leaves RDS empty.

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
```

**Adding a 2026 tournament:**
1. Add a row to `data/seed/2026_tournaments.csv` (get ID from `pdga.com/tour/event/{id}`)
2. `DATABASE_URL=... python scripts/enrich_2026_tournaments.py`
3. `make invoke-etl` to load rounds immediately, or wait for nightly cron

---

## Deploy code changes

```bash
git push origin main   # GitHub Actions builds + deploys automatically
```

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
# then follow steps 3-6 of "After make destroy" above
make upload-legacy   # archive legacy JSONs to S3 (one time)
```

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| ECS tasks failing | Check CloudWatch `/ecs/disc-golf`. Usually ECR empty → `make build-push` |
| `cdk deploy` fails: bucket already exists | Delete S3 bucket (see S3 note above) |
| `cdk deploy` fails: OIDC provider exists | See comment in `infra/stacks/app_stack.py` |
| Site shows "relation tournament does not exist" | RDS not seeded — run `alembic upgrade head` with RDS `DATABASE_URL` |
| Alembic ran but RDS still empty | You forgot the `DATABASE_URL=...` prefix — it ran against localhost |
| Lambda logs "RDS unavailable" | Run `make start` first |
| `make invoke-etl` loads 0 rounds | Tournament not registered, or round not started yet |
