#!/bin/bash
# Vercel deployment script for IRPhotolink

echo "🚀 IRPhotolink Vercel Deployment"
echo ""

# Check if vercel CLI is installed
if ! command -v vercel &> /dev/null; then
    echo "❌ Vercel CLI not found. Installing..."
    npm i -g vercel
fi

# Check if logged in
if ! vercel whoami &> /dev/null; then
    echo "🔐 Please login to Vercel:"
    vercel login
fi

# Link project (if not already linked)
if [ ! -f ".vercel/project.json" ]; then
    echo "📦 Linking to Vercel project..."
    vercel link
fi

# Deploy
echo "🌐 Deploying to Vercel..."
vercel --prod --yes

echo ""
echo "✅ Deployment complete!"
echo "📝 Don't forget to set environment variables in Vercel dashboard:"
echo "   - GOOGLE_CLIENT_ID"
echo "   - GOOGLE_CLIENT_SECRET"
echo "   - MICROSOFT_CLIENT_ID"
echo "   - MICROSOFT_CLIENT_SECRET"
echo "   - FRONTEND_ORIGIN (your Vercel URL)"
echo ""
echo "🔗 Update OAuth redirect URIs in Google Cloud Console and Azure Portal!"
