# Production Deployment Guide

**Version**: 1.0  
**Last Updated**: 2026-01-11  
**Status**: Draft (for beta/production use)

> [!WARNING]
> namel3ss is currently in **alpha** (v0.1.0a24). This deployment guide is prepared for future beta and production releases. Do not deploy alpha versions to production.

---

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Deployment Options](#deployment-options)
4. [Docker Deployment](#docker-deployment)
5. [Kubernetes Deployment](#kubernetes-deployment)
6. [Cloud Platform Deployment](#cloud-platform-deployment)
7. [Database Configuration](#database-configuration)
8. [Security Hardening](#security-hardening)
9. [Monitoring and Observability](#monitoring-and-observability)
10. [Performance Tuning](#performance-tuning)
11. [Backup and Disaster Recovery](#backup-and-disaster-recovery)
12. [Troubleshooting](#troubleshooting)

---

## Overview

This guide covers production deployment of namel3ss applications. It includes:

- **Infrastructure setup** for various platforms
- **Security best practices** for production environments
- **Monitoring and observability** configuration
- **Performance optimization** strategies
- **Disaster recovery** procedures

### Deployment Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     Load Balancer                        │
│                    (HTTPS/TLS)                          │
└────────────────────┬────────────────────────────────────┘
                     │
         ┌───────────┴───────────┐
         │                       │
    ┌────▼─────┐          ┌─────▼────┐
    │ namel3ss │          │ namel3ss │
    │ Instance │          │ Instance │
    │    1     │          │    2     │
    └────┬─────┘          └─────┬────┘
         │                       │
         └───────────┬───────────┘
                     │
              ┌──────▼──────┐
              │  PostgreSQL │
              │   Database  │
              └─────────────┘
```

---

## Prerequisites

### System Requirements

**Minimum** (Development/Testing):
- **CPU**: 2 cores
- **RAM**: 4 GB
- **Storage**: 20 GB
- **OS**: Linux (Ubuntu 20.04+, Debian 11+, RHEL 8+)

**Recommended** (Production):
- **CPU**: 4+ cores
- **RAM**: 8+ GB
- **Storage**: 50+ GB SSD
- **OS**: Linux (Ubuntu 22.04 LTS or RHEL 9)

### Software Requirements

- **Python**: 3.14
- **Database**: PostgreSQL 13+ (production) or SQLite (development)
- **Reverse Proxy**: Nginx or Caddy (recommended)
- **Container Runtime**: Docker 20.10+ or containerd (if using containers)

### Network Requirements

- **Inbound**: Port 443 (HTTPS), Port 80 (HTTP redirect)
- **Outbound**: AI provider APIs (OpenAI, Anthropic, etc.)
- **Database**: Port 5432 (PostgreSQL) - internal only

---

## Deployment Options

### 1. Docker Deployment (Recommended)

**Best for**: Quick deployment, consistent environments, easy scaling

**Pros**:
- Consistent environment across dev/staging/prod
- Easy rollback and versioning
- Simplified dependency management

**Cons**:
- Additional layer of complexity
- Slightly higher resource usage

### 2. Kubernetes Deployment

**Best for**: Large-scale deployments, auto-scaling, high availability

**Pros**:
- Auto-scaling and self-healing
- Advanced orchestration features
- Multi-region deployment

**Cons**:
- Higher operational complexity
- Steeper learning curve

### 3. Traditional VM/Bare Metal

**Best for**: Simple deployments, legacy infrastructure

**Pros**:
- Direct control over environment
- Lower overhead

**Cons**:
- Manual dependency management
- More complex updates and rollbacks

### 4. Cloud Platform (PaaS)

**Best for**: Rapid deployment, managed infrastructure

**Supported Platforms**:
- AWS (ECS, Fargate, EC2)
- Google Cloud (Cloud Run, GKE, Compute Engine)
- Azure (Container Instances, AKS, VMs)
- DigitalOcean (App Platform, Droplets)
- Heroku (Dynos)

---

## Docker Deployment

### Step 1: Create Dockerfile

Create `Dockerfile` in your project root:

```dockerfile
FROM python:3.14-slim

# Set working directory
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
COPY pyproject.toml .
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install tool dependencies
RUN n3 deps install

# Create non-root user
RUN useradd -m -u 1000 namel3ss && \\
    chown -R namel3ss:namel3ss /app
USER namel3ss

# Expose Studio port (if using)
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
    CMD n3 app.ai check || exit 1

# Default command
CMD ["n3", "app.ai", "studio", "--host", "0.0.0.0", "--port", "8080"]
```

### Step 2: Create docker-compose.yml

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
      - N3_STUDIO_AUTH_ENABLED=true
      - N3_STUDIO_AUTH_TOKEN=${STUDIO_AUTH_TOKEN}
    depends_on:
      db:
        condition: service_healthy
    restart: unless-stopped
    volumes:
      - ./data:/app/data
    networks:
      - namel3ss-network

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
    networks:
      - namel3ss-network

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - namel3ss
    restart: unless-stopped
    networks:
      - namel3ss-network

volumes:
  postgres-data:

networks:
  namel3ss-network:
    driver: bridge
```

### Step 3: Create .env File

```bash
# Database
DB_PASSWORD=<strong-random-password>

# AI Providers
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Studio Authentication
STUDIO_AUTH_TOKEN=<secure-random-token>

# Optional: Monitoring
SENTRY_DSN=https://...
```

### Step 4: Create nginx.conf

```nginx
events {
    worker_connections 1024;
}

http {
    upstream namel3ss {
        server namel3ss:8080;
    }

    server {
        listen 80;
        server_name example.com;
        return 301 https://$server_name$request_uri;
    }

    server {
        listen 443 ssl http2;
        server_name example.com;

        ssl_certificate /etc/nginx/ssl/cert.pem;
        ssl_certificate_key /etc/nginx/ssl/key.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers HIGH:!aNULL:!MD5;

        client_max_body_size 10M;

        location / {
            proxy_pass http://namel3ss;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            
            # WebSocket support (if needed)
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
        }

        # Health check endpoint
        location /health {
            access_log off;
            proxy_pass http://namel3ss/health;
        }
    }
}
```

### Step 5: Deploy

```bash
# Build and start services
docker-compose up -d

# Check logs
docker-compose logs -f namel3ss

# Check health
curl https://example.com/health
```

---

## Kubernetes Deployment

### Step 1: Create Kubernetes Manifests

**deployment.yaml**:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: namel3ss
  labels:
    app: namel3ss
spec:
  replicas: 3
  selector:
    matchLabels:
      app: namel3ss
  template:
    metadata:
      labels:
        app: namel3ss
    spec:
      containers:
      - name: namel3ss
        image: your-registry/namel3ss:latest
        ports:
        - containerPort: 8080
        env:
        - name: N3_PERSIST_TARGET
          value: "postgres"
        - name: N3_DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: namel3ss-secrets
              key: database-url
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: namel3ss-secrets
              key: openai-api-key
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "2000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 5
```

**service.yaml**:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: namel3ss-service
spec:
  selector:
    app: namel3ss
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8080
  type: LoadBalancer
```

**secrets.yaml** (use sealed secrets or external secrets in production):

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: namel3ss-secrets
type: Opaque
stringData:
  database-url: "postgres://user:pass@postgres-service:5432/namel3ss"
  openai-api-key: "sk-..."
```

### Step 2: Deploy to Kubernetes

```bash
# Create namespace
kubectl create namespace namel3ss

# Apply secrets
kubectl apply -f secrets.yaml -n namel3ss

# Deploy application
kubectl apply -f deployment.yaml -n namel3ss
kubectl apply -f service.yaml -n namel3ss

# Check status
kubectl get pods -n namel3ss
kubectl logs -f deployment/namel3ss -n namel3ss
```

---

## Cloud Platform Deployment

### AWS (ECS Fargate)

```bash
# 1. Build and push Docker image
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com
docker build -t namel3ss .
docker tag namel3ss:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/namel3ss:latest
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/namel3ss:latest

# 2. Create task definition (task-definition.json)
# 3. Create ECS service
aws ecs create-service \\
  --cluster namel3ss-cluster \\
  --service-name namel3ss-service \\
  --task-definition namel3ss:1 \\
  --desired-count 2 \\
  --launch-type FARGATE \\
  --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx],securityGroups=[sg-xxx],assignPublicIp=ENABLED}"
```

### Google Cloud (Cloud Run)

```bash
# Build and deploy
gcloud builds submit --tag gcr.io/PROJECT_ID/namel3ss
gcloud run deploy namel3ss \\
  --image gcr.io/PROJECT_ID/namel3ss \\
  --platform managed \\
  --region us-central1 \\
  --allow-unauthenticated \\
  --set-env-vars N3_PERSIST_TARGET=postgres,N3_DATABASE_URL=<connection-string>
```

### DigitalOcean App Platform

```yaml
# app.yaml
name: namel3ss
services:
- name: web
  github:
    repo: your-org/your-repo
    branch: main
  dockerfile_path: Dockerfile
  http_port: 8080
  instance_count: 2
  instance_size_slug: professional-xs
  envs:
  - key: N3_PERSIST_TARGET
    value: postgres
  - key: N3_DATABASE_URL
    value: ${db.DATABASE_URL}
databases:
- name: db
  engine: PG
  version: "15"
```

---

## Database Configuration

### PostgreSQL (Production)

**Connection String Format**:
```
postgres://username:password@host:port/database?sslmode=require
```

**Environment Variables**:
```bash
N3_PERSIST_TARGET=postgres
N3_DATABASE_URL=postgres://namel3ss:password@db.example.com:5432/namel3ss?sslmode=require
```

**Recommended PostgreSQL Configuration**:

```sql
-- Create database
CREATE DATABASE namel3ss;

-- Create user
CREATE USER namel3ss WITH ENCRYPTED PASSWORD 'strong-password';

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE namel3ss TO namel3ss;

-- Connection pooling (recommended)
ALTER SYSTEM SET max_connections = 200;
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
```

### SQLite (Development Only)

```bash
N3_PERSIST_TARGET=sqlite
# Database file: .namel3ss/namel3ss.db
```

> [!CAUTION]
> SQLite is NOT recommended for production use. Use PostgreSQL for production deployments.

---

## Security Hardening

### 1. Environment Variables

**Never commit secrets to version control**. Use:
- Environment variables
- Secret management services (AWS Secrets Manager, GCP Secret Manager, HashiCorp Vault)
- Kubernetes Secrets (with encryption at rest)

### 2. Network Security

```nginx
# Nginx security headers
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Referrer-Policy "no-referrer-when-downgrade" always;
add_header Content-Security-Policy "default-src 'self' http: https: data: blob: 'unsafe-inline'" always;
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
```

### 3. Database Security

- Use strong passwords (20+ characters, random)
- Enable SSL/TLS for database connections
- Restrict database access to application IPs only
- Regular backups with encryption
- Implement least-privilege access

### 4. Application Security

```bash
# Studio authentication (production)
N3_STUDIO_AUTH_ENABLED=true
N3_STUDIO_AUTH_TOKEN=<secure-random-token-64-chars>

# Generate secure token
openssl rand -hex 32
```

### 5. Container Security

- Run as non-root user
- Use minimal base images (alpine, distroless)
- Scan images for vulnerabilities
- Keep base images updated
- Implement resource limits

---

## Monitoring and Observability

### Logging

**Structured Logging Configuration**:

```python
# In your application
import logging
import json

logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    handlers=[logging.StreamHandler()]
)

# Log in JSON format for parsing
logger = logging.getLogger(__name__)
logger.info(json.dumps({
    "timestamp": "2026-01-11T18:00:00Z",
    "level": "INFO",
    "message": "Flow executed",
    "flow_name": "process_order",
    "duration_ms": 150
}))
```

### Metrics

**Prometheus Metrics** (example):

```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'namel3ss'
    static_configs:
      - targets: ['namel3ss:8080']
```

**Key Metrics to Monitor**:
- Request rate and latency
- Error rate
- AI provider API calls and latency
- Database query performance
- Memory and CPU usage
- Active connections

### Health Checks

Implement health check endpoint:

```bash
# Basic health check
curl https://example.com/health

# Expected response
{"status": "healthy", "timestamp": "2026-01-11T18:00:00Z"}
```

### Alerting

**Critical Alerts**:
- Application down (5xx errors > threshold)
- Database connection failures
- High error rate (> 5%)
- High latency (p95 > 2s)
- Disk space < 10%

---

## Performance Tuning

### Application-Level Optimization

1. **Connection Pooling**: Use pgbouncer for PostgreSQL
2. **Caching**: Implement Redis for frequently accessed data
3. **Async Processing**: Use background workers for long-running tasks
4. **Rate Limiting**: Protect against abuse

### Database Optimization

```sql
-- Create indexes for common queries
CREATE INDEX idx_records_created_at ON records(created_at);
CREATE INDEX idx_memory_user_id ON memory(user_id);

-- Analyze query performance
EXPLAIN ANALYZE SELECT * FROM records WHERE created_at > NOW() - INTERVAL '1 day';
```

### Resource Limits

```yaml
# Kubernetes resource limits
resources:
  requests:
    memory: "512Mi"
    cpu: "500m"
  limits:
    memory: "2Gi"
    cpu: "2000m"
```

---

## Backup and Disaster Recovery

### Database Backups

**Automated PostgreSQL Backups**:

```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/namel3ss_$TIMESTAMP.sql.gz"

# Create backup
pg_dump -h $DB_HOST -U $DB_USER -d namel3ss | gzip > $BACKUP_FILE

# Upload to S3 (optional)
aws s3 cp $BACKUP_FILE s3://your-backup-bucket/

# Retain last 30 days
find $BACKUP_DIR -name "namel3ss_*.sql.gz" -mtime +30 -delete
```

**Backup Schedule**:
- **Production**: Every 6 hours, retain 30 days
- **Staging**: Daily, retain 7 days

### Disaster Recovery

**RTO (Recovery Time Objective)**: < 1 hour  
**RPO (Recovery Point Objective)**: < 6 hours

**Recovery Procedure**:

```bash
# 1. Restore database
gunzip < backup.sql.gz | psql -h $DB_HOST -U $DB_USER -d namel3ss

# 2. Redeploy application
docker-compose up -d

# 3. Verify health
curl https://example.com/health
```

---

## Troubleshooting

### Common Issues

#### 1. Application Won't Start

```bash
# Check logs
docker-compose logs namel3ss

# Common causes:
# - Database connection failure
# - Missing environment variables
# - Port already in use
```

#### 2. Database Connection Errors

```bash
# Test database connectivity
psql -h $DB_HOST -U $DB_USER -d namel3ss

# Check connection string
echo $N3_DATABASE_URL
```

#### 3. High Memory Usage

```bash
# Check container stats
docker stats

# Adjust memory limits in docker-compose.yml
```

#### 4. Slow Performance

```bash
# Check database queries
# Enable slow query log in PostgreSQL
ALTER SYSTEM SET log_min_duration_statement = 1000; -- Log queries > 1s

# Check application logs for slow operations
```

### Debug Mode

```bash
# Enable debug logging
N3_LOG_LEVEL=DEBUG n3 app.ai studio
```

---

## Checklist: Pre-Production Deployment

- [ ] SSL/TLS certificates configured
- [ ] Database backups automated
- [ ] Monitoring and alerting configured
- [ ] Security headers implemented
- [ ] Secrets stored securely (not in code)
- [ ] Health checks implemented
- [ ] Resource limits configured
- [ ] Logging configured and centralized
- [ ] Disaster recovery plan documented
- [ ] Load testing completed
- [ ] Security audit completed
- [ ] Documentation updated

---

## Additional Resources

- [Security Best Practices](../SECURITY.md)
- [Quick Deployment Guide](quick-deployment-guide.md)
- [Production Readiness Roadmap](production-readiness-roadmap.md)
- [Grammar and Type Modernisation](grammar-types-modernisation.md)

### Operational Commands

Use these deterministic commands during production operations:

```bash
# Check cluster status and scale based on current load
n3 cluster status --json
n3 cluster scale 85 --json

# Perform rolling deployment to a new runtime version
n3 cluster deploy 1.2.0 --json

# Validate security/compliance config and run retention purge
n3 security check --json
n3 security purge --json

# Inspect federation contracts and usage before cross-tenant rollouts
n3 federation list --json
```

### Incident Response Quick Runbook

1. Confirm health and error rate:
   - Query `/health`, `/api/metrics`, and `/api/traces`.
2. Contain impact:
   - Scale down noisy traffic paths with `n3 cluster scale`.
   - Disable unsafe cross-tenant calls by removing the federation contract.
3. Recover:
   - Deploy last known good build with `n3 cluster deploy <version>`.
   - Restore database snapshot if required.
4. Verify and close:
   - Re-run smoke tests.
   - Confirm audit and retention jobs completed.
   - Log the incident in the operations tracker.

---

**Document Version**: 1.0  
**Feedback**: Please report issues or suggestions via [GitHub Issues](https://github.com/namel3ss-Ai/namel3ss/issues)
