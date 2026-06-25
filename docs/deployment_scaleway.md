# DAVE RPG — Scaleway Production Deployment Guide

This guide covers deploying DAVE RPG on a Scaleway VPS using the Scaleway Generative APIs backend.

## Architecture Overview

- **Hosting**: Scaleway VPS (Ubuntu 24.04 LTS)
- **LLM Backend**: Scaleway Generative APIs (OpenAI-compatible endpoint)
- **Model**: `mistral/mistral-small-3.2-24b-instruct-2506:fp8`
- **Web Server**: Gunicorn (single-threaded) behind Caddy reverse proxy
- **Database**: SQLite (per-user instances)
- **Process Management**: systemd

## Prerequisites

- Scaleway VPS (BASIC3-X2C-8G or equivalent recommended)
- Scaleway IAM API key (from [console](https://console.scaleway.com/iam/api-keys))
- Domain name with DNS A record pointing to VPS IP
- Root or sudo access

## Quick Start

### 1. Install System Dependencies

```bash
sudo apt update
sudo apt install -y python3.12-venv sqlite3 git caddy

2. Clone and Setup DAVE

cd ~
git clone https://github.com/emdalton/dave-rpg.git
cd dave-rpg

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt


3. Build Module Databases

# Hidden Hostel (test world)
sqlite3 modules/hidden_hostel/hidden_hostel.db < schema/schema.sql
sqlite3 modules/hidden_hostel/hidden_hostel.db < modules/hidden_hostel/seed.sql

# I Am a Cat
sqlite3 modules/i_am_a_cat/i_am_a_cat.db < schema/schema.sql
sqlite3 modules/i_am_a_cat/i_am_a_cat.db < modules/i_am_a_cat/seed.sql

# Meryton Assembly (if available)
sqlite3 modules/Meryton/meryton.db < schema/schema.sql
sqlite3 modules/Meryton/meryton.db < modules/Meryton/seed.sql


4. Configure Environment

# Copy template and edit
cp .env.example dave-rpg.env
nano dave-rpg.env

# Generate Flask secret key
python3 -c "import secrets; print(secrets.token_hex(32))"
# Add the output to dave-rpg.env as DAVE_SECRET_KEY


Required environment variables:





DAVE_LLM_BACKEND=scaleway



DAVE_SCALEWAY_MODEL=mistral/mistral-small-3.2-24b-instruct-2506:fp8



SCW_SECRET_KEY=your_actual_key



DAVE_SECRET_KEY=generated_key

5. Create Directories

mkdir -p user_dbs logs


6. Setup systemd Service

# Copy service template
sudo cp dave-rpg-web.service.template /etc/systemd/system/dave-rpg-web.service

# Edit if needed (update username, paths)
sudo nano /etc/systemd/system/dave-rpg-web.service

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable dave-rpg-web
sudo systemctl start dave-rpg-web

# Check status
sudo systemctl status dave-rpg-web


7. Configure Caddy Reverse Proxy

Edit /etc/caddy/Caddyfile:

dave.yourdomain.com {
    reverse_proxy localhost:8001
    
    encode gzip
    
    header {
        X-Content-Type-Options "nosniff"
        X-Frame-Options "DENY"
        X-XSS-Protection "1; mode=block"
        Referrer-Policy "strict-origin-when-cross-origin"
    }
    
    log {
        output file /var/log/caddy/dave-access.log
    }
}


Reload Caddy:

sudo systemctl reload caddy


8. Verify Deployment

# Test locally
curl -I http://localhost:8001

# Test via domain
curl -I https://dave.yourdomain.com

# Check logs
tail -f ~/dave-rpg/logs/error.log
sudo tail -f /var/log/caddy/dave-access.log


Important Configuration Notes

Single-Threaded Gunicorn Required

The service template uses --workers 1 --threads 1. This is required because:





In-memory session storage: The ACTIVE_SESSIONS dict in web/app.py is not shared across processes



SQLite thread-safety: Database connections are created in one thread and used in another if threading is enabled

Using multiple workers or threads will result in:





SQLite objects created in a thread can only be used in that same thread errors



Session state not being shared across requests

Scaleway Backend vs. Ollama Backend

Use DAVE_LLM_BACKEND=scaleway (not ollama) for Scaleway APIs. The backends use different API structures:





Scaleway: OpenAI-compatible (/v1/chat/completions)



Ollama: Ollama-specific (/api/generate)

The Scaleway backend is implemented in engine/llm/scaleway.py and uses the openai Python package.

Database Paths

Use absolute paths in the systemd service file. Relative paths can cause issues when systemd starts the service from a different working directory.

Troubleshooting

Service Won't Start

# Check logs
sudo journalctl -u dave-rpg-web -n 100 --no-pager

# Test manually
cd ~/dave-rpg
source .venv/bin/activate
gunicorn "web.app:create_app()" --bind 127.0.0.1:8001 --workers 1 --threads 1


LLM API Errors

# Verify API key
cat ~/dave-rpg/dave-rpg.env | grep SCW_SECRET_KEY

# Test Scaleway endpoint directly
curl -X POST https://api.scaleway.ai/v1/chat/completions \
  -H "Authorization: Bearer $SCW_SECRET_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"mistral/mistral-small-3.2-24b-instruct-2506:fp8","messages":[{"role":"user","content":"test"}]}'


SQLite Threading Errors

If you see SQLite objects created in a thread can only be used in that same thread:





Verify gunicorn is running with --threads 1



Restart the service: sudo systemctl restart dave-rpg-web

Caddy TLS Issues

# Check Caddy logs
sudo journalctl -u caddy -n 50 --no-pager

# Force certificate renewal
sudo caddy stop
sudo caddy start


Security Considerations





Never commit dave-rpg.env to git (contains API keys)



Firewall: Only ports 80, 443, and 22 should be open to the public



API Key Rotation: Rotate Scaleway IAM keys periodically



User Limits: Adjust DAVE_MAX_USERS and DAVE_MAX_TURNS based on budget



Cloudflare Turnstile: Replace test keys with production keys for public deployment

Monitoring

# Service status
sudo systemctl status dave-rpg-web

# Resource usage
systemctl show dave-rpg-web --property=MemoryCurrent,CPUUsageNSec

# Active users
sqlite3 ~/dave-rpg/web/dave_users.db "SELECT username, created_at, turn_count FROM users;"

# Token usage (approximate)
grep -c "POST /session/turn" ~/dave-rpg/logs/access.log


Updates

To update DAVE:

cd ~/dave-rpg
git pull
source .venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart dave-rpg-web




For more configuration options, see configuration.md.
For module authoring, see module_authoring.md.
