"""
AppStack — ECR repository, ECS Fargate service, ALB, GitHub OIDC role,
           S3 data lake bucket, and nightly ETL Lambda + EventBridge rule.

Fargate task: 0.5 vCPU / 1 GB RAM
  Sized for comfortable Streamlit operation. Scale up by editing cpu/memory_limit_mib
  and running cdk deploy if the app feels sluggish.

DATABASE_URL assembly:
  ECS injects DB_USER and DB_PASSWORD from Secrets Manager at task start.
  DB_HOST, DB_PORT, and DB_NAME are non-sensitive plain environment variables.
  entrypoint.sh assembles DATABASE_URL from these before starting Streamlit,
  matching the format db_config.py already expects.

GitHub OIDC:
  Creates an IAM Identity Provider for GitHub Actions so the deploy workflow
  can assume an IAM role without storing AWS credentials in GitHub Secrets.
  The role is scoped to pushes on the main branch of taylorandrews/disc-golf.

  If you already have a GitHub OIDC provider in this AWS account (from another
  project), CDK will error on the duplicate. Replace the OpenIdConnectProvider(...)
  block with:
    iam.OpenIdConnectProvider.from_open_id_connect_provider_arn(
        self, "GithubOidc",
        "arn:aws:iam::368365885895:oidc-provider/token.actions.githubusercontent.com"
    )

S3 data lake:
  Bucket name: disc-golf-data-lake-{account}
  Legacy data (2020-2025): raw/pdga/legacy/{tourn_id}/tournament_{id}_MPO_round_{n}.json
  ETL data (2026+):        raw/pdga/2026/{tourn_id}/tournament_{id}_MPO_round_{n}.json
  Upload legacy JSONs once with: make upload-legacy

Nightly ETL Lambda:
  Function name: disc-golf-nightly-etl
  Cron: 06:00 UTC daily (EventBridge)
  Invoke manually: make invoke-etl
  Logs: make logs-etl
  Connects to RDS via public endpoint — no VPC required since RDS is publicly accessible.
  Exits cleanly (503) if RDS is stopped.
"""
import aws_cdk as cdk
import aws_cdk.aws_ec2 as ec2
import aws_cdk.aws_ecr as ecr
import aws_cdk.aws_ecs as ecs
import aws_cdk.aws_elasticloadbalancingv2 as elbv2
import aws_cdk.aws_events as events
import aws_cdk.aws_events_targets as targets
import aws_cdk.aws_iam as iam
import aws_cdk.aws_lambda as lambda_
import aws_cdk.aws_logs as logs
import aws_cdk.aws_rds as rds
import aws_cdk.aws_s3 as s3
import aws_cdk.aws_secretsmanager as secretsmanager
from constructs import Construct

GITHUB_REPO = "taylorandrews/disc-golf"


