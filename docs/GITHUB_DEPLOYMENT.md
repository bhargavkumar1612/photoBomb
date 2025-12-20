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

| Secret Name | Description |
|---|---|
| `HOST` | The IP address of your VPS. |
| `USERNAME` | Your SSH username (usually `root` or `ubuntu`). |
| `SSH_KEY` | Your private SSH key (generate one locally with `ssh-keygen` and add public key to VPS `~/.ssh/authorized_keys`). |
| `B2_KEY_ID` | Backblaze Application Key ID. |
| `B2_KEY` | Backblaze Application Key. |
| `B2_BUCKET_ID` | Backblaze Bucket ID. |
| `JWT_SECRET` | A long random string for JWT signing. |
| `DB_PASSWORD` | A secure password for the production database. |

## 3. Configure the Deployment Workflow

Create a file at `.github/workflows/deploy.yml` in your repository:

```yaml
name: Deploy to Production

on:
  push:
    branches: [ "main" ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v3

      - name: Copy files via SCP
        uses: appleboy/scp-action@master
        with:
          host: ${{ secrets.HOST }}
          username: ${{ secrets.USERNAME }}
          key: ${{ secrets.SSH_KEY }}
          source: "."
          target: "/opt/photobomb"

      - name: Deploy via SSH
        uses: appleboy/ssh-action@master
        with:
          host: ${{ secrets.HOST }}
          username: ${{ secrets.USERNAME }}
          key: ${{ secrets.SSH_KEY }}
          script: |
            cd /opt/photobomb
            
            # Create/Update .env file from secrets
            echo "DATABASE_URL=postgresql+asyncpg://photobomb:${{ secrets.DB_PASSWORD }}@postgres:5432/photobomb" > backend/.env
            echo "REDIS_URL=redis://redis:6379/0" >> backend/.env
            echo "JWT_SECRET_KEY=${{ secrets.JWT_SECRET }}" >> backend/.env
            echo "B2_APPLICATION_KEY_ID=${{ secrets.B2_KEY_ID }}" >> backend/.env
            echo "B2_APPLICATION_KEY=${{ secrets.B2_KEY }}" >> backend/.env
            echo "B2_BUCKET_NAME=photobomb-prod" >> backend/.env
            echo "B2_BUCKET_ID=${{ secrets.B2_BUCKET_ID }}" >> backend/.env
            
            # Restart containers
            docker compose down
            docker compose up -d --build
            
            # Run migrations
            docker compose exec -T api alembic upgrade head
```

## 4. Initial Push

1.  Initialize git if you haven't:
    ```bash
    git init
    git add .
    git commit -m "Initial commit"
    ```
2.  Create a repo on GitHub.
3.  Push your code:
    ```bash
    git branch -M main
    git remote add origin https://github.com/YOUR_USERNAME/photobomb.git
    git push -u origin main
    ```

Once pushed, the check the **Actions** tab in GitHub to watch the deployment proceed.

## 5. Reverse Proxy (Nginx)

For production, run Nginx on the host to handle SSL (HTTPS).

1.  Install Nginx: `sudo apt install nginx`
2.  Install Certbot: `sudo apt install certbot python3-certbot-nginx`
3.  Configure Nginx to proxy requests:
    - Port 80/443 -> localhost:3000 (Frontend)
    - /api -> localhost:8000 (Backend)
4.  Run `sudo certbot --nginx` to get a free SSL certificate.
