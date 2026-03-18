# ─────────────────────────────────────────────────────────────────────────────
# disc-golf — AWS infrastructure management
#
# Commands:
#   make start      → Start RDS + scale ECS to 1  (use after make stop)
#   make stop       → Scale ECS to 0 + stop RDS   (eliminates hourly charges)
#   make status     → Show current ECS and RDS state
#   make build-push → Build Docker image and push to ECR (initial deploy / manual push)
#   make destroy    → Tear down ALL infrastructure via CDK  ⚠ deletes data
# ─────────────────────────────────────────────────────────────────────────────

AWS_REGION   := us-east-1
ACCOUNT_ID   := 368365885895
ECR_REGISTRY := $(ACCOUNT_ID).dkr.ecr.$(AWS_REGION).amazonaws.com
ECR_REPO     := disc-golf-app

# These names are set explicitly in the CDK stacks — keep in sync if changed.
CLUSTER := disc-golf-cluster
SERVICE := disc-golf-service
DB_ID   := disc-golf-db

.PHONY: start stop status build-push destroy

## start: Start RDS and scale ECS service to 1  (takes 2–5 min for RDS to be ready)
start:
	@echo "Starting RDS instance (may take 2–5 minutes)..."
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

## stop: Scale ECS to 0 and stop RDS — eliminates hourly compute charges
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
	@echo "── ECS Service ──────────────────────────────────────"
	@aws ecs describe-services \
	    --cluster $(CLUSTER) \
	    --services $(SERVICE) \
	    --region $(AWS_REGION) \
	    --query 'services[0].{Status:status,Running:runningCount,Desired:desiredCount}' \
	    --output table \
	    --no-cli-pager
	@echo ""
	@echo "── RDS Instance ─────────────────────────────────────"
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
	docker build -t $(ECR_REGISTRY)/$(ECR_REPO):latest .
	docker push $(ECR_REGISTRY)/$(ECR_REPO):latest
	aws ecs update-service \
	    --cluster $(CLUSTER) \
	    --service $(SERVICE) \
	    --force-new-deployment \
	    --region $(AWS_REGION) \
	    --no-cli-pager
	@echo "Done. New deployment initiated — live in ~1 minute."

## destroy: Tear down ALL AWS infrastructure. Data will be permanently deleted.
destroy:
	@echo "WARNING: This permanently deletes all infrastructure and database data."
	@echo "         Data can be restored by re-running Alembic migrations locally."
	@read -p "Type 'yes' to confirm: " confirm && [ "$$confirm" = "yes" ] || exit 1
	cd infra && cdk destroy --all --force
