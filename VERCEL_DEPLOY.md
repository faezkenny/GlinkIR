# Vercel Deployment Guide

## Prerequisites

1. Install Vercel CLI:
```bash
npm i -g vercel
```

2. Login to Vercel:
```bash
vercel login
```

## Deployment Steps

### 1. Link to Vercel Project
```bash
cd /Users/eddy/IRPhotolink
vercel link
```

### 2. Set Environment Variables

In Vercel Dashboard → Project Settings → Environment Variables, add:

```
FRONTEND_ORIGIN=https://your-project.vercel.app
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
GOOGLE_REDIRECT_URI=https://your-project.vercel.app/auth/google/callback
MICROSOFT_CLIENT_ID=your_microsoft_client_id
MICROSOFT_CLIENT_SECRET=your_microsoft_client_secret
MICROSOFT_REDIRECT_URI=https://your-project.vercel.app/auth/microsoft/callback
```

**Important**: Update your OAuth app redirect URIs in Google Cloud Console and Azure Portal to match your Vercel URL!

### 3. Deploy
```bash
vercel --prod
```

## Project Structure for Vercel

- `api/` - Serverless functions (FastAPI backend)
- `frontend/` - Static files (HTML/JS)
- `vercel.json` - Vercel configuration

## Notes

- Backend runs as serverless functions
- Frontend is served as static files
- Environment variables are set in Vercel dashboard
- OAuth redirect URIs must match your Vercel domain
