# Terraform Configuration for PhotoBomb Infrastructure

terraform {
  required_version = ">= 1.6"
  
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    cloudflare = {
      source  = "cloudflare/cloudflare"
      version = "~> 4.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.24"
    }
  }
  
  backend "gcs" {
    bucket = "photobomb-terraform-state"
    prefix = "prod"
  }
}

provider "google" {
  project = var.gcp_project_id
  region  = var.gcp_region
}

provider "cloudflare" {
  api_token = var.cloudflare_api_token
}

variable "gcp_project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "gcp_region" {
  description = "GCP Region"
  type        = string
  default     = "us-central1"
}

variable "environment" {
  description = "Environment (dev/staging/prod)"
  type        = string
}

variable "cloudflare_api_token" {
  description = "Cloudflare API token"
  type        = string
  sensitive   = true
}

variable "cloudflare_zone_id" {
  description = "Cloudflare Zone ID for photobomb.app"
  type        = string
}

variable "db_password" {
  description = "PostgreSQL password"
  type        = string
  sensitive   = true
}

variable "b2_application_key_id" {
  description = "Backblaze B2 Application Key ID"
  type        = string
  sensitive   = true
}

variable "b2_application_key" {
  description = "Backblaze B2 Application Key"
  type        = string
  sensitive   = true
}

# ============================================================================
# VPC & Networking
# ============================================================================

resource "google_compute_network" "main" {
  name                    = "photobomb-${var.environment}-vpc"
  auto_create_subnetworks = false
}

resource "google_compute_subnetwork" "private" {
  name          = "photobomb-${var.environment}-private"
  ip_cidr_range = "10.0.0.0/24"
  region        = var.gcp_region
  network       = google_compute_network.main.id
  
  secondary_ip_range {
    range_name    = "pods"
    ip_cidr_range = "10.1.0.0/16"
  }
  
  secondary_ip_range {
    range_name    = "services"
    ip_cidr_range = "10.2.0.0/16"
  }
}

resource "google_compute_router" "main" {
  name    = "photobomb-${var.environment}-router"
  region  = var.gcp_region
  network = google_compute_network.main.id
}

resource "google_compute_router_nat" "main" {
  name   = "photobomb-${var.environment}-nat"
  router = google_compute_router.main.name
  region = var.gcp_region
  
  nat_ip_allocate_option = "AUTO_ONLY"
  source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"
}

# ============================================================================
# Cloud SQL (PostgreSQL)
# ============================================================================

resource "google_sql_database_instance" "main" {
  name             = "photobomb-${var.environment}-db"
  database_version = "POSTGRES_16"
  region           = var.gcp_region
  
  settings {
    tier              = var.environment == "prod" ? "db-custom-4-16384" : "db-f1-micro"
    availability_type = var.environment == "prod" ? "REGIONAL" : "ZONAL"
    disk_size         = 100 # GB
    disk_type         = "PD_SSD"
    
    backup_configuration {
      enabled                        = true
      start_time                     = "03:00"
      point_in_time_recovery_enabled = var.environment == "prod"
      transaction_log_retention_days = 7
    }
    
    ip_configuration {
      ipv4_enabled    = false
      private_network = google_compute_network.main.id
      require_ssl     = true
    }
    
    database_flags {
      name  = "max_connections"
      value = "200"
    }
    
    database_flags {
      name  = "shared_buffers"
      value = "4096" # MB for 16GB RAM
    }
    
    insights_config {
      query_insights_enabled  = true
      query_string_length     = 1024
      record_application_tags = true
    }
  }
  
  deletion_protection = var.environment == "prod"
}

resource "google_sql_database" "main" {
  name     = "photobomb"
  instance = google_sql_database_instance.main.name
}

resource "google_sql_user" "main" {
  name     = "photobomb_app"
  instance = google_sql_database_instance.main.name
  password = var.db_password
}

# ============================================================================
# GKE Cluster (for workers)
# ============================================================================

resource "google_container_cluster" "main" {
  name     = "photobomb-${var.environment}-gke"
  location = var.gcp_region
  
  remove_default_node_pool = true
  initial_node_count       = 1
  
  network    = google_compute_network.main.name
  subnetwork = google_compute_subnetwork.private.name
  
  ip_allocation_policy {
    cluster_secondary_range_name  = "pods"
    services_secondary_range_name = "services"
  }
  
  workload_identity_config {
    workload_pool = "${var.gcp_project_id}.svc.id.goog"
  }
  
  addons_config {
    horizontal_pod_autoscaling {
      disabled = false
    }
    network_policy_config {
      disabled = false
    }
  }
  
  network_policy {
    enabled = true
  }
  
  release_channel {
    channel = "REGULAR"
  }
}

# CPU node pool (for thumbnail generation)
resource "google_container_node_pool" "cpu_workers" {
  name       = "cpu-workers"
  location   = var.gcp_region
  cluster    = google_container_cluster.main.name
  node_count = var.environment == "prod" ? 3 : 1
  
  autoscaling {
    min_node_count = var.environment == "prod" ? 2 : 1
    max_node_count = var.environment == "prod" ? 10 : 3
  }
  
  node_config {
    machine_type = "n2-standard-4" # 4 vCPU, 16 GB RAM
    disk_size_gb = 50
    
    oauth_scopes = [
      "https://www.googleapis.com/auth/cloud-platform"
    ]
    
    labels = {
      workload = "cpu"
    }
    
    tags = ["photobomb-worker"]
    
    workload_metadata_config {
      mode = "GKE_METADATA"
    }
  }
}

