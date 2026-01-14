"""
Vercel serverless function entry point for FastAPI backend.
"""
import sys
import os

# Add backend directory to path
backend_path = os.path.join(os.path.dirname(__file__), '..', 'backend')
sys.path.insert(0, backend_path)

from main import app

# Vercel expects the app to be named 'app'
__all__ = ['app']
