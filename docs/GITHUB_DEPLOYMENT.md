# PhotoBomb GitHub Deployment Guide

This guide explains how to deploy PhotoBomb to a VPS (Virtual Private Server) like DigitalOcean, Linode, or AWS EC2 using GitHub Actions for continuous deployment.

## Prerequisites

1.  **A GitHub Repository**: Your code must be pushed to GitHub.
2.  **A VPS**: A Linux server (Ubuntu 22.04 LTS recommended) with a public IP.
3.  **Domain Name**: Pointed to your VPS IP (e.g., `photobomb.yourdomain.com`).

## 1. Prepare Your VPS

SSH into your server and install Docker & Docker Compose:

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose Plugin
sudo apt install docker-compose-plugin

# Check installation
docker compose version
```

## 2. Setup GitHub Secrets

Go to your repository **Settings** > **Secrets and variables** > **Actions** and add the following secrets:

### Backend Secrets (for VPS Deployment)
| Secret Name | Description |
|---|---|
| `GCE_HOST` | The IP address of your VPS. |
| `GCE_USERNAME` | Your SSH username (usually `root` or `ubuntu`). |
| `SSH_KEY` | Your private SSH key. |
| `S3_ENDPOINT_URL` | Cloudflare R2 Endpoint URL (e.g. `https://<account>.r2.cloudflarestorage.com`). |
| `S3_ACCESS_KEY_ID` | R2 Access Key ID. |
| `S3_SECRET_ACCESS_KEY` | R2 Secret Access Key. |
| `S3_BUCKET_NAME` | R2 Bucket Name. |
| `S3_REGION_NAME` | R2 Region (usually `auto`). |
| `JWT_SECRET` | A long random string for JWT signing. |
| `DB_PASSWORD` | A secure password for the production database. |

### 🔑 Setting up SSH Access

1.  **Generate a new SSH key pair** on your local machine:
    ```bash
    ssh-keygen -t rsa -b 4096 -C "github-actions-deploy" -f ./github_deploy_key
    ```
    This creates `github_deploy_key` (Private Key) and `github_deploy_key.pub` (Public Key).

2.  **Add Public Key to Server**:
    - **GCE**: Go to Compute Engine -> Metadata -> SSH Keys -> Edit -> Add Item. Paste the content of `github_deploy_key.pub`.
    - **VPS**: Append content of `github_deploy_key.pub` to `~/.ssh/authorized_keys` on your server.

3.  **Add Private Key to GitHub**:
    - Copy the entire content of `github_deploy_key`.
    - Go to your GitHub Repo -> Settings -> Secrets and variables -> Actions -> New repository secret.
    - Name: `SSH_KEY`
    - Value: (Paste key content)


### Frontend Secrets (for Cloudflare Deployment)
| Secret Name | Description |
|---|---|
| `CLOUDFLARE_API_TOKEN` | Token with Workers/Pages edit permissions. |
| `CLOUDFLARE_ACCOUNT_ID` | Your Cloudflare Account ID. |
| `VITE_GOOGLE_CLIENT_ID` | Google OAuth Client ID for the frontend. |

## 3. Configure Deployment Workflows

The project uses a **Split Deployment Architecture**:
1. **Backend**: Deployed to a VPS (via Docker Compose/SSH) using `.github/workflows/deploy.yml`.
2. **Frontend**: Deployed to Cloudflare Workers/Pages using `.github/workflows/deploy-frontend.yml`.

### Backend Workflow (`deploy.yml`)
(Already configured in repo - pushes to VPS, builds Docker containers, runs migrations)

### Frontend Workflow (`deploy-frontend.yml`)
(Already configured in repo - builds React app, deploys to Cloudflare)

## 4. Reverse Proxy (Nginx) for Backend

Since the frontend is hosted on Cloudflare, your VPS only needs to serve the API.

1.  install Nginx: `sudo apt install nginx`
2.  Install Certbot: `sudo apt install certbot python3-certbot-nginx`
3.  Configure Nginx to proxy API requests:
    - **Domain**: `api.yourdomain.com` (or similar)
    - **Proxy Pass**: `http://localhost:8000`
4.  Run `sudo certbot --nginx` to enable HTTPS.

**Note**: Ensure your Backend `ALLOWED_ORIGINS` env var (or config) allows requests from your Cloudflare frontend domain.
