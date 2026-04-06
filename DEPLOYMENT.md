# Deployment Guide - Render.com + PlanetScale MySQL

## Prerequisites
1. GitHub account
2. Render.com account (free)
3. PlanetScale account (free) - untuk MySQL database
4. Push project ke GitHub repository

## Step-by-Step Deployment

### 1. Setup PlanetScale MySQL Database (Free)

#### A. Create PlanetScale Account
1. Buka [PlanetScale](https://planetscale.com)
2. Sign up dengan GitHub (gratis)
3. Verify email

#### B. Create Database
1. Click "Create a database"
2. Settings:
   - Name: `quran-hafalan`
   - Region: `AWS ap-southeast-1` (Singapore)
   - Plan: Hobby (Free)
3. Click "Create database"
4. Wait sampai status "Ready"

#### C. Create Password
1. Di database dashboard, click "Connect"
2. Click "New password"
3. Name: `render-app`
4. Click "Create password"
5. **PENTING**: Copy semua credentials (host, username, password)
   - Host: `xxx.aws.connect.psdb.cloud`
   - Username: `xxx`
   - Password: `pscale_pw_xxx`
   - Database: `quran-hafalan`
6. Atau copy "Connection string" format: 
   ```
   mysql://username:password@host/database?sslaccept=strict
   ```

#### D. Import Database Schema
1. Install PlanetScale CLI (optional) atau pakai web console
2. Via Web Console:
   - Click "Console" tab
   - Copy-paste isi file `database/schema.sql`
   - Run query
3. Via MySQL Client:
   ```bash
   mysql -h xxx.aws.connect.psdb.cloud -u username -p database < database/schema.sql
   ```

### 2. Push ke GitHub
```bash
git init
git add .
git commit -m "Setup for Render + PlanetScale deployment"
git remote add origin https://github.com/username/repo-name.git
git push -u origin main
```

### 3. Setup di Render.com

#### A. Create Web Service
1. Login ke [Render Dashboard](https://dashboard.render.com)
2. Click "New +" → "Web Service"
3. Connect GitHub repository
4. Settings:
   - Name: `quran-hafalan-app`
   - Region: Singapore
   - Branch: `main`
   - Root Directory: (kosongkan)
   - Runtime: Python 3
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `bash start.sh`
   - Plan: Free

#### B. Environment Variables
Click "Add Environment Variable" untuk setiap variable:

1. `PYTHON_VERSION` = `3.11.0`

2. `DATABASE_URL` = (paste connection string dari PlanetScale)
   Format: `mysql://username:password@host/database?ssl={"rejectUnauthorized":true}`
   
   Atau set individual:
   - `DB_HOST` = `xxx.aws.connect.psdb.cloud`
   - `DB_USER` = `username dari PlanetScale`
   - `DB_PASSWORD` = `password dari PlanetScale`
   - `DB_NAME` = `quran-hafalan`
   - `DB_PORT` = `3306`

3. `SECRET_KEY` = (generate random string)
   ```bash
   # Generate via terminal:
   python -c "import secrets; print(secrets.token_hex(32))"
   ```

4. Click "Create Web Service"

### 4. Wait for Deployment
- First deploy: 5-10 menit
- Check logs untuk error
- Kalau sukses: `https://quran-hafalan-app.onrender.com`

### 5. Setup Admin User
Setelah deploy sukses, buat admin via PlanetScale Console:
```sql
INSERT INTO users (nama, email, password, role, must_change_password) 
VALUES ('Admin', 'admin@example.com', SHA2('admin123', 256), 'admin', 0);
```

## Important Notes

### Free Tier Limitations

**PlanetScale (MySQL):**
- 5GB storage
- 1 billion row reads/month
- 10 million row writes/month
- 1 production branch + 1 development branch
- Cukup untuk project skripsi/demo

**Render (Web Service):**
- Auto-sleep setelah 15 menit idle
- Cold start: 30-60 detik
- 750 jam/bulan (cukup 24/7)

### Production Checklist
- ✅ PlanetScale database created
- ✅ Database schema imported
- ✅ Connection string copied
- ✅ Environment variables configured di Render
- ✅ Admin user created
- ✅ App deployed successfully

### Troubleshooting

**Error: Can't connect to database**
- Check DATABASE_URL format benar
- Pastikan SSL enabled: `?ssl={"rejectUnauthorized":true}`
- Cek PlanetScale password belum expired
- Test connection via MySQL client dulu

**Error: SSL connection error**
- PlanetScale require SSL
- Pastikan pymysql support SSL (sudah include di requirements.txt)
- Add `ssl={"rejectUnauthorized":true}` di connection string

**Error: Module not found**
- Check requirements.txt lengkap
- Rebuild service di Render dashboard

**App sleep/cold start**
- Free tier auto-sleep setelah 15 menit
- Upgrade ke paid ($7/month) untuk always-on
- Atau pakai cron job untuk ping setiap 10 menit

**PlanetScale connection limit**
- Free tier: 1000 concurrent connections
- Kalau exceed, upgrade atau optimize connection pooling

## Monitoring

### Render
- Logs: Dashboard → Service → Logs
- Metrics: Dashboard → Service → Metrics

### PlanetScale
- Dashboard → Database → Insights
- Monitor queries, connections, storage

## Custom Domain (Optional)
1. Render Dashboard → Service → Settings
2. "Custom Domain" → Add domain
3. Update DNS records

## Upgrade Plans

### Render Web Service
- Starter: $7/month (512MB RAM, always-on)
- Standard: $25/month (2GB RAM)

### PlanetScale Database
- Scaler: $29/month (10GB storage, unlimited reads/writes)
- Scaler Pro: $59/month (100GB storage)

## Tips

1. **Keep PlanetScale connection alive**: 
   - Set connection timeout di pymysql
   - Implement connection retry logic

2. **Monitor usage**:
   - Check PlanetScale dashboard untuk row reads/writes
   - Free tier cukup untuk 1000+ users

3. **Backup**:
   - PlanetScale auto-backup (7 days retention di free tier)
   - Export manual via mysqldump kalau perlu

4. **Development**:
   - Pakai PlanetScale development branch untuk testing
   - Merge ke production branch setelah tested

