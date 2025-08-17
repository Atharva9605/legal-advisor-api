# 🚀 Legal Advisor AI Agent API - Render Deployment Guide

## 📋 Prerequisites
- GitHub account
- Render account
- Python 3.10+ knowledge
- Basic Git knowledge

---

## 🔧 Step 1: Prepare Your Local Project

### 1.1 Initialize Git Repository (if not already done)
```bash
git init
git add .
git commit -m "Initial commit: Legal Advisor AI Agent API"
```

### 1.2 Create .gitignore file
```bash
# Create .gitignore file
echo "# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual Environment
venv/
env/
ENV/

# Environment Variables
.env
.env.local
.env.production

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Logs
*.log

# Temporary files
*.tmp
*.temp" > .gitignore
```

### 1.3 Remove virtual environment from Git
```bash
git rm -r --cached venv/
git commit -m "Remove virtual environment from tracking"
```

---

## 📤 Step 2: Push to GitHub

### 2.1 Create GitHub Repository
1. Go to [GitHub.com](https://github.com)
2. Click "New repository"
3. Name: `legal-advisor-api`
4. Description: `AI-powered legal analysis API with step-by-step thinking`
5. Make it **Public** (Render free tier requirement)
6. Don't initialize with README (you already have one)
7. Click "Create repository"

### 2.2 Connect and Push to GitHub
```bash
# Add remote origin (replace YOUR_USERNAME with your GitHub username)
git remote add origin https://github.com/YOUR_USERNAME/legal-advisor-api.git

# Push to GitHub
git branch -M main
git push -u origin main
```

---

## 🌐 Step 3: Deploy to Render

### 3.1 Sign Up/Login to Render
1. Go to [Render.com](https://render.com)
2. Sign up with GitHub (recommended)
3. Complete your profile

### 3.2 Create New Web Service
1. Click "New +"
2. Select "Web Service"
3. Connect your GitHub repository
4. Select the `legal-advisor-api` repository

### 3.3 Configure Web Service
```
Name: legal-advisor-api
Environment: Python 3
Region: Choose closest to your users
Branch: main
Root Directory: (leave empty)
Build Command: pip install -r requirements.txt
Start Command: uvicorn api:app --host 0.0.0.0 --port $PORT
```

### 3.4 Set Environment Variables
Click "Environment" tab and add:

```
GOOGLE_API_KEY=your_google_api_key_here
TAVILY_API_KEY=your_tavily_api_key_here
```

### 3.5 Deploy
1. Click "Create Web Service"
2. Wait for build to complete (5-10 minutes)
3. Your API will be available at: `https://your-app-name.onrender.com`

---

## 🔍 Step 4: Test Your Deployed API

### 4.1 Test Health Check
```bash
curl https://your-app-name.onrender.com/api/health
```

### 4.2 Test Analysis Endpoint
```bash
curl -X POST https://your-app-name.onrender.com/analyze-case \
  -H "Content-Type: application/json" \
  -d '{
    "case_description": "Test legal case for API verification"
  }'
```

### 4.3 Test in Browser
- Health: `https://your-app-name.onrender.com/api/health`
- Test: `https://your-app-name.onrender.com/test`
- Docs: `https://your-app-name.onrender.com/docs`

---

## 🛠️ Step 5: Troubleshooting Common Issues

### 5.1 Build Failures
```bash
# Check build logs in Render dashboard
# Common issues:
# - Missing dependencies in requirements.txt
# - Python version mismatch
# - Environment variable issues
```

### 5.2 Runtime Errors
```bash
# Check application logs in Render dashboard
# Common issues:
# - Missing API keys
# - Port binding issues
# - Import errors
```

### 5.3 Performance Issues
```bash
# Render free tier limitations:
# - 750 hours/month
# - Spins down after 15 minutes of inactivity
# - Cold start delays
```

---

## 🔄 Step 6: Update and Redeploy

### 6.1 Make Changes Locally
```bash
# Edit your files
# Test locally
python api.py
```

### 6.2 Push Changes
```bash
git add .
git commit -m "Description of changes"
git push origin main
```

### 6.3 Render Auto-Deploys
- Render automatically detects changes
- Builds and deploys automatically
- No manual intervention needed

---

## 📱 Step 7: Frontend Integration

### 7.1 Update Base URL
In your Lovable frontend, use:
```
Base URL: https://your-app-name.onrender.com
```

### 7.2 Test Integration
```bash
# Test CORS is working
curl -H "Origin: https://your-frontend-domain.com" \
  https://your-app-name.onrender.com/api/health
```

---

## 🔐 Step 8: Security Considerations

### 8.1 Environment Variables
- Never commit `.env` files
- Use Render's environment variable system
- Rotate API keys regularly

### 8.2 API Protection
- Consider adding rate limiting
- Implement authentication if needed
- Monitor usage and costs

---

## 📊 Step 9: Monitoring and Maintenance

### 9.1 Render Dashboard
- Monitor uptime
- Check build status
- View logs
- Monitor costs

### 9.2 Health Checks
```bash
# Set up external monitoring
# Check API response times
# Monitor error rates
```

---

## 🎯 Final Checklist

- [ ] Code pushed to GitHub
- [ ] Repository is public
- [ ] Render service created
- [ ] Environment variables set
- [ ] Build successful
- [ ] API responding
- [ ] Frontend integrated
- [ ] Testing completed

---

## 🆘 Support

### Render Support
- [Render Documentation](https://render.com/docs)
- [Render Community](https://community.render.com)

### API Issues
- Check application logs
- Verify environment variables
- Test locally first

---

## 💰 Cost Considerations

### Render Free Tier
- 750 hours/month
- Automatic spin-down
- Perfect for development/testing

### Render Paid Plans
- Always-on services
- Better performance
- More resources

---

**🎉 Congratulations! Your Legal Advisor AI Agent API is now deployed and ready for production use!**
