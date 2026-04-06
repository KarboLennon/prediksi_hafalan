# Deployment Guide - Railway.app

## Prerequisites
1. GitHub account
2. Railway.app account (free $5 credit/month)
3. Push project ke GitHub repository

## Step-by-Step Deployment

### 1. Push ke GitHub
```bash
git init
git add .
git commit -m "Setup for Railway deployment"
git remote add origin https://github.com/username/repo-name.git
git push -u origin main
```

### 2. Setup Railway Account
1. Buka [Railway.app](https://railway.app)
2. Click "Login" → Sign in with GitHub
3. Authorize Railway
4. Verify email kalau diminta

### 3. Create New Project

#### A. Create Project
1. Di Railway dashboard, click "New Project"
2. Pilih "Deploy from GitHub repo"
3. Select repository project lu
4. Railway akan auto-detect Python project

#### B. Add MySQL Database
1. Di project dashboard, click "New" → "Database" → "Add MySQL"
2. Railway akan auto-provision MySQL database
3. Wait sampai status "Active" (1-2 menit)

#### C. Configure Environment Variables
1. Click service app lu (bukan database)
2. Tab "Variables"
3. Click "Add Variable" atau "Raw Editor"
4. Add variables berikut:

```env
# Python version
PYTHON_VERSION=3.11.0

# Secret key (generate random)
SECRET_KEY=your-random-secret-key-here

# Database akan auto-inject oleh Railway sebagai DATABASE_URL
# Tapi kita perlu individual vars juga untuk compatibility
```

Railway akan otomatis inject variable `DATABASE_URL` dari MySQL service.

#### D. Configure Build & Start
1. Masih di service app, tab "Settings"
2. Scroll ke "Build & Deploy"
3. Build Command: `pip install -r requirements.txt`
4. Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

Atau bisa pakai Gunicorn (lebih production-ready):
```
gunicorn app.main:app --workers 2 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT
```

### 4. Deploy
1. Railway akan auto-deploy setelah setup
2. Check tab "Deployments" untuk status
3. Kalau ada error, check "View Logs"
4. Kalau sukses, akan dapat URL: `https://xxx.up.railway.app`

### 5. Import Database Schema

#### Via Railway MySQL Client
1. Di project dashboard, click MySQL database
2. Tab "Data"
3. Click "Query" atau connect via MySQL client
4. Copy-paste isi `database/schema.sql`
5. Execute

#### Via MySQL Workbench/CLI
1. Di MySQL service, tab "Connect"
2. Copy credentials:
   - Host: `xxx.railway.internal` atau public host
   - Port: `3306`
   - User: `root`
   - Password: (dari Railway)
   - Database: `railway`
3. Connect dan import schema:
```bash
mysql -h host -P port -u root -p railway < database/schema.sql
```

### 6. Create Admin User
Via Railway MySQL Query tab:
```sql
INSERT INTO users (nama, email, password, role, must_change_password) 
VALUES ('Admin', 'admin@example.com', SHA2('admin123', 256), 'admin', 0);
```

### 7. Enable Public Domain
1. Di service app, tab "Settings"
2. Scroll ke "Networking"
3. Click "Generate Domain"
4. Akan dapat public URL: `https://your-app.up.railway.app`

## Important Notes

### Free Tier ($5 Credit/Month)
- $5 credit = ~500 jam runtime
- Cukup untuk 1 app + 1 database 24/7 (~$3-4/month)
- No credit card required untuk trial
- Setelah credit habis, service akan pause

### Usage Estimation
- Web service: ~$0.002/hour = ~$1.50/month
- MySQL: ~$0.003/hour = ~$2.20/month
- Total: ~$3.70/month (masih dalam $5 credit)

### Production Checklist
- ✅ GitHub repo connected
- ✅ MySQL database created
- ✅ Environment variables set
- ✅ Database schema imported
- ✅ Admin user created
- ✅ Public domain generated
- ✅ App accessible via URL

### Troubleshooting

**Error: Can't connect to database**
- Railway auto-inject `DATABASE_URL` variable
- Check di tab "Variables" ada `DATABASE_URL`
- Format: `mysql://root:password@host:port/railway`
- Pastikan app dan database dalam 1 project

**Error: Module not found**
- Check requirements.txt complete
- Rebuild: Tab "Deployments" → click "..." → "Redeploy"

**Error: Port binding**
- Railway inject `PORT` variable otomatis
- Pastikan app listen di `0.0.0.0:$PORT`
- Jangan hardcode port 8000

**App not accessible**
- Check "Generate Domain" sudah diklik
- Check deployment status "Success"
- Check logs untuk error

**Database connection timeout**
- Railway database bisa sleep kalau idle
- Add connection retry logic
- Atau upgrade ke paid plan

### Monitoring

**Metrics**
- Dashboard → Service → "Metrics" tab
- Monitor CPU, RAM, Network usage
- Track credit usage

**Logs**
- Dashboard → Service → "Deployments" → "View Logs"
- Real-time logs untuk debugging

**Database**
- Dashboard → MySQL → "Metrics"
- Monitor queries, connections, storage

### Custom Domain (Optional)
1. Service → Settings → Networking
2. "Custom Domain" → Add your domain
3. Update DNS records:
   - Type: CNAME
   - Name: subdomain
   - Value: your-app.up.railway.app

### Upgrade to Paid Plan
Kalau $5 credit gak cukup:
- Hobby Plan: $5/month + usage
- Pro Plan: $20/month + usage
- Usage: ~$0.002/hour untuk web service

### Tips

1. **Monitor Credit Usage**:
   - Check dashboard regularly
   - Set up usage alerts
   - Optimize resource usage

2. **Database Backup**:
   - Railway auto-backup (paid plan)
   - Manual backup via mysqldump:
     ```bash
     mysqldump -h host -u root -p railway > backup.sql
     ```

3. **Environment-specific Config**:
   - Use Railway variables untuk production
   - Keep .env untuk local development

4. **Optimize Costs**:
   - Use 1 worker untuk Gunicorn (free tier)
   - Implement connection pooling
   - Cache static assets

5. **CI/CD**:
   - Railway auto-deploy on git push
   - Configure branch deployment di Settings
   - Use PR deployments untuk testing

## Alternative: Railway CLI

Install Railway CLI untuk deploy via terminal:
```bash
# Install
npm i -g @railway/cli

# Login
railway login

# Link project
railway link

# Deploy
railway up

# View logs
railway logs

# Open in browser
railway open
```

## Next Steps After Deployment

1. Test semua fitur (login, input hafalan, dashboard, dll)
2. Monitor logs untuk error
3. Check database connection stable
4. Test ML prediction working
5. Share URL untuk testing
6. Monitor credit usage

## Support
- Docs: https://docs.railway.app
- Discord: https://discord.gg/railway
- Status: https://status.railway.app


