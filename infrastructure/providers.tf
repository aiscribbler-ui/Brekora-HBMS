terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Uncomment after creating the S3 backend bucket manually (bootstrap):
  # backend "s3" {
  #   bucket         = "brekora-terraform-state-ap-south-1"
  #   key            = "infrastructure/terraform.tfstate"
  #   region         = "ap-south-1"
  #   encrypt        = true
  #   dynamodb_table = "brekora-terraform-locks"
  # }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "brekora-bms"
      Environment = terraform.workspace
      ManagedBy   = "terraform"
    }
  }
}
