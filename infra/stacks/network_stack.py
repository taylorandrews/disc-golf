"""
NetworkStack — VPC, subnets, and security groups.

Architecture:
  Single public-subnet VPC across 2 AZs. No NAT gateway (saves ~$32/month).
  ECS Fargate tasks run in public subnets with a public IP assigned directly.
  RDS is in a public subnet with publicly_accessible=True.

Security group relationships:
  internet → alb_security_group (port 80)
  alb_security_group → app_security_group (port 8501, Streamlit)
  anywhere → db_security_group (port 5432)

RDS is open to all IPs on 5432 so the developer can run Alembic migrations
from a local machine without managing a bastion or VPN. This is an accepted
trade-off for a dev project: the data is entirely public, and the RDS password
is a 32-character auto-generated string stored in Secrets Manager.

To restrict DB access to your IP only, replace the 0.0.0.0/0 ingress rule
with: ec2.Peer.ipv4("YOUR_PUBLIC_IP/32")
"""
import aws_cdk as cdk
import aws_cdk.aws_ec2 as ec2
from constructs import Construct


class NetworkStack(cdk.Stack):
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # ── VPC — public subnets only, no NAT gateway ─────────────────────────
        self.vpc = ec2.Vpc(
            self,
            "Vpc",
            max_azs=2,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="Public",
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=24,
                )
            ],
            nat_gateways=0,
        )

        # ── ALB security group — internet → port 80 ───────────────────────────
        self.alb_security_group = ec2.SecurityGroup(
            self,
            "AlbSecurityGroup",
            vpc=self.vpc,
            description="Allow inbound HTTP from the internet",
            allow_all_outbound=True,
        )
        self.alb_security_group.add_ingress_rule(
            ec2.Peer.any_ipv4(),
            ec2.Port.tcp(80),
            "HTTP from internet",
        )

        # ── ECS task security group — ALB → port 8501 (Streamlit) ─────────────
        self.app_security_group = ec2.SecurityGroup(
            self,
            "AppSecurityGroup",
            vpc=self.vpc,
            description="Allow Streamlit traffic inbound from ALB only",
            allow_all_outbound=True,
        )
        self.app_security_group.add_ingress_rule(
            self.alb_security_group,
            ec2.Port.tcp(8501),
            "Streamlit from ALB",
        )

        # ── RDS security group — open on 5432 for developer migrations ─────────
        # See module docstring for the security trade-off discussion.
        self.db_security_group = ec2.SecurityGroup(
            self,
            "DbSecurityGroup",
            vpc=self.vpc,
            description="Allow PostgreSQL from ECS tasks and developer machine",
            allow_all_outbound=False,
        )
        self.db_security_group.add_ingress_rule(
            ec2.Peer.any_ipv4(),
            ec2.Port.tcp(5432),
            "PostgreSQL — open for developer access (see module docstring to restrict)",
        )