# GPU node pool (for face detection, optional for MVP)
resource "google_container_node_pool" "gpu_workers" {
  count = var.environment == "prod" ? 1 : 0
  
  name       = "gpu-workers"
  location   = var.gcp_region
  cluster    = google_container_cluster.main.name
  node_count = 0 # Scale to zero when idle
  
  autoscaling {
    min_node_count = 0
    max_node_count = 3
  }
  
  node_config {
    machine_type = "n1-standard-4"
    disk_size_gb = 50
    
    guest_accelerator {
      type  = "nvidia-tesla-t4"
      count = 1
    }
    
    oauth_scopes = [
      "https://www.googleapis.com/auth/cloud-platform"
    ]
    
    labels = {
      workload = "gpu"
    }
    
    taint {
      key    = "nvidia.com/gpu"
      value  = "true"
      effect = "NO_SCHEDULE"
    }
  }
}

# ============================================================================
# Cloud Run (FastAPI backend)
# ============================================================================

resource "google_cloud_run_service" "api" {
  name     = "photobomb-api"
  location = var.gcp_region
  
  template {
    spec {
      containers {
        image = "gcr.io/${var.gcp_project_id}/photobomb-api:latest"
        
        env {
          name  = "DATABASE_URL"
          value = "postgresql://photobomb_app:${var.db_password}@${google_sql_database_instance.main.private_ip_address}/photobomb?sslmode=require"
        }
        
        env {
          name  = "B2_APPLICATION_KEY_ID"
          value = var.b2_application_key_id
        }
        
        env {
          name  = "B2_APPLICATION_KEY"
          value = var.b2_application_key
        }
        
        env {
          name  = "REDIS_URL"
          value = "redis://${google_redis_instance.main.host}:${google_redis_instance.main.port}"
        }
        
        resources {
          limits = {
            cpu    = "2"
            memory = "2Gi"
          }
        }
      }
      
      container_concurrency = 80
    }
    
    metadata {
      annotations = {
        "autoscaling.knative.dev/minScale" = var.environment == "prod" ? "2" : "1"
        "autoscaling.knative.dev/maxScale" = var.environment == "prod" ? "100" : "10"
        "run.googleapis.com/vpc-access-connector" = google_vpc_access_connector.main.id
      }
    }
  }
  
  traffic {
    percent         = 100
    latest_revision = true
  }
}

resource "google_cloud_run_service_iam_member" "public" {
  service  = google_cloud_run_service.api.name
  location = google_cloud_run_service.api.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# VPC Connector for Cloud Run -> Cloud SQL
resource "google_vpc_access_connector" "main" {
  name          = "photobomb-${var.environment}-connector"
  region        = var.gcp_region
  network       = google_compute_network.main.name
  ip_cidr_range = "10.8.0.0/28"
}

# ============================================================================
# Redis (Celery broker)
# ============================================================================

resource "google_redis_instance" "main" {
  name           = "photobomb-${var.environment}-redis"
  tier           = var.environment == "prod" ? "STANDARD_HA" : "BASIC"
  memory_size_gb = var.environment == "prod" ? 5 : 1
  region         = var.gcp_region
  
  authorized_network = google_compute_network.main.id
  
  redis_version = "REDIS_7_0"
  display_name  = "PhotoBomb Celery Broker"
}

# ============================================================================
# Cloudflare (CDN & DNS)
# ============================================================================

resource "cloudflare_zone_settings_override" "photobomb" {
  zone_id = var.cloudflare_zone_id
  
  settings {
    tls_1_3                  = "on"
    automatic_https_rewrites = "on"
    ssl                      = "strict"
    always_use_https         = "on"
    min_tls_version          = "1.2"
    opportunistic_encryption = "on"
    
    brotli = "on"
    minify {
      css  = "on"
      js   = "on"
      html = "on"
    }
  }
}

resource "cloudflare_record" "api" {
  zone_id = var.cloudflare_zone_id
  name    = "api"
  value   = google_cloud_run_service.api.status[0].url
  type    = "CNAME"
  proxied = true
}

resource "cloudflare_page_rule" "api_cache" {
  zone_id  = var.cloudflare_zone_id
  target   = "api.photobomb.app/api/v1/*"
  priority = 1
  
  actions {
    cache_level = "bypass" # Don't cache API responses
  }
}

resource "cloudflare_page_rule" "thumbnails_cache" {
  zone_id  = var.cloudflare_zone_id
  target   = "cdn.photobomb.app/thumb/*"
  priority = 2
  
  actions {
    cache_level         = "cache_everything"
    edge_cache_ttl      = 2592000 # 30 days
    browser_cache_ttl   = 31536000 # 1 year
    cache_on_cookie     = "none"
  }
}

# ============================================================================
# Outputs
# ============================================================================

output "api_url" {
  value = google_cloud_run_service.api.status[0].url
}

output "db_private_ip" {
  value     = google_sql_database_instance.main.private_ip_address
  sensitive = true
}

output "gke_cluster_name" {
  value = google_container_cluster.main.name
}

output "redis_host" {
  value     = google_redis_instance.main.host
  sensitive = true
}
