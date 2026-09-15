# Phase 7: Deployment Guide (Step by Step)

This guide assumes you have never used Neon, Render, or Vercel before. Every click is documented.

---

## Prerequisites

Before starting, make sure:
1. Your code is pushed to GitHub (you already have `BarotMeet05/simple-rag-fastapi`)
2. You have your **Gemini API key** (from your `.env` file — the `GEMINI_API_KEY` value)

---

## Part 0: Create a Free Cloud Database on Neon

### What is Neon?
During development, you ran PostgreSQL locally using Docker. But when your backend is hosted on Render, it can't access your laptop's Docker container. You need a cloud-hosted PostgreSQL database. Neon gives you one for free — with `pgvector` support built in (which we need for our vector search).

### Step-by-step

**Step 1 — Create a Neon account**
1. Go to [neon.tech](https://neon.tech)
2. Click **"Sign Up"** (top-right)
3. Sign up with your **GitHub account** (fastest option)

**Step 2 — Create a new project**
1. After logging in, you'll land on the Neon Console
2. Click **"New Project"**
3. Fill in:

| Field | Value |
|---|---|
| **Project name** | `documind` (or whatever you like) |
| **Postgres version** | Leave default (latest) |
| **Region** | Pick the one closest to you (e.g., `Asia Southeast` for India) |

4. Click **"Create Project"**

**Step 3 — Get your connection string**
1. After creating the project, Neon immediately shows you a **Connection Details** dialog
2. Make sure the dropdown at the top says **"Connection string"**
3. You'll see a URL like:
   ```
   postgresql://neondb_owner:abc123xyz@ep-cool-name-12345.ap-southeast-1.aws.neon.tech/neondb?sslmode=require
   ```
4. **Copy this URL** — you'll need it in the next steps

**Step 4 — Convert the URL for our app**
Our app uses `asyncpg` (async PostgreSQL driver), so the connection string needs a small tweak. Change the beginning from:
```
postgresql://neondb_owner:...
```
to:
```
postgresql+asyncpg://neondb_owner:...
```

Just add `+asyncpg` after `postgresql`. The rest stays the same.

Your final `DATABASE_URL` will look like:
```
postgresql+asyncpg://neondb_owner:abc123xyz@ep-cool-name-12345.ap-southeast-1.aws.neon.tech/neondb?sslmode=require
```

**Step 5 — Enable pgvector extension**
1. In the Neon Console, click on your project
2. Go to **"SQL Editor"** in the left sidebar
3. Run this SQL command:
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   ```
4. Click **"Run"** — you should see `CREATE EXTENSION` as the result

That's it! Your cloud database is ready. Save that `DATABASE_URL` — you'll paste it into Render in the next part.

> **Tip:** You can also update your local `.env` file with this Neon URL if you want your local dev to use the same database as production. Just replace the old `DATABASE_URL` value.

---

## Part 1: Deploy the Backend on Render

### What is Render?
Render is a cloud platform (like Heroku) that hosts web applications. Their free tier gives you a web service that runs your FastAPI backend. The catch: it "sleeps" after 15 minutes of no traffic, and the first request after sleep takes ~30-60 seconds.

### Step-by-step

**Step 1 — Create a Render account**
1. Go to [render.com](https://render.com)
2. Click **"Get Started for Free"**
3. Sign up with your **GitHub account** (this is the easiest way — it also lets Render access your repos)

**Step 2 — Create a new Web Service**
1. After logging in, you'll be on the Render Dashboard
2. Click the **"New +"** button in the top-right corner
3. Select **"Web Service"**

**Step 3 — Connect your GitHub repository**
1. Render will show a list of your GitHub repositories
2. Find `simple-rag-fastapi` and click **"Connect"**
3. If you don't see it, click **"Configure account"** to grant Render access to the repo

**Step 4 — Configure the service**
Fill in these fields:

| Field | Value |
|---|---|
| **Name** | `simple-rag-api` (or whatever you like) |
| **Region** | Pick the one closest to you (e.g., Oregon or Singapore) |
| **Branch** | `main` |
| **Root Directory** | Leave empty (the backend is at the root of the repo) |
| **Runtime** | `Python 3` |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| **Instance Type** | **Free** |

**Step 5 — Add environment variables**
Scroll down to the **"Environment Variables"** section and click **"Add Environment Variable"** for each of these:

| Key | Value |
|---|---|
| `DATABASE_URL` | Your Neon database URL (copy from your `.env` file). Keep it as `postgresql+asyncpg://...` since our code uses asyncpg. |
| `GEMINI_API_KEY` | Your Google Gemini API key |
| `ALLOWED_ORIGINS` | Put `*` for now (you'll update this after deploying the frontend) |
| `ENVIRONMENT` | `production` |
| `DEBUG` | `false` |

**Step 6 — Deploy**
1. Click **"Create Web Service"**
2. Render will start building your project. You'll see logs scrolling — it's installing Python packages and starting the server.
3. Wait 3-5 minutes for the first build.
4. When you see `Uvicorn running on http://0.0.0.0:XXXX`, it's live!

**Step 7 — Test the backend**
1. Render gives you a URL like `https://simple-rag-fastapi.onrender.com`
2. Open `https://simple-rag-fastapi.onrender.com/docs` in your browser
3. You should see the Swagger UI! Your backend is now live on the internet.

> Save this URL — you'll need it in Part 2 when configuring the frontend.

---

## Part 2: Deploy the Frontend on Vercel

### What is Vercel?
Vercel is the company that created Next.js. They host frontend applications for free with automatic deploys from GitHub. Every time you push code, Vercel rebuilds and deploys automatically.

### Step-by-step

**Step 1 — Create a Vercel account**
1. Go to [vercel.com](https://vercel.com)
2. Click **"Sign Up"**
3. Sign up with your **GitHub account**

**Step 2 — Import your project**
1. After logging in, click **"Add New..."** then **"Project"**
2. Vercel will show your GitHub repositories
3. Find `simple-rag-fastapi` and click **"Import"**

**Step 3 — Configure the project**
This is the critical part. Since your frontend is inside the `frontend/` folder (not the root), you need to tell Vercel:

| Field | Value |
|---|---|
| **Project Name** | `documind` (or whatever you like) |
| **Framework Preset** | `Vite` (Vercel auto-detects this) |
| **Root Directory** | Click **"Edit"** and type `frontend` then click **"Continue"** |
| **Build Command** | `npm run build` (should be auto-filled) |
| **Output Directory** | `dist` (should be auto-filled) |

**Step 4 — Add the environment variable**
Expand the **"Environment Variables"** section and add:

| Key | Value |
|---|---|
| `VITE_API_URL` | `https://simple-rag-fastapi.onrender.com` (your Render backend URL from Part 1) |

IMPORTANT: The variable MUST start with `VITE_` — Vite only exposes environment variables that start with this prefix to the frontend code. Without the `VITE_` prefix, the variable will be invisible to your app.

**Step 5 — Deploy**
1. Click **"Deploy"**
2. Vercel will build your frontend (takes about 30-60 seconds)
3. Once done, you'll see a celebration screen with your live URL!

**Step 6 — Test the frontend**
1. Vercel gives you a URL like `https://documind.vercel.app`
2. Open it in your browser
3. You should see the DocuMind UI!

---

## Part 3: Connect Them Together

Right now the frontend knows about the backend (VITE_API_URL). But the backend doesn't know about the frontend yet — it will block requests due to CORS.

**Step 1 — Update CORS on Render**
1. Go to your Render Dashboard at dashboard.render.com
2. Click on your `simple-rag-api` service
3. Go to the **"Environment"** tab on the left
4. Find `ALLOWED_ORIGINS` and update it to your Vercel URL:
   `https://documind.vercel.app`
   (Replace `documind` with whatever your actual Vercel URL is)
5. Click **"Save Changes"**
6. Render will automatically redeploy with the new setting

**Step 2 — Test end-to-end**
1. Open your Vercel URL
2. Upload a document — it should appear in the sidebar
3. Ask a question — the AI should respond

Note: The first request may take 30-60 seconds if Render's free tier has gone to sleep. After that, responses will be much faster.

---

## Troubleshooting

### "Failed to fetch" or CORS errors in browser console
- Double-check that `ALLOWED_ORIGINS` on Render exactly matches your Vercel URL (including `https://`)
- Make sure there are no trailing slashes

### Backend builds but crashes on start
- Check the Render logs (click on your service then Logs tab)
- Most likely cause: `DATABASE_URL` is wrong or Neon database is paused
- Go to Neon dashboard at console.neon.tech and make sure your project is active

### Frontend builds but shows blank page
- Check browser console (F12 then Console tab) for errors
- Most likely cause: `VITE_API_URL` is missing or wrong

### Upload works but chat gives errors
- Your Gemini API key may be invalid or rate-limited
- Check the Render logs for the exact error

---

## How Auto-Deploys Work

After this initial setup, deployment is automatic:

1. You make code changes locally
2. You run `git add .` then `git commit -m "my change"` then `git push`
3. **Render** detects the push and rebuilds the backend (~2-3 minutes)
4. **Vercel** detects the push and rebuilds the frontend (~30 seconds)

You never have to manually deploy again. This is called CI/CD (Continuous Integration / Continuous Deployment).

---

## Summary

| Component | Platform | URL Pattern | Cost |
|---|---|---|---|
| Frontend | Vercel | `https://documind.vercel.app` | Free |
| Backend | Render | `https://simple-rag-fastapi.onrender.com` | Free |
| Database | Neon | (connection string, no public URL) | Free |
| AI | Google Gemini | (API key, no public URL) | Free tier |
