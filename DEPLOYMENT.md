# Deployment Guide - Render.com

## Prerequisites
1. GitHub account
2. Render.com account (free)
3. Push project ke GitHub repository

## Step-by-Step Deployment

### 1. Push ke GitHub
```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/username/repo-name.git
git push -u origin main
```

### 2. Setup di Render.com

#### A. Create MySQL Database
1. Login ke [Render Dashboard](https://dashboard.render.com)
2. Click "New +" → "MySQL"
3. Settings:
   - Name: `quran-hafalan-db`
   - Database: `quran_hafalan`
   - User: `quran_user`
   - Region: Singapore
   - Plan: Free
4. Click "Create Database"
5. Wait sampai status "Available"
6. Copy "Internal Database URL" untuk nanti

#### B. Import Database Schema
1. Di Render dashboard, buka database yang baru dibuat
2. Click "Connect" → pilih MySQL client
3. Run SQL dari file `database/schema.sql`
4. Atau connect via MySQL Workbench/phpMyAdmin dengan credentials dari Render

#### C. Create Web Service
1. Click "New +" → "Web Service"
2. Connect GitHub repository
3. Settings:
   - Name: `quran-hafalan-app`
   - Region: Singapore
   - Branch: `main`
   - Root Directory: (kosongkan)
   - Runtime: Python 3
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `bash start.sh`
   - Plan: Free
4. Environment Variables (click "Add Environment Variable"):
   - `PYTHON_VERSION` = `3.11.0`
   - `DATABASE_URL` = (paste Internal Database URL dari step B)
   - `SECRET_KEY` = (generate random string, bisa pakai: `openssl rand -hex 32`)
5. Click "Create Web Service"

### 3. Wait for Deployment
- First deploy bisa 5-10 menit
- Check logs untuk error
- Kalau sukses, akan dapat URL: `https://quran-hafalan-app.onrender.com`

### 4. Setup Admin User
Setelah deploy sukses, buat admin user pertama via database:
```sql
INSERT INTO users (nama, email, password, role, must_change_password) 
VALUES ('Admin', 'admin@example.com', SHA2('admin123', 256), 'admin', 0);
```

## Important Notes

### Free Tier Limitations
- Database: 1GB storage, 97 hari retention
- Web service: Auto-sleep setelah 15 menit idle
- Cold start: 30-60 detik saat pertama kali diakses setelah sleep
- 750 jam/bulan (cukup untuk 1 service 24/7)

### Production Checklist
- ✅ Environment variables configured
- ✅ Database schema imported
- ✅ Admin user created
- ✅ Static files accessible
- ✅ ML models loaded correctly
- ✅ CSV data files accessible

### Troubleshooting

**Error: Can't connect to database**
- Check DATABASE_URL format: `mysql://user:pass@host:port/dbname`
- Pastikan database sudah "Available"
- Cek firewall/network settings

**Error: Module not found**
- Check requirements.txt lengkap
- Rebuild service di Render dashboard

**Error: Static files not loading**
- Check path di main.py: `app/static`
- Pastikan folder static ter-commit ke git

**App sleep/cold start**
- Free tier auto-sleep setelah 15 menit
- Upgrade ke paid plan ($7/month) untuk always-on

## Monitoring
- Logs: Render Dashboard → Service → Logs
- Metrics: Render Dashboard → Service → Metrics
- Database: Render Dashboard → Database → Metrics

## Custom Domain (Optional)
1. Render Dashboard → Service → Settings
2. Scroll ke "Custom Domain"
3. Add domain dan update DNS records

## Upgrade to Paid Plan
Kalau perlu always-on dan lebih cepat:
- Web Service: $7/month (512MB RAM, always-on)
- Database: $7/month (1GB RAM, 10GB storage)
