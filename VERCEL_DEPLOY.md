# Vercel Deployment Guide

## Quick Deploy

Run the deployment script:
```bash
cd /Users/eddy/IRPhotolink
./deploy.sh
```

Or manually:

### 1. Login to Vercel
```bash
vercel login
```

### 2. Link Project (first time only)
```bash
vercel link
```

### 3. Deploy
```bash
vercel --prod --yes
```

## Environment Variables Setup

After first deployment, go to **Vercel Dashboard** → Your Project → **Settings** → **Environment Variables** and add:

```
FRONTEND_ORIGIN=https://your-project.vercel.app
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
GOOGLE_REDIRECT_URI=https://your-project.vercel.app/auth/google/callback
MICROSOFT_CLIENT_ID=your_microsoft_client_id
MICROSOFT_CLIENT_SECRET=your_microsoft_client_secret
MICROSOFT_REDIRECT_URI=https://your-project.vercel.app/auth/microsoft/callback
```

**⚠️ CRITICAL**: After deployment, update OAuth redirect URIs:
- **Google Cloud Console**: Add `https://your-project.vercel.app/auth/google/callback`
- **Azure Portal**: Add `https://your-project.vercel.app/auth/microsoft/callback`

## Project Structure

- `api/index.py` - Vercel serverless function entry point
- `backend/` - FastAPI application code
- `frontend/` - Static HTML/JS files
- `vercel.json` - Vercel configuration
- `requirements.txt` - Python dependencies

## Important Notes

- Backend runs as serverless functions (may have cold starts)
- Environment variables must be set in Vercel dashboard
- OAuth redirect URIs must exactly match your Vercel domain
- For production, consider using Vercel's environment variable encryption
