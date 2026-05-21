#!/bin/bash

# Deploy script for WebMajak Django Application
# Spustit jako: bash deploy.sh

set -e  # Exit on any error

echo "🚀 Starting deployment of WebMajak Django Application..."

# Configuration
VPS_USER="root"
VPS_HOST="80.211.198.189"
VPS_PATH="/home/webmajak/webapp"
LOCAL_PATH="$(dirname $(realpath $0))"
SSH_KEY="~/.ssh/webmajak_vps"

echo "📁 Local path: $LOCAL_PATH"
echo "🌐 VPS: $VPS_USER@$VPS_HOST:$VPS_PATH"
echo "🔑 Using SSH key: $SSH_KEY"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Step 1: Test SSH connection
echo -e "\n${YELLOW}🔑 Step 1: Testing SSH connection...${NC}"
ssh -i $SSH_KEY -o ConnectTimeout=10 $VPS_USER@$VPS_HOST "echo 'SSH connection successful!'"
print_status "SSH connection working"

# Step 2: Create webmajak user and directory structure
echo -e "\n${YELLOW}👤 Step 2: Setting up user and directories...${NC}"
ssh -i $SSH_KEY $VPS_USER@$VPS_HOST << 'EOF'
# Create webmajak user if it doesn't exist
if ! id "webmajak" &>/dev/null; then
    adduser webmajak --gecos "WebMajak User" --disabled-password
    echo 'webmajak:WebMajak2025!' | chpasswd
    usermod -aG sudo webmajak
fi

# Create directory structure
mkdir -p /home/webmajak/webapp/{logs,static,media,staticfiles}
chown -R webmajak:webmajak /home/webmajak/webapp
EOF
print_status "User and directories created"

# Step 3: Upload Django application
echo -e "\n${YELLOW}📦 Step 3: Uploading Django application...${NC}"
rsync -avz -e "ssh -i $SSH_KEY" --delete \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.env' \
    --exclude='venv' \
    --exclude='logs/*' \
    --exclude='media/news_files/*' \
    $LOCAL_PATH/ $VPS_USER@$VPS_HOST:$VPS_PATH/
print_status "Django application uploaded"

# Step 4: Install system packages
echo -e "\n${YELLOW}📦 Step 4: Installing system packages...${NC}"
ssh -i $SSH_KEY $VPS_USER@$VPS_HOST << 'EOF'
apt update
apt install -y python3-pip python3-venv python3-dev nginx mysql-client \
               libmysqlclient-dev build-essential libssl-dev libffi-dev \
               python3-setuptools supervisor
systemctl enable nginx
systemctl enable supervisor
EOF
print_status "System packages installed"

# Step 5: Setup Python virtual environment
echo -e "\n${YELLOW}🐍 Step 5: Setting up Python environment...${NC}"
ssh -i $SSH_KEY $VPS_USER@$VPS_HOST << 'EOF'
cd /home/webmajak/webapp
sudo -u webmajak python3 -m venv venv
sudo -u webmajak venv/bin/pip install --upgrade pip
sudo -u webmajak venv/bin/pip install -r requirements.txt
chown -R webmajak:webmajak /home/webmajak/webapp
EOF
print_status "Python environment setup complete"

# Step 6: Run Django migrations and collect static files
echo -e "\n${YELLOW}🗄️ Step 6: Running Django setup...${NC}"
ssh -i $SSH_KEY $VPS_USER@$VPS_HOST << 'EOF'
cd /home/webmajak/webapp
sudo -u webmajak bash -c "
    source venv/bin/activate
    export DJANGO_SETTINGS_MODULE=webapp.settings_production
    python manage.py migrate
    python manage.py collectstatic --noinput
    python manage.py check --deploy
"
EOF
print_status "Django setup complete"

# Step 7: Configure systemd service
echo -e "\n${YELLOW}⚙️ Step 7: Configuring systemd service...${NC}"
ssh -i $SSH_KEY $VPS_USER@$VPS_HOST << 'EOF'
cp /home/webmajak/webapp/webmajak.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable webmajak
systemctl stop webmajak 2>/dev/null || true
systemctl start webmajak
systemctl status webmajak --no-pager
EOF
print_status "Systemd service configured and started"

# Step 8: Configure Nginx
echo -e "\n${YELLOW}🌐 Step 8: Configuring Nginx...${NC}"
ssh -i $SSH_KEY $VPS_USER@$VPS_HOST << 'EOF'
cp /home/webmajak/webapp/nginx_webmajak.conf /etc/nginx/sites-available/webmajak
ln -sf /etc/nginx/sites-available/webmajak /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx
systemctl status nginx --no-pager
EOF
print_status "Nginx configured and reloaded"

# Step 9: Set final permissions
echo -e "\n${YELLOW}🔒 Step 9: Setting final permissions...${NC}"
ssh -i $SSH_KEY $VPS_USER@$VPS_HOST << 'EOF'
chown -R webmajak:webmajak /home/webmajak/webapp
chmod -R 755 /home/webmajak/webapp
chmod -R 777 /home/webmajak/webapp/logs
chmod -R 777 /home/webmajak/webapp/media
EOF
print_status "Permissions set correctly"

# Step 10: Final verification
echo -e "\n${YELLOW}✅ Step 10: Verifying deployment...${NC}"
echo "Testing Django application..."

# Test API endpoint
if curl -f -s "http://$VPS_HOST/health/" > /dev/null; then
    print_status "Django API is responding"
else
    print_warning "Django API test failed - checking logs..."
    ssh -i $SSH_KEY $VPS_USER@$VPS_HOST "systemctl status webmajak --no-pager"
fi

# Test Nginx
if curl -f -s "http://$VPS_HOST/" > /dev/null; then
    print_status "Nginx is serving requests"
else
    print_error "Nginx test failed"
fi

# Show service status
echo -e "\n📊 Service Status:"
ssh -i $SSH_KEY $VPS_USER@$VPS_HOST "systemctl is-active webmajak && echo 'Django: ✓ Running' || echo 'Django: ✗ Stopped'"
ssh -i $SSH_KEY $VPS_USER@$VPS_HOST "systemctl is-active nginx && echo 'Nginx: ✓ Running' || echo 'Nginx: ✗ Stopped'"

echo -e "\n${GREEN}🎉 Deployment completed!${NC}"
echo -e "Django Backend API: ${GREEN}http://$VPS_HOST/api/${NC}"
echo -e "Django Admin: ${GREEN}http://$VPS_HOST/admin/${NC}"
echo -e "Health Check: ${GREEN}http://$VPS_HOST/health/${NC}"
echo -e "Logs: ${YELLOW}ssh -i $SSH_KEY $VPS_USER@$VPS_HOST 'tail -f $VPS_PATH/logs/*.log'${NC}"

echo -e "\n📝 Next steps:"
echo "1. Update frontend API endpoints to point to: http://$VPS_HOST/api/"
echo "2. Upload frontend to Webglobe hosting"
echo "3. Test complete application flow"
echo "4. Consider setting up SSL certificate"

print_status "Ready for frontend deployment!" 