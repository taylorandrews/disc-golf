# -----------------------------------------------------------------------------
# disc-golf -- AWS infrastructure management
#
# Commands:
#   make start         -> Start RDS + scale ECS to 1  (use after make stop)
#   make stop          -> Scale ECS to 0 + stop RDS   (eliminates hourly charges)
#   make status        -> Show current ECS and RDS state
#   make build-push    -> Build Docker image and push to ECR (initial deploy / manual push)
#   make invoke-etl    -> Manually run the nightly ETL Lambda
#   make logs-etl      -> Tail the ETL Lambda's CloudWatch log group
#   make upload-legacy -> One-time upload of data/pdga/ JSONs to S3 legacy prefix
#   make destroy       -> Tear down ALL infrastructure via CDK  [warning: deletes data]
# -----------------------------------------------------------------------------

AWS_REGION   := us-east-1
ACCOUNT_ID   := 368365885895
ECR_REGISTRY := $(ACCOUNT_ID).dkr.ecr.$(AWS_REGION).amazonaws.com
ECR_REPO     := disc-golf-app
S3_BUCKET    := disc-golf-data-lake-$(ACCOUNT_ID)

# These names are set explicitly in the CDK stacks -- keep in sync if changed.
CLUSTER      := disc-golf-cluster
SERVICE      := disc-golf-service
DB_ID        := disc-golf-db
ETL_FUNCTION := disc-golf-nightly-etl

.PHONY: start stop status build-push invoke-etl logs-etl upload-legacy destroy seed-and-etl print-rds-config migrate-prod

## start: Start RDS and scale ECS service to 1  (takes 2-5 min for RDS to be ready)
start:
	@echo "Starting RDS instance (may take 2-5 minutes)..."
	aws rds start-db-instance \
	    --db-instance-identifier $(DB_ID) \
	    --region $(AWS_REGION) \
	    --no-cli-pager
	@echo "Waiting for RDS to be available..."
	aws rds wait db-instance-available \
	    --db-instance-identifier $(DB_ID) \
	    --region $(AWS_REGION)
	@echo "Scaling ECS service to 1..."
	aws ecs update-service \
	    --cluster $(CLUSTER) \
	    --service $(SERVICE) \
	    --desired-count 1 \
	    --region $(AWS_REGION) \
	    --no-cli-pager
	@echo "Done. Site should be live at the ALB URL within ~1 minute."

## stop: Scale ECS to 0 and stop RDS -- eliminates hourly compute charges
stop:
	@echo "Scaling ECS service to 0..."
	aws ecs update-service \
	    --cluster $(CLUSTER) \
	    --service $(SERVICE) \
	    --desired-count 0 \
	    --region $(AWS_REGION) \
	    --no-cli-pager
	@echo "Stopping RDS instance (may take a few minutes)..."
	aws rds stop-db-instance \
	    --db-instance-identifier $(DB_ID) \
	    --region $(AWS_REGION) \
	    --no-cli-pager
	@echo "Done. No hourly charges while stopped."

## status: Show current ECS service and RDS instance state
status:
	@echo ""
	@echo "-- ECS Service ------------------------------------------------------"
	@aws ecs describe-services \
	    --cluster $(CLUSTER) \
	    --services $(SERVICE) \
	    --region $(AWS_REGION) \
	    --query 'services[0].{Status:status,Running:runningCount,Desired:desiredCount}' \
	    --output table \
	    --no-cli-pager
	@echo ""
	@echo "-- RDS Instance -----------------------------------------------------"
	@aws rds describe-db-instances \
	    --db-instance-identifier $(DB_ID) \
	    --region $(AWS_REGION) \
	    --query 'DBInstances[0].{Status:DBInstanceStatus,Class:DBInstanceClass,Endpoint:Endpoint.Address}' \
	    --output table \
	    --no-cli-pager

## build-push: Build Docker image and push to ECR, then force ECS redeployment.
##             Use this for the initial deploy or if you want to push manually
##             without waiting for GitHub Actions.
build-push:
	aws ecr get-login-password --region $(AWS_REGION) | \
	    docker login --username AWS --password-stdin $(ECR_REGISTRY)
	docker build --platform linux/amd64 -t $(ECR_REGISTRY)/$(ECR_REPO):latest .
	docker push $(ECR_REGISTRY)/$(ECR_REPO):latest
	aws ecs update-service \
	    --cluster $(CLUSTER) \
	    --service $(SERVICE) \
	    --desired-count 1 \
	    --force-new-deployment \
	    --region $(AWS_REGION) \
	    --no-cli-pager
	@echo "Done. New deployment initiated -- live in ~1 minute."