class AppStack(cdk.Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        *,
        vpc: ec2.Vpc,
        app_security_group: ec2.SecurityGroup,
        alb_security_group: ec2.SecurityGroup,
        db_instance: rds.DatabaseInstance,
        db_secret: secretsmanager.Secret,
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        # -- Anthropic API key (Secrets Manager) ------------------------------
        anthropic_secret = secretsmanager.Secret.from_secret_name_v2(
            self,
            "AnthropicSecret",
            "disc-golf-anthropic-key",
        )

        # -- ECR repository ---------------------------------------------------
        self.ecr_repo = ecr.Repository(
            self,
            "AppRepo",
            repository_name="disc-golf-app",
            removal_policy=cdk.RemovalPolicy.DESTROY,
            empty_on_delete=True,
        )

        # -- ECS cluster ------------------------------------------------------
        cluster = ecs.Cluster(
            self,
            "Cluster",
            vpc=vpc,
            cluster_name="disc-golf-cluster",
        )

        # -- Task definition -- 0.5 vCPU / 1 GB RAM --------------------------
        task_def = ecs.FargateTaskDefinition(
            self,
            "TaskDef",
            cpu=512,
            memory_limit_mib=1024,
        )

        # -- Container --------------------------------------------------------
        container = task_def.add_container(
            "App",
            image=ecs.ContainerImage.from_ecr_repository(self.ecr_repo, "latest"),
            environment={
                "DB_HOST": db_instance.db_instance_endpoint_address,
                "DB_PORT": "5432",
                "DB_NAME": "pdga_data",
            },
            secrets={
                "DB_USER": ecs.Secret.from_secrets_manager(db_secret, "username"),
                "DB_PASSWORD": ecs.Secret.from_secrets_manager(db_secret, "password"),
                "ANTHROPIC_API_KEY": ecs.Secret.from_secrets_manager(anthropic_secret, "api_key"),
            },
            logging=ecs.LogDrivers.aws_logs(
                stream_prefix="disc-golf",
                log_retention=logs.RetentionDays.ONE_WEEK,
            ),
        )
        container.add_port_mappings(ecs.PortMapping(container_port=8501))
        anthropic_secret.grant_read(task_def.task_role)

        # -- Fargate service --------------------------------------------------
        # assign_public_ip=True is required when running in a public subnet
        # without a NAT gateway -- tasks need outbound internet for ECR pulls.
        service = ecs.FargateService(
            self,
            "Service",
            cluster=cluster,
            task_definition=task_def,
            service_name="disc-golf-service",
            security_groups=[app_security_group],
            assign_public_ip=True,
            # Start at 0 so CDK does not wait for tasks to launch during initial
            # deploy (the ECR repo is empty at that point). make build-push
            # pushes the first image and scales the service up to 1.
            desired_count=0,
        )

        # -- Application Load Balancer -----------------------------------------
        alb = elbv2.ApplicationLoadBalancer(
            self,
            "Alb",
            vpc=vpc,
            internet_facing=True,
            security_group=alb_security_group,
            load_balancer_name="disc-golf-alb",
        )

        listener = alb.add_listener("HttpListener", port=80, open=False)
        listener.add_targets(
            "AppTarget",
            port=8501,
            protocol=elbv2.ApplicationProtocol.HTTP,
            targets=[service],
            health_check=elbv2.HealthCheck(
                path="/_stcore/health",
                healthy_http_codes="200",
                interval=cdk.Duration.seconds(30),
                timeout=cdk.Duration.seconds(10),
                healthy_threshold_count=2,
                unhealthy_threshold_count=5,
            ),
        )

        # -- GitHub Actions OIDC ----------------------------------------------
        # See module docstring if you already have a GitHub OIDC provider
        # in this account and hit a "resource already exists" error.
        github_provider = iam.OpenIdConnectProvider(
            self,
            "GithubOidcProvider",
            url="https://token.actions.githubusercontent.com",
            client_ids=["sts.amazonaws.com"],
        )

        github_role = iam.Role(
            self,
            "GithubActionsRole",
            role_name="disc-golf-github-actions",
            assumed_by=iam.WebIdentityPrincipal(
                github_provider.open_id_connect_provider_arn,
                conditions={
                    "StringEquals": {
                        "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
                        "token.actions.githubusercontent.com:sub": (
                            f"repo:{GITHUB_REPO}:ref:refs/heads/main"
                        ),
                    }
                },
            ),
        )

        self.ecr_repo.grant_push(github_role)

        github_role.add_to_policy(
            iam.PolicyStatement(
                actions=["ecr:GetAuthorizationToken"],
                resources=["*"],
            )
        )

        github_role.add_to_policy(
            iam.PolicyStatement(
                actions=["ecs:UpdateService", "ecs:DescribeServices"],
                resources=[
                    f"arn:aws:ecs:{self.region}:{self.account}"
                    f":service/disc-golf-cluster/disc-golf-service"
                ],
            )
        )

        # -- S3 data lake -----------------------------------------------------
        # RETAIN on destroy -- data should survive infrastructure teardowns.
        data_lake = s3.Bucket(
            self,
            "DataLake",
            bucket_name=f"disc-golf-data-lake-{self.account}",
            removal_policy=cdk.RemovalPolicy.RETAIN,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
        )

        # -- Nightly ETL Lambda -----------------------------------------------
        # Packaged from repo root: etl/ and helpers/ copied into the Lambda
        # deployment package alongside their pip dependencies.
        # Connects to RDS via its public endpoint -- no VPC needed.
        etl_function = lambda_.Function(
            self,
            "NightlyEtl",
            function_name="disc-golf-nightly-etl",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="etl.lambda_handler.handler",
            code=lambda_.Code.from_asset(
                # Relative to infra/ where CDK runs. ".." = repo root.
                "..",
                bundling=cdk.BundlingOptions(
                    image=lambda_.Runtime.PYTHON_3_12.bundling_image,
                    command=[
                        "bash", "-c",
                        "pip install -r etl/requirements.txt -t /asset-output --quiet"
                        " && cp -r etl helpers /asset-output",
                    ],
                ),
            ),
            timeout=cdk.Duration.minutes(5),
            memory_size=512,
            environment={
                "DB_HOST": db_instance.db_instance_endpoint_address,
                "DB_NAME": "pdga_data",
                "DB_SECRET_ARN": db_secret.secret_arn,
                "S3_BUCKET": data_lake.bucket_name,
            },
            log_retention=logs.RetentionDays.TWO_WEEKS,
        )

        db_secret.grant_read(etl_function)
        data_lake.grant_write(etl_function)

        # -- EventBridge cron -- 06:00 UTC daily ------------------------------
        etl_rule = events.Rule(
            self,
            "NightlyEtlSchedule",
            rule_name="disc-golf-nightly-etl",
            schedule=events.Schedule.cron(minute="0", hour="6"),
            description="Trigger nightly ETL to check for new PDGA round data",
        )
        etl_rule.add_target(targets.LambdaFunction(etl_function))

        # -- Outputs ----------------------------------------------------------
        cdk.CfnOutput(
            self,
            "AlbUrl",
            value=f"http://{alb.load_balancer_dns_name}",
            description="Public site URL -- accessible after the first image push",
        )
        cdk.CfnOutput(
            self,
            "EcrRepoUri",
            value=self.ecr_repo.repository_uri,
            description="ECR repository URI for docker push commands",
        )
        cdk.CfnOutput(
            self,
            "GithubActionsRoleArn",
            value=github_role.role_arn,
            description="IAM role ARN assumed by GitHub Actions via OIDC",
        )
        cdk.CfnOutput(
            self,
            "DataLakeBucket",
            value=data_lake.bucket_name,
            description="S3 data lake bucket -- raw PDGA JSON archive",
        )
        cdk.CfnOutput(
            self,
            "EtlFunctionArn",
            value=etl_function.function_arn,
            description="Nightly ETL Lambda ARN -- invoke manually with: make invoke-etl",
        )
