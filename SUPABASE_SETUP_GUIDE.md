# NEUROTWIN OS × SUPABASE Integration Guide
## 🚀 Cloud-First AI Platform Setup

**Status:** Ready for Supabase Cloud Configuration  
**Date:** March 17, 2026  
**Project:** neurotwin-os  

---

## STEP 1: Get Your Database Password (2 minutes)

You have the API keys, but you also need the **Supabase database password**.

### Find it here:

1. Go to: https://supabase.com/dashboard
2. Select your **neurotwin-os** project
3. Click **"Settings"** (bottom left) → **"Database"**
4. Look for **"Connection string"** section
5. Find the password in the connection string or the **"Password"** field
6. Copy your database password

### Example connection string:
```
postgresql://postgres:[PASSWORD]@xywuhwdijgxlfdgfktnn.supabase.co:5432/postgres
```

Extract `[PASSWORD]` and use it in the next step.

---

## STEP 2: Update .env File with Database Password

Replace `YOUR_DB_PASSWORD` in the `.env.supabase` file:

```bash
# Old (with placeholder):
DATABASE_URL=postgresql://postgres:YOUR_DB_PASSWORD@xywuhwdijgxlfdgfktnn.supabase.co:5432/postgres

# New (with your actual password):
DATABASE_URL=postgresql://postgres:your_actual_password_here@xywuhwdijgxlfdgfktnn.supabase.co:5432/postgres
```

---

## STEP 3: Copy New Environment to Main .env

Once you have the password, copy this file:
```powershell
# Copy the Supabase config
Copy-Item D:\neurotwin\.env.supabase D:\neurotwin\.env -Force
```

---

## STEP 4: Create Supabase Tables

Run these SQL commands in Supabase SQL Editor:

### Go to:
1. https://supabase.com/dashboard
2. Select **neurotwin-os**
3. Click **"SQL Editor"** (left sidebar)
4. Click **"New Query"**
5. Paste the SQL from: `D:\neurotwin\supabase_migrations.sql`
6. Click **"Run"**

---

## STEP 5: Restart Services with Supabase

```powershell
cd D:\neurotwin

# Disable local PostgreSQL (it's now in the cloud!)
docker-compose stop postgres

# Restart API to use Supabase
docker-compose restart api

# Verify connection
docker logs neurotwin-api --tail 30
```

---

## What's Changing

| Component | Before (Local) | After (Supabase) |
|-----------|---|---|
| **Database** | Local PostgreSQL container | Supabase Cloud PostgreSQL |
| **Auth** | Local sessions | Supabase Auth (coming next) |
| **Storage** | N/A | Supabase Storage (optional) |
| **Real-time** | Not configured | Available via Supabase |

---

## Next Steps (After Supabase is Connected)

1. ✅ **Setup Supabase Auth** → Login/Signup pages
2. ✅ **Configure Supabase Storage** → File uploads
3. ✅ **Enable Row Level Security** → Data access control
4. ✅ **Set up Real-time subscriptions** → Live updates

---

## Quick Checklist

- [ ] Got Supabase project created ✅
- [ ] Copied API keys ✅
- [ ] Found database password (next step)
- [ ] Updated .env file (next step)
- [ ] Created Supabase tables (next step)
- [ ] Restarted services (next step)
- [ ] Verified connection (next step)

---

**Ready to connect to Supabase cloud, CEO?** 👑

Next: Find your database password and let me know.
