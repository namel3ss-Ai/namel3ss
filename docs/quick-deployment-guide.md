# Quick Deployment Guide for namel3ss Applications

**Version**: 1.0  
**Last Updated**: 2026-01-11  
**Audience**: Developers deploying namel3ss apps to production

> [!NOTE]
> This is a quick-start deployment guide. For comprehensive production deployment including security, monitoring, and disaster recovery, see [Production Deployment Guide](production-deployment.md).

---

## Prerequisites

Before deploying, ensure you have:

- **Git**: For cloning your application repository
- **Docker and Docker Compose**: For containerized deployment (recommended)
- **Python 3.10+**: For non-containerized deployment
- **Nginx** (optional): For reverse proxy and SSL
- **PostgreSQL**: For production database (or use managed database service)

---

## Method 1: Docker Deployment (Recommended)

This is the easiest and most reliable way to deploy namel3ss applications.

### Step 1: Create Deployment Files

Create these files in your project root:

**Dockerfile**:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    gcc \\
    postgresql-client \\
    && rm -rf /var/lib/apt/lists/*

# Install namel3ss
RUN pip install --no-cache-dir namel3ss

# Copy application files
COPY app.ai .
COPY modules/ modules/
COPY tools/ tools/
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt
RUN n3 deps install

# Create non-root user
RUN useradd -m -u 1000 namel3ss && \\
    chown -R namel3ss:namel3ss /app
USER namel3ss

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
    CMD n3 app.ai check || exit 1

CMD ["n3", "app.ai", "studio", "--host", "0.0.0.0", "--port", "8080"]
```

**docker-compose.yml**:
```yaml
version: '3.8'

services:
  namel3ss:
    build: .
    ports:
      - "8080:8080"
    environment:
      - N3_PERSIST_TARGET=postgres
      - N3_DATABASE_URL=postgres://namel3ss:${DB_PASSWORD}@db:5432/namel3ss
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    depends_on:
      db:
        condition: service_healthy
    restart: unless-stopped
    volumes:
      - ./data:/app/data

  db:
    image: postgres:15-alpine
    environment:
      - POSTGRES_DB=namel3ss
      - POSTGRES_USER=namel3ss
      - POSTGRES_PASSWORD=${DB_PASSWORD}
    volumes:
      - postgres-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U namel3ss"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

volumes:
  postgres-data:
```

**.env**:
```bash
DB_PASSWORD=your-secure-password-here
OPENAI_API_KEY=sk-your-api-key-here
```

### Step 2: Create Deployment Script

**deploy.sh**:
```bash
#!/bin/bash
set -e

echo "🚀 Deploying namel3ss application..."

# Stop existing containers
echo "📦 Stopping existing containers..."
docker-compose down || true

# Build and start
echo "🔨 Building Docker image..."
docker-compose build

echo "▶️  Starting application..."
docker-compose up -d

# Wait for health check
echo "⏳ Waiting for application to be ready..."
sleep 10

# Check if running
if docker-compose ps | grep -q "Up"; then
    echo "✅ Application deployed successfully!"
    echo "📍 Access at: http://localhost:8080"
    echo ""
    echo "📋 Useful commands:"
    echo "  View logs:    docker-compose logs -f"
    echo "  Stop app:     docker-compose down"
    echo "  Restart app:  docker-compose restart"
else
    echo "❌ Deployment failed. Check logs with: docker-compose logs"
    exit 1
fi
```

Make it executable:
```bash
chmod +x deploy.sh
```

### Step 3: Deploy

```bash
# Deploy the application
./deploy.sh

# View logs
docker-compose logs -f namel3ss

# Access the application
# Open http://your-server-ip:8080 in your browser
```

### Managing the Docker Deployment

```bash
# View logs
docker-compose logs -f

# Stop application
docker-compose down

# Restart application
docker-compose restart

# Update application
git pull
./deploy.sh

# Access database
docker-compose exec db psql -U namel3ss -d namel3ss
```

---

## Method 2: Systemd Service (Non-Containerized)

For deploying directly on the host system without Docker.

### Step 1: Install namel3ss

```bash
# Install namel3ss
sudo pip3 install namel3ss

# Verify installation
n3 --version
```

### Step 2: Set Up Application Directory

```bash
# Create application directory
sudo mkdir -p /opt/namel3ss-app/data

# Copy your application files
sudo cp -r . /opt/namel3ss-app/

# Set ownership (replace 'ubuntu' with your user)
sudo chown -R ubuntu:ubuntu /opt/namel3ss-app

# Install dependencies
cd /opt/namel3ss-app
pip3 install -r requirements.txt
n3 deps install
```

### Step 3: Create Systemd Service

**namel3ss-app.service**:
```ini
[Unit]
Description=namel3ss Application
After=network.target postgresql.service

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/namel3ss-app
Environment="N3_PERSIST_TARGET=postgres"
Environment="N3_DATABASE_URL=postgres://namel3ss:password@localhost:5432/namel3ss"
Environment="OPENAI_API_KEY=sk-your-api-key"
ExecStart=/usr/local/bin/n3 app.ai studio --host 0.0.0.0 --port 8080
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Step 4: Install and Start Service

```bash
# Copy service file
sudo cp namel3ss-app.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable service (start on boot)
sudo systemctl enable namel3ss-app.service

# Start service
sudo systemctl start namel3ss-app.service

# Check status
sudo systemctl status namel3ss-app.service
```

### Managing the Systemd Service

```bash
# View logs
sudo journalctl -u namel3ss-app.service -f

# Stop service
sudo systemctl stop namel3ss-app.service

# Restart service
sudo systemctl restart namel3ss-app.service

# Disable service
sudo systemctl disable namel3ss-app.service
```

---

## Setting Up Nginx Reverse Proxy (Optional)

To access your application via a custom domain with SSL.

### Step 1: Install Nginx

```bash
sudo apt-get update
sudo apt-get install -y nginx
```

### Step 2: Configure Nginx

Create `/etc/nginx/sites-available/namel3ss`:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

Enable the site:
```bash
sudo ln -s /etc/nginx/sites-available/namel3ss /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### Step 3: Set Up SSL with Let's Encrypt

```bash
# Install certbot
sudo apt-get install -y certbot python3-certbot-nginx

# Obtain SSL certificate
sudo certbot --nginx -d your-domain.com

# Certbot will automatically configure SSL
```

Your application is now accessible at `https://your-domain.com`

---

## Environment Variables Reference

| Variable | Description | Example |
|----------|-------------|---------|
| `N3_PERSIST_TARGET` | Database type | `postgres` or `sqlite` |
| `N3_DATABASE_URL` | Database connection string | `postgres://user:pass@host:5432/db` |
| `OPENAI_API_KEY` | OpenAI API key | `sk-...` |
| `ANTHROPIC_API_KEY` | Anthropic API key | `sk-ant-...` |
| `N3_STUDIO_AUTH_ENABLED` | Enable Studio auth | `true` or `false` |
| `N3_STUDIO_AUTH_TOKEN` | Studio auth token | Random secure string |

---

## Health Checks

### Application Health

```bash
# Check if application is running
curl http://localhost:8080/health

# Check namel3ss CLI
n3 app.ai check
```

### Database Health

```bash
# PostgreSQL
pg_isready -h localhost -U namel3ss

# Or via Docker
docker-compose exec db pg_isready -U namel3ss
```

---

## Troubleshooting

### Application Won't Start

```bash
# Check logs (Docker)
docker-compose logs namel3ss

# Check logs (systemd)
sudo journalctl -u namel3ss-app.service -n 50

# Common issues:
# - Database connection failed
# - Missing environment variables
# - Port already in use
```

### Database Connection Issues

```bash
# Test database connection
psql -h localhost -U namel3ss -d namel3ss

# Check database is running (Docker)
docker-compose ps db

# Check database is running (systemd)
sudo systemctl status postgresql
```

### Port Already in Use

```bash
# Find what's using port 8080
sudo lsof -i :8080

# Kill the process (replace PID)
sudo kill -9 <PID>
```

---

## Production Checklist

Before going to production, ensure:

- [ ] SSL/TLS configured (HTTPS)
- [ ] Database backups automated
- [ ] Environment variables secured (not in code)
- [ ] Firewall configured (only necessary ports open)
- [ ] Monitoring set up
- [ ] Log rotation configured
- [ ] Health checks implemented
- [ ] Disaster recovery plan documented

---

## Next Steps

- **Comprehensive Guide**: See [Production Deployment Guide](production-deployment.md) for advanced topics
- **Security**: Review [Security Policy](../SECURITY.md)
- **Monitoring**: Set up logging and metrics
- **Backups**: Implement automated database backups
- **Scaling**: Consider Kubernetes for multi-instance deployments

---

## Support

- **Documentation**: [namel3ss docs](https://github.com/namel3ss-Ai/namel3ss/tree/main/docs)
- **Issues**: [GitHub Issues](https://github.com/namel3ss-Ai/namel3ss/issues)
- **Community**: [Discord](https://discord.gg/x8s6aEwdU)

---

**Document Version**: 1.0  
**For**: namel3ss applications  
**Status**: Ready for beta/production use
