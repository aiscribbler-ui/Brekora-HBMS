environment        = "dev"
api_cpu            = 256
api_memory         = 512
worker_cpu         = 256
worker_memory      = 512
api_desired_count  = 1
worker_desired_count = 1
use_fargate_spot   = true

db_instance_class    = "db.t3.micro"
db_allocated_storage = 20
db_multi_az          = false

elasticache_node_type = "cache.t3.micro"

enable_https               = false
enable_deletion_protection = false
enable_rds_encryption      = false
