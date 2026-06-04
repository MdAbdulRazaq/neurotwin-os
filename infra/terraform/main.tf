################################################################################
# NEUROTWIN OS — Terraform (AWS EKS)
# Provisions: VPC, EKS cluster, RDS PostgreSQL, ElastiCache Redis, ECR repos
################################################################################

terraform {
  required_version = ">= 1.9"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.60" }
  }
  backend "s3" {
    bucket = "neurotwin-terraform-state"
    key    = "prod/terraform.tfstate"
    region = "us-east-1"
  }
}

provider "aws" {
  region = var.aws_region
  default_tags { tags = local.common_tags }
}

locals {
  name = "neurotwin"
  env  = var.environment
  common_tags = {
    Project     = "NEUROTWIN OS"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# ── Variables ─────────────────────────────────────────────────────────────────
variable "aws_region"   { default = "us-east-1" }
variable "environment"  { default = "production" }
variable "cluster_version" { default = "1.30" }
variable "db_password"  { sensitive = true }

# ── VPC ───────────────────────────────────────────────────────────────────────
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0"

  name = "${local.name}-vpc"
  cidr = "10.0.0.0/16"

  azs             = ["${var.aws_region}a", "${var.aws_region}b", "${var.aws_region}c"]
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]

  enable_nat_gateway     = true
  single_nat_gateway     = false
  one_nat_gateway_per_az = true
  enable_dns_hostnames   = true
  enable_dns_support     = true

  public_subnet_tags  = { "kubernetes.io/role/elb" = 1 }
  private_subnet_tags = { "kubernetes.io/role/internal-elb" = 1 }
}

# ── EKS Cluster ───────────────────────────────────────────────────────────────
module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 20.0"

  cluster_name    = "${local.name}-cluster"
  cluster_version = var.cluster_version
  vpc_id          = module.vpc.vpc_id
  subnet_ids      = module.vpc.private_subnets

  cluster_endpoint_public_access = true

  eks_managed_node_groups = {
    # General purpose nodes
    general = {
      instance_types = ["m5.xlarge"]
      min_size       = 2
      max_size       = 10
      desired_size   = 3
      disk_size      = 50
    }
    # GPU nodes for ML worker (optional)
    gpu = {
      instance_types = ["g4dn.xlarge"]
      min_size       = 0
      max_size       = 4
      desired_size   = 0
      labels         = { workload = "ml" }
      taints         = [{ key = "nvidia.com/gpu", value = "true", effect = "NO_SCHEDULE" }]
    }
  }

  enable_cluster_creator_admin_permissions = true
}

# ── RDS PostgreSQL ────────────────────────────────────────────────────────────
module "rds" {
  source  = "terraform-aws-modules/rds/aws"
  version = "~> 6.0"

  identifier           = "${local.name}-postgres"
  engine               = "postgres"
  engine_version       = "16"
  family               = "postgres16"
  major_engine_version = "16"
  instance_class       = "db.t4g.large"

  allocated_storage     = 50
  max_allocated_storage = 500
  storage_encrypted     = true

  db_name  = "neurotwin_db"
  username = "neurotwin"
  password = var.db_password
  port     = 5432

  multi_az               = true
  subnet_ids             = module.vpc.private_subnets
  vpc_security_group_ids = [aws_security_group.rds.id]

  backup_retention_period = 7
  deletion_protection     = true
  skip_final_snapshot     = false
}

# ── ElastiCache Redis ─────────────────────────────────────────────────────────
resource "aws_elasticache_replication_group" "redis" {
  replication_group_id = "${local.name}-redis"
  description          = "NEUROTWIN Redis cluster"
  node_type            = "cache.t4g.medium"
  num_cache_clusters   = 2
  port                 = 6379
  subnet_group_name    = aws_elasticache_subnet_group.redis.name
  security_group_ids   = [aws_security_group.redis.id]
  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  automatic_failover_enabled = true
}

resource "aws_elasticache_subnet_group" "redis" {
  name       = "${local.name}-redis-subnet"
  subnet_ids = module.vpc.private_subnets
}

# ── Security Groups ───────────────────────────────────────────────────────────
resource "aws_security_group" "rds" {
  name   = "${local.name}-rds-sg"
  vpc_id = module.vpc.vpc_id
  ingress {
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = [module.vpc.vpc_cidr_block]
  }
  egress { from_port = 0; to_port = 0; protocol = "-1"; cidr_blocks = ["0.0.0.0/0"] }
}

resource "aws_security_group" "redis" {
  name   = "${local.name}-redis-sg"
  vpc_id = module.vpc.vpc_id
  ingress {
    from_port   = 6379
    to_port     = 6379
    protocol    = "tcp"
    cidr_blocks = [module.vpc.vpc_cidr_block]
  }
  egress { from_port = 0; to_port = 0; protocol = "-1"; cidr_blocks = ["0.0.0.0/0"] }
}

# ── ECR Repositories ──────────────────────────────────────────────────────────
resource "aws_ecr_repository" "repos" {
  for_each             = toset(["api", "perception", "memory", "avatar", "worker", "web"])
  name                 = "${local.name}-${each.key}"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration { scan_on_push = true }
  encryption_configuration { encryption_type = "AES256" }
}

# ── Outputs ───────────────────────────────────────────────────────────────────
output "cluster_endpoint"        { value = module.eks.cluster_endpoint }
output "rds_endpoint"            { value = module.rds.db_instance_endpoint }
output "redis_endpoint"          { value = aws_elasticache_replication_group.redis.primary_endpoint_address }
output "ecr_registry"            { value = "${data.aws_caller_identity.current.account_id}.dkr.ecr.${var.aws_region}.amazonaws.com" }

data "aws_caller_identity" "current" {}
