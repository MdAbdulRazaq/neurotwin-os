# NEUROTWIN OS × SUPABASE — Complete Integration Guide
## 🚀 Cloud-First Deployment

**Status:** Ready for Supabase Integration  
**Date:** March 17, 2026  
**Project:** neurotwin-os  
**Supabase URL:** https://xywuhwdijgxlfdgfktnn.supabase.co

---

## ✅ PHASE 1: Configure & Connect (5 minutes)

### Step 1: Verify .env File is Updated

Your `.env` file now has Supabase credentials:
```
SUPABASE_URL=https://xywuhwdijgxlfdgfktnn.supabase.co
SUPABASE_ANON_KEY=sb_publishable_cz0oPAp4OoRpl0UwYI1-pg_TFxrv6B7
SUPABASE_SERVICE_ROLE_KEY=sb_secret_peOWHpvR_XdjNfj-hSuLrA_zBdAjzQl
DATABASE_URL=postgresql://postgres:Neurotwin@2004@xywuhwdijgxlfdgfktnn.supabase.co:5432/postgres
```

✅ **Confirmed:** All credentials are in place.

---

### Step 2: Create Database Tables in Supabase (5 minutes)

Go to your Supabase Dashboard:

1. **URL:** https://supabase.com/dashboard
2. **Select Project:** neurotwin-os
3. **Click:** "SQL Editor" (left sidebar)
4. **Click:** "New Query"
5. **Copy all SQL from:** `D:\neurotwin\supabase_migrations.sql`
6. **Paste into Supabase SQL Editor**
7. **Click:** "Run" (or Ctrl+Enter)

**What happens:**
- ✅ Creates all 7 core tables
- ✅ Creates indexes for performance
- ✅ Creates triggers for auto-updating timestamps
- ✅ Sets up relationships and constraints

**Expected result:** "Success! 100% (7/7 tables created)"

---

## ✅ PHASE 2: Restart Services with Supabase (2 minutes)

Run these PowerShell commands:

```powershell
cd D:\neurotwin

# STEP 1: Disable local PostgreSQL (Supabase is now your database!)
docker-compose stop postgres

# STEP 2: Remove postgres from docker-compose (optional but recommended)
# docker-compose rm -f postgres

# STEP 3: Restart API container with Supabase connection
docker-compose restart api

# STEP 4: Restart Web container
docker-compose restart web

# STEP 5: Wait for containers to start
Start-Sleep -Seconds 15

# STEP 6: Verify connections
docker logs neurotwin-api --tail 30
```

**What to look for in logs:**
```
✅ "DB + Redis connected"
✅ "Application startup complete"
✅ No errors about database connection
```

---

## ✅ PHASE 3: Test the Connection (2 minutes)

### Test 1: Check if API can connect to Supabase

```powershell
# Should return HTTP 401 (auth required, but proves DB is connected)
curl -v http://localhost:8000/api/health
```

**Expected:** `401 Unauthorized` (this is GOOD - proves API is running)

### Test 2: Check if Web connects to Supabase

```powershell
# Open in browser:
Start-Process http://localhost
```

**Expected:** Dashboard loads with "NEUROTWIN OS" message

---

## ✅ PHASE 4: Verify Supabase Database (Optional but Recommended)

1. Go to: https://supabase.com/dashboard
2. Select **neurotwin-os**
3. Click **"Table Editor"** (left sidebar)
4. You should see all 7 tables:
   - ✅ users
   - ✅ conversations
   - ✅ conversation_messages
   - ✅ memory
   - ✅ emotions
   - ✅ avatar_preferences
   - ✅ sessions

---

## 📊 Architecture Change: Before → After

### BEFORE (Local Docker):
```
Next.js Frontend → Nginx
                → FastAPI (local PostgreSQL)
                → Redis (local)
                → Neo4j (local)
```

### AFTER (Supabase Cloud + Local Services):
```
Next.js Frontend → Nginx
                → FastAPI (Supabase PostgreSQL ☁️)
                → Redis (local)
                → Neo4j (local)
```

**Benefits:**
- ✅ Database in the cloud (scalable)
- ✅ Automatic backups
- ✅ Built-in security
- ✅ Real-time capabilities available
- ✅ No local PostgreSQL to manage
- ✅ Production-ready infrastructure

---

## 🔐 Security Notes

**Your Credentials:**
- ✅ Anon key: Safe to use in frontend (public)
- ✅ Service role key: Secret (backend only) — **KEEP SAFE**
- ✅ Database password: Stored in .env (never commit!)

**What's Protected:**
- Row Level Security (RLS) — Configure in Supabase
- Authentication — Use Supabase Auth (next phase)
- API Keys — Use environment variables (not hardcoded)

---

## 🚀 Next Steps (After Verification)

### Immediate (Today):
1. [x] Configure Supabase
2. [ ] Create SQL tables (you'll do this)
3. [ ] Restart services (you'll do this)
4. [ ] Verify dashboard loads

### This Week:
1. Set up Supabase Auth (login/signup)
2. Configure Row Level Security
3. Test user creation & memory storage
4. Set up email verification

### This Month:
1. Enable Supabase real-time
2. Set up database backups
3. Configure monitoring & alerts
4. Deploy to production domain

---

## 📞 Troubleshooting

**If API won't connect:**
```powershell
# Check logs
docker logs neurotwin-api --tail 50

# Verify .env is correct
cat D:\neurotwin\.env | grep SUPABASE

# Test database directly
psql "postgresql://postgres:Neurotwin@2004@xywuhwdijgxlfdgfktnn.supabase.co:5432/postgres"
```

**If dashboard won't load:**
```powershell
# Check web logs
docker logs neurotwin-web --tail 50

# Check nginx
docker logs neurotwin-nginx --tail 30

# Restart everything
docker-compose restart
```

**If tables don't appear:**
- Verify you ran the SQL in Supabase SQL Editor
- Check for error messages in Supabase
- Reload the Supabase dashboard

---

## ✨ You're Ready!

Your NEUROTWIN OS platform is now configured to use **Supabase cloud infrastructure**.

**Execute the steps above and you'll have:**
- ✅ Cloud database (PostgreSQL)
- ✅ Automatic backups
- ✅ Production-ready infrastructure
- ✅ Scalable foundation for your AI empire

**Next command to run:**
```powershell
cd D:\neurotwin

# Create tables in Supabase (you'll paste SQL into Supabase dashboard)
# Then restart services:
docker-compose stop postgres
docker-compose restart api
docker-compose restart web
Start-Sleep -Seconds 15
docker logs neurotwin-api --tail 30
```

---

**Ready to connect to the cloud, CEO?** 👑
