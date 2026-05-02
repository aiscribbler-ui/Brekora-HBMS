# ------------------------------------------------------------------------------
# Outputs
# ------------------------------------------------------------------------------
output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.main.id
}

output "public_subnet_ids" {
  description = "Public subnet IDs"
  value       = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  description = "Private subnet IDs"
  value       = aws_subnet.private[*].id
}

output "database_subnet_ids" {
  description = "Database subnet IDs"
  value       = aws_subnet.database[*].id
}

output "alb_dns_name" {
  description = "DNS name of the Application Load Balancer"
  value       = aws_lb.main.dns_name
}

output "api_target_group_arn" {
  description = "ARN of the API target group"
  value       = aws_lb_target_group.api.arn
}

output "ecs_cluster_name" {
  description = "ECS cluster name"
  value       = aws_ecs_cluster.main.name
}

output "ecs_api_service_name" {
  description = "ECS API service name"
  value       = aws_ecs_service.api.name
}

output "ecs_worker_service_name" {
  description = "ECS worker service name"
  value       = aws_ecs_service.worker.name
}

output "rds_endpoint" {
  description = "RDS PostgreSQL endpoint"
  value       = aws_db_instance.main.address
  sensitive   = true
}

output "redis_endpoint" {
  description = "ElastiCache Redis primary endpoint"
  value       = aws_elasticache_replication_group.main.primary_endpoint_address
  sensitive   = true
}

output "s3_bucket_name" {
  description = "S3 bucket for assets"
  value       = aws_s3_bucket.main.id
}

output "db_password_secret_arn" {
  description = "ARN of the Secrets Manager secret for DB password"
  value       = aws_secretsmanager_secret.db_password.arn
  sensitive   = true
}

output "route53_nameservers" {
  description = "Route 53 nameservers (if zone created)"
  value       = var.domain_name != "" ? aws_route53_zone.main[0].name_servers : []
}
