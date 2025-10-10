# HTTPS Setup Guide for VIGILANTEye

## Current Status
- ❌ HTTP only: http://vigilanteye-app.eastus.azurecontainer.io:8000
- ⚠️ Not secure for production

## 🔒 Options to Enable HTTPS

### Option 1: Azure Application Gateway (Recommended for Production)

Azure Application Gateway provides SSL termination and acts as a reverse proxy.

**Pros:**
- Enterprise-grade SSL/TLS
- Automatic certificate management
- Web Application Firewall (WAF) support
- Load balancing capabilities

**Cons:**
- Additional cost (~$125/month)
- More complex setup

**Setup Steps:**

1. **Create Application Gateway:**
```bash
# Create public IP
az network public-ip create \
  --resource-group vigilanteye-docker-rg \
  --name vigilanteye-gateway-ip \
  --sku Standard \
  --allocation-method Static

# Create virtual network
az network vnet create \
  --resource-group vigilanteye-docker-rg \
  --name vigilanteye-vnet \
  --address-prefix 10.0.0.0/16 \
  --subnet-name gateway-subnet \
  --subnet-prefix 10.0.1.0/24

# Create Application Gateway with SSL
az network application-gateway create \
  --resource-group vigilanteye-docker-rg \
  --name vigilanteye-gateway \
  --location eastus \
  --capacity 2 \
  --sku Standard_v2 \
  --public-ip-address vigilanteye-gateway-ip \
  --vnet-name vigilanteye-vnet \
  --subnet gateway-subnet \
  --servers vigilanteye-app.eastus.azurecontainer.io \
  --priority 100
```

2. **Add SSL Certificate:**
```bash
# Upload your SSL certificate
az network application-gateway ssl-cert create \
  --resource-group vigilanteye-docker-rg \
  --gateway-name vigilanteye-gateway \
  --name ssl-cert \
  --cert-file /path/to/your/certificate.pfx \
  --cert-password your-cert-password
```

---

### Option 2: Azure Front Door (Best for Global Apps)

Azure Front Door provides SSL, CDN, and global load balancing.

**Pros:**
- Built-in SSL certificate (free)
- Global CDN
- DDoS protection
- Better performance worldwide

**Cons:**
- Additional cost (~$35/month base)

**Setup Steps:**

```bash
# Create Front Door profile
az afd profile create \
  --resource-group vigilanteye-docker-rg \
  --profile-name vigilanteye-frontdoor \
  --sku Standard_AzureFrontDoor

# Create endpoint
az afd endpoint create \
  --resource-group vigilanteye-docker-rg \
  --profile-name vigilanteye-frontdoor \
  --endpoint-name vigilanteye-endpoint \
  --enabled-state Enabled

# Add origin
az afd origin-group create \
  --resource-group vigilanteye-docker-rg \
  --profile-name vigilanteye-frontdoor \
  --origin-group-name default-origin-group

az afd origin create \
  --resource-group vigilanteye-docker-rg \
  --profile-name vigilanteye-frontdoor \
  --origin-group-name default-origin-group \
  --origin-name container-origin \
  --host-name vigilanteye-app.eastus.azurecontainer.io \
  --origin-host-header vigilanteye-app.eastus.azurecontainer.io \
  --http-port 8000 \
  --https-port 443 \
  --priority 1 \
  --weight 1000
```

Your application will be available at:
`https://vigilanteye-endpoint-xxxxx.azurefd.net`

---

### Option 3: Cloudflare (Easiest & Free)

Use Cloudflare as a reverse proxy with free SSL.

**Pros:**
- Free SSL certificate
- Free CDN
- DDoS protection
- Easy setup (5 minutes)
- No code changes needed

**Cons:**
- Requires custom domain
- Third-party service

**Setup Steps:**

1. **Register domain** (if you don't have one)
   - Get a domain from Namecheap, GoDaddy, etc.

2. **Add site to Cloudflare:**
   - Go to https://dash.cloudflare.com
   - Click "Add a Site"
   - Enter your domain

3. **Update nameservers** at your domain registrar

4. **Add DNS record:**
   ```
   Type: A
   Name: @ (or subdomain like 'app')
   Content: 4.157.146.155 (current container IP)
   Proxy: Enabled (orange cloud)
   ```

5. **Configure SSL:**
   - Go to SSL/TLS → Overview
   - Select "Full" or "Full (strict)"

6. **Access your app:**
   ```
   https://yourdomain.com
   ```

---

### Option 4: Azure Container Apps (Simplest Migration)

Azure Container Apps has built-in HTTPS support.

**Pros:**
- Free SSL certificate
- Built-in HTTPS
- Better scaling
- Similar to Container Instances

**Cons:**
- Need to migrate from Container Instances
- Slightly more expensive

**Migration Steps:**

1. **Create Container App Environment:**
```bash
az containerapp env create \
  --resource-group vigilanteye-docker-rg \
  --name vigilanteye-env \
  --location eastus
```

2. **Deploy Container App:**
```bash
az containerapp create \
  --resource-group vigilanteye-docker-rg \
  --name vigilanteye-app \
  --environment vigilanteye-env \
  --image vigilanteyeacr.azurecr.io/vigilanteye-web:latest \
  --registry-server vigilanteyeacr.azurecr.io \
  --registry-username vigilanteyeacr \
  --registry-password $(az acr credential show --name vigilanteyeacr --query "passwords[0].value" -o tsv) \
  --target-port 8000 \
  --ingress external \
  --env-vars \
    FLASK_ENV=production \
    SECRET_KEY=your-secret-key-here \
    JWT_SECRET_KEY=jwt-secret-string \
    DATABASE_URL='mysql+pymysql://vigilanteye:YourPassword123%21@vigilanteye-mysql.mysql.database.azure.com:3306/flaskapi?ssl_ca=/etc/ssl/certs/ca-certificates.crt' \
  --cpu 2 \
  --memory 4Gi \
  --min-replicas 1 \
  --max-replicas 3
```

Your app will automatically have HTTPS at:
`https://vigilanteye-app.xxxxx.eastus.azurecontainerapps.io`

---

### Option 5: Nginx Reverse Proxy with Let's Encrypt (DIY)

Add an Nginx container with SSL certificates.

**Pros:**
- Full control
- Free (Let's Encrypt)
- No vendor lock-in

**Cons:**
- More complex setup
- Manual certificate renewal

---

## 🎯 Recommended Approach

### For Quick Testing: **Option 3 - Cloudflare** (Free & Fast)
### For Production: **Option 4 - Azure Container Apps** (Native HTTPS)
### For Enterprise: **Option 1 - Application Gateway** (Full Features)

## 📝 Quick Decision Matrix

| Option | Cost | Setup Time | SSL | CDN | Complexity |
|--------|------|------------|-----|-----|------------|
| App Gateway | $$ | 30 min | ✅ | ❌ | High |
| Front Door | $ | 20 min | ✅ | ✅ | Medium |
| Cloudflare | Free | 5 min | ✅ | ✅ | Low |
| Container Apps | $ | 10 min | ✅ | ❌ | Low |
| Nginx + LE | Free | 60 min | ✅ | ❌ | High |

## 🚀 Quick Start - Option 4 (Container Apps)

I recommend migrating to Azure Container Apps for built-in HTTPS support.

Would you like me to:
1. Migrate to Azure Container Apps (built-in HTTPS)
2. Set up Cloudflare (if you have a domain)
3. Set up Azure Front Door

Let me know which option you prefer!

