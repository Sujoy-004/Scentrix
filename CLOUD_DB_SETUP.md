# Cloud Database Setup Guide - ScentScape

This guide will get you connected to free-tier managed databases in 10 minutes.

---

## **Step 1: PostgreSQL via Neon** (2 minutes)

**Why Neon?** Free tier PostgreSQL with generous limits.

### Instructions:
1. Go to: https://neon.tech
2. Click **"Sign Up"** → Use GitHub OAuth or email
3. Create a new project called `scentscape`
4. Copy your connection string (looks like):
   ```
   postgresql://user:password@ep-xxxxx.us-east-1.neon.tech/scentscape?sslmode=require
   ```

**You'll need:** The full connection string

---

## **Step 2: Redis via Upstash** (2 minutes)

**Why Upstash?** Free serverless Redis with REST API support.

### Instructions:
1. Go to: https://upstash.com
2. Click **"Sign Up"** → Use GitHub OAuth or email
3. Create a new Redis database
4. In the dashboard, copy the connection URL (looks like):
   ```
   redis://default:password@us1-xxxxx.upstash.io:38xxx
   ```

**You'll need:** The full Redis URL

---

## **Step 3: Graph Database via Neo4j Aura** (2 minutes)

**Why Neo4j Aura?** Free managed graph database, perfect for fragrance knowledge graphs.

### Instructions:
1. Go to: https://neo4j.com/cloud/aura/
2. Click **"Sign Up"** → Use email (free community tier)
3. Create an instance called `scentscape`
4. Copy both:
   - **Bolt URI** (looks like): `neo4j+s://xxx.databases.neo4j.io`
   - **Password** (Neo4j generates one - save this!)

**You'll need:** The Bolt URI and password

---

## **Checklist:**

Once ready, you should have:

- [ ] Neon PostgreSQL connection string (postgresql://...)
- [ ] Upstash Redis URL (redis://...)
- [ ] Neo4j Bolt URI (neo4j+s://...)
- [ ] Neo4j password

**Give these to me, and I'll:**
1. Update your `.env` file
2. Start the backend
3. You'll see the full workflow: frontend → backend → databases

---

## **Connection String Examples**

```env
# PostgreSQL (Neon)
DATABASE_URL=postgresql://user:password@ep-xxxxx.us-east-1.neon.tech/db?sslmode=require

# Redis (Upstash)
REDIS_URL=redis://default:password@us1-xxxxx.upstash.io:38xxx

# Neo4j (Aura)
NEO4J_URI=neo4j+s://xxx.databases.neo4j.io
NEO4J_PASSWORD=your_password_here
```

---

## **Time Estimate:**
- Neon signup: 1 minute
- Upstash signup: 1 minute
- Neo4j Aura signup: 1 minute
- **Total: ~3-5 minutes**

Let me know once you have these credentials! 🚀
