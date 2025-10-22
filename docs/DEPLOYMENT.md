# WawaTrader Deployment Guide

## Table of Contents

- [Local Development](#local-development)
- [Docker Deployment](#docker-deployment)
- [Cloud Deployment](#cloud-deployment)
- [Production Checklist](#production-checklist)
- [Monitoring](#monitoring)
- [Troubleshooting](#troubleshooting)

---

## Local Development

### Prerequisites

- Python 3.12+
- pip/venv
- LM Studio
- Alpaca paper trading account

### Setup Steps

1. **Clone Repository**
   ```bash
   git clone https://github.com/yourusername/WawaTrader.git
   cd WawaTrader
   ```

2. **Create Virtual Environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On macOS/Linux
   # Or on Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set Environment Variables**
   ```bash
   # Create .env file
   cat > .env << EOF
   ALPACA_API_KEY=your_api_key_here
   ALPACA_SECRET_KEY=your_secret_key_here
   ALPACA_PAPER=true
   
   LM_STUDIO_BASE_URL=http://localhost:1234/v1
   LM_STUDIO_MODEL=gemma-3-4b
   
   ALERT_EMAIL_ENABLED=false
   ALERT_SLACK_ENABLED=false
   EOF
   
   # Load environment variables
   source .env  # Or export them manually
   ```

5. **Start LM Studio**
   - Open LM Studio application
   - Load Gemma 3 4B model
   - Start local server on port 1234
   - Verify: `curl http://localhost:1234/v1/models`

6. **Run Tests**
   ```bash
   pytest tests/ -v
   ```

7. **Start Configuration UI**
   ```bash
   python scripts/run_config_ui.py
   # Open http://localhost:5001
   ```

8. **Start Dashboard**
   ```bash
   python -m wawatrader.dashboard
   # Open http://localhost:8050
   ```

---

## Docker Deployment

### Build Docker Image

1. **Create Dockerfile**
   ```dockerfile
   # Dockerfile
   FROM python:3.12-slim
   
   WORKDIR /app
   
   # Install dependencies
   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt
   
   # Copy application
   COPY wawatrader/ ./wawatrader/
   COPY scripts/ ./scripts/
   
   # Create data directory
   RUN mkdir -p /data
   
   # Expose ports
   EXPOSE 5001 8050
   
   # Environment variables
   ENV PYTHONUNBUFFERED=1
   ENV DATABASE_PATH=/data/wawatrader.db
   ENV CONFIG_DATABASE_PATH=/data/wawatrader_config.db
   
   # Health check
   HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
     CMD python -c "import requests; requests.get('http://localhost:5001/health')"
   
   # Default command
   CMD ["python", "-m", "wawatrader.trading_agent"]
   ```

2. **Create docker-compose.yml**
   ```yaml
   version: '3.8'
   
   services:
     wawatrader:
       build: .
       container_name: wawatrader
       environment:
         - ALPACA_API_KEY=${ALPACA_API_KEY}
         - ALPACA_SECRET_KEY=${ALPACA_SECRET_KEY}
         - ALPACA_PAPER=true
         - LM_STUDIO_BASE_URL=http://host.docker.internal:1234/v1
         - LM_STUDIO_MODEL=gemma-3-4b
         - ALERT_EMAIL_ENABLED=${ALERT_EMAIL_ENABLED:-false}
         - ALERT_EMAIL_FROM=${ALERT_EMAIL_FROM}
         - ALERT_EMAIL_PASSWORD=${ALERT_EMAIL_PASSWORD}
         - ALERT_EMAIL_TO=${ALERT_EMAIL_TO}
         - ALERT_SLACK_ENABLED=${ALERT_SLACK_ENABLED:-false}
         - ALERT_SLACK_WEBHOOK_URL=${ALERT_SLACK_WEBHOOK_URL}
       ports:
         - "5001:5001"
         - "8050:8050"
       volumes:
         - ./data:/data
       restart: unless-stopped
       
     config-ui:
       build: .
       container_name: wawatrader-config-ui
       command: python scripts/run_config_ui.py --host 0.0.0.0
       environment:
         - CONFIG_DATABASE_PATH=/data/wawatrader_config.db
       ports:
         - "5001:5001"
       volumes:
         - ./data:/data
       restart: unless-stopped
       
     dashboard:
       build: .
       container_name: wawatrader-dashboard
       command: python -m wawatrader.dashboard
       environment:
         - DATABASE_PATH=/data/wawatrader.db
       ports:
         - "8050:8050"
       volumes:
         - ./data:/data
       restart: unless-stopped
   ```

3. **Build and Run**
   ```bash
   # Build image
   docker-compose build
   
   # Start services
   docker-compose up -d
   
   # View logs
   docker-compose logs -f
   
   # Stop services
   docker-compose down
   ```

4. **Verify Deployment**
   ```bash
   # Check containers
   docker-compose ps
   
   # Check logs
   docker-compose logs wawatrader
   
   # Test endpoints
   curl http://localhost:5001/api/config
   curl http://localhost:8050
   ```

---

## Cloud Deployment

### AWS EC2 Deployment

1. **Launch EC2 Instance**
   - AMI: Ubuntu 22.04 LTS
   - Instance Type: t3.medium (2 vCPU, 4 GB RAM)
   - Storage: 30 GB gp3
   - Security Group: Open ports 22, 5001, 8050

2. **Connect and Setup**
   ```bash
   # SSH into instance
   ssh -i your-key.pem ubuntu@your-ec2-ip
   
   # Update system
   sudo apt update && sudo apt upgrade -y
   
   # Install Python 3.12
   sudo add-apt-repository ppa:deadsnakes/ppa -y
   sudo apt install python3.12 python3.12-venv python3-pip -y
   
   # Install Docker (optional)
   curl -fsSL https://get.docker.com -o get-docker.sh
   sudo sh get-docker.sh
   sudo usermod -aG docker ubuntu
   ```

3. **Deploy Application**
   ```bash
   # Clone repository
   git clone https://github.com/yourusername/WawaTrader.git
   cd WawaTrader
   
   # Create virtual environment
   python3.12 -m venv venv
   source venv/bin/activate
   
   # Install dependencies
   pip install -r requirements.txt
   
   # Set environment variables
   nano .env  # Add your credentials
   source .env
   
   # Run with systemd (see Production Setup below)
   ```

4. **Configure Systemd Service**
   ```bash
   # Create service file
   sudo nano /etc/systemd/system/wawatrader.service
   ```
   
   ```ini
   [Unit]
   Description=WawaTrader Trading System
   After=network.target
   
   [Service]
   Type=simple
   User=ubuntu
   WorkingDirectory=/home/ubuntu/WawaTrader
   Environment="PATH=/home/ubuntu/WawaTrader/venv/bin"
   EnvironmentFile=/home/ubuntu/WawaTrader/.env
   ExecStart=/home/ubuntu/WawaTrader/venv/bin/python -m wawatrader.trading_agent
   Restart=always
   RestartSec=10
   
   [Install]
   WantedBy=multi-user.target
   ```
   
   ```bash
   # Enable and start service
   sudo systemctl daemon-reload
   sudo systemctl enable wawatrader
   sudo systemctl start wawatrader
   sudo systemctl status wawatrader
   ```

5. **Configure Nginx Reverse Proxy**
   ```bash
   # Install Nginx
   sudo apt install nginx -y
   
   # Create config
   sudo nano /etc/nginx/sites-available/wawatrader
   ```
   
   ```nginx
   server {
       listen 80;
       server_name your-domain.com;
       
       location / {
           proxy_pass http://localhost:8050;
           proxy_http_version 1.1;
           proxy_set_header Upgrade $http_upgrade;
           proxy_set_header Connection 'upgrade';
           proxy_set_header Host $host;
           proxy_cache_bypass $http_upgrade;
       }
       
       location /config {
           proxy_pass http://localhost:5001;
           proxy_http_version 1.1;
           proxy_set_header Host $host;
       }
   }
   ```
   
   ```bash
   # Enable site
   sudo ln -s /etc/nginx/sites-available/wawatrader /etc/nginx/sites-enabled/
   sudo nginx -t
   sudo systemctl restart nginx
   ```

### Google Cloud Run Deployment

1. **Create cloudbuild.yaml**
   ```yaml
   steps:
     - name: 'gcr.io/cloud-builders/docker'
       args: ['build', '-t', 'gcr.io/$PROJECT_ID/wawatrader', '.']
     - name: 'gcr.io/cloud-builders/docker'
       args: ['push', 'gcr.io/$PROJECT_ID/wawatrader']
     - name: 'gcr.io/cloud-builders/gcloud'
       args:
         - 'run'
         - 'deploy'
         - 'wawatrader'
         - '--image=gcr.io/$PROJECT_ID/wawatrader'
         - '--platform=managed'
         - '--region=us-central1'
         - '--allow-unauthenticated'
   ```

2. **Deploy**
   ```bash
   # Install gcloud CLI
   curl https://sdk.cloud.google.com | bash
   gcloud init
   
   # Set project
   gcloud config set project YOUR_PROJECT_ID
   
   # Build and deploy
   gcloud builds submit --config cloudbuild.yaml
   ```

### Heroku Deployment

1. **Create Procfile**
   ```
   web: python -m wawatrader.trading_agent
   config: python scripts/run_config_ui.py --host 0.0.0.0 --port $PORT
   dashboard: python -m wawatrader.dashboard
   ```

2. **Deploy**
   ```bash
   # Install Heroku CLI
   brew tap heroku/brew && brew install heroku  # macOS
   
   # Login
   heroku login
   
   # Create app
   heroku create wawatrader
   
   # Set environment variables
   heroku config:set ALPACA_API_KEY=your_key
   heroku config:set ALPACA_SECRET_KEY=your_secret
   
   # Deploy
   git push heroku main
   
   # Scale dynos
   heroku ps:scale web=1 config=1 dashboard=1
   ```

---

## Production Checklist

### Pre-Deployment

- [ ] All tests passing (134/134)
- [ ] Environment variables configured
- [ ] LM Studio running and tested
- [ ] Alpaca API credentials verified (paper trading)
- [ ] Alert system configured (email/Slack)
- [ ] Configuration database initialized
- [ ] Trading database initialized
- [ ] Risk limits configured appropriately
- [ ] Watchlist symbols selected
- [ ] Backtesting completed with satisfactory results

### Security

- [ ] API keys stored securely (never in code)
- [ ] Database files have proper permissions (600)
- [ ] Web UI access restricted (localhost or VPN)
- [ ] SSL/TLS enabled for production
- [ ] Firewall rules configured
- [ ] Regular security updates enabled
- [ ] Monitoring and alerting configured

### Performance

- [ ] LM Studio response time < 200ms
- [ ] Alpaca API latency < 100ms
- [ ] Database queries < 10ms
- [ ] System memory usage < 1GB
- [ ] CPU usage < 10% during trading hours
- [ ] Disk space monitored (min 10GB free)

### Reliability

- [ ] Systemd service configured (auto-restart)
- [ ] Health checks enabled
- [ ] Log rotation configured
- [ ] Database backups automated
- [ ] Disaster recovery plan documented
- [ ] Failover strategy defined
- [ ] Monitoring alerts configured

---

## Monitoring

### Metrics to Track

1. **Trading Performance**
   - Total return (daily, weekly, monthly)
   - Sharpe ratio
   - Max drawdown
   - Win rate
   - Average trade P&L

2. **System Health**
   - API connection status
   - LLM response time
   - Database size
   - Error rate
   - Uptime percentage

3. **Risk Metrics**
   - Current portfolio exposure
   - Daily P&L
   - Position sizes
   - Trade frequency
   - Risk limit violations

### Monitoring Tools

**Prometheus + Grafana** (Recommended)

1. Install Prometheus:
   ```bash
   docker run -d -p 9090:9090 \
     -v /path/to/prometheus.yml:/etc/prometheus/prometheus.yml \
     prom/prometheus
   ```

2. Install Grafana:
   ```bash
   docker run -d -p 3000:3000 grafana/grafana
   ```

3. Create dashboard with panels for:
   - Portfolio value over time
   - Daily P&L
   - Trade execution rate
   - API latency
   - Error rate

**Application Logs**

```bash
# View logs
tail -f /var/log/wawatrader/trading.log

# Search logs
grep "ERROR" /var/log/wawatrader/trading.log

# Rotate logs (logrotate)
sudo nano /etc/logrotate.d/wawatrader
```

```
/var/log/wawatrader/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 ubuntu ubuntu
    sharedscripts
}
```

### Health Checks

Create health check endpoint:

```python
# wawatrader/health.py
from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/health')
def health_check():
    # Check database
    db = get_database()
    db_ok = db.test_connection()
    
    # Check Alpaca API
    client = AlpacaClient()
    api_ok = client.test_connection()
    
    # Check LM Studio
    llm = LLMBridge()
    llm_ok = llm.test_connection()
    
    status = "healthy" if (db_ok and api_ok and llm_ok) else "unhealthy"
    
    return jsonify({
        'status': status,
        'database': db_ok,
        'alpaca_api': api_ok,
        'lm_studio': llm_ok
    }), 200 if status == "healthy" else 503

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
```

---

## Troubleshooting

### Common Issues

**1. LM Studio Connection Failed**

```bash
# Check if LM Studio is running
curl http://localhost:1234/v1/models

# Check firewall
sudo ufw status
sudo ufw allow 1234

# Check environment variable
echo $LM_STUDIO_BASE_URL

# Test connection
python -c "from wawatrader.llm_bridge import LLMBridge; print(LLMBridge().test_connection())"
```

**2. Alpaca API Connection Failed**

```bash
# Check credentials
echo $ALPACA_API_KEY
echo $ALPACA_SECRET_KEY

# Test connection
python -c "from wawatrader.alpaca_client import AlpacaClient; print(AlpacaClient().get_account())"

# Check API status
curl https://status.alpaca.markets/
```

**3. Database Locked Error**

```bash
# Find process using database
lsof wawatrader.db

# Kill process if needed
kill -9 <PID>

# Fix permissions
chmod 600 wawatrader.db
chown ubuntu:ubuntu wawatrader.db
```

**4. High Memory Usage**

```bash
# Check memory
free -h
ps aux | grep python

# Reduce LM Studio model size
# Use Gemma 3 2B instead of 4B

# Limit concurrent processes
# Reduce check_interval_seconds
```

**5. Email Alerts Not Sending**

```bash
# Check SMTP settings
echo $ALERT_EMAIL_FROM
echo $ALERT_EMAIL_PASSWORD

# Test email
python scripts/test_email.py

# Gmail: Use App Password (not regular password)
# Enable 2FA and generate app password at:
# https://myaccount.google.com/apppasswords
```

**6. Configuration UI Not Loading**

```bash
# Check if running
curl http://localhost:5001/api/config

# Check logs
python scripts/run_config_ui.py --debug

# Check port availability
lsof -i :5001
```

### Debug Mode

Enable debug logging:

```python
# In your script
import logging
logging.basicConfig(level=logging.DEBUG)

# Or via environment variable
export LOG_LEVEL=DEBUG
```

### Performance Profiling

Profile slow components:

```python
import cProfile
import pstats

# Profile trading agent
profiler = cProfile.Profile()
profiler.enable()

# Run trading logic
agent = TradingAgent()
agent.run_once()

profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative')
stats.print_stats(20)
```

### Database Maintenance

```bash
# Backup database
cp wawatrader.db wawatrader_backup_$(date +%Y%m%d).db

# Vacuum database (reclaim space)
sqlite3 wawatrader.db "VACUUM;"

# Check integrity
sqlite3 wawatrader.db "PRAGMA integrity_check;"

# Export for analysis
sqlite3 wawatrader.db ".mode csv" ".output trades.csv" "SELECT * FROM trades;"
```

---

## Backup and Recovery

### Automated Backups

Create backup script:

```bash
#!/bin/bash
# backup.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups/wawatrader"
DB_FILE="/data/wawatrader.db"
CONFIG_FILE="/data/wawatrader_config.db"

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup databases
cp $DB_FILE "$BACKUP_DIR/wawatrader_$DATE.db"
cp $CONFIG_FILE "$BACKUP_DIR/wawatrader_config_$DATE.db"

# Compress backups older than 7 days
find $BACKUP_DIR -name "*.db" -mtime +7 -exec gzip {} \;

# Delete backups older than 30 days
find $BACKUP_DIR -name "*.db.gz" -mtime +30 -delete

# Upload to S3 (optional)
aws s3 sync $BACKUP_DIR s3://your-backup-bucket/wawatrader/
```

Schedule with cron:

```bash
# Edit crontab
crontab -e

# Add backup job (daily at 2 AM)
0 2 * * * /home/ubuntu/backup.sh
```

### Recovery

```bash
# Stop service
sudo systemctl stop wawatrader

# Restore database
cp /backups/wawatrader/wawatrader_20241022.db /data/wawatrader.db
cp /backups/wawatrader/wawatrader_config_20241022.db /data/wawatrader_config.db

# Fix permissions
chown ubuntu:ubuntu /data/*.db
chmod 600 /data/*.db

# Start service
sudo systemctl start wawatrader
```

---

## Scaling

### Horizontal Scaling

Run multiple instances for different symbols:

```bash
# Instance 1: Tech stocks
export TRADING_SYMBOLS="AAPL,TSLA,NVDA"
python -m wawatrader.trading_agent &

# Instance 2: Finance stocks
export TRADING_SYMBOLS="JPM,GS,BAC"
python -m wawatrader.trading_agent &

# Instance 3: Energy stocks
export TRADING_SYMBOLS="XOM,CVX,COP"
python -m wawatrader.trading_agent &
```

### Vertical Scaling

Increase resources:

```bash
# Increase LM Studio context window
# Use larger model (Gemma 3 7B instead of 4B)

# Increase EC2 instance size
# t3.medium → t3.large → t3.xlarge
```

---

## Support

For deployment issues:
- **GitHub Issues**: https://github.com/yourusername/WawaTrader/issues
- **Email**: support@wawatrader.com
- **Documentation**: https://docs.wawatrader.com

---

**Last Updated**: October 22, 2025
