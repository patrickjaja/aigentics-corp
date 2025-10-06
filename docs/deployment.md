# AI Offer Agent - Deployment Guide

Complete step-by-step guide for deploying the AI Offer Agent to production using Coolify on Hetzner Cloud.

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Infrastructure Setup](#infrastructure-setup)
3. [Coolify Installation](#coolify-installation)
4. [Application Deployment](#application-deployment)
5. [Database Setup](#database-setup)
6. [Environment Configuration](#environment-configuration)
7. [SSL/TLS Configuration](#ssltls-configuration)
8. [Monitoring & Logging](#monitoring--logging)
9. [Backup & Recovery](#backup--recovery)
10. [Scaling](#scaling)
11. [Troubleshooting](#troubleshooting)

## Prerequisites

### Required Accounts
- Hetzner Cloud account (https://www.hetzner.com/cloud)
- Domain name with DNS access
- OpenAI API key (for GPT-4)
- Email service (SMTP credentials)

### Local Tools
- SSH client
- `ssh-keygen` for key generation
- Git
- Browser for Coolify dashboard

### Knowledge Requirements
- Basic Linux command line
- Docker concepts
- DNS configuration
- SSL/TLS basics

## Infrastructure Setup

### 1. Create Hetzner Cloud Server

**Recommended Specifications:**
- **Development/Staging**: CPX31 (4 vCPU, 8 GB RAM, 160 GB SSD)
- **Production**: CPX51 (16 vCPU, 32 GB RAM, 360 GB SSD)
- **Location**: Choose nearest to your users (e.g., Nuremberg for EU)
- **OS**: Ubuntu 22.04 LTS

**Step-by-step:**

1. Log in to Hetzner Cloud Console
2. Create new project: "AI Offer Agent Production"
3. Click "Add Server"
4. Select:
   - Location: Nuremberg (nbg1)
   - Image: Ubuntu 22.04
   - Type: CPX51 (or CPX31 for staging)
   - SSH Key: Add your public key (generate with `ssh-keygen -t ed25519`)
5. Set server name: `ai-offer-agent-prod`
6. Click "Create & Buy now"

**Cost Estimate (CPX51):**
- Server: ~€30/month
- Volumes: ~€10/month (200GB for backups)
- Traffic: Included (20TB)
- **Total**: ~€40/month

### 2. Configure Firewall

Create firewall in Hetzner Console:

```
Inbound Rules:
- SSH (22): Your IP only (for security)
- HTTP (80): 0.0.0.0/0
- HTTPS (443): 0.0.0.0/0

Outbound Rules:
- Allow all (for updates and external API calls)
```

Apply firewall to your server.

### 3. Create Block Storage (Optional but Recommended)

For database persistence:

1. In Hetzner Console, go to Volumes
2. Create volume:
   - Name: `ai-offer-agent-data`
   - Size: 200 GB
   - Location: Same as server (nbg1)
3. Attach to server
4. Format and mount:

```bash
ssh root@your-server-ip

# Find volume device
lsblk

# Format volume (first time only!)
mkfs.ext4 /dev/sdb

# Create mount point
mkdir -p /mnt/data

# Mount volume
mount /dev/sdb /mnt/data

# Add to /etc/fstab for auto-mount
echo '/dev/sdb /mnt/data ext4 defaults 0 0' >> /etc/fstab

# Verify
df -h
```

### 4. Initial Server Setup

```bash
# SSH into server
ssh root@your-server-ip

# Update system
apt update && apt upgrade -y

# Install basic tools
apt install -y curl wget git htop vim ufw fail2ban

# Configure firewall
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw enable

# Configure fail2ban (protection against brute force)
systemctl enable fail2ban
systemctl start fail2ban

# Set timezone
timedatectl set-timezone Europe/Berlin

# Set hostname
hostnamectl set-hostname ai-offer-agent-prod
```

## Coolify Installation

### 1. Install Coolify

```bash
# Install Coolify (official installation script)
curl -fsSL https://get.coollabs.io/install.sh | bash

# This will:
# - Install Docker Engine
# - Install Docker Compose
# - Set up Coolify dashboard
# - Configure reverse proxy (Traefik)
# - Generate SSL certificates (Let's Encrypt)
```

Installation takes 5-10 minutes. Wait for completion.

### 2. Access Coolify Dashboard

1. Open browser: `http://your-server-ip:8000`
2. Create admin account:
   - Email: your-email@company.com
   - Password: Strong password (min 12 chars)
   - Save credentials securely!

3. Configure email notifications:
   - Go to Settings → Notifications
   - Add SMTP details
   - Test email delivery

### 3. Configure Coolify Settings

In Coolify Dashboard:

**General Settings:**
- Instance Name: "AI Offer Agent Production"
- Timezone: Europe/Berlin
- Auto-update: Enabled

**Security:**
- Enable 2FA (highly recommended)
- Set IP whitelist for dashboard access
- Configure webhook secret

**Backup:**
- S3 bucket for backups (or Hetzner Object Storage)
- Backup schedule: Daily at 2 AM
- Retention: 30 days

## Application Deployment

### 1. Add GitHub Repository

1. In Coolify Dashboard: Sources → Add Source
2. Select: GitHub
3. Authenticate with GitHub
4. Add repository: `aigentics-corp/aigentics-corp`
5. Branch: `main` (production) or `staging` (for testing)

### 2. Create Backend Service

1. Resources → New Resource → Docker Compose
2. Configuration:
   - Name: `ai-offer-backend`
   - Source: Select your GitHub repo
   - Branch: `main`
   - Build Pack: Docker Compose
   - Docker Compose File: `/docker-compose.yml`

3. Build Configuration:
   ```yaml
   # This will use the docker-compose.yml from repo
   # Coolify will automatically detect services
   ```

### 3. Create Frontend Service

1. Resources → New Resource → Application
2. Configuration:
   - Name: `ai-offer-frontend`
   - Source: GitHub repo
   - Branch: `main`
   - Build Pack: Nixpacks (auto-detects Next.js)
   - Build Command: `npm run build`
   - Start Command: `npm start`
   - Port: 3000

### 4. Configure Domains

**Backend API:**
1. Select backend service
2. Domains → Add Domain
3. Domain: `api.aigentics-corp.com`
4. Enable HTTPS (Let's Encrypt)
5. Coolify auto-configures SSL

**Frontend:**
1. Select frontend service
2. Domains → Add Domain
3. Domain: `app.aigentics-corp.com`
4. Enable HTTPS

**DNS Configuration** (at your domain provider):
```
api.aigentics-corp.com  →  A     →  your-server-ip
app.aigentics-corp.com  →  A     →  your-server-ip
```

Wait 5-10 minutes for DNS propagation.

## Database Setup

### 1. PostgreSQL with TimescaleDB

In Coolify:

1. Resources → New Resource → Database → PostgreSQL
2. Configuration:
   - Name: `ai-offer-postgres`
   - Version: PostgreSQL 16
   - Database: `ai_offer_agent`
   - Username: `ai_offer_user`
   - Password: Auto-generated (save it!)
   - Storage Path: `/mnt/data/postgres`

3. Enable TimescaleDB extension:
   ```bash
   # Connect to database
   docker exec -it <postgres-container> psql -U ai_offer_user -d ai_offer_agent

   # Enable extension
   CREATE EXTENSION IF NOT EXISTS timescaledb;

   # Verify
   \dx timescaledb
   ```

### 2. Redis Cache

1. Resources → New Resource → Database → Redis
2. Configuration:
   - Name: `ai-offer-redis`
   - Version: Redis 7
   - Max Memory: 2GB
   - Eviction Policy: allkeys-lru
   - Persistence: RDB + AOF

### 3. Qdrant Vector Database

1. Resources → New Resource → Docker Image
2. Configuration:
   - Name: `ai-offer-qdrant`
   - Image: `qdrant/qdrant:latest`
   - Port: 6333
   - Volume: `/mnt/data/qdrant:/qdrant/storage`

## Environment Configuration

### Backend Environment Variables

In Coolify → Backend Service → Environment:

```bash
# Application
NODE_ENV=production
PORT=8000
HOST=0.0.0.0
LOG_LEVEL=info

# Database
DATABASE_URL=postgresql://ai_offer_user:PASSWORD@ai-offer-postgres:5432/ai_offer_agent
REDIS_URL=redis://ai-offer-redis:6379
QDRANT_URL=http://ai-offer-qdrant:6333

# OpenAI
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-4-turbo-preview
OPENAI_MAX_TOKENS=4096

# Security
API_KEY_SALT=random-32-char-string
JWT_SECRET=random-64-char-string
CORS_ORIGINS=https://app.aigentics-corp.com

# Email (SMTP)
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USER=apikey
SMTP_PASSWORD=your-sendgrid-key
SMTP_FROM=noreply@aigentics-corp.com

# Monitoring
SENTRY_DSN=https://your-sentry-dsn
PROMETHEUS_ENABLED=true

# Rate Limiting
RATE_LIMIT_GLOBAL=100
RATE_LIMIT_CONVERSATION=50
RATE_LIMIT_OFFER_GENERATION=10

# Feature Flags
FEATURE_APPROVAL_WORKFLOW=true
FEATURE_ANALYTICS=true
GDPR_MODE=strict
```

**Generate secrets:**
```bash
# API Key Salt
openssl rand -hex 32

# JWT Secret
openssl rand -hex 64
```

### Frontend Environment Variables

```bash
# Application
NODE_ENV=production
NEXT_PUBLIC_API_URL=https://api.aigentics-corp.com/v1
NEXT_PUBLIC_WS_URL=wss://api.aigentics-corp.com/ws

# Analytics
NEXT_PUBLIC_ANALYTICS_ID=your-analytics-id

# Feature Flags
NEXT_PUBLIC_ENABLE_ANALYTICS=true
```

## SSL/TLS Configuration

Coolify handles SSL automatically via Let's Encrypt:

1. Domains are configured in service settings
2. Certificates auto-renew every 60 days
3. HTTPS redirect is automatic

**Manual verification:**
```bash
# Check certificate
curl -vI https://api.aigentics-corp.com

# Expected: HTTP/2 200, valid certificate
```

**Custom SSL certificate (optional):**
1. In service settings: SSL/TLS
2. Upload custom certificate + private key
3. Coolify will use instead of Let's Encrypt

## Monitoring & Logging

### 1. Application Metrics (Prometheus + Grafana)

Deploy monitoring stack:

```bash
# In Coolify: Add Docker Compose service
# Use monitoring compose from infrastructure/prometheus/
```

1. Resources → New Resource → Docker Compose
2. Name: `monitoring-stack`
3. Paste compose from `/infrastructure/grafana/docker-compose.yml`

**Access:**
- Grafana: `https://grafana.aigentics-corp.com`
- Prometheus: Internal only (port 9090)

**Import dashboards:**
1. Log in to Grafana (admin/admin)
2. Import dashboard from `/infrastructure/grafana/dashboards/`
3. Configure data source: Prometheus URL

### 2. Application Logs

**View logs in Coolify:**
1. Select service
2. Logs tab
3. Real-time streaming

**Export logs to external service:**
```bash
# Configure in docker-compose.yml
logging:
  driver: "syslog"
  options:
    syslog-address: "tcp://logs.example.com:514"
```

**Log aggregation with Loki (optional):**
1. Add Loki service in Coolify
2. Configure log shipping
3. Query logs in Grafana

### 3. Uptime Monitoring

**Setup health checks:**
1. In Coolify → Service → Health Check
2. Path: `/health`
3. Interval: 30 seconds
4. Timeout: 5 seconds
5. Retries: 3

**External monitoring (recommended):**
- UptimeRobot (free): https://uptimerobot.com
- StatusCake
- Pingdom

Monitor endpoints:
- `https://api.aigentics-corp.com/health`
- `https://app.aigentics-corp.com`

## Backup & Recovery

### 1. Database Backups

**Automated backups in Coolify:**
1. Database service → Backups
2. Schedule: Daily at 2:00 AM
3. Retention: 30 days
4. Storage: Hetzner Object Storage or S3

**Manual backup:**
```bash
# PostgreSQL backup
docker exec ai-offer-postgres pg_dump -U ai_offer_user -d ai_offer_agent -F c -f /backups/backup-$(date +%F).dump

# Copy to local machine
scp root@server-ip:/backups/backup-*.dump ./backups/
```

**Backup to S3:**
```bash
# Install s3cmd
apt install s3cmd

# Configure
s3cmd --configure

# Backup script
#!/bin/bash
BACKUP_FILE="/tmp/db-backup-$(date +%F-%H%M%S).dump"
docker exec ai-offer-postgres pg_dump -U ai_offer_user -d ai_offer_agent -F c -f $BACKUP_FILE
s3cmd put $BACKUP_FILE s3://ai-offer-backups/db/
rm $BACKUP_FILE
```

**Cron job for automated backups:**
```bash
# Edit crontab
crontab -e

# Add daily backup at 2 AM
0 2 * * * /usr/local/bin/backup-db.sh
```

### 2. Application State Backup

**Backup volumes:**
```bash
# Backup entire data volume
tar -czf /tmp/data-backup-$(date +%F).tar.gz /mnt/data/

# Upload to S3
s3cmd put /tmp/data-backup-*.tar.gz s3://ai-offer-backups/volumes/
```

### 3. Recovery Procedures

**Restore database:**
```bash
# Copy backup to server
scp backup-2025-10-06.dump root@server-ip:/tmp/

# Restore
docker exec -i ai-offer-postgres pg_restore -U ai_offer_user -d ai_offer_agent -c /tmp/backup-2025-10-06.dump

# Verify
docker exec ai-offer-postgres psql -U ai_offer_user -d ai_offer_agent -c "SELECT COUNT(*) FROM offers;"
```

**Full system recovery:**
1. Create new Hetzner server
2. Install Coolify
3. Restore volume from backup
4. Redeploy services from Coolify
5. Update DNS if IP changed

## Scaling

### Vertical Scaling (Increase Resources)

**Upgrade Hetzner server:**
1. Create snapshot of current server
2. Power off server
3. Resize to larger plan (e.g., CPX51 → CCX63)
4. Power on
5. Verify services

**Coolify auto-restarts services.**

### Horizontal Scaling (Multiple Instances)

**Load Balancer Setup:**
1. Create Hetzner Load Balancer
2. Add backend servers (multiple instances)
3. Configure health checks
4. Update DNS to point to LB IP

**Database replication:**
```yaml
# PostgreSQL read replicas
# Configure in docker-compose.yml
postgres-replica:
  image: postgres:16
  environment:
    POSTGRES_REPLICATION_MODE: slave
    POSTGRES_MASTER_HOST: postgres-primary
```

**Redis Sentinel for HA:**
```yaml
# High-availability Redis
redis-sentinel:
  image: redis:7
  command: redis-sentinel /etc/redis/sentinel.conf
```

### Caching Strategy

**Implement Redis caching:**
- Offer templates: 1 hour TTL
- Customer data: 15 minutes TTL
- Conversation state: Session-based
- Analytics: 5 minutes TTL

## Troubleshooting

### Common Issues

**1. Service won't start:**
```bash
# Check logs
docker logs <container-name>

# Check environment variables
docker exec <container> env

# Restart service
docker restart <container>
```

**2. Database connection failed:**
```bash
# Test connection
docker exec -it ai-offer-postgres psql -U ai_offer_user -d ai_offer_agent

# Check network
docker network inspect coolify

# Verify credentials in .env
```

**3. SSL certificate issues:**
```bash
# Check certificate
openssl s_client -connect api.aigentics-corp.com:443

# Force renewal
docker exec coolify-proxy certbot renew --force-renewal

# Check Traefik logs
docker logs coolify-proxy
```

**4. Out of memory:**
```bash
# Check memory usage
free -h
docker stats

# Increase swap (emergency)
fallocate -l 4G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile

# Permanent: add to /etc/fstab
echo '/swapfile none swap sw 0 0' >> /etc/fstab
```

**5. High CPU usage:**
```bash
# Identify process
htop
docker stats

# Check application logs for errors
docker logs ai-offer-backend --tail 100

# May indicate:
# - Infinite loop in code
# - Database query issues
# - External API rate limiting causing retries
```

### Performance Tuning

**PostgreSQL:**
```sql
-- Analyze query performance
EXPLAIN ANALYZE SELECT * FROM offers WHERE status = 'pending_approval';

-- Add indexes
CREATE INDEX idx_offers_status ON offers(status);
CREATE INDEX idx_offers_created_at ON offers(created_at);

-- Vacuum database
VACUUM ANALYZE;
```

**Redis:**
```bash
# Monitor Redis
docker exec -it ai-offer-redis redis-cli MONITOR

# Check memory usage
docker exec -it ai-offer-redis redis-cli INFO memory

# Increase max memory in Coolify settings
```

### Health Check Commands

```bash
# Quick system check
#!/bin/bash

echo "=== System Health Check ==="

# Disk space
echo "Disk Space:"
df -h | grep -E 'Filesystem|/dev/sd'

# Memory
echo -e "\nMemory:"
free -h

# Docker containers
echo -e "\nDocker Containers:"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Database connection
echo -e "\nDatabase:"
docker exec ai-offer-postgres pg_isready -U ai_offer_user

# Redis connection
echo -e "\nRedis:"
docker exec ai-offer-redis redis-cli PING

# API health
echo -e "\nAPI Health:"
curl -s https://api.aigentics-corp.com/health | jq .

# SSL expiry
echo -e "\nSSL Certificate:"
echo | openssl s_client -servername api.aigentics-corp.com -connect api.aigentics-corp.com:443 2>/dev/null | openssl x509 -noout -dates
```

Save as `/usr/local/bin/health-check.sh` and run daily.

## Maintenance

### Regular Tasks

**Weekly:**
- Review application logs for errors
- Check disk space usage
- Monitor API response times
- Review failed backup jobs

**Monthly:**
- Update Docker images (test in staging first)
- Review and rotate API keys
- Audit user access logs
- Check SSL certificate validity
- Performance optimization review

**Quarterly:**
- Security audit
- Disaster recovery drill
- Review and update documentation
- Capacity planning review

### Update Procedures

**Application updates:**
1. Test in staging environment
2. Create database backup
3. Deploy to production via Coolify:
   - Go to service → Deployments
   - Click "Redeploy"
   - Coolify pulls latest from GitHub and redeploys
4. Monitor logs for errors
5. Run smoke tests
6. Rollback if issues detected

**System updates:**
```bash
# Update OS packages
apt update && apt upgrade -y

# Update Docker
curl -fsSL https://get.docker.com | bash

# Update Coolify
curl -fsSL https://get.coollabs.io/install.sh | bash
```

## Support & Resources

- **Coolify Docs**: https://coolify.io/docs
- **Hetzner Status**: https://status.hetzner.com
- **Internal Runbook**: See `/docs/runbook.md`
- **On-call**: +49 30 1234-5678

## Checklist

Use this checklist for new deployments:

- [ ] Hetzner server created and configured
- [ ] Firewall rules applied
- [ ] Block storage attached and mounted
- [ ] Coolify installed
- [ ] GitHub repository connected
- [ ] Backend service deployed
- [ ] Frontend service deployed
- [ ] PostgreSQL database running
- [ ] Redis cache running
- [ ] Qdrant vector DB running
- [ ] Environment variables configured
- [ ] DNS records updated
- [ ] SSL certificates active (HTTPS working)
- [ ] Database migrations run
- [ ] Monitoring stack deployed
- [ ] Backup jobs configured and tested
- [ ] Health checks passing
- [ ] Smoke tests successful
- [ ] Documentation updated
- [ ] Team notified of deployment

---

**Document Version**: 1.0.0
**Last Updated**: 2025-10-06
**Maintainer**: DevOps Team
