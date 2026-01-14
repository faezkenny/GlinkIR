"""
Vercel serverless function entry point for FastAPI backend.
"""
from backend.main import app

# Vercel expects the app to be named 'app'
__all__ = ['app']
