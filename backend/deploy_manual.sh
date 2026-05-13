#!/bin/bash

# Manual Deploy script for WebMajak Django Application
# Pro případ problémů s SSH klíči - jednotlivé kroky

set -e

echo "🚀 Manual deployment of WebMajak Django Application..."

VPS_USER="webmajak"
VPS_HOST="80.211.198.189"
VPS_PATH="/home/webmajak/webapp"

echo "📋 Manual deployment steps:"
echo "1. Upload files to VPS"
echo "2. Setup Python environment"
echo "3. Install dependencies"
echo "4. Configure services"

echo -e "\n📁 Step 1: Upload Django files"
echo "Run this command:"
echo "rsync -avz --exclude='__pycache__' --exclude='*.pyc' --exclude='venv' backend/ $VPS_USER@$VPS_HOST:$VPS_PATH/"

echo -e "\n🐍 Step 2: Setup on VPS (SSH manually)"
echo "ssh $VPS_USER@$VPS_HOST"
echo "Then run these commands on VPS:"

cat << 'EOF'
cd /home/webmajak/webapp
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
export DJANGO_SETTINGS_MODULE=webapp.settings_production
python manage.py migrate
python manage.py collectstatic --noinput
EOF

echo -e "\n⚙️ Step 3: Configure services (as root)"
echo "ssh root@$VPS_HOST"
echo "Then run these commands:"

cat << 'EOF'
cp /home/webmajak/webapp/webmajak.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable webmajak
systemctl start webmajak
systemctl status webmajak

cp /home/webmajak/webapp/nginx_webmajak.conf /etc/nginx/sites-available/webmajak
ln -sf /etc/nginx/sites-available/webmajak /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx

chown -R webmajak:webmajak /home/webmajak/webapp
EOF

echo -e "\n✅ Step 4: Test"
echo "curl -s http://$VPS_HOST/health/"
echo "curl -s http://$VPS_HOST/api/users/current/"

echo -e "\n📝 If VPS is not responding:"
echo "1. Check Forpsi administration panel"
echo "2. Restart VPS if needed"
echo "3. Wait 2-3 minutes for SSH to come online" 