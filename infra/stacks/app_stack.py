"""
AppStack — ECR repository, ECS Fargate service, ALB, and GitHub OIDC role.

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
"""
import aws_cdk as cdk
import aws_cdk.aws_ec2 as ec2
import aws_cdk.aws_ecr as ecr
import aws_cdk.aws_ecs as ecs
import aws_cdk.aws_elasticloadbalancingv2 as elbv2
import aws_cdk.aws_iam as iam
import aws_cdk.aws_logs as logs
import aws_cdk.aws_rds as rds
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

        # ── ECR repository ────────────────────────────────────────────────────
        self.ecr_repo = ecr.Repository(
            self,
            "AppRepo",
            repository_name="disc-golf-app",
            # Allow cdk destroy to remove the repo and all images inside it.
            removal_policy=cdk.RemovalPolicy.DESTROY,
            empty_on_delete=True,
        )

        # ── ECS cluster ───────────────────────────────────────────────────────
        cluster = ecs.Cluster(
            self,
            "Cluster",
            vpc=vpc,
            cluster_name="disc-golf-cluster",
        )

        # ── Task definition — 0.5 vCPU / 1 GB RAM ────────────────────────────
        task_def = ecs.FargateTaskDefinition(
            self,
            "TaskDef",
            cpu=512,
            memory_limit_mib=1024,
        )

        # ── Container ─────────────────────────────────────────────────────────
        container = task_def.add_container(
            "App",
            image=ecs.ContainerImage.from_ecr_repository(self.ecr_repo, "latest"),
            # Non-sensitive connection details as plain environment variables.
            environment={
                "DB_HOST": db_instance.db_instance_endpoint_address,
                "DB_PORT": "5432",
                "DB_NAME": "pdga_data",
            },
            # Sensitive credentials pulled from Secrets Manager at task start.
            # ECS grants the task execution role GetSecretValue automatically.
            secrets={
                "DB_USER": ecs.Secret.from_secrets_manager(db_secret, "username"),
                "DB_PASSWORD": ecs.Secret.from_secrets_manager(db_secret, "password"),
            },
            logging=ecs.LogDrivers.aws_logs(
                stream_prefix="disc-golf",
                log_retention=logs.RetentionDays.ONE_WEEK,
            ),
        )
        container.add_port_mappings(ecs.PortMapping(container_port=8501))

        # ── Fargate service ───────────────────────────────────────────────────
        # assign_public_ip=True is required when running in a public subnet
        # without a NAT gateway — tasks need outbound internet for ECR pulls.
        service = ecs.FargateService(
            self,
            "Service",
            cluster=cluster,
            task_definition=task_def,
            service_name="disc-golf-service",
            security_groups=[app_security_group],
            assign_public_ip=True,
            desired_count=1,
        )

        # ── Application Load Balancer ─────────────────────────────────────────
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

        # ── GitHub Actions OIDC ───────────────────────────────────────────────
        # See module docstring if you already have a GitHub OIDC provider
        # in this account and hit a "resource already exists" error.
        github_provider = iam.OpenIdConnectProvider(
            self,
            "GithubOidcProvider",
            url="https://token.actions.githubusercontent.com",
            client_ids=["sts.amazonaws.com"],
        )

        # Scoped to main-branch pushes on this specific repo only.
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

        # ECR: push images. grant_push covers BatchCheckLayerAvailability,
        # InitiateLayerUpload, UploadLayerPart, CompleteLayerUpload, PutImage.
        self.ecr_repo.grant_push(github_role)

        # GetAuthorizationToken is account-level — cannot scope to a single repo.
        github_role.add_to_policy(
            iam.PolicyStatement(
                actions=["ecr:GetAuthorizationToken"],
                resources=["*"],
            )
        )

        # ECS: trigger redeployment, scoped to this service only.
        github_role.add_to_policy(
            iam.PolicyStatement(
                actions=["ecs:UpdateService", "ecs:DescribeServices"],
                resources=[
                    f"arn:aws:ecs:{self.region}:{self.account}"
                    f":service/disc-golf-cluster/disc-golf-service"
                ],
            )
        )

        # ── Outputs ───────────────────────────────────────────────────────────
        cdk.CfnOutput(
            self,
            "AlbUrl",
            value=f"http://{alb.load_balancer_dns_name}",
            description="Public site URL — accessible after the first image push",
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
