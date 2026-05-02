# ------------------------------------------------------------------------------
# General
# ------------------------------------------------------------------------------
variable "aws_region" {
  description = "AWS region for all resources"
  type        = string
  default     = "ap-south-1"
}

variable "project_name" {
  description = "Name prefix for all resources"
  type        = string
  default     = "brekora"
}

variable "environment" {
  description = "Environment name (dev/staging/prod)"
  type        = string
}

# ------------------------------------------------------------------------------
# Networking
# ------------------------------------------------------------------------------
variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "AZs to deploy into"
  type        = list(string)
  default     = ["ap-south-1a", "ap-south-1b"]
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for public subnets"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24"]
}

variable "private_subnet_cidrs" {
  description = "CIDR blocks for private subnets"
  type        = list(string)
  default     = ["10.0.3.0/24", "10.0.4.0/24"]
}

variable "database_subnet_cidrs" {
  description = "CIDR blocks for database subnets"
  type        = list(string)
  default     = ["10.0.5.0/24", "10.0.6.0/24"]
}

# ------------------------------------------------------------------------------
# ECS / Compute
# ------------------------------------------------------------------------------
variable "api_container_image" {
  description = "Docker image URI for the API service"
  type        = string
  default     = "" # To be set per environment
}

variable "worker_container_image" {
  description = "Docker image URI for the worker service"
  type        = string
  default     = ""
}

variable "api_cpu" {
  description = "Fargate task CPU units for API"
  type        = number
  default     = 256
}

variable "api_memory" {
  description = "Fargate task memory (MiB) for API"
  type        = number
  default     = 512
}

variable "worker_cpu" {
  description = "Fargate task CPU units for worker"
  type        = number
  default     = 256
}

variable "worker_memory" {
  description = "Fargate task memory (MiB) for worker"
  type        = number
  default     = 512
}

variable "api_desired_count" {
  description = "Desired number of API tasks"
  type        = number
  default     = 1
}

variable "worker_desired_count" {
  description = "Desired number of worker tasks"
  type        = number
  default     = 1
}

variable "use_fargate_spot" {
  description = "Use Fargate Spot for non-prod environments"
  type        = bool
  default     = false
}

# ------------------------------------------------------------------------------
# RDS
# ------------------------------------------------------------------------------
variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.micro"
}

variable "db_allocated_storage" {
  description = "RDS allocated storage in GB"
  type        = number
  default     = 20
}

variable "db_engine_version" {
  description = "PostgreSQL engine version"
  type        = string
  default     = "16.1"
}

variable "db_name" {
  description = "Name of the default database"
  type        = string
  default     = "brekora"
}

variable "db_username" {
  description = "Master DB username"
  type        = string
  default     = "brekora_admin"
}

variable "db_multi_az" {
  description = "Enable Multi-AZ for RDS"
  type        = bool
  default     = false
}

# ------------------------------------------------------------------------------
# ElastiCache
# ------------------------------------------------------------------------------
variable "elasticache_node_type" {
  description = "ElastiCache Redis node type"
  type        = string
  default     = "cache.t3.micro"
}

variable "elasticache_engine_version" {
  description = "Redis engine version"
  type        = string
  default     = "7.1"
}

# ------------------------------------------------------------------------------
# ALB / TLS
# ------------------------------------------------------------------------------
variable "domain_name" {
  description = "Primary domain name (e.g., brekora.in)"
  type        = string
  default     = ""
}

variable "api_subdomain" {
  description = "Subdomain for the API"
  type        = string
  default     = "api"
}

variable "app_subdomain" {
  description = "Subdomain for the frontend"
  type        = string
  default     = "app"
}

variable "enable_https" {
  description = "Enable HTTPS listener and ACM certificate"
  type        = bool
  default     = false
}

# ------------------------------------------------------------------------------
# Security
# ------------------------------------------------------------------------------
variable "enable_deletion_protection" {
  description = "Enable deletion protection on stateful resources"
  type        = bool
  default     = false
}

variable "enable_rds_encryption" {
  description = "Enable storage encryption for RDS"
  type        = bool
  default     = false
}