## invoke-etl: Manually trigger the nightly ETL Lambda and stream its output.
##             RDS must be running (make start) before invoking.
invoke-etl:
	@echo "Invoking $(ETL_FUNCTION)..."
	aws lambda invoke \
	    --function-name $(ETL_FUNCTION) \
	    --region $(AWS_REGION) \
	    --log-type Tail \
	    --query 'LogResult' \
	    --output text \
	    /tmp/etl-response.json | base64 --decode
	@echo ""
	@echo "Response:"
	@cat /tmp/etl-response.json

## logs-etl: Tail the ETL Lambda CloudWatch log group (last 30 minutes).
logs-etl:
	aws logs tail /aws/lambda/$(ETL_FUNCTION) \
	    --region $(AWS_REGION) \
	    --since 30m \
	    --follow

## upload-legacy: One-time upload of local data/pdga/ JSONs to S3 legacy prefix.
##                Run once after the S3 bucket is created (cdk deploy).
##                Safe to re-run -- S3 sync skips files that are already present.
upload-legacy:
	@echo "Syncing data/pdga/ to s3://$(S3_BUCKET)/raw/pdga/legacy/ ..."
	aws s3 sync data/pdga/ s3://$(S3_BUCKET)/raw/pdga/legacy/ \
	    --region $(AWS_REGION) \
	    --no-cli-pager
	@echo "Done."

## seed-and-etl: Seed tournament table in RDS then run the ETL Lambda.
##               Run this after adding rows to data/seed/{year}_tournaments.csv.
##               RDS must be running (make start) before invoking.
seed-and-etl:
	@echo "Seeding tournament table in RDS..."
	python scripts/enrich_tournaments.py --prod
	@echo ""
	@echo "Running ETL Lambda..."
	$(MAKE) invoke-etl

## print-rds-config: Print DB_SECRET_ARN and DB_HOST from CloudFormation.
##                   Copy these into your .env file to enable --prod mode.
print-rds-config:
	@echo ""
	@echo "Paste these into your .env file:"
	@echo ""
	@printf "DB_SECRET_ARN=" && aws cloudformation describe-stacks \
	    --stack-name DiscGolfDatabase \
	    --region $(AWS_REGION) \
	    --query "Stacks[0].Outputs[?OutputKey=='DbSecretArn'].OutputValue" \
	    --output text \
	    --no-cli-pager
	@printf "DB_HOST=" && aws cloudformation describe-stacks \
	    --stack-name DiscGolfDatabase \
	    --region $(AWS_REGION) \
	    --query "Stacks[0].Outputs[?OutputKey=='DbEndpoint'].OutputValue" \
	    --output text \
	    --no-cli-pager
	@echo ""

## migrate-prod: Run alembic upgrade head against RDS using Secrets Manager credentials.
##               Requires DB_SECRET_ARN and DB_HOST in .env (run make print-rds-config first).
##               RDS must be running (make start) before invoking.
migrate-prod:
	@echo "Fetching RDS credentials and running alembic upgrade head..."
	@SECRET=$$(aws secretsmanager get-secret-value \
	    --secret-id $$(grep DB_SECRET_ARN .env | cut -d= -f2) \
	    --region $(AWS_REGION) \
	    --query SecretString --output text --no-cli-pager) && \
	DB_USER=$$(echo "$$SECRET" | python3 -c "import sys,json; print(json.load(sys.stdin)['username'])") && \
	DB_PASS=$$(echo "$$SECRET" | python3 -c "import sys,json; print(json.load(sys.stdin)['password'])") && \
	DB_HOST=$$(grep DB_HOST .env | cut -d= -f2) && \
	DATABASE_URL="postgresql+psycopg2://$$DB_USER:$$DB_PASS@$$DB_HOST:5432/pdga_data" \
	    alembic upgrade head
	@echo "Done."

## destroy: Tear down ALL AWS infrastructure. Data will be permanently deleted.
##          Note: the S3 data lake bucket has RemovalPolicy.RETAIN and will NOT
##          be deleted by this command -- remove it manually if desired.
destroy:
	@echo "WARNING: This permanently deletes all infrastructure and database data."
	@echo "         The S3 data lake bucket is retained and must be deleted manually."
	@echo "         Data can be restored by re-running Alembic migrations locally."
	@read -p "Type 'yes' to confirm: " confirm && [ "$$confirm" = "yes" ] || exit 1
	cd infra && cdk destroy --all --force
