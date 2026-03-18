#!/usr/bin/env python3
"""
CDK app entrypoint for disc-golf AWS infrastructure.

Stacks (deployed in dependency order, CDK resolves this automatically):
  DiscGolfNetwork  — VPC, subnets, security groups
  DiscGolfDatabase — RDS PostgreSQL instance + Secrets Manager credentials
  DiscGolfApp      — ECR repo, ECS Fargate service, ALB, GitHub OIDC role

Deploy:   cd infra && cdk deploy --all
Destroy:  cd infra && cdk destroy --all   (or: make destroy from repo root)
"""
import aws_cdk as cdk

from stacks.network_stack import NetworkStack
from stacks.database_stack import DatabaseStack
from stacks.app_stack import AppStack

app = cdk.App()

env = cdk.Environment(account="368365885895", region="us-east-1")

network = NetworkStack(app, "DiscGolfNetwork", env=env)

database = DatabaseStack(
    app,
    "DiscGolfDatabase",
    vpc=network.vpc,
    db_security_group=network.db_security_group,
    env=env,
)

AppStack(
    app,
    "DiscGolfApp",
    vpc=network.vpc,
    app_security_group=network.app_security_group,
    alb_security_group=network.alb_security_group,
    db_instance=database.db_instance,
    db_secret=database.db_secret,
    env=env,
)

app.synth()
