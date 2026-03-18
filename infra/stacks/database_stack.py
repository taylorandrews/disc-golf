"""
DatabaseStack — RDS PostgreSQL instance and Secrets Manager credentials.

Instance:  t3.micro, single-AZ, PostgreSQL 15  (~$15/month when running)
Storage:   20 GB GP2, encrypted at rest
Backups:   disabled (backup_retention=0) to eliminate snapshot storage costs.
           Data is always restorable by re-running Alembic migrations locally.

Credentials:
  Auto-generated 32-char password, stored in Secrets Manager.
  Never set or rotated manually. The ECS task reads the secret at startup.
  To retrieve credentials manually (e.g. for psql or a DB client):
    aws secretsmanager get-secret-value --secret-id <DbSecretArn output> \
        --query SecretString --output text

Seeding the database after first deploy:
  1. Get the RDS endpoint from the DbEndpoint CloudFormation output.
  2. Retrieve the password from Secrets Manager (command above).
  3. Run: DATABASE_URL=postgresql://postgres:<pw>@<endpoint>:5432/pdga_data \
              alembic upgrade head
  See docs/runbook.md for the full step-by-step.

Note on hand-edited PDGA JSON files:
  The files in data/pdga/ have been manually cleaned to satisfy stricter
  NOT NULL constraints than the raw PDGA API returns. Do not re-fetch and
  overwrite these files without re-applying those edits, or migrations will
  fail. See docs/runbook.md for details.
"""
import json

import aws_cdk as cdk
import aws_cdk.aws_ec2 as ec2
import aws_cdk.aws_rds as rds
import aws_cdk.aws_secretsmanager as secretsmanager
from constructs import Construct


class DatabaseStack(cdk.Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        *,
        vpc: ec2.Vpc,
        db_security_group: ec2.SecurityGroup,
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        # ── Credentials — auto-generated, stored in Secrets Manager ───────────
        # Punctuation excluded to avoid URL-encoding issues in connection strings.
        self.db_secret = secretsmanager.Secret(
            self,
            "DbSecret",
            description="PostgreSQL credentials for the disc-golf RDS instance",
            generate_secret_string=secretsmanager.SecretStringGenerator(
                secret_string_template=json.dumps({"username": "postgres"}),
                generate_string_key="password",
                exclude_punctuation=True,
                password_length=32,
            ),
        )

        # ── RDS PostgreSQL t3.micro ────────────────────────────────────────────
        self.db_instance = rds.DatabaseInstance(
            self,
            "Database",
            # Explicit identifier so Makefile and runbook commands use a known name.
            instance_identifier="disc-golf-db",
            engine=rds.DatabaseInstanceEngine.postgres(
                version=rds.PostgresEngineVersion.VER_15
            ),
            instance_type=ec2.InstanceType.of(
                ec2.InstanceClass.T3, ec2.InstanceSize.MICRO
            ),
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
            security_groups=[db_security_group],
            publicly_accessible=True,
            database_name="pdga_data",
            credentials=rds.Credentials.from_secret(self.db_secret),
            # Single-AZ — acceptable cost trade-off for a personal project.
            multi_az=False,
            allocated_storage=20,
            storage_encrypted=True,
            # Disable automated backups to keep storage costs at zero.
            backup_retention=cdk.Duration.days(0),
            # Allow cdk destroy to delete this instance cleanly.
            deletion_protection=False,
            removal_policy=cdk.RemovalPolicy.DESTROY,
        )

        # ── Outputs ───────────────────────────────────────────────────────────
        cdk.CfnOutput(
            self,
            "DbEndpoint",
            value=self.db_instance.db_instance_endpoint_address,
            description="RDS hostname — use as DB_HOST when building DATABASE_URL",
        )
        cdk.CfnOutput(
            self,
            "DbSecretArn",
            value=self.db_secret.secret_arn,
            description="Secrets Manager ARN — retrieve DB credentials from here",
        )
