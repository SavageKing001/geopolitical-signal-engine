# Deployment Guide

## Railway.app (Recommended)

Railway is the fastest way to deploy — no config files needed, just push and go.

### Step 1 — Create account
Go to [railway.app](https://railway.app) and sign up with GitHub.

### Step 2 — Install Railway CLI
```bash
npm install -g @railway/cli
```

### Step 3 — Login
```bash
railway login
```

### Step 4 — Create new project
Run this from the project root:
```bash
railway init
```
Select "Empty project" when prompted.

### Step 5 — Add environment variable
In the Railway dashboard, go to your project → Variables → Add:
```
NEWSAPI_KEY=your_real_api_key_here
```

### Step 6 — Deploy
```bash
railway up
```

### Step 7 — Get your public URL
In the Railway dashboard → your service → Settings → Domains.
Railway assigns a public URL like `https://your-project.up.railway.app`.

---

## Render.com (Alternative)

Render is a good free-tier alternative with automatic GitHub deploys.

### Step 1 — Create account
Go to [render.com](https://render.com) and sign up.

### Step 2 — Connect GitHub repository
In the Render dashboard → New → Web Service → Connect your GitHub repo.

### Step 3 — Create new Web Service
Select the `geopolitical-signal-engine` repository.

### Step 4 — Set build command
```
pip install -r requirements.txt
```

### Step 5 — Set start command
```
python dashboard/app.py
```

### Step 6 — Add environment variable
In the service settings → Environment → Add environment variable:
```
NEWSAPI_KEY=your_real_api_key_here
```

### Step 7 — Deploy
Click **Create Web Service**. Render will build and deploy automatically.
On the free tier, the service spins down after inactivity — first request after idle takes ~30 seconds.

---

## Running with Docker locally

Build and run both services with one command:
```bash
docker-compose up --build
```

- Main dashboard: http://localhost:5000
- Vaibhav's command center: http://localhost:5001/vaibhav

Make sure your `.env` file has a real `NEWSAPI_KEY` before running.

---

## Environment variables reference

| Variable | Required | Description |
|---|---|---|
| `NEWSAPI_KEY` | Yes | API key from [newsapi.org](https://newsapi.org) |
