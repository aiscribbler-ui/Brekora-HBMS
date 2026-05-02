environment        = "prod"
api_cpu            = 512
api_memory         = 1024
worker_cpu         = 512
worker_memory      = 1024
api_desired_count  = 2
worker_desired_count = 2
use_fargate_spot   = false

db_instance_class    = "db.t3.small"
db_allocated_storage = 50
db_multi_az          = true

elasticache_node_type = "cache.t3.small"

enable_https               = true
enable_deletion_protection = true
enable_rds_encryption      = true
